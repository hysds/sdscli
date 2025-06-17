"""
SDSKit command line interface.
"""


from sdscli.log_utils import logger
from sdscli.func_utils import get_module, get_func
import sdscli
from importlib import import_module
import logging
import argparse
import traceback
import yaml
import json
import importlib
import sys
import os
from future import standard_library
standard_library.install_aliases()


def get_adapter_func(sds_type, mod_name, func_name):
    """Import adapter function."""

    adapter_mod = f'sdscli.adapters.{sds_type}.{mod_name}'
    try:
        return get_func(adapter_mod, func_name)
    except ImportError:
        logger.error('Failed to import adapter module "{}" for SDS type "{}".'.format(
            mod_name, sds_type))
        logger.error('Not implemented yet. Mahalo for trying. ;)')
        sys.exit(1)
    except AttributeError:
        logger.error('Failed to get function "{}" from adapter module "{}".'.format(
            func_name, adapter_mod))
        logger.error('Not implemented yet. Mahalo for trying. ;)')
        sys.exit(1)


def kibana(args):
    """Update SDS components."""
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)

    func = get_adapter_func(sds_type, 'update', 'kibana')
    logger.debug("func: %s" % func)
    func(args.job_type, args.debug, args.force)


def configure(args):
    """Configure SDS config file."""

    logger.debug("got to configure(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'configure', 'configure')
    logger.debug("func: %s" % func)
    func()


def update(args):
    """Update SDS components."""

    logger.debug("got to update(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'update', 'update')
    logger.debug("func: %s" % func)
    func(args.component, args.debug, args.force, args.ndeps, args.config_only)


def ship(args):
    """Ship verdi code/config bundle."""

    logger.debug("got to ship(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'update', 'ship')
    logger.debug("func: %s" % func)
    func(args.encrypt, args.debug)


def start_tps(args):
    """Start TPS on SDS components."""

    logger.debug("got to start_tps(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'start_tps', 'start')
    logger.debug("func: %s" % func)
    func(args.component, args.debug, args.force)


def stop_tps(args):
    """Stop TPS on SDS components."""

    logger.debug("got to stop_tps(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'stop_tps', 'stop')
    logger.debug("func: %s" % func)
    func(args.component, args.debug, args.force)


def start(args):
    """Start SDS components."""

    logger.debug("got to start(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'start', 'start')
    logger.debug("func: %s" % func)
    func(args.component, args.debug, args.force)


def stop(args):
    """Stop SDS components."""

    logger.debug("got to stop(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'stop', 'stop')
    logger.debug("func: %s" % func)
    func(args.component, args.debug, args.force)


def reset(args):
    """Reset SDS components."""

    logger.debug("got to reset(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'reset', 'reset')
    logger.debug("func: %s" % func)
    func(args.component, args.debug, args.force)


def status(args):
    """SDS component status."""

    logger.debug("got to status(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'status', 'status')
    logger.debug("func: %s" % func)
    func(args.component, args.debug)


def ci(args):
    """Continuous integration functions."""

    logger.debug("got to ci(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'ci', args.subparser)
    logger.debug("func: %s" % func)
    func(args)


def pkg(args):
    """SDS package managment functions."""

    logger.debug("got to pkg(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(
        sds_type, 'pkg', 'import_pkg' if args.subparser == 'import' else args.subparser)
    logger.debug("func: %s" % func)
    func(args)


def cloud(args):
    """SDS cloud managment functions."""

    logger.debug("got to cloud(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'cloud', args.subparser)
    logger.debug("func: %s" % func)
    func(args)


def rules(args):
    """SDS user rules managment functions."""

    logger.debug("got to pkg(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(
        sds_type, 'rules', 'import_rules' if args.subparser == 'import' else args.subparser)
    logger.debug("func: %s" % func)
    func(args)


def job_list(args):
    """Configure SDS config file."""

    logger.debug("got to job_list(): %s" % args)


def orch(args):
    """SDS container orchestration functions."""

    logger.debug("got to orch(): %s" % args)
    sds_type = args.type
    logger.debug("sds_type: %s" % sds_type)
    func = get_adapter_func(sds_type, 'orch', args.subparser)
    logger.debug("func: %s" % func)
    if args.subparser == 'logs':
        func(args.component, args.debug, args.follow)
    elif args.subparser == 'start':
        func(args.component, args.release, args.debug, args.force)
    elif args.subparser == 'ps':
        func(args.component, args.debug)
    elif args.subparser == 'run':
        func(args.component, " ".join(args.cmd))
    else:
        func(args.component, args.debug, args.force)


def dispatch(args):
    """Dispatch to appropriate function."""

    # turn on debugging
    if args.debug:
        logger.setLevel(logging.DEBUG)

    logger.debug("args: %s" % args)

    if args.func:
        return args.func(args)
    else:
        logger.error("No func specified for args %s" % args)
        return 1


def main():
    """Process command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debug', '-d', action='store_true',
                        help="turn on debugging")
    subparsers = parser.add_subparsers(help='Functions')

    # parser for configure
    parser_configure = subparsers.add_parser(
        'configure', help="configure SDS config file")
    parser_configure.add_argument('type', default='hysds', const='hysds', nargs='?',
                                  choices=['hysds', 'sdskit'])
    parser_configure.set_defaults(func=configure)

    # parser for update
    parser_update = subparsers.add_parser(
        'update', help="update SDS components")
    parser_update.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                               choices=['hysds', 'sdskit'])
    parser_update.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                     'factotum', 'ci', 'verdi', 'all'])
    parser_update.add_argument('--force', '-f', action='store_true',
                               help="force update without user confirmation")
    parser_update.add_argument('--ndeps', '-n', action='store_true',
                               help="skip the external accesses for dependencies")
    parser_update.add_argument('--config-only', '-c', action='store_true',
                               help="update configuration files only")
    parser_update.set_defaults(func=update)

    # parser for kibana
    parser_kibana = subparsers.add_parser(
        'kibana', help="update SDS components")
    parser_kibana.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                               choices=['hysds', 'sdskit'])
    parser_kibana.add_argument('--force', '-f', action='store_true',
                               help="force update without user confirmation")

    parser_kibana.add_argument(
        'job_type', choices=['import', 'export', 'delete'])
    parser_kibana.set_defaults(func=kibana)

    # parser for ship
    parser_ship = subparsers.add_parser(
        'ship', help="ship verdi code/config bundle")
    parser_ship.add_argument('type', default='hysds', const='hysds', nargs='?',
                             choices=['hysds', 'sdskit'])
    parser_ship.add_argument('--encrypt', '-e', action='store_true',
                             help="encrypt code/config bundle")
    parser_ship.set_defaults(func=ship)

    # parser for start_tps
    parser_start_tps = subparsers.add_parser(
        'start_tps', help="start TPS on SDS components")
    parser_start_tps.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                                  choices=['hysds', 'sdskit'])
    parser_start_tps.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                        'ci', 'all'])
    parser_start_tps.add_argument('--force', '-f', action='store_true',
                                  help="force start without user confirmation")
    parser_start_tps.set_defaults(func=start_tps)

    # parser for stop_tps
    parser_stop_tps = subparsers.add_parser(
        'stop_tps', help="stop TPS on SDS components")
    parser_stop_tps.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                                 choices=['hysds', 'sdskit'])
    parser_stop_tps.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                       'ci', 'all'])
    parser_stop_tps.add_argument('--force', '-f', action='store_true',
                                 help="force stop without user confirmation")
    parser_stop_tps.set_defaults(func=stop_tps)

    # parser for start
    parser_start = subparsers.add_parser('start', help="start SDS components")
    parser_start.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                              choices=['hysds', 'sdskit'])
    parser_start.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                    'factotum', 'all'])
    parser_start.add_argument('--force', '-f', action='store_true',
                              help="force start without user confirmation")
    parser_start.set_defaults(func=start)

    # parser for stop
    parser_stop = subparsers.add_parser('stop', help="stop SDS components")
    parser_stop.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                             choices=['hysds', 'sdskit'])
    parser_stop.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                   'factotum', 'all'])
    parser_stop.add_argument('--force', '-f', action='store_true',
                             help="force stop without user confirmation")
    parser_stop.set_defaults(func=stop)

    # parser for reset
    parser_reset = subparsers.add_parser('reset', help="reset SDS components")
    parser_reset.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                              choices=['hysds', 'sdskit'])
    parser_reset.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                    'factotum', 'all'])
    parser_reset.add_argument('--force', '-f', action='store_true',
                              help="force reset without user confirmation")
    parser_reset.set_defaults(func=reset)

    # parser for status
    parser_status = subparsers.add_parser(
        'status', help="status of SDS components")
    parser_status.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                               choices=['hysds', 'sdskit'])
    parser_status.add_argument('component', default='all', const='all', nargs='?',
                               choices=['mozart', 'grq', 'metrics', 'factotum', 'ci', 'verdi', 'all'])
    parser_status.set_defaults(func=status)

    # parser for ci
    parser_ci = subparsers.add_parser(
        'ci', help="configure continuous integration for SDS cluster")
    parser_ci.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                           choices=['hysds', 'sdskit'])
    parser_ci_subparsers = parser_ci.add_subparsers(
        dest='subparser', required=True,
        help='Continuous integration functions')
    parser_ci_add_job = parser_ci_subparsers.add_parser(
        'add_job', help="add Jenkins job")
    parser_ci_add_job.add_argument('repo', help='git repository url')
    parser_ci_add_job.add_argument('storage', choices=['s3', 's3s', 'gs', 'dav', 'davs'],
                                   help='image storage type')
    parser_ci_add_job.add_argument('--branch', '-b', default=None,
                                   help="register git branch instead of release")
    parser_ci_add_job.add_argument(
        '--token', '-k', action='store_true', help="use configured OAuth token")
    parser_ci_remove_job = parser_ci_subparsers.add_parser(
        'remove_job', help="remove Jenkins job")
    parser_ci_remove_job.add_argument('repo', help='git repository url')
    parser_ci_remove_job.add_argument('--branch', '-b', default=None,
                                      help="git branch instead of release")
    parser_ci_build_job = parser_ci_subparsers.add_parser(
        'build_job', help="build Jenkins job")
    parser_ci_build_job.add_argument('repo', help='git repository url')
    parser_ci_build_job.add_argument('--branch', '-b', default=None,
                                     help="git branch instead of release")
    parser_ci.set_defaults(func=ci)

    # parser for pkg
    parser_pkg = subparsers.add_parser('pkg', help="SDS package management")
    parser_pkg.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                            choices=['hysds', 'sdskit'])
    parser_pkg_subparsers = parser_pkg.add_subparsers(
        dest='subparser', required=True,
        help='SDS package management functions')
    parser_pkg_ls = parser_pkg_subparsers.add_parser(
        'ls', help="list SDS package ids")
    parser_pkg_export = parser_pkg_subparsers.add_parser(
        'export', help="export SDS package")
    parser_pkg_export.add_argument('id', help='SDS package id to export')
    parser_pkg_export.add_argument('--outdir', '-o', default=".",
                                   help="root output directory of SDS package")
    parser_pkg_export.add_argument(
        '--accounts', '-a', action='store_true', help="save allowed accounts")
    parser_pkg_export.add_argument(
        '--skip-include-dependency-images', '-D', action='store_true',
        help="Do not include dependency images in the SDS package"
    )
    parser_pkg_import = parser_pkg_subparsers.add_parser(
        'import', help="import SDS package")
    parser_pkg_import.add_argument('file', help='SDS package to import')
    parser_pkg_import.add_argument(
        '--skip-include-dependency-images', '-D', action='store_true',
        help="Do not attempt to include dependency images when importing the SDS package"
    )
    parser_pkg_rm = parser_pkg_subparsers.add_parser(
        'rm', help="remove SDS package")
    parser_pkg_rm.add_argument('id', help='SDS package id to remove')
    parser_pkg.set_defaults(func=pkg)

    # parser for cloud
    parser_cloud = subparsers.add_parser('cloud', help="SDS cloud management")
    parser_cloud.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                              choices=['hysds', 'sdskit'])
    parser_cloud_subparsers = parser_cloud.add_subparsers(
        dest='subparser', required=True,
        help='SDS cloud management functions')
    parser_cloud_ls = parser_cloud_subparsers.add_parser(
        'ls', help="list configured cloud vendors")
    parser_cloud_asg = parser_cloud_subparsers.add_parser(
        'asg', help="SDS cloud Autoscaling management")
    parser_cloud_asg.add_argument('--cloud', '-c', default='aws', const='aws', nargs='?',
                                  choices=['aws', 'azure', 'gcp'])
    parser_cloud_asg_subparsers = parser_cloud_asg.add_subparsers(
        dest='subparser2', required=True,
        help='SDS cloud Autoscaling management functions')
    parser_cloud_asg_ls = parser_cloud_asg_subparsers.add_parser(
        'ls', help="list Autoscaling groups")
    parser_cloud_asg_create = parser_cloud_asg_subparsers.add_parser(
        'create', help="create Autoscaling group")
    parser_cloud_storage = parser_cloud_subparsers.add_parser(
        'storage', help="SDS cloud storage management")
    parser_cloud_storage.add_argument('--cloud', '-c', default='aws', const='aws', nargs='?',
                                      choices=['aws', 'azure', 'gcp'])
    parser_cloud_storage_subparsers = parser_cloud_storage.add_subparsers(
        dest='subparser2', required=True,
        help='SDS cloud storage management functions')
    parser_cloud_storage_ls = parser_cloud_storage_subparsers.add_parser(
        'ls', help="list buckets")
    parser_cloud_storage_ship_style = parser_cloud_storage_subparsers.add_parser(
        'ship_style', help="ship browse style to bucket")
    parser_cloud_storage_ship_style.add_argument(
        '--bucket', '-b', default=None, help="bucket name")
    parser_cloud_storage_ship_style.add_argument('--encrypt', '-e', action='store_true',
                                                 help="encrypt")
    parser_cloud_storage_create_staging_area = parser_cloud_storage_subparsers.add_parser('create_staging_area',
                                                                                          help="provision staging area under bucket")
    parser_cloud_storage_create_staging_area.add_argument(
        '--bucket', '-b', default=None, help="bucket name")
    parser_cloud_storage_create_staging_area.add_argument('--prefix', '-p', default="staging_area/",
                                                          help="staging area prefix")
    parser_cloud_storage_create_staging_area.add_argument(
        '--suffix', help="staging area signal file suffix")
    parser_cloud.set_defaults(func=cloud)

    # parser for user rules
    parser_rules = subparsers.add_parser(
        'rules', help="SDS user rules management")
    parser_rules.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                              choices=['hysds', 'sdskit'])
    parser_rules_subparsers = parser_rules.add_subparsers(
        dest='subparser', required=True,
        help='SDS user rules management functions')
    parser_rules_export = parser_rules_subparsers.add_parser(
        'export', help="export user rules")
    parser_rules_export.add_argument('--outfile', '-o', default="user_rules.json",
                                     help="output JSON file for user rules")
    parser_rules_import = parser_rules_subparsers.add_parser(
        'import', help="import user rules")
    parser_rules_import.add_argument(
        'file', help='input JSON file for user rules import')
    parser_rules.set_defaults(func=rules)

    # parser for jobs
    parser_job = subparsers.add_parser('job', help="SDS job subcommand")
    job_subparsers = parser_job.add_subparsers(help="Job functions.")

    # parser for jobs listing
    parser_job_list = job_subparsers.add_parser(
        'list', help="list SDS job counts")
    parser_job_list.add_argument(
        "status", help="job status to list counts for")
    parser_job_list.set_defaults(func=job_list)

    # parser for container orchestration
    parser_orch = subparsers.add_parser(
        'orch', help="SDS container orchestration")
    parser_orch.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                             choices=['hysds', 'sdskit'])
    parser_orch_subparsers = parser_orch.add_subparsers(
        dest='subparser', required=True,
        help='SDS container orchestration functions')
    parser_orch_init = parser_orch_subparsers.add_parser(
        'init', help="Initialize container-orchestrated SDS components")
    parser_orch_init.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                                   choices=['hysds', 'sdskit'])
    parser_orch_init.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                         'factotum', 'ci', 'all', 'core'])
    parser_orch_init.add_argument('--force', '-f', action='store_true',
                                   help="force initialization without user confirmation")
    parser_orch_start = parser_orch_subparsers.add_parser(
        'start', help="start container-orchestrated SDS components")
    parser_orch_start.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                                   choices=['hysds', 'sdskit'])
    parser_orch_start.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                         'factotum', 'ci', 'all', 'core'])
    parser_orch_start.add_argument('--force', '-f', action='store_true',
                                   help="force start without user confirmation")
    parser_orch_start.add_argument('--release', '-r', default='latest',
                                   help="HySDS core release")
    parser_orch_stop = parser_orch_subparsers.add_parser(
        'stop', help="stop container-orchestrated SDS components")
    parser_orch_stop.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                                  choices=['hysds', 'sdskit'])
    parser_orch_stop.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                        'factotum', 'ci', 'all', 'core'])
    parser_orch_stop.add_argument('--force', '-f', action='store_true',
                                  help="force stop without user confirmation")
    parser_orch_logs = parser_orch_subparsers.add_parser(
        'logs', help="show logs of container-orchestrated SDS components")
    parser_orch_logs.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                                  choices=['hysds', 'sdskit'])
    parser_orch_logs.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                        'factotum', 'ci'])
    parser_orch_logs.add_argument('--follow', '-f', action='store_true',
                                  help="follow log output")
    parser_orch_ps = parser_orch_subparsers.add_parser(
        'ps', help="list orchestrated containers of SDS components")
    parser_orch_ps.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                                  choices=['hysds', 'sdskit'])
    parser_orch_ps.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                      'factotum', 'ci', 'all', 'core'])
    parser_orch_run = parser_orch_subparsers.add_parser(
        'run', help="Run command in container-orchestrated SDS component")
    parser_orch_run.add_argument('--type', '-t', default='hysds', const='hysds', nargs='?',
                                  choices=['hysds', 'sdskit'])
    parser_orch_run.add_argument('component', choices=['mozart', 'grq', 'metrics',
                                                        'factotum', 'ci'])
    parser_orch_run.add_argument('cmd', nargs=argparse.REMAINDER, help="command")
    parser_orch.set_defaults(func=orch)

    # parse
    args = parser.parse_args()

    # print help
    if len(sys.argv) == 1 or not hasattr(args, 'func'):
        parser.print_help(sys.stderr)
        sys.exit(1)

    # dispatch
    return dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
