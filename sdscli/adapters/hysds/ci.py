"""
Continuous integration functions.
"""


from future import standard_library
standard_library.install_aliases()
import os
import yaml
import pwd
import hashlib
import traceback
from fabric.api import execute, hide
from tqdm import tqdm
from urllib.parse import urlparse

from prompt_toolkit.shortcuts import prompt, print_tokens
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.validation import Validator, ValidationError
from pygments.token import Token

from sdscli.log_utils import logger
from sdscli.conf_utils import get_user_files_path, SettingsConf
from sdscli.os_utils import validate_dir
from sdscli.prompt_utils import print_component_header

from . import fabfile as fab


def remove_job(args):
    """Remove jenkins jobs."""

    # get user's SDS conf settings
    conf = SettingsConf()

    # remove jenkins job for branch or release
    if args.branch is None:
        execute(fab.remove_ci_job, args.repo, roles=['ci'])
    else:
        execute(fab.remove_ci_job, args.repo, args.branch, roles=['ci'])


def add_job(args):
    """Add jenkins job."""

    # get user's SDS conf settings
    conf = SettingsConf()

    # if using OAuth token, check its defined
    if args.token:
        if conf.get('GIT_OAUTH_TOKEN') is None:
            logger.error("Cannot use OAuth token. Undefined in SDS config.")
            return 1
        u = urlparse(args.repo)
        repo_url = u._replace(netloc="{}@{}".format(
            conf.get('GIT_OAUTH_TOKEN'), u.netloc)).geturl()
    else:
        repo_url = args.repo

    logger.debug(f"repo_url: {repo_url}")

    # add jenkins job for branch or release
    if args.branch is None:
        execute(fab.add_ci_job_release, repo_url, args.storage, roles=['ci'])
    else:
        pipeline = getattr(args, 'pipeline', False)
        execute(fab.add_ci_job, repo_url, args.storage,
                args.branch, pipeline=pipeline, roles=['ci'])

    # reload
    execute(fab.reload_configuration, roles=['ci'])


def build_job(args):
    """Build jenkins job."""

    # get user's SDS conf settings
    conf = SettingsConf()

    # build jenkins job for branch or release
    if args.branch is None:
        execute(fab.build_ci_job, args.repo, roles=['ci'])
    else:
        execute(fab.build_ci_job, args.repo, args.branch, roles=['ci'])
