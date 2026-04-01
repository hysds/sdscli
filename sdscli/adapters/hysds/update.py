"""
Update components for HySDS.
"""
from future import standard_library
standard_library.install_aliases()

import os
from fabric.api import execute, hide
from tqdm import tqdm

from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
from pygments.token import Token

from sdscli.log_utils import logger
from sdscli.conf_utils import get_user_files_path, SettingsConf
from sdscli.prompt_utils import YesNoValidator, set_bar_desc
from os.path import expanduser

from . import fabfile as fab


def update_mozart(conf, ndeps=False, config_only=False, comp='mozart'):
    """"Update mozart component."""

    num_updates = 31 if config_only else 45  # number of progress bar updates

    with tqdm(total=num_updates) as bar:  # progress bar
        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping mozartd')
        execute(fab.mozartd_stop, roles=[comp])
        bar.update()

        # update reqs
        if not config_only:
            set_bar_desc(bar, 'Updating HySDS core')
            execute(fab.pip_install_with_req, 'mozart', '~/mozart/ops/osaka', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'mozart', '~/mozart/ops/prov_es', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'mozart', '~/mozart/ops/hysds_commons', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'mozart', '~/mozart/ops/hysds', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'mozart', '~/mozart/ops/sciflo', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'mozart', '~/mozart/ops/chimera', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'mozart', '~/mozart/ops/mozart', ndeps, roles=[comp])
            bar.update()
            execute(fab.npm_install_package_json, '~/mozart/ops/hysds_ui', roles=[comp])
            bar.update()

        # update celery config
        set_bar_desc(bar, 'Updating celery config')
        execute(fab.rm_rf, '~/mozart/ops/hysds/celeryconfig.py', roles=[comp])
        execute(fab.rm_rf, '~/mozart/ops/hysds/celeryconfig.pyc', roles=[comp])
        execute(fab.send_celeryconf, 'mozart', roles=[comp])
        bar.update()

        # set default ES shard number
        set_bar_desc(bar, 'Setting default ES shard number')
        execute(fab.install_base_es_template, roles=[comp])
        bar.update()

        # set the ES ILM policy
        set_bar_desc(bar, 'Setting ES Index Lifecycle Manager policy')
        execute(fab.install_es_policy, roles=[comp])
        bar.update()

        # install the templates in order to attach the ILM policy onto them
        set_bar_desc(bar, 'Installing ES templates')
        execute(fab.install_mozart_es_templates, roles=[comp])
        bar.update()

        # update logstash jvm.options to increase heap size
        set_bar_desc(bar, 'Updating logstash jvm.options')
        execute(fab.send_logstash_jvm_options, 'mozart', roles=[comp])
        bar.update()

        # update supervisor config
        set_bar_desc(bar, 'Updating supervisor config')
        execute(fab.rm_rf, '~/mozart/etc/supervisord.conf', roles=[comp])
        execute(fab.send_template_user_override, 'supervisord.conf.mozart',
                '~/mozart/etc/supervisord.conf', '~/mozart/ops/hysds/configs/supervisor',
                roles=[comp])
        bar.update()

        # update orchestrator config
        set_bar_desc(bar, 'Updating orchestrator config')
        execute(fab.rm_rf, '~/mozart/etc/orchestrator_*.json', roles=[comp])
        execute(fab.copy_package_config_file, 'hysds', 'configs/orchestrator/orchestrator_jobs.json',
                '~/mozart/etc/orchestrator_jobs.json', roles=[comp])
        execute(fab.copy_package_config_file, 'hysds', 'configs/orchestrator/orchestrator_datasets.json',
                '~/mozart/etc/orchestrator_datasets.json', roles=[comp])
        bar.update()

        # update job_creators
        set_bar_desc(bar, 'Updating job_creators')
        execute(fab.rm_rf, '~/mozart/etc/job_creators', roles=[comp])
        execute(fab.copy_package_dir, 'hysds', 'scripts/job_creators',
                '~/mozart/etc/job_creators', roles=[comp])
        bar.update()

        # update datasets config; overwrite datasets config with domain-specific config
        set_bar_desc(bar, 'Updating datasets config')
        execute(fab.rm_rf, '~/mozart/etc/datasets.json', roles=[comp])
        execute(fab.send_template, 'datasets.json',
                '~/mozart/etc/datasets.json', roles=[comp])
        bar.update()

        # ship logstash shipper configs
        set_bar_desc(bar, 'Updating logstash shipper config')
        execute(fab.send_shipper_conf, 'mozart', '~/mozart/log', conf.get('MOZART_ES_CLUSTER'),
                '127.0.0.1', conf.get('METRICS_ES_CLUSTER'),
                conf.get('METRICS_REDIS_PVT_IP'), roles=[comp])
        bar.update()

        # update HySDS scripts
        set_bar_desc(bar, 'Updating HySDS scripts')
        execute(fab.send_hysds_scripts, 'mozart', roles=[comp])
        bar.update()

        # update mozart config
        set_bar_desc(bar, 'Updating mozart config')
        execute(fab.rm_rf, '~/mozart/ops/mozart/settings.cfg', roles=[comp])
        execute(fab.send_mozartconf, roles=[comp])
        bar.update()

        # update hysds_ui config
        set_bar_desc(bar, 'Updating hysds_ui config')
        execute(fab.rm_rf, '~/mozart/ops/hysds_ui/src/config/index.js', roles=[comp])
        execute(fab.send_hysds_ui_conf, roles=[comp])
        bar.update()

        # building HySDS UI
        set_bar_desc(bar, 'Building HySDS UI')
        execute(fab.build_hysds_ui, roles=[comp])
        bar.update()

        # create user_rules index
        set_bar_desc(bar, 'Creating user_rules index')
        execute(fab.create_user_rules_index, roles=[comp])
        bar.update()

        # create hysds_ios-mozart index
        set_bar_desc(bar, 'Creating hysds_ios-grq index')
        execute(fab.create_hysds_ios_index, roles=[comp])
        bar.update()

        # ensure self-signed SSL certs exist
        set_bar_desc(bar, 'Configuring SSL')
        execute(fab.ensure_ssl, 'mozart', roles=[comp])
        bar.update()

        # link ssl certs to apps
        # Create runtime directory for SSL certs (needed for PyPI installs)
        execute(fab.mkdir, '~/mozart/ops/mozart', None, None, roles=[comp])
        execute(fab.ln_sf, '~/ssl/server.key', '~/mozart/ops/mozart/server.key', roles=[comp])
        execute(fab.ln_sf, '~/ssl/server.pem', '~/mozart/ops/mozart/server.pem', roles=[comp])
        bar.update()

        # expose hysds log dir via webdav
        set_bar_desc(bar, 'Expose logs')
        execute(fab.mkdir, '/data/work', None, None, roles=[comp])
        execute(fab.ln_sf, '~/mozart/log', '/data/work/log', roles=[comp])
        bar.update()

        # ship netrc
        set_bar_desc(bar, 'Configuring netrc')
        execute(fab.send_template, 'netrc.mozart',
                '.netrc', node_type='mozart', roles=[comp])
        execute(fab.chmod, 600, '.netrc', roles=[comp])
        bar.update()

        # update ES template
        set_bar_desc(bar, 'Update ES template')
        execute(fab.install_pkg_es_templates, roles=[comp])
        bar.update()

        # ship AWS creds
        set_bar_desc(bar, 'Configuring AWS creds')
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Updated mozart')

        # update verdi for code/config bundle
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.rm_rf, '~/verdi', roles=[comp])
        execute(fab.ensure_venv, 'verdi',
                update_bash_profile=False, roles=[comp])
        bar.update()

        # remove code bundle stuff
        set_bar_desc(bar, 'Remove code bundle')
        execute(fab.rm_rf, '~/verdi/ops/etc', roles=[comp])
        execute(fab.rm_rf, '~/verdi/ops/install.sh', roles=[comp])
        bar.update()

        # update
        set_bar_desc(bar, 'Syncing packages')
        execute(fab.rm_rf, '~/verdi/ops/*', roles=[comp])
        execute(fab.rsync_code, 'verdi', roles=[comp])
        # execute(fab.set_spyddder_settings, roles=[comp])  # Deprecated - spyddder-man not in PyPI deployments
        bar.update()

        # update reqs
        if not config_only:
            set_bar_desc(bar, 'Updating HySDS core')
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/osaka', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/prov_es', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/hysds_commons', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/hysds', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/sciflo', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/chimera', ndeps, roles=[comp])
            bar.update()

        # update celery config
        set_bar_desc(bar, 'Updating celery config')
        execute(fab.rm_rf, '~/verdi/ops/hysds/celeryconfig.py', roles=[comp])
        execute(fab.rm_rf, '~/verdi/ops/hysds/celeryconfig.pyc', roles=[comp])
        execute(fab.send_celeryconf, 'verdi-asg', roles=[comp])
        bar.update()

        # update supervisor config
        set_bar_desc(bar, 'Updating supervisor config')
        execute(fab.rm_rf, '~/verdi/etc/supervisord.conf', roles=[comp])
        execute(fab.send_template_user_override, 'supervisord.conf.verdi',
                '~/verdi/etc/supervisord.conf', '~/mozart/ops/hysds/configs/supervisor',
                roles=[comp])
        bar.update()

        # update datasets config; overwrite datasets config with domain-specific config
        set_bar_desc(bar, 'Updating datasets config')
        execute(fab.rm_rf, '~/verdi/etc/datasets.json', roles=[comp])
        execute(fab.send_template, 'datasets.json',
                '~/verdi/etc/datasets.json', roles=[comp])
        bar.update()

        # ship logstash shipper configs
        set_bar_desc(bar, 'Updating logstash shipper config')
        execute(fab.send_shipper_conf, 'verdi-asg', '~/verdi/log', conf.get('MOZART_ES_CLUSTER'),
                conf.get('MOZART_REDIS_PVT_IP'), conf.get('METRICS_ES_CLUSTER'),
                conf.get('METRICS_REDIS_PVT_IP'), roles=[comp])
        bar.update()

        # update HySDS scripts
        set_bar_desc(bar, 'Updating HySDS scripts')
        execute(fab.send_hysds_scripts, 'verdi-asg', roles=[comp])
        bar.update()

        # ship netrc
        netrc = os.path.join(get_user_files_path(), 'netrc')
        if os.path.exists(netrc):
            set_bar_desc(bar, 'Configuring netrc')
            execute(fab.send_template, 'netrc', '.netrc.verdi', roles=[comp])
            execute(fab.chmod, 600, '.netrc.verdi', roles=[comp])

        # ship AWS creds
        set_bar_desc(bar, 'Configuring AWS creds')
        execute(fab.send_awscreds, suffix='.verdi', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Updated verdi code/config')

        # ship the run_podman script
        set_bar_desc(bar, 'Updating run_verdi_podman.sh.tmpl')
        execute(fab.mkdir, '~/verdi/ops/hysds-dockerfiles/verdi', None, None, roles=[comp])
        execute(fab.rm_rf, '~/verdi/ops/hysds-dockerfiles/verdi/run_verdi_podman.sh', roles=[comp])
        execute(fab.send_template,
                "run_verdi_podman.sh.tmpl",
                "~/verdi/ops/hysds-dockerfiles/verdi/run_verdi_podman.sh",
                "~/mozart/ops/hysds-dockerfiles/verdi",
                roles=[comp]
        )
        bar.update()


def update_metrics(conf, ndeps=False, config_only=False, comp='metrics'):
    """"Update metrics component."""

    num_updates = 15 if config_only else 22  # number of progress bar updates

    with tqdm(total=num_updates) as bar:  # progress bar
        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping metricsd')
        execute(fab.metricsd_stop, roles=[comp])
        bar.update()

        # update
        if not config_only:
            set_bar_desc(bar, 'Syncing packages')
            execute(fab.rm_rf, '~/metrics/ops/*', roles=[comp])
            execute(fab.rsync_code, 'metrics', roles=[comp])
            bar.update()

            # update reqs
            set_bar_desc(bar, 'Updating HySDS core')
            execute(fab.pip_install_with_req, 'metrics',
                    '~/metrics/ops/osaka', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'metrics',
                    '~/metrics/ops/prov_es', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'metrics',
                    '~/metrics/ops/hysds_commons', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'metrics',
                    '~/metrics/ops/hysds', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'metrics',
                    '~/metrics/ops/sciflo', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'metrics',
                    '~/metrics/ops/chimera', ndeps, roles=[comp])
            bar.update()

        # update logstash jvm.options to increase heap size
        set_bar_desc(bar, 'Updating logstash jvm.options')
        execute(fab.send_logstash_jvm_options, 'metrics', roles=[comp])
        bar.update()

        # update celery config
        set_bar_desc(bar, 'Updating celery config')
        execute(fab.rm_rf, '~/metrics/ops/hysds/celeryconfig.py', roles=[comp])
        bar.update()
        execute(fab.rm_rf, '~/metrics/ops/hysds/celeryconfig.pyc',
                roles=[comp])
        bar.update()
        execute(fab.send_celeryconf, 'metrics', roles=[comp])
        bar.update()

        # update supervisor config
        set_bar_desc(bar, 'Updating supervisor config')
        execute(fab.rm_rf, '~/metrics/etc/supervisord.conf', roles=[comp])
        bar.update()
        execute(fab.send_template_user_override, 'supervisord.conf.metrics',
                '~/metrics/etc/supervisord.conf', '~/mozart/ops/hysds/configs/supervisor',
                roles=[comp])
        bar.update()

        # update datasets config; overwrite datasets config with domain-specific config
        set_bar_desc(bar, 'Updating datasets config')
        execute(fab.rm_rf, '~/metrics/etc/datasets.json', roles=[comp])
        bar.update()
        execute(fab.send_template, 'datasets.json',
                '~/metrics/etc/datasets.json', roles=[comp])
        bar.update()

        # ship logstash shipper configs
        set_bar_desc(bar, 'Updating logstash shipper config')
        execute(fab.send_shipper_conf, 'metrics', '~/metrics/log', conf.get('MOZART_ES_CLUSTER'),
                conf.get('MOZART_REDIS_PVT_IP'), conf.get('METRICS_ES_CLUSTER'),
                '127.0.0.1', roles=[comp])
        bar.update()

        # update HySDS scripts
        set_bar_desc(bar, 'Updating HySDS scripts')
        execute(fab.send_hysds_scripts, 'metrics', roles=[comp])
        bar.update()

        # ship kibana config
        set_bar_desc(bar, 'Updating kibana config')
        if fab.metrics_es_engine != "opensearch":
            execute(fab.send_template, 'kibana.yml',
                    '~/kibana/config/kibana.yml', roles=[comp])
        bar.update()

        # expose hysds log dir via webdav
        set_bar_desc(bar, 'Expose logs')
        execute(fab.mkdir, '/data/work', None, None, roles=[comp])
        execute(fab.ln_sf, '~/metrics/log', '/data/work/log', roles=[comp])
        bar.update()

        # ship AWS creds
        set_bar_desc(bar, 'Configuring AWS creds')
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Updated metrics')


def update_grq(conf, ndeps=False, config_only=False, comp='grq'):
    """"Update grq component."""

    num_updates = 17 if config_only else 26  # number of progress bar updates

    with tqdm(total=num_updates) as bar:  # progress bar
        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'sciflo', roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping grqd')
        execute(fab.grqd_stop, roles=[comp])
        bar.update()

        # update
        if not config_only:
            set_bar_desc(bar, 'Syncing packages')
            execute(fab.rm_rf, '~/sciflo/ops/*', roles=[comp])
            execute(fab.rsync_code, 'grq', 'sciflo', roles=[comp])
            execute(fab.pip_upgrade, 'gunicorn', 'sciflo',
                    roles=[comp])  # ensure latest gunicorn
            bar.update()

            # update reqs
            set_bar_desc(bar, 'Updating HySDS core')
            execute(fab.pip_install_with_req, 'sciflo',
                    '~/sciflo/ops/osaka', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'sciflo',
                    '~/sciflo/ops/prov_es', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'sciflo',
                    '~/sciflo/ops/hysds_commons', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'sciflo',
                    '~/sciflo/ops/hysds', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'sciflo',
                    '~/sciflo/ops/sciflo', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'sciflo',
                    '~/sciflo/ops/chimera', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'sciflo',
                    '~/sciflo/ops/grq2', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'sciflo',
                    '~/sciflo/ops/pele', ndeps, roles=[comp])
            bar.update()

        # update celery config
        set_bar_desc(bar, 'Updating celery config')
        execute(fab.rm_rf, '~/sciflo/ops/hysds/celeryconfig.py', roles=[comp])
        execute(fab.rm_rf, '~/sciflo/ops/hysds/celeryconfig.pyc', roles=[comp])
        execute(fab.send_celeryconf, 'grq', roles=[comp])
        bar.update()

        # update grq2 config
        set_bar_desc(bar, 'Updating grq2 config')
        execute(fab.rm_rf, '~/sciflo/ops/grq2/settings.cfg', roles=[comp])
        execute(fab.send_grq2conf, roles=[comp])
        bar.update()

        # set default ES shard number
        set_bar_desc(bar, 'Setting default ES shard number')
        execute(fab.install_base_es_template, roles=[comp])
        bar.update()

        # update pele config
        set_bar_desc(bar, 'Updating pele config')
        execute(fab.rm_rf, '~/sciflo/ops/pele/settings.cfg', roles=[comp])
        execute(fab.send_peleconf, 'pele_settings.cfg.tmpl', roles=[comp])
        bar.update()

        # create user_rules index
        set_bar_desc(bar, 'Creating user_rules index')
        execute(fab.create_grq_user_rules_index, roles=[comp])
        bar.update()

        # create hysds_ios-grq index
        set_bar_desc(bar, 'Creating hysds_ios-grq index')
        execute(fab.create_hysds_ios_grq_index, roles=[comp])
        bar.update()

        # update supervisor config
        set_bar_desc(bar, 'Updating supervisor config')
        execute(fab.rm_rf, '~/sciflo/etc/supervisord.conf', roles=[comp])
        execute(fab.send_template_user_override, 'supervisord.conf.grq',
                '~/sciflo/etc/supervisord.conf', '~/mozart/ops/hysds/configs/supervisor',
                roles=[comp])
        bar.update()

        # update datasets config; overwrite datasets config with domain-specific config
        set_bar_desc(bar, 'Updating datasets config')
        execute(fab.rm_rf, '~/sciflo/etc/datasets.json', roles=[comp])
        execute(fab.send_template, 'datasets.json',
                '~/sciflo/etc/datasets.json', roles=[comp])
        bar.update()

        # ship logstash shipper configs
        set_bar_desc(bar, 'Updating logstash shipper config')
        execute(fab.send_shipper_conf, 'grq', '~/sciflo/log', conf.get('MOZART_ES_CLUSTER'),
                conf.get('MOZART_REDIS_PVT_IP'), conf.get('METRICS_ES_CLUSTER'),
                conf.get('METRICS_REDIS_PVT_IP'), roles=[comp])
        bar.update()

        # update HySDS scripts
        set_bar_desc(bar, 'Updating HySDS scripts')
        execute(fab.send_hysds_scripts, 'grq', roles=[comp])
        bar.update()

        # ensure self-signed SSL certs exist
        set_bar_desc(bar, 'Configuring SSL')
        execute(fab.ensure_ssl, 'grq', roles=[comp])
        bar.update()

        # link ssl certs to apps
        # Create runtime directories for SSL certs (needed for PyPI installs)
        execute(fab.mkdir, '~/sciflo/ops/grq2', None, None, roles=[comp])
        execute(fab.mkdir, '~/sciflo/ops/pele', None, None, roles=[comp])
        execute(fab.ln_sf, '~/ssl/server.key',
                '~/sciflo/ops/grq2/server.key', roles=[comp])
        execute(fab.ln_sf, '~/ssl/server.pem',
                '~/sciflo/ops/grq2/server.pem', roles=[comp])
        execute(fab.ln_sf, '~/ssl/server.key',
                '~/sciflo/ops/pele/server.key', roles=[comp])
        execute(fab.ln_sf, '~/ssl/server.pem',
                '~/sciflo/ops/pele/server.pem', roles=[comp])
        bar.update()

        # expose hysds log dir via webdav
        set_bar_desc(bar, 'Expose logs')
        execute(fab.mkdir, '/data/work', None, None, roles=[comp])
        execute(fab.ln_sf, '~/sciflo/log', '/data/work/log', roles=[comp])
        bar.update()

        # installing ingest pipeline
        # set_bar_desc(bar, 'Install GRQ Elasticsearch ingest pipeline')
        # execute(fab.install_ingest_pipeline, roles=[comp])
        # bar.update()

        # update ES template
        set_bar_desc(bar, 'Update ES template')
        execute(fab.install_es_template, roles=[comp])
        bar.update()

        # ship AWS creds
        set_bar_desc(bar, 'Configuring AWS creds')
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Updated grq')


def update_factotum(conf, ndeps=False, config_only=False, comp='factotum'):
    """"Update factotum component."""

    num_updates = 9 if config_only else 16  # number of progress bar updates

    with tqdm(total=num_updates) as bar:  # progress bar
        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, 'verdi', roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping verdid')
        execute(fab.verdid_stop, roles=[comp])
        execute(fab.kill_hung, roles=[comp])
        bar.update()

        # update
        if not config_only:
            set_bar_desc(bar, 'Syncing packages')
            execute(fab.rm_rf, '~/verdi/ops/*', roles=[comp])
            execute(fab.rsync_code, 'factotum', 'verdi', roles=[comp])
            # execute(fab.set_spyddder_settings, roles=[comp])  # Deprecated - spyddder-man not in PyPI deployments
            bar.update()

            # update reqs
            set_bar_desc(bar, 'Updating HySDS core')
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/osaka', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/prov_es', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/hysds_commons', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/hysds', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/sciflo', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/chimera', ndeps, roles=[comp])
            bar.update()

        # update celery config
        set_bar_desc(bar, 'Updating celery config')
        execute(fab.rm_rf, '~/verdi/ops/hysds/celeryconfig.py', roles=[comp])
        execute(fab.rm_rf, '~/verdi/ops/hysds/celeryconfig.pyc', roles=[comp])
        execute(fab.send_celeryconf, 'verdi', roles=[comp])
        bar.update()

        # update supervisor config
        set_bar_desc(bar, 'Updating supervisor config')
        execute(fab.rm_rf, '~/verdi/etc/supervisord.conf', roles=[comp])
        execute(fab.send_template_user_override, 'supervisord.conf.factotum',
                '~/verdi/etc/supervisord.conf', '~/mozart/ops/hysds/configs/supervisor',
                roles=[comp])
        bar.update()

        # update datasets config; overwrite datasets config with domain-specific config
        set_bar_desc(bar, 'Updating datasets config')
        execute(fab.rm_rf, '~/verdi/etc/datasets.json', roles=[comp])
        execute(fab.send_template, 'datasets.json',
                '~/verdi/etc/datasets.json', roles=[comp])
        bar.update()

        # ship logstash shipper configs
        set_bar_desc(bar, 'Updating logstash shipper config')
        execute(fab.send_shipper_conf, 'factotum', '~/verdi/log', conf.get('MOZART_ES_CLUSTER'),
                conf.get('MOZART_REDIS_PVT_IP'), conf.get('METRICS_ES_CLUSTER'),
                conf.get('METRICS_REDIS_PVT_IP'), roles=[comp])
        bar.update()

        # update HySDS scripts
        set_bar_desc(bar, 'Updating HySDS scripts')
        execute(fab.send_hysds_scripts, 'factotum', roles=[comp])
        bar.update()

        # expose hysds log dir via webdav
        set_bar_desc(bar, 'Expose logs')
        execute(fab.mkdir, '/data/work', None, None, roles=[comp])
        execute(fab.ln_sf, '~/verdi/log', '/data/work/log', roles=[comp])
        bar.update()

        # ship netrc
        netrc    = os.path.join(get_user_files_path(), 'netrc')
        netrc_os = os.path.expanduser("~/.netrc-os")

        if os.path.exists(netrc):
            set_bar_desc(bar, 'Configuring netrc')
            execute(fab.send_template, 'netrc', '.netrc', roles=[comp])
            execute(fab.chmod, 600, '.netrc', roles=[comp])

        if os.path.exists(netrc_os):
            set_bar_desc(bar, 'Configuring netrc-os')
            execute(fab.send_template, '.netrc-os', '.netrc-os', '~/', roles=[comp])
            execute(fab.chmod, 600, '.netrc-os', roles=[comp])

        # ship AWS creds
        set_bar_desc(bar, 'Configuring AWS creds')
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Updated factotum')


