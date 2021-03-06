"""Classes to hold the system state and simulated container/service placements"""

import logging

from zoe_lib.state import Execution, Service
from zoe_master.stats import ClusterStats, NodeStats
from zoe_master.backends.interface import list_available_images


log = logging.getLogger(__name__)


class SimulatedNode:
    """A simulated node where containers can be run"""
    def __init__(self, real_node: NodeStats):
        self.real_reservations = {
            "memory": real_node.memory_reserved,
            "cores": real_node.cores_reserved
        }
        self.real_free_resources = {
            "memory": real_node.memory_total - real_node.memory_reserved,
            "cores": real_node.cores_total - real_node.cores_reserved
        }
        self.real_active_containers = real_node.container_count
        self.services = []
        self.name = real_node.name
        self.labels = real_node.labels
        self.images = list_available_images(self.name)

    def service_fits(self, service: Service) -> bool:
        """Checks whether a service can fit in this node"""
        ret = set(service.labels).issubset(self.labels)
        ret = ret and service.resource_reservation.memory.min < self.node_free_memory()
        ret = ret and service.resource_reservation.cores.min <= self.node_free_cores()
        ret = ret and self._image_is_available(service.image_name)
        return ret

    def service_why_unfit(self, service) -> str:
        """Generate an explanation of why the service does not fit this node."""
        if service.resource_reservation.memory.min >= self.node_free_memory():
            return 'needs {} bytes of memory'.format(self.node_free_memory() - service.resource_reservation.memory.min)
        elif service.resource_reservation.cores.min > self.node_free_cores():
            return 'needs {} more cores'.format(self.node_free_cores() - service.resource_reservation.cores.min)
        elif not set(service.labels).issubset(self.labels):
            return 'service required labels {} to be defined on the node'.format(service.labels)
        elif not self._image_is_available(service.image_name):
            return 'image {} is not available on this node'.format(service.image_name)

    def _image_is_available(self, image_name) -> bool:
        for image in self.images:
            if image_name in image['names']:
                return True
        return False

    def service_add(self, service):
        """Add a service in this node."""
        if self.service_fits(service):
            self.services.append(service)
            return True
        else:
            return False

    def service_remove(self, service):
        """Add a service in this node."""
        try:
            self.services.remove(service)
        except ValueError:
            return False
        else:
            return True

    @property
    def container_count(self):
        """Return the number of containers on this node"""
        return self.real_active_containers + len(self.services)

    def node_free_memory(self):
        """Return the amount of free memory for this node"""
        simulated_reservation = 0
        for service in self.services:  # type: Service
            simulated_reservation += service.resource_reservation.memory.min
        free = self.real_free_resources['memory'] - simulated_reservation
        if free < 0:
            log.warning('More memory reserved than there is free on node {}: {}'.format(self.name, free))
        return free

    def node_free_cores(self):
        """Return the amount of free cores available in this node."""
        simulated_reservation = 0
        for service in self.services:  # type: Service
            simulated_reservation += service.resource_reservation.cores.min
        free = self.real_free_resources['cores'] - simulated_reservation
        if free < 0:
            log.warning('More cores reserved than there are free on node {}: {}'.format(self.name, free))
        return free

    def __repr__(self):
        out = 'SN {} | m {} | c {}'.format(self.name, self.node_free_memory(), self.node_free_cores())
        return out


class SimulatedPlatform:
    """A simulated cluster, composed by simulated nodes"""
    def __init__(self, platform_status: ClusterStats):
        self.nodes = {}
        for node in platform_status.nodes:
            if node.status == 'online':
                self.nodes[node.name] = SimulatedNode(node)

    def allocate_essential(self, execution: Execution) -> bool:
        """Try to find an allocation for essential services"""
        for service in execution.essential_services:
            candidate_nodes = []
            for node_id_, node in self.nodes.items():
                if node.service_fits(service):
                    candidate_nodes.append(node)
                else:
                    log.debug('Cannot fit essential service {} on node {}: {}'.format(service.id, node.name, node.service_why_unfit(service)))
            if len(candidate_nodes) == 0:  # this service does not fit anywhere
                self.deallocate_essential(execution)
                log.info('Cannot fit essential service {} anywhere, bailing out'.format(service.id))
                return False
            candidate_nodes.sort(key=lambda n: n.container_count)  # smallest first
            candidate_nodes[0].service_add(service)
        return True

    def deallocate_essential(self, execution: Execution):
        """Remove all essential services from the simulated cluster"""
        for service in execution.essential_services:
            for node_id_, node in self.nodes.items():
                if node.service_remove(service):
                    break

    def allocate_elastic(self, execution: Execution) -> bool:
        """Try to find an allocation for elastic services"""
        at_least_one_allocated = False
        for service in execution.elastic_services:
            if service.status == service.ACTIVE_STATUS and service.backend_status != service.BACKEND_DIE_STATUS:
                continue
            candidate_nodes = []
            for node_id_, node in self.nodes.items():
                if node.service_fits(service):
                    candidate_nodes.append(node)
                else:
                    log.debug('Cannot fit elastic service {} on node {}: {}'.format(service.id, node.name, node.service_why_unfit(service)))
            if len(candidate_nodes) == 0:  # this service does not fit anywhere
                log.info('Cannot fit elastic service {} anywhere'.format(service.id))
                continue
            candidate_nodes.sort(key=lambda n: n.container_count)  # smallest first
            candidate_nodes[0].service_add(service)
            service.set_runnable()
            at_least_one_allocated = True
        return at_least_one_allocated

    def deallocate_elastic(self, execution: Execution):
        """Remove all elastic services from the simulated cluster"""
        for service in execution.elastic_services:
            for node_id_, node in self.nodes.items():
                if node.service_remove(service):
                    service.set_inactive()
                    break

    def aggregated_free_memory(self):
        """Return the amount of free memory across all nodes"""
        total = 0
        for node_id_, node in self.nodes.items():
            total += node.node_free_memory()
        return total

    def get_service_allocation(self):
        """Return a map of service IDs to nodes where they have been allocated."""
        placements = {}
        for node_id, node in self.nodes.items():
            for service in node.services:
                placements[service.id] = node_id
        return placements

    def __repr__(self):
        out = ''
        for node_id_, node in self.nodes.items():
            out += str(node) + " # "
        return out
