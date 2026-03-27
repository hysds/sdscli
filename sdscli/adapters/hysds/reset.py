"""
Reset components for HySDS.
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


prompt_style = Style.from_dict({
    Token.Alert: 'bg:#D8060C',
    Token.Username: '#D8060C',
    Token.Param: '#3CFF33',
})


def reset_mozart(conf, comp='mozart'):
    """"Start mozart component."""

    # progress bar
    with tqdm(total=6) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping mozartd')
        execute(fab.mozartd_stop, roles=[comp])
        bar.update()

        # clear rabbitmq
        set_bar_desc(bar, 'Clearing rabbitMQ queues')
        execute(fab.rabbitmq_queues_flush, roles=[comp])
        bar.update()

        # clear redis
        set_bar_desc(bar, 'Clearing redis')
        execute(fab.mozart_redis_flush, roles=[comp])
        bar.update()

        # clear ES
        set_bar_desc(bar, 'Clearing ES')
        execute(fab.mozart_es_flush, roles=[comp])
        bar.update()

        # start services
        set_bar_desc(bar, 'Resetting mozartd')
        execute(fab.mozartd_start, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Reset mozart')


def reset_metrics(conf, comp='metrics'):
    """"Start metrics component."""

    # progress bar
    with tqdm(total=4) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping metricsd')
        execute(fab.metricsd_stop, roles=[comp])
        bar.update()

        # clear redis
        set_bar_desc(bar, 'Clearing redis')
        execute(fab.redis_flush, roles=[comp])
        bar.update()

        # start services
        set_bar_desc(bar, 'Resetting metricsd')
        execute(fab.metricsd_clean_start, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Reset metrics')


def reset_grq(conf, comp='grq'):
    """"Start grq component."""

    # progress bar
    with tqdm(total=3) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'sciflo', roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping grqd')
        execute(fab.grqd_stop, roles=[comp])
        bar.update()

        # clear out ES
        #set_bar_desc(bar, 'Clearing out ES')
        #execute(fab.clean_hysds_ios, roles=[comp])
        # bar.update()

        # start services
        set_bar_desc(bar, 'Resetting grqd')
        execute(fab.grqd_clean_start, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Reset grq')


def reset_factotum(conf, comp='factotum'):
    """"Start factotum component."""

    # progress bar
    with tqdm(total=3) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'verdi', roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping verdid')
        execute(fab.verdid_stop, roles=[comp])
        execute(fab.kill_hung, roles=[comp])
        bar.update()

        # start services
        set_bar_desc(bar, 'Resetting verdid')
        execute(fab.verdid_clean_start, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Reset factotum')


def reset_comp(comp, conf):
    """Start component."""

    # if all, create progress bar
    if comp == 'all':

        # progress bar
        with tqdm(total=4) as bar:
            set_bar_desc(bar, "Resetting grq")
            reset_grq(conf)
            bar.update()
            set_bar_desc(bar, "Resetting mozart")
            reset_mozart(conf)
            bar.update()
            set_bar_desc(bar, "Resetting metrics")
            reset_metrics(conf)
            bar.update()
            set_bar_desc(bar, "Resetting factotum")
            reset_factotum(conf)
            bar.update()
            set_bar_desc(bar, "Reset all")
            print("")
    else:
        if comp == 'grq':
            reset_grq(conf)
        if comp == 'mozart':
            reset_mozart(conf)
        if comp == 'metrics':
            reset_metrics(conf)
        if comp == 'factotum':
            reset_factotum(conf)


def reset(comp, debug=False, force=False):
    """Start components."""

    # prompt user
    if not force:
        cont = prompt(get_prompt_tokens=lambda x: [(Token.Alert,
                                                    f"Resetting component[s]: {comp}. Continue [y/n]: "), (Token, " ")],
                      validator=YesNoValidator(), style=prompt_style) == 'y'
        if not cont:
            return 0

    # get user's SDS conf settings
    conf = SettingsConf()

    logger.debug("Resetting %s" % comp)

    if debug:
        reset_comp(comp, conf)
    else:
        with hide('everything'):
            reset_comp(comp, conf)
