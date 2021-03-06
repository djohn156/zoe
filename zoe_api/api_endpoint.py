# Copyright (c) 2016, Daniele Venzano
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The real API, exposed as web pages or REST API."""

import logging
import os

import zoe_api.exceptions
import zoe_api.master_api
import zoe_lib.applications
import zoe_lib.exceptions
import zoe_lib.state
from zoe_lib.config import get_conf

log = logging.getLogger(__name__)

GUEST_QUOTA_MAX_EXECUTIONS = 1


class APIEndpoint:
    """
    The APIEndpoint class.

    :type master: zoe_api.master_api.APIManager
    :type sql: zoe_lib.sql_manager.SQLManager
    """
    def __init__(self, master_api, sql_manager: zoe_lib.state.SQLManager):
        self.master = master_api
        self.sql = sql_manager

    def execution_by_id(self, uid, role, execution_id) -> zoe_lib.state.Execution:
        """Lookup an execution by its ID."""
        e = self.sql.executions.select(id=execution_id, only_one=True)
        if e is None:
            raise zoe_api.exceptions.ZoeNotFoundException('No such execution')
        assert isinstance(e, zoe_lib.state.Execution)
        if e.user_id != uid and role != 'admin':
            raise zoe_api.exceptions.ZoeAuthException()
        return e

    def execution_list(self, uid, role, **filters):
        """Generate a optionally filtered list of executions."""
        execs = self.sql.executions.select(**filters)
        ret = [e for e in execs if e.user_id == uid or role == 'admin']
        return ret

    def zapp_validate(self, application_description):
        """Validates the passed ZApp description against the supported schema."""
        try:
            zoe_lib.applications.app_validate(application_description)
        except zoe_lib.exceptions.InvalidApplicationDescription as e:
            raise zoe_api.exceptions.ZoeException('Invalid application description: ' + e.message)

    def execution_start(self, uid, role, exec_name, application_description):  # pylint: disable=unused-argument
        """Start an execution."""
        try:
            zoe_lib.applications.app_validate(application_description)
        except zoe_lib.exceptions.InvalidApplicationDescription as e:
            raise zoe_api.exceptions.ZoeException('Invalid application description: ' + e.message)

        # quota check
        if role == "guest":
            running_execs = self.execution_list(uid, role, **{'status': 'running'})
            running_execs += self.execution_list(uid, role, **{'status': 'starting'})
            running_execs += self.execution_list(uid, role, **{'status': 'scheduled'})
            running_execs += self.execution_list(uid, role, **{'status': 'image download'})
            running_execs += self.execution_list(uid, role, **{'status': 'submitted'})
            if len(running_execs) >= GUEST_QUOTA_MAX_EXECUTIONS:
                raise zoe_api.exceptions.ZoeException('Guest users cannot run more than one execution at a time, quota exceeded.')

        new_id = self.sql.executions.insert(exec_name, uid, application_description)
        success, message = self.master.execution_start(new_id)
        if not success:
            raise zoe_api.exceptions.ZoeException('The Zoe master is unavailable, execution will be submitted automatically when the master is back up ({}).'.format(message))

        return new_id

    def execution_terminate(self, uid, role, exec_id):
        """Terminate an execution."""
        e = self.sql.executions.select(id=exec_id, only_one=True)
        assert isinstance(e, zoe_lib.state.Execution)
        if e is None:
            raise zoe_api.exceptions.ZoeNotFoundException('No such execution')

        if e.user_id != uid and role != 'admin':
            raise zoe_api.exceptions.ZoeAuthException()

        if e.is_active:
            return self.master.execution_terminate(exec_id)
        else:
            raise zoe_api.exceptions.ZoeException('Execution is not running')

    def execution_delete(self, uid, role, exec_id):
        """Delete an execution."""
        if role != "admin":
            raise zoe_api.exceptions.ZoeAuthException()

        e = self.sql.executions.select(id=exec_id, only_one=True)
        assert isinstance(e, zoe_lib.state.Execution)
        if e is None:
            raise zoe_api.exceptions.ZoeNotFoundException('No such execution')

        if e.user_id != uid and role != 'admin':
            raise zoe_api.exceptions.ZoeAuthException()

        if e.is_active:
            raise zoe_api.exceptions.ZoeException('Cannot delete an active execution')

        status, message = self.master.execution_delete(exec_id)
        if status:
            self.sql.executions.delete(exec_id)
            return True, ''
        else:
            raise zoe_api.exceptions.ZoeException(message)

    def service_by_id(self, uid, role, service_id) -> zoe_lib.state.Service:
        """Lookup a service by its ID."""
        service = self.sql.services.select(id=service_id, only_one=True)
        if service is None:
            raise zoe_api.exceptions.ZoeNotFoundException('No such execution')
        if service.user_id != uid and role != 'admin':
            raise zoe_api.exceptions.ZoeAuthException()
        return service

    def service_list(self, uid, role, **filters):
        """Generate a optionally filtered list of services."""
        services = self.sql.services.select(**filters)
        ret = [s for s in services if s.user_id == uid or role == 'admin']
        return ret

    def service_logs(self, uid, role, service_id):
        """Retrieve the logs for the given service.
        If stream is True, a file object is returned, otherwise the log contents as a str object.
        """
        service = self.sql.services.select(id=service_id, only_one=True)
        if service is None:
            raise zoe_api.exceptions.ZoeNotFoundException('No such service')
        if service.user_id != uid and role != 'admin':
            raise zoe_api.exceptions.ZoeAuthException()

        path = os.path.join(get_conf().service_logs_base_path, get_conf().deployment_name, str(service.execution_id), service.name + '.txt')
        if not os.path.exists(path):
            raise zoe_api.exceptions.ZoeNotFoundException('Service log not available')
        return open(path, encoding='utf-8')

    def statistics_scheduler(self, uid_, role_):
        """Retrieve statistics about the scheduler."""
        success, message = self.master.scheduler_statistics()
        if success:
            for node in message['platform_stats']['nodes']:  # JSON does not like hash keys to be integers, so we need to convert manually
                for str_service_id in list(node['service_stats'].keys()):
                    node['service_stats'][int(str_service_id)] = node['service_stats'][str_service_id]
                    del node['service_stats'][str_service_id]
            return message
        else:
            raise zoe_api.exceptions.ZoeException(message=message)

    def execution_endpoints(self, uid: str, role: str, execution: zoe_lib.state.Execution):
        """Return a list of the services and public endpoints available for a certain execution."""
        services_info = []
        endpoints = []
        for service in execution.services:
            services_info.append(self.service_by_id(uid, role, service.id))
            for port in service.description['ports']:
                port_key = str(port['port_number']) + "/" + port['protocol']
                backend_port = self.sql.ports.select(only_one=True, service_id=service.id, internal_name=port_key)
                if backend_port is not None and backend_port.external_ip is not None:
                    endpoint = port['url_template'].format(**{"ip_port": backend_port.external_ip + ":" + str(backend_port.external_port)})
                    endpoints.append((port['name'], endpoint))

        return services_info, endpoints
