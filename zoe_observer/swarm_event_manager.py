import logging

from zoe_observer.config import get_conf
from zoe_lib.containers import ZoeContainerAPI
from zoe_lib.exceptions import ZoeAPIException

log = logging.getLogger(__name__)


def main_callback(event):
    log.debug(event)
    if event['Type'] != 'container':
        return

    try:
        if event['Actor']['Attributes']['zoe.prefix'] != get_conf().container_name_prefix:
            return
    except KeyError:
        return

    if event['Action'] == "die":
        try:
            zoe_id = event['Actor']['Attributes']['zoe.container.id']
            zoe_id = int(zoe_id)
            container_died(zoe_id)
        except KeyError:
            return


def container_died(zoe_id: int):
    log.debug('A container died')
    # tell the master via the rest api
    cont_api = ZoeContainerAPI(get_conf().scheduler_url, 'zoeadmin', get_conf().zoeadmin_password)
    try:
        cont_api.died(zoe_id)
    except ZoeAPIException as e:
        if e.message != "No such container":
            log.exception('Error reporting a dead container')
