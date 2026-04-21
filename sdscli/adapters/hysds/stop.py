"""
Stop components for HySDS.
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

from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator, ValidationError
from pygments.token import Token

from sdscli.log_utils import logger
from sdscli.conf_utils import get_user_files_path, SettingsConf
from sdscli.os_utils import validate_dir
from sdscli.prompt_utils import YesNoValidator, set_bar_desc

from . import fabfile as fab


def stop_mozart(conf, comp='mozart'):
    """"Stop mozart component."""

    # progress bar
    with tqdm(total=2) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping mozartd')
        execute(fab.mozartd_stop, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped mozart')


def stop_metrics(conf, comp='metrics'):
    """"Stop metrics component."""

    # progress bar
    with tqdm(total=2) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping metricsd')
        execute(fab.metricsd_stop, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped metrics')


def stop_grq(conf, comp='grq'):
    """"Stop grq component."""

    # progress bar
    with tqdm(total=2) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'sciflo', roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping grqd')
        execute(fab.grqd_stop, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped grq')


def stop_factotum(conf, comp='factotum'):
    """"Stop factotum component."""

    # progress bar
    with tqdm(total=2) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'verdi', roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping verdid')
        execute(fab.verdid_stop, roles=[comp])
        execute(fab.kill_hung, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped factotum')


def stop_comp(comp, conf):
    """Stop component."""

    # if all, create progress bar
    if comp == 'all':

        # progress bar
        with tqdm(total=4) as bar:
            set_bar_desc(bar, "Stopping grq")
            stop_grq(conf)
            bar.update()
            set_bar_desc(bar, "Stopping mozart")
            stop_mozart(conf)
            bar.update()
            set_bar_desc(bar, "Stopping metrics")
            stop_metrics(conf)
            bar.update()
            set_bar_desc(bar, "Stopping factotum")
            stop_factotum(conf)
            bar.update()
            set_bar_desc(bar, "Stopped all")
            print("")
    else:
        if comp == 'grq':
            stop_grq(conf)
        if comp == 'mozart':
            stop_mozart(conf)
        if comp == 'metrics':
            stop_metrics(conf)
        if comp == 'factotum':
            stop_factotum(conf)


def stop(comp, debug=False, force=False):
    """Stop components."""

    # prompt user
    if not force:
        cont = prompt(get_prompt_tokens=lambda x: [(Token.Alert,
                                                    f"Stopping component[s]: {comp}. Continue [y/n]: "), (Token, " ")],
                      validator=YesNoValidator()) == 'y'
        if not cont:
            return 0

    # get user's SDS conf settings
    conf = SettingsConf()

    logger.debug("Stopping %s" % comp)

    if debug:
        stop_comp(comp, conf)
    else:
        with hide('everything'):
            stop_comp(comp, conf)
