"""
Start components for HySDS.
"""


from . import fabfile as fab
from sdscli.prompt_utils import YesNoValidator, set_bar_desc
from sdscli.os_utils import validate_dir
from sdscli.conf_utils import get_user_files_path, SettingsConf
from sdscli.log_utils import logger
from pygments.token import Token
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import prompt
from tqdm import tqdm
from fabric.api import execute, hide
import traceback
import hashlib
import pwd
import yaml
import os
from future import standard_library
standard_library.install_aliases()


def start_mozart(conf, comp='mozart'):
    """"Start mozart component."""

    # progress bar
    with tqdm(total=2) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # start services
        set_bar_desc(bar, 'Starting mozartd')
        execute(fab.mozartd_start, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Started mozart')


def start_metrics(conf, comp='metrics'):
    """"Start metrics component."""

    # progress bar
    with tqdm(total=2) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # start services
        set_bar_desc(bar, 'Starting metricsd')
        execute(fab.metricsd_start, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Started metrics')


def start_grq(conf, comp='grq'):
    """"Start grq component."""

    # progress bar
    with tqdm(total=2) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'sciflo', roles=[comp])
        bar.update()

        # start services
        set_bar_desc(bar, 'Starting grqd')
        execute(fab.grqd_start, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Started grq')


def start_factotum(conf, comp='factotum'):
    """"Start factotum component."""

    # progress bar
    with tqdm(total=2) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'verdi', roles=[comp])
        bar.update()

        # start services
        set_bar_desc(bar, 'Starting factotum')
        execute(fab.verdid_start, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Started factotum')


def start_comp(comp, conf):
    """Start component."""

    # if all, create progress bar
    if comp == 'all':

        # progress bar
        with tqdm(total=4) as bar:
            set_bar_desc(bar, "Starting grq")
            start_grq(conf)
            bar.update()
            set_bar_desc(bar, "Starting mozart")
            start_mozart(conf)
            bar.update()
            set_bar_desc(bar, "Starting metrics")
            start_metrics(conf)
            bar.update()
            set_bar_desc(bar, "Starting factotum")
            start_factotum(conf)
            bar.update()
            set_bar_desc(bar, "Started all")
            print("")
    else:
        if comp == 'grq':
            start_grq(conf)
        if comp == 'mozart':
            start_mozart(conf)
        if comp == 'metrics':
            start_metrics(conf)
        if comp == 'factotum':
            start_factotum(conf)


def start(comp, debug=False, force=False):
    """Start components."""

    # prompt user
    if not force:
        cont = prompt(f"Starting component[s]: {comp}. Continue [y/n]: ",
                      validator=YesNoValidator()) == 'y'
        if not cont:
            return 0

    # get user's SDS conf settings
    conf = SettingsConf()

    logger.debug("Starting %s" % comp)

    if debug:
        start_comp(comp, conf)
    else:
        with hide('everything'):
            start_comp(comp, conf)