def update_verdi(conf, ndeps=False, config_only=False, comp='verdi'):
    """"Update verdi component."""

    num_updates = 10 if config_only else 17  # number of progress bar updates

    with tqdm(total=num_updates) as bar:  # progress bar
        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # stop services
        set_bar_desc(bar, 'Stopping verdid')
        execute(fab.verdid_stop, roles=[comp])
        execute(fab.kill_hung, roles=[comp])
        bar.update()

        # remove code bundle stuff
        set_bar_desc(bar, 'Remove code bundle')
        execute(fab.rm_rf, '~/verdi/ops/etc', roles=[comp])
        execute(fab.rm_rf, '~/verdi/ops/install.sh', roles=[comp])
        bar.update()

        # update
        if not config_only:
            set_bar_desc(bar, 'Syncing packages')
            execute(fab.rm_rf, '~/verdi/ops/*', roles=[comp])
            execute(fab.rsync_code, 'verdi', roles=[comp])
            # execute(fab.set_spyddder_settings, roles=[comp])  # Deprecated - spyddder-man not in PyPI deployments
            bar.update()

            # update reqs
            set_bar_desc(bar, 'Updating HySDS core')
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/osaka', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/prov_es', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/hysds_commons', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/hysds', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/sciflo', ndeps, roles=[comp])
            bar.update()
            execute(fab.pip_install_with_req, 'verdi',
                    '~/verdi/ops/chimera', ndeps, roles=[comp])
            bar.update()

        # update celery config
        set_bar_desc(bar, 'Updating celery config')
        execute(fab.rm_rf, '~/verdi/ops/hysds/celeryconfig.py', roles=[comp])
        execute(fab.rm_rf, '~/verdi/ops/hysds/celeryconfig.pyc', roles=[comp])
        execute(fab.send_celeryconf, 'verdi', roles=[comp])
        bar.update()

        # update supervisor config
        set_bar_desc(bar, 'Updating supervisor config')
        execute(fab.rm_rf, '~/verdi/etc/supervisord.conf', roles=[comp])
        execute(fab.send_template_user_override, 'supervisord.conf.verdi',
                '~/verdi/etc/supervisord.conf', '~/mozart/ops/hysds/configs/supervisor',
                roles=[comp])
        bar.update()

        # update datasets config; overwrite datasets config with domain-specific config
        set_bar_desc(bar, 'Updating datasets config')
        execute(fab.rm_rf, '~/verdi/etc/datasets.json', roles=[comp])
        execute(fab.send_template, 'datasets.json',
                '~/verdi/etc/datasets.json', roles=[comp])
        bar.update()

        # ship logstash shipper configs
        set_bar_desc(bar, 'Updating logstash shipper config')
        execute(fab.send_shipper_conf, 'verdi', '~/verdi/log', conf.get('MOZART_ES_CLUSTER'),
                conf.get('MOZART_REDIS_PVT_IP'), conf.get('METRICS_ES_CLUSTER'),
                conf.get('METRICS_REDIS_PVT_IP'), roles=[comp])
        bar.update()

        # update HySDS scripts
        set_bar_desc(bar, 'Updating HySDS scripts')
        execute(fab.send_hysds_scripts, 'verdi', roles=[comp])
        bar.update()

        # expose hysds log dir via webdav
        set_bar_desc(bar, 'Expose logs')
        execute(fab.mkdir, '/data/work', None, None, roles=[comp])
        execute(fab.ln_sf, '~/verdi/log', '/data/work/log', roles=[comp])
        bar.update()

        # ship netrc
        netrc = os.path.join(get_user_files_path(), 'netrc')
        if os.path.exists(netrc):
            set_bar_desc(bar, 'Configuring netrc')
            execute(fab.send_template, 'netrc', '.netrc', roles=[comp])
            execute(fab.chmod, 600, '.netrc', roles=[comp])

        # ship AWS creds
        set_bar_desc(bar, 'Configuring AWS creds')
        execute(fab.send_awscreds, roles=[comp])
        bar.update()
        set_bar_desc(bar, 'Updated verdi')

        # ship the run_podman script
        set_bar_desc(bar, 'Updating run_verdi_podman.sh.tmpl')
        execute(fab.mkdir, '~/verdi/ops/hysds-dockerfiles/verdi', None, None, roles=[comp])
        execute(fab.rm_rf, '~/verdi/ops/hysds-dockerfiles/verdi/run_verdi_podman.sh', roles=[comp])
        execute(fab.send_template,
                "run_verdi_podman.sh.tmpl",
                "~/verdi/ops/hysds-dockerfiles/verdi/run_verdi_podman.sh",
                "~/mozart/ops/hysds-dockerfiles/verdi",
                roles=[comp]
        )
        bar.update()


