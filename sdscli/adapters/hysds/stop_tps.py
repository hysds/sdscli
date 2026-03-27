"""
Stop TPS components for HySDS.
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


def stop_mozart(conf, comp='mozart'):
    """"Stop TPS on mozart component."""

    # progress bar
    with tqdm(total=3) as bar:

        # stop rabbitmq
        set_bar_desc(bar, 'Stopping rabbitmq-server')
        execute(fab.systemctl, 'stop', 'rabbitmq-server', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped rabbitmq-server')

        # stop redis
        set_bar_desc(bar, 'Stopping redis')
        execute(fab.systemctl, 'stop', 'redis', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped redis')

        # stop elasticsearch
        set_bar_desc(bar, 'Stopping elasticsearch')
        execute(fab.systemctl, 'stop', 'elasticsearch', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped elasticsearch')


def stop_metrics(conf, comp='metrics'):
    """"Stop TPS on metrics component."""

    # progress bar
    with tqdm(total=2) as bar:

        # stop redis
        set_bar_desc(bar, 'Stopping redis')
        execute(fab.systemctl, 'stop', 'redis', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped redis')

        # stop elasticsearch
        set_bar_desc(bar, 'Stopping elasticsearch')
        execute(fab.systemctl, 'stop', 'elasticsearch', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped elasticsearch')


def stop_grq(conf, comp='grq'):
    """"Stop TPS on grq component."""

    # progress bar
    with tqdm(total=1) as bar:

        # stop elasticsearch
        set_bar_desc(bar, 'Stopping elasticsearch')
        execute(fab.systemctl, 'stop', 'elasticsearch', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped elasticsearch')


def stop_ci(conf, comp='ci'):
    """"Stop TPS on CI component."""

    # progress bar
    with tqdm(total=1) as bar:

        # stop jenkins
        set_bar_desc(bar, 'Stopping jenkins')
        execute(fab.systemctl, 'stop', 'jenkins', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Stopped jenkins')


def stop_comp(comp, conf):
    """Stop component."""

    # if all, create progress bar
    if comp == 'all':

        # progress bar
        with tqdm(total=4) as bar:
            set_bar_desc(bar, "Stopping TPS on grq")
            stop_grq(conf)
            bar.update()
            set_bar_desc(bar, "Stopping TPS on mozart")
            stop_mozart(conf)
            bar.update()
            set_bar_desc(bar, "Stopping TPS on metrics")
            stop_metrics(conf)
            bar.update()
            set_bar_desc(bar, "Stopping TPS on ci")
            stop_ci(conf)
            bar.update()
            set_bar_desc(bar, "Stopped TPS on all")
            print("")
    else:
        if comp == 'grq':
            stop_grq(conf)
        if comp == 'mozart':
            stop_mozart(conf)
        if comp == 'metrics':
            stop_metrics(conf)
        if comp == 'ci':
            stop_ci(conf)


def stop(comp, debug=False, force=False):
    """Stop TPS components."""

    # prompt user
    if not force:
        cont = prompt(get_prompt_tokens=lambda x: [(Token.Alert,
                                                    f"Stopping TPS on component[s]: {comp}. Continue [y/n]: "), (Token, " ")],
                      validator=YesNoValidator(), style=prompt_style) == 'y'
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
