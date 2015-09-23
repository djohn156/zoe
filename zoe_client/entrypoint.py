from argparse import ArgumentParser, Namespace, FileType
import json
import logging
from zipfile import is_zipfile
from pprint import pprint

from zoe_client import ZoeClient
from common.configuration import init as conf_init, zoeconf
from zoe_client.state import create_tables, init as state_init

argparser = None
db_engine = None


def get_zoe_client(args) -> ZoeClient:
    return ZoeClient(args.ipc_server, args.ipc_port)


def stats_cmd(args):
    client = get_zoe_client(args)
    stats = client.platform_stats()
    pprint(stats)


def user_new_cmd(args):
    client = get_zoe_client(args)
    user = client.user_new(args.email)
    print("New user ID: {}".format(user.id))


def user_get_cmd(args):
    client = get_zoe_client(args)
    user = client.user_get_by_email(args.email)
    print("User ID: {}".format(user.id))


def app_new_cmd(args):
    client = get_zoe_client(args)
    app_descr = json.load(args.jsonfile)
    application_id = client.application_new(args.user_id, app_descr)
    print("Application added with ID: {}".format(application_id))


def app_bin_put_cmd(args):
    client = get_zoe_client(args)
    if not is_zipfile(args.zipfile):
        print("Error: application binary must be a zip file")
        return
    args.zipfile.rewind()
    zipdata = args.zipfile.read()
    client.application_binary_put(args.app_id, zipdata)


def app_start_cmd(args):
    client = get_zoe_client(args)
    ret = client.application_start(args.id)
    if ret:
        print("Application scheduled successfully, use the app-inspect command to check its status")
    else:
        print("Admission control refused to run the application specified")


def app_rm_cmd(args):
    client = get_zoe_client(args)
    client.application_remove(args.id, args.force)


def app_inspect_cmd(args):
    client = get_zoe_client(args)
    application = client.application_get(args.id)
    if application is None:
        print("Error: application {} does not exist".format(args.id))
        return
    print(application)


def app_list_cmd(args):
    client = get_zoe_client(args)
    applications = client.application_list(args.id)
    if len(applications) > 0:
        print("{:4} {:20} {:25}".format("ID", "Name", "Type"))
    for app in applications:
        print("{:4} {:20} {:25}".format(app.id, app.name, app.type))


def exec_kill_cmd(args):
    client = get_zoe_client(args)
    execution = client.execution_get(args.id)
    if execution is None:
        print("Error: execution {} does not exist".format(args.id))
        return
    client.execution_terminate(execution.id)


def log_get_cmd(args):
    client = get_zoe_client(args)
    log = client.log_get(args.id)
    if log is None:
        print("Error: No log found for container ID {}".format(args.id))
    print(log)


def gen_config_cmd(args):
    zoeconf().write(open(args.output_file, "w"))


def container_stats_cmd(args):
    client = get_zoe_client(args)
    stats = client.container_stats(args.container_id)
    print(stats)


def process_arguments() -> Namespace:
    global argparser
    argparser = ArgumentParser(description="Zoe - Container Analytics as a Service command-line client")
    argparser.add_argument('-d', '--debug', action='store_true', default=False, help='Enable debug output')
    argparser.add_argument('--ipc-server', default='localhost', help='Address of the Zoe scheduler process')
    argparser.add_argument('--ipc-port', default=8723, type=int, help='Port of the Zoe scheduler process')
    subparser = argparser.add_subparsers(title='subcommands', description='valid subcommands')

    argparser_stats = subparser.add_parser('stats', help="Show the platform statistics")
    argparser_stats.set_defaults(func=stats_cmd)

    argparser_user_new = subparser.add_parser('user-new', help="Create a new user")
    argparser_user_new.add_argument('email', help="User email address")
    argparser_user_new.set_defaults(func=user_new_cmd)

    argparser_user_get = subparser.add_parser('user-get', help="Get the user id for an existing user")
    argparser_user_get.add_argument('email', help="User email address")
    argparser_user_get.set_defaults(func=user_get_cmd)

    argparser_app_new = subparser.add_parser('app-new', help="Upload a JSON application description")
    argparser_app_new.add_argument('--user-id', type=int, required=True, help='Application owner')
    argparser_app_new.add_argument('jsonfile', type=FileType("r"), help='Application description')
    argparser_app_new.set_defaults(func=app_new_cmd)

    argparser_app_binary_put = subparser.add_parser('app-binary-put', help="Upload an application binary")
    argparser_app_binary_put.add_argument('--app-id', type=int, required=True, help='Application ID')
    argparser_app_binary_put.add_argument('zipfile', type=FileType("rb"), help='Application zip file')
    argparser_app_binary_put.set_defaults(func=app_bin_put_cmd)

    argparser_app_rm = subparser.add_parser('app-rm', help="Delete an application")
    argparser_app_rm.add_argument('id', type=int, help="Application id")
    argparser_app_rm.add_argument('-f', '--force', action="store_true", help="Kill also all active executions, if any")
    argparser_app_rm.set_defaults(func=app_rm_cmd)

    argparser_app_inspect = subparser.add_parser('app-inspect', help="Gather details about an application and its active executions")
    argparser_app_inspect.add_argument('id', type=int, help="Application id")
    argparser_app_inspect.set_defaults(func=app_inspect_cmd)

    argparser_app_inspect = subparser.add_parser('app-ls', help="List all applications for a user")
    argparser_app_inspect.add_argument('id', type=int, help="User id")
    argparser_app_inspect.set_defaults(func=app_list_cmd)

    argparser_app_run = subparser.add_parser('start', help="Start a previously registered application")
    argparser_app_run.add_argument('id', type=int, help="Application id")
    argparser_app_run.set_defaults(func=app_start_cmd)

    argparser_execution_kill = subparser.add_parser('terminate', help="Terminates an execution")
    argparser_execution_kill.add_argument('id', type=int, help="Execution id")
    argparser_execution_kill.set_defaults(func=exec_kill_cmd)

    argparser_log_get = subparser.add_parser('log-get', help="Retrieves the logs of a running container")
    argparser_log_get.add_argument('id', type=int, help="Container id")
    argparser_log_get.set_defaults(func=log_get_cmd)

    argparser_log_get = subparser.add_parser('write-config', help="Generates a sample file containing current configuration values")
    argparser_log_get.add_argument('output_file', help="Filename to create with default configuration")
    argparser_log_get.set_defaults(func=gen_config_cmd)

    argparser_container_stats = subparser.add_parser('container-stats', help="Retrieve statistics on a running container")
    argparser_container_stats.add_argument('container_id', help="ID of the container")
    argparser_container_stats.set_defaults(func=container_stats_cmd)

    return argparser.parse_args()


def zoe():
    args = process_arguments()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    conf_init()
    state_init(zoeconf().db_url)

#    try:
    args.func(args)
#    except AttributeError:
#        argparser.print_help()
#        return