def update_comp(comp, conf, ndeps=False, config_only=False):
    """Update component."""

    if comp == 'all':  # if all, create progress bar
        # progress bar
        with tqdm(total=5) as bar:
            set_bar_desc(bar, "Updating grq")
            update_grq(conf, ndeps, config_only)
            bar.update()
            set_bar_desc(bar, "Updating mozart")
            update_mozart(conf, ndeps, config_only)
            bar.update()
            set_bar_desc(bar, "Updating metrics")
            update_metrics(conf, ndeps, config_only)
            bar.update()
            set_bar_desc(bar, "Updating factotum")
            update_factotum(conf, ndeps, config_only)
            bar.update()
            set_bar_desc(bar, "Updating verdi")
            update_verdi(conf, ndeps, config_only)
            bar.update()
            set_bar_desc(bar, "Updated all")
            print("")
    else:
        if comp == 'grq':
            update_grq(conf, ndeps, config_only)
        if comp == 'mozart':
            update_mozart(conf, ndeps, config_only)
        if comp == 'metrics':
            update_metrics(conf, ndeps, config_only)
        if comp == 'factotum':
            update_factotum(conf, ndeps, config_only)
        if comp == 'verdi':
            update_verdi(conf, ndeps, config_only)


def update(comp, debug=False, force=False, ndeps=False, config_only=False):
    """Update components."""

    # prompt user
    if not force:
        cont = prompt(get_prompt_tokens=lambda x: [(Token.Alert,
                                                    f"Updating component[s]: {comp}. Continue [y/n]: "), (Token, " ")],
                      validator=YesNoValidator(), style=prompt_style) == 'y'
        if not cont:
            return 0

    # get user's SDS conf settings
    conf = SettingsConf()

    logger.debug("Updating %s" % comp)

    if debug:
        update_comp(comp, conf, ndeps, config_only)
    else:
        with hide('everything'):
            update_comp(comp, conf, ndeps, config_only)


