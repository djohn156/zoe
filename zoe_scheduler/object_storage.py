import http.server
from io import BytesIO
import logging
import os
import socketserver
import threading
import zipfile

from zoe_scheduler.state.application import ApplicationState
from zoe_scheduler.state.execution import ExecutionState
from common.configuration import zoeconf

log = logging.getLogger(__name__)


def init_history_paths() -> bool:
    if not os.path.exists(zoeconf().history_path):
        try:
            os.makedirs(zoeconf().history_path)
        except OSError:
            log.error("Cannot create history directory in {}".format(zoeconf().history_path))
            return False
        os.makedirs(os.path.join(zoeconf().history_path, 'apps'))
        os.makedirs(os.path.join(zoeconf().history_path, 'logs'))
    return True


def application_data_upload(application: ApplicationState, data: bytes) -> bool:
    fpath = os.path.join(zoeconf().history_path, 'apps', 'app-{}.zip'.format(application.id))
    open(fpath, "wb").write(data)


def application_data_download(application: ApplicationState) -> bytes:
    fpath = os.path.join(zoeconf().history_path, 'apps', 'app-{}.zip'.format(application.id))
    data = open(fpath, "rb").read()
    return data


def application_data_delete(application: ApplicationState):
    fpath = os.path.join(zoeconf().history_path, 'apps', 'app-{}.zip'.format(application.id))
    try:
        os.unlink(fpath)
    except OSError:
        log.warning("Binary data for application {} not found, cannot delete".format(application.id))


def logs_archive_create(execution: ExecutionState, logs: list):
    zipdata = BytesIO()
    with zipfile.ZipFile(zipdata, "w", compression=zipfile.ZIP_DEFLATED) as logzip:
        for c in logs:
            fname = c[0] + "-" + c[1] + ".txt"
            logzip.writestr(fname, c[2])
        logs_archive_upload(execution, zipdata.getvalue())


def logs_archive_upload(execution: ExecutionState, data: bytes) -> bool:
    fpath = os.path.join(zoeconf().history_path, 'logs', 'log-{}.zip'.format(execution.id))
    open(fpath, "wb").write(data)


def logs_archive_download(execution: ExecutionState) -> bytes:
    fpath = os.path.join(zoeconf().history_path, 'logs', 'log-{}.zip'.format(execution.id))
    data = open(fpath, "rb").read()
    return data


def logs_archive_delete(execution: ExecutionState):
    fpath = os.path.join(zoeconf().history_path, 'logs', 'log-{}.zip'.format(execution.id))
    try:
        os.unlink(fpath)
    except OSError:
        log.warning("Logs archive for execution {} not found, cannot delete".format(execution.id))


def generate_application_binary_url(application: ApplicationState) -> str:
    return 'http://' + zoeconf().scheduler_internal_hostname + '/apps/{}'.format(application.id)


def object_server(terminate: threading.Event, started: threading.Semaphore):
    log.info("Object server started")
    os.chdir(zoeconf().history_path)
    httpd = socketserver.TCPServer(("", zoeconf().scheduler_internal_server_port), http.server.SimpleHTTPRequestHandler)
    httpd.timeout = 1
    started.release()
    while not terminate.wait(0):
        httpd.handle_request()
        httpd.service_actions()
    log.info("Object server terminated")