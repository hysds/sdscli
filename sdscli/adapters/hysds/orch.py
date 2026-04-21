"""
SDS container orchestration functions.
"""


from . import fabfile as fab
from sdscli.func_utils import get_module, get_func
from sdscli.prompt_utils import YesNoValidator, highlight, set_bar_desc
from sdscli.conf_utils import get_user_files_path, SettingsConf
from sdscli.log_utils import logger
from pygments.token import Token
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.styles import Style
from prompt_toolkit.shortcuts import prompt
from tqdm import tqdm
from fabric.api import execute, hide
import traceback
import pkgutil
import json
import os
from future import standard_library
standard_library.install_aliases()


def init_mozart(conf, comp='mozart'):
    """"Initialize mozart component."""

    # progress bar
    with tqdm(total=7) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, system_site_packages=False,
                install_supervisor=False, roles=[comp])
        bar.update()

        # initialize sdsadm
        set_bar_desc(bar, 'Initializing mozart')
        execute(fab.init_sdsadm, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Initialized mozart')

        # configure for cluster
        set_bar_desc(bar, 'Configuring mozart')
        execute(fab.conf_sdsadm, 'celeryconfig.py',
                '~/mozart/etc/celeryconfig.py',
                roles=[comp])
        bar.update()
        execute(fab.conf_sdsadm, 'datasets.json',
                '~/mozart/etc/datasets.json', True,
                roles=[comp])
        bar.update()
        execute(fab.conf_sdsadm, 'settings.cfg',
                '~/mozart/etc/settings.cfg',
                roles=[comp])
        bar.update()
        execute(fab.conf_sdsadm, 'netrc', '.netrc',
                roles=[comp])
        execute(fab.chmod, 600, '.netrc', roles=[comp])
        bar.update()
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Configured mozart')


def init_grq(conf, comp='grq'):
    """"Initialize grq component."""

    # progress bar
    with tqdm(total=7) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'sciflo', system_site_packages=False,
                install_supervisor=False, roles=[comp])
        bar.update()

        # rsync sdsadm
        set_bar_desc(bar, 'Syncing sdsadm')
        execute(fab.rm_rf, '~/sciflo/ops/sdsadm', roles=[comp])
        execute(fab.rsync_sdsadm, roles=[comp])
        bar.update()

        # initialize sdsadm
        set_bar_desc(bar, 'Initializing grq')
        execute(fab.init_sdsadm, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Initialized grq')

        # configure for cluster
        set_bar_desc(bar, 'Configuring grq')
        execute(fab.conf_sdsadm, 'celeryconfig.py', '~/sciflo/etc/celeryconfig.py', roles=[comp])
        bar.update()
        execute(fab.conf_sdsadm, 'datasets.json', '~/sciflo/etc/datasets.json', True, roles=[comp])
        bar.update()
        execute(fab.conf_sdsadm, 'pele_settings.cfg', '~/sciflo/etc/pele_settings.cfg', roles=[comp])
        bar.update()
        netrc = os.path.join(get_user_files_path(), 'netrc')
        if os.path.exists(netrc):
            set_bar_desc(bar, 'Configuring netrc')
            execute(fab.send_template, 'netrc', '.netrc', roles=[comp])
            execute(fab.chmod, 600, '.netrc', roles=[comp])
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Configured grq')


def init_metrics(conf, comp='metrics'):
    """"Initialize metrics component."""

    # progress bar
    with tqdm(total=6) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, system_site_packages=False,
                install_supervisor=False, roles=[comp])
        bar.update()

        # rsync sdsadm
        set_bar_desc(bar, 'Syncing sdsadm')
        execute(fab.rm_rf, f'~/{comp}/ops/sdsadm', roles=[comp])
        execute(fab.rsync_sdsadm, roles=[comp])
        bar.update()

        # initialize sdsadm
        set_bar_desc(bar, 'Initializing metrics')
        execute(fab.init_sdsadm, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Initialized metrics')

        # configure for cluster
        set_bar_desc(bar, 'Configuring metrics')
        execute(fab.conf_sdsadm, 'celeryconfig.py',
                '~/metrics/etc/celeryconfig.py',
                roles=[comp])
        bar.update()
        execute(fab.conf_sdsadm, 'datasets.json',
                '~/metrics/etc/datasets.json', True,
                roles=[comp])
        bar.update()
        netrc = os.path.join(get_user_files_path(), 'netrc')
        if os.path.exists(netrc):
            set_bar_desc(bar, 'Configuring netrc')
            execute(fab.send_template, 'netrc', '.netrc', roles=[comp])
            execute(fab.chmod, 600, '.netrc', roles=[comp])
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Configured metrics')


def init_factotum(conf, comp='factotum'):
    """"Initialize factotum component."""

    # progress bar
    with tqdm(total=6) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'verdi', system_site_packages=False,
                install_supervisor=False, roles=[comp])
        bar.update()

        # rsync sdsadm
        set_bar_desc(bar, 'Syncing sdsadm')
        execute(fab.rm_rf, '~/verdi/ops/sdsadm', roles=[comp])
        execute(fab.rsync_sdsadm, roles=[comp])
        bar.update()

        # initialize sdsadm
        set_bar_desc(bar, 'Initializing factotum')
        execute(fab.init_sdsadm, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Initialized factotum')

        # configure for cluster
        set_bar_desc(bar, 'Configuring factotum')
        execute(fab.conf_sdsadm, 'celeryconfig.py',
                '~/verdi/etc/celeryconfig.py',
                roles=[comp])
        bar.update()
        execute(fab.conf_sdsadm, 'datasets.json',
                '~/verdi/etc/datasets.json', True,
                roles=[comp])
        bar.update()
        netrc = os.path.join(get_user_files_path(), 'netrc')
        if os.path.exists(netrc):
            set_bar_desc(bar, 'Configuring netrc')
            execute(fab.send_template, 'netrc', '.netrc', roles=[comp])
            execute(fab.chmod, 600, '.netrc', roles=[comp])
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Configured factotum')


def init_ci(conf, comp='ci'):
    """"Initialize ci component."""

    # progress bar
    with tqdm(total=6) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'verdi', system_site_packages=False,
                install_supervisor=False, roles=[comp])
        bar.update()

        # rsync sdsadm
        set_bar_desc(bar, 'Syncing sdsadm')
        execute(fab.rm_rf, '~/verdi/ops/sdsadm', roles=[comp])
        execute(fab.rsync_sdsadm, roles=[comp])
        bar.update()

        # initialize sdsadm
        set_bar_desc(bar, 'Initializing ci')
        execute(fab.init_sdsadm, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Initialized ci')

        # configure for cluster
        set_bar_desc(bar, 'Configuring ci')
        execute(fab.conf_sdsadm, 'celeryconfig.py',
                '~/verdi/etc/celeryconfig.py',
                roles=[comp])
        bar.update()
        execute(fab.conf_sdsadm, 'datasets.json',
                '~/verdi/etc/datasets.json', True,
                roles=[comp])
        bar.update()
        netrc = os.path.join(get_user_files_path(), 'netrc')
        if os.path.exists(netrc):
            set_bar_desc(bar, 'Configuring netrc')
            execute(fab.send_template, 'netrc', '.netrc', roles=[comp])
            execute(fab.chmod, 600, '.netrc', roles=[comp])
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Configured ci')


def init_comp(comp, conf):
    """Initialize component."""

    if comp == 'all':
        comps = ['metrics', 'grq', 'mozart', 'factotum', 'ci']
    elif comp == 'core':
        comps = ['metrics', 'grq', 'mozart', 'factotum']
    else:
        comps = [comp]

    with tqdm(total=len(comps)) as bar:
        for c in comps:
            set_bar_desc(bar, f'Initializing {c}')
            globals()[f"init_{c}"](conf)
            bar.update()
            set_bar_desc(bar, f'Initialized {c}')
        set_bar_desc(bar, f"Initialized {comp}")
        print("")


def init(comp, debug=False, force=False):
    """Initialize components."""

    # prompt user
    if not force:
        cont = prompt(f"Initializing component[s]: {comp}. Continue [y/n]: ",
                      validator=YesNoValidator()) == 'y'
        if not cont:
            return 0

    # get user's SDS conf settings
    conf = SettingsConf()

    logger.debug("Initializing %s" % comp)

    if debug:
        init_comp(comp, conf)
    else:
        with hide('everything'):
            init_comp(comp, conf)


def start_comp(comp, release, conf):
    """Start component."""

    if comp == 'all':
        comps = ['metrics', 'grq', 'mozart', 'factotum', 'ci']
    elif comp == 'core':
        comps = ['metrics', 'grq', 'mozart', 'factotum']
    else:
        comps = [comp]
    with tqdm(total=len(comps)) as bar:
        for c in comps:
            set_bar_desc(bar, f'Starting {c} ({release})')
            execute(fab.start_sdsadm, release, roles=[c])
            bar.update()
            set_bar_desc(bar, f'Started {c} ({release})')
        set_bar_desc(bar, "Started all")
        print("")


def start(comp, release, debug=False, force=False):
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

    start_comp(comp, release, conf)


def stop_comp(comp, conf):
    """Stop component."""

    if comp == 'all':
        comps = ['metrics', 'grq', 'mozart', 'factotum', 'ci']
    elif comp == 'core':
        comps = ['metrics', 'grq', 'mozart', 'factotum']
    else:
        comps = [comp]
    with tqdm(total=len(comps)) as bar:
        for c in comps:
            set_bar_desc(bar, f'Stopping {c}')
            execute(fab.stop_sdsadm, roles=[c])
            bar.update()
            set_bar_desc(bar, f'Stopped {c}')
        set_bar_desc(bar, "Stopped all")
        print("")


def stop(comp, debug=False, force=False):
    """Stop components."""

    # prompt user
    if not force:
        cont = prompt(f"Stopping component[s]: {comp}. Continue [y/n]: ",
                      validator=YesNoValidator()) == 'y'
        if not cont:
            return 0

    # get user's SDS conf settings
    conf = SettingsConf()

    logger.debug("Stopping %s" % comp)

    stop_comp(comp, conf)


def logs_comp(comp, conf, follow):
    """Show logs for component."""

    execute(fab.logs_sdsadm, follow, roles=[comp])


def logs(comp, debug=False, follow=False):
    """Show logs for components."""

    # get user's SDS conf settings
    conf = SettingsConf()

    logs_comp(comp, conf, follow)


def ps_comp(comp, conf):
    """List containers for component."""

    if comp == 'all':
        comps = ['metrics', 'grq', 'mozart', 'factotum', 'ci']
    elif comp == 'core':
        comps = ['metrics', 'grq', 'mozart', 'factotum']
    else:
        comps = [comp]
    for c in comps:
        execute(fab.ps_sdsadm, roles=[c])


def ps(comp, debug=False):
    """List containers for components."""

    # get user's SDS conf settings
    conf = SettingsConf()

    ps_comp(comp, conf)


def run_comp(comp, cmd, conf):
    """Run command in component."""

    execute(fab.run_sdsadm, cmd, roles=[comp])


def run(comp, cmd):
    """Run command in components."""

    # get user's SDS conf settings
    conf = SettingsConf()

    run_comp(comp, cmd, conf)