def ship_verdi(conf, encrypt=False, comp='mozart'):
    """"Ship verdi code/config bundle."""

    venue = conf.get('VENUE')
    queues = [q['QUEUE_NAME'] for q in conf.get('QUEUES')]
    # progress bar
    with tqdm(total=len(queues)+1) as bar:

        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # iterate over queues
        for queue in queues:

            set_bar_desc(bar, f'Shipping {queue} queue')

            # progress bar
            with tqdm(total=5) as queue_bar:

                # send queue-specific install.sh script and configs
                set_bar_desc(queue_bar, 'Sending queue-specific config')
                execute(fab.rm_rf, '~/verdi/ops/install.sh', roles=[comp])
                execute(fab.rm_rf, '~/verdi/etc/datasets.json', roles=[comp])
                execute(fab.rm_rf, '~/verdi/etc/supervisord.conf',
                        roles=[comp])
                execute(fab.rm_rf, '~/verdi/etc/supervisord.conf.tmpl',
                        roles=[comp])
                execute(fab.send_queue_config, queue, roles=[comp])
                execute(fab.chmod, '755',
                        '~/verdi/ops/install.sh', roles=[comp])
                execute(fab.chmod, '644',
                        '~/verdi/etc/datasets.json', roles=[comp])
                queue_bar.update()

                # copy config
                set_bar_desc(queue_bar, 'Copying config')
                execute(fab.rm_rf, '~/verdi/ops/etc', roles=[comp])
                execute(fab.cp_rp, '~/verdi/etc', '~/verdi/ops/', roles=[comp])
                queue_bar.update()

                # copy creds
                set_bar_desc(queue_bar, 'Copying creds')
                execute(fab.rm_rf, '~/verdi/ops/creds', roles=[comp])
                execute(fab.mkdir, '~/verdi/ops/creds',
                        'ops', 'ops', roles=[comp])
                execute(fab.cp_rp_exists, '~/.netrc.verdi',
                        '~/verdi/ops/creds/.netrc', roles=[comp])
                execute(fab.cp_rp_exists, '~/.netrc-os',
                        '~/verdi/ops/creds/.netrc-os', roles=[comp])
                execute(fab.cp_rp_exists, '~/.boto.verdi',
                        '~/verdi/ops/creds/.boto', roles=[comp])
                execute(fab.cp_rp_exists, '~/.s3cfg.verdi',
                        '~/verdi/ops/creds/.s3cfg', roles=[comp])
                execute(fab.cp_rp_exists, '~/.aws.verdi',
                        '~/verdi/ops/creds/.aws', roles=[comp])
                queue_bar.update()

                # send work directory stylesheets
                style_tar = os.path.join(
                    get_user_files_path(), 'beefed-autoindex-open_in_new_win.tbz2')
                set_bar_desc(queue_bar, 'Sending work dir stylesheets')
                execute(
                    fab.rm_rf, '~/verdi/ops/beefed-autoindex-open_in_new_win.tbz2', roles=[comp])
                execute(fab.copy, style_tar,
                        '~/verdi/ops/beefed-autoindex-open_in_new_win.tbz2', roles=[comp])
                queue_bar.update()

                # create venue bundle
                set_bar_desc(queue_bar, 'Creating/shipping bundle')
                execute(fab.mkdir, '~/code_configs',
                        'ops', 'ops', roles=[comp])
                execute(
                    fab.rm_rf, f'~/code_configs/{queue}-{venue}.tbz2', roles=[comp])
                execute(fab.ship_code, '~/verdi/ops',
                        f'~/code_configs/{queue}-{venue}.tbz2', encrypt, roles=[comp])
                queue_bar.update()
            bar.update()
        set_bar_desc(bar, 'Finished shipping')
        print("")


