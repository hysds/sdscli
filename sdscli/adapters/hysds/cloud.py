"""
SDS cloud management functions.
"""


from future import standard_library
standard_library.install_aliases()
import os
import json
import pkgutil
import traceback
from fabric.api import execute, hide

from prompt_toolkit.shortcuts import prompt, print_tokens
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.validation import Validator, ValidationError
from pygments.token import Token

from sdscli.log_utils import logger
from sdscli.conf_utils import get_user_files_path, SettingsConf
from sdscli.prompt_utils import highlight
from sdscli.func_utils import get_module, get_func
import sdscli.cloud


def ls(args):
    """List HySDS packages."""

    # get user's SDS conf settings
    conf = SettingsConf()

    # check which cloud platforms configured
    for importer, mod_name, ispkg in pkgutil.iter_modules(sdscli.cloud.__path__):
        mod = get_module(f'sdscli.cloud.{mod_name}.utils')
        print("{}: {}".format(mod_name, highlight("configured", 'green') if
                               mod.is_configured() else highlight("unimplemented or not configured", 'red')))


def asg(args):
    """ASG management functions."""

    # print args
    logger.debug(f"In asg(): {args}")

    # get user's SDS conf settings
    conf = SettingsConf()

    # get func
    try:
        func = get_func('sdscli.cloud.{}.{}'.format(
            args.cloud, args.subparser), args.subparser2)
    except (ImportError, AttributeError):
        logger.error('Not implemented yet. Mahalo for trying. ;)')
        return 1

    # run
    return func(args, conf)


def storage(args):
    """Cloud storage management functions."""

    # print args
    logger.debug(f"In storage(): {args}")

    # get user's SDS conf settings
    conf = SettingsConf()

    # get func
    try:
        func = get_func('sdscli.cloud.{}.{}'.format(
            args.cloud, args.subparser), args.subparser2)
    except (ImportError, AttributeError):
        logger.error('Not implemented yet. Mahalo for trying. ;)')
        return 1

    # run
    return func(args, conf)