def ship(encrypt, debug=False):
    """Update components."""

    # get user's SDS conf settings
    conf = SettingsConf()

    if debug:
        ship_verdi(conf, encrypt)
    else:
        with hide('everything'):
            ship_verdi(conf, encrypt)


def import_kibana(comp='grq'):
    """"Update metrics component."""

    with tqdm(total=4) as bar:  # progress bar
        # ensure venv
        set_bar_desc(bar, 'Ensuring HySDS venv')
        execute(fab.ensure_venv, comp, roles=[comp])
        bar.update()

        # create kibana metrics
        set_bar_desc(bar, 'creating kibana metrics')
        execute(fab.rm_rf, '~/metrics/ops/kibana_metrics', roles=[comp])
        execute(fab.mkdir, '~/metrics/ops/kibana_metrics',
                'ops', 'ops', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'copying over dashboards and scripts')

        if fab.grq_es_engine == "opensearch":
            execute(fab.send_template_user_override, 'import_dashboard.sh.tmpl',
                    '~/metrics/ops/kibana_metrics/import_dashboard.sh',
                    '~/.sds/files/opensearch_dashboards_import',
                    roles=[comp])
            execute(fab.chmod, 755,
                    '~/metrics/ops/kibana_metrics/import_dashboard.sh', roles=[comp])
            execute(fab.copy, '~/.sds/files/opensearch_dashboards_import/job-dashboards.json',
                    '~/metrics/ops/kibana_metrics/job-dashboards.json', roles=[comp])
            execute(fab.copy, '~/.sds/files/opensearch_dashboards_import/worker-dashboards.json',
                    '~/metrics/ops/kibana_metrics/worker-dashboards.json', roles=[comp])
            execute(fab.copy, '~/.sds/files/opensearch_dashboards_import/sdswatch-dashboards.json',
                    '~/metrics/ops/kibana_metrics/sdswatch-dashboards.json', roles=[comp])
            execute(fab.copy, '~/.sds/files/opensearch_dashboards_import/wait-for-it.sh',
                    '~/metrics/ops/kibana_metrics/wait-for-it.sh', roles=[comp])
            execute(fab.chmod, 755,
                    '~/metrics/ops/kibana_metrics/wait-for-it.sh', roles=[comp])
        else:
            execute(fab.send_template_user_override, 'import_dashboard.sh.tmpl',
                    '~/metrics/ops/kibana_metrics/import_dashboard.sh',
                    '~/.sds/files/kibana_dashboard_import',
                    roles=[comp])
            execute(fab.chmod, 755,
                    '~/metrics/ops/kibana_metrics/import_dashboard.sh', roles=[comp])
            execute(fab.copy, '~/.sds/files/kibana_dashboard_import/job-dashboards.json',
                    '~/metrics/ops/kibana_metrics/job-dashboards.json', roles=[comp])
            execute(fab.copy, '~/.sds/files/kibana_dashboard_import/worker-dashboards.json',
                    '~/metrics/ops/kibana_metrics/worker-dashboards.json', roles=[comp])
            execute(fab.copy, '~/.sds/files/kibana_dashboard_import/sdswatch-dashboards.json',
                    '~/metrics/ops/kibana_metrics/sdswatch-dashboards.json', roles=[comp])
            execute(fab.copy, '~/.sds/files/kibana_dashboard_import/wait-for-it.sh',
                    '~/metrics/ops/kibana_metrics/wait-for-it.sh', roles=[comp])
            execute(fab.chmod, 755,
                    '~/metrics/ops/kibana_metrics/wait-for-it.sh', roles=[comp])
        bar.update()
        set_bar_desc(bar, 'importing dashboards and other saved objects')
        execute(fab.import_kibana,
                '~/metrics/ops/kibana_metrics', roles=[comp])
        bar.update()


def process_kibana_job(job_type, conf):
    if job_type.lower() == "import":
        import_kibana()
    else:
        logger.debug("Not implemented %s" % job_type)


def kibana(job_type, debug=False, force=False):
    """Update components."""

    if not force:  # prompt user
        cont = prompt(get_prompt_tokens=lambda x: [(Token.Alert,
                                                    f"Updating Kibana: {job_type}. Continue [y/n]: "), (Token, " ")],
                      validator=YesNoValidator(), style=prompt_style) == 'y'
        if not cont:
            return 0

    # get user's SDS conf settings
    conf = SettingsConf()

    logger.debug("Processing %s" % job_type)

    if debug:
        process_kibana_job(job_type, conf)
    else:
        with hide('everything'):
            process_kibana_job(job_type, conf)
