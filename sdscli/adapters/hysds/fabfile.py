"""
Fabric file for HySDS.
"""
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from sdscli.prompt_utils import highlight, blink
from sdscli.conf_utils import get_user_config_path, get_user_files_path
from sdscli.log_utils import logger
from fabric.contrib.project import rsync_project
from fabric.contrib.files import upload_template, exists, append
from fabric.api import run, cd, put, sudo, prefix, env, settings, hide
from copy import deepcopy
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context
import urllib3
import json
import yaml
import re
import os
from builtins import open
from future import standard_library

standard_library.install_aliases()


# class for custom cipher for rabbitmq
class CustomCipherAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ssl_context = create_urllib3_context(ciphers="DHE-RSA-AES128-GCM-SHA256")
        kwargs['ssl_context'] = ssl_context
        return super(CustomCipherAdapter, self).init_poolmanager(*args, **kwargs)


# ssh_opts and extra_opts for rsync and rsync_project
ssh_opts = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
extra_opts = "-k"

# repo regex
repo_re = re.compile(r'.+//.*?/(.*?)/(.*?)(?:\.git)?$')

# define private EC2 IP addresses for infrastructure hosts
this_dir = os.path.dirname(os.path.abspath(__file__))
sds_cfg = get_user_config_path()
if not os.path.isfile(sds_cfg):
    raise RuntimeError(
        "SDS configuration file doesn't exist. Run 'sds configure'.")

with open(sds_cfg) as f:
    context = yaml.load(f, Loader=yaml.FullLoader)

# define and build groups to reduce redundancy in defining roles

# mozart hosts
mozart_es_engine = context.get("MOZART_ES_ENGINE", "elasticsearch")
mozart_host = '%s' % context['MOZART_PVT_IP']
mozart_rabbit_host = '%s' % context['MOZART_RABBIT_PVT_IP']
mozart_redis_host = '%s' % context['MOZART_REDIS_PVT_IP']
mozart_es_host = '%s' % context['MOZART_ES_PVT_IP']

# metrics host
metrics_es_engine = context.get("METRICS_ES_ENGINE", "elasticsearch")
metrics_host = '%s' % context['METRICS_PVT_IP']
metrics_redis_host = '%s' % context['METRICS_REDIS_PVT_IP']
metrics_es_host = '%s' % context['METRICS_ES_PVT_IP']

# grq host
grq_es_engine = context.get("GRQ_ES_ENGINE", "elasticsearch")
grq_host = '%s' % context['GRQ_PVT_IP']
grq_es_host = '%s' % context['GRQ_ES_PVT_IP']

# factotum host
factotum_host = '%s' % context['FACTOTUM_PVT_IP']

# continuous integration host
ci_host = '%s' % context['CI_PVT_IP']

# all verdi hosts
verdi_hosts = [
    '%s' % context['VERDI_PVT_IP'],
]
if context.get('OTHER_VERDI_HOSTS', None) is not None:
    verdi_hosts.extend([i['VERDI_PVT_IP']
                        for i in context['OTHER_VERDI_HOSTS'] if i['VERDI_PVT_IP'] is not None])

# define roles
env.roledefs = {
    'mozart': [mozart_host],
    'mozart-rabbit': [mozart_rabbit_host],
    'mozart-redis': [mozart_redis_host],
    'mozart-es': mozart_es_host if type(mozart_es_host) is list else [mozart_es_host],
    'metrics': [metrics_host],
    'metrics-redis': [metrics_redis_host],
    'metrics-es': metrics_es_host if type(metrics_es_host) is list else [metrics_es_host],
    'grq': [grq_host],
    'grq-es': grq_es_host if type(grq_es_host) is list else [grq_es_host],
    'factotum': [factotum_host],
    'ci': [ci_host],
    'verdi': verdi_hosts,
}

# define key file
env.key_filename = context['KEY_FILENAME']
if not os.path.isfile(env.key_filename):
    raise RuntimeError("SSH key filename %s doesn't exist. " % env.key_filename +
                       "Run 'ssh-keygen -t rsa' or copy existing key.")

# abort on prompts (password, hosts, etc.)
env.abort_on_prompts = True

# do all tasks in parallel
env.parallel = True

# set connection timeout
env.timeout = 60

# define ops home directory
ops_dir = context['OPS_HOME']


##########################
# general functions
##########################
def get_context(node_type=None):
    """Modify context based on host string."""

    ctx = deepcopy(context)

    if node_type == 'mozart':
        if ctx['MOZART_PVT_IP'] == ctx['MOZART_RABBIT_PVT_IP']:
            ctx['MOZART_RABBIT_PVT_IP'] = "127.0.0.1"
        if ctx['MOZART_PVT_IP'] == ctx['MOZART_REDIS_PVT_IP']:
            ctx['MOZART_REDIS_PVT_IP'] = "127.0.0.1"
        if ctx['MOZART_PVT_IP'] == ctx['MOZART_ES_PVT_IP']:
            ctx['MOZART_ES_PVT_IP'] = "127.0.0.1"

    if node_type == 'metrics':
        if ctx['METRICS_PVT_IP'] == ctx['METRICS_REDIS_PVT_IP']:
            ctx['METRICS_REDIS_PVT_IP'] = "127.0.0.1"
        if ctx['METRICS_PVT_IP'] == ctx['METRICS_ES_PVT_IP']:
            ctx['METRICS_ES_PVT_IP'] = "127.0.0.1"

    if node_type == 'grq':
        if ctx['GRQ_PVT_IP'] == ctx['GRQ_ES_PVT_IP']:
            ctx['GRQ_ES_PVT_IP'] = "127.0.0.1"

    # set redis passwords
    if ctx['MOZART_REDIS_PASSWORD'] is None:
        ctx['MOZART_REDIS_PASSWORD'] = ''
    if ctx['METRICS_REDIS_PASSWORD'] is None:
        ctx['METRICS_REDIS_PASSWORD'] = ''

    # set hostname
    ctx['HOST_STRING'] = env.host_string

    # split LDAP groups
    ctx['LDAP_GROUPS'] = [i.strip() for i in ctx['LDAP_GROUPS'].split(',')]

    return ctx


def resolve_files_dir(fname, files_dir):
    """Resolve file or template from user SDS files or default location."""

    user_path = get_user_files_path()
    return user_path if os.path.exists(os.path.join(user_path, fname)) else files_dir


def resolve_role():
    """Resolve role and hysds directory."""

    for role in env.effective_roles:
        if env.host_string in env.roledefs[role]:
            if '@' in env.host_string:
                hostname = env.host_string.split('@')[1]
            else:
                hostname = env.host_string
            break
    if role in ('factotum', 'ci'):
        hysds_dir = "verdi"
    elif role == 'grq':
        hysds_dir = "sciflo"
    else:
        hysds_dir = role
    return role, hysds_dir, hostname


def host_type():
    run('uname -s')


def fqdn():
    run('hostname --fqdn')


def get_ram_size_bytes():
    return run("free -b | grep ^Mem: | awk '{print $2}'")


def yum_update():
    sudo('yum -y -q update')


def yum_install(package):
    sudo('yum -y install %s' % package)


def yum_remove(package):
    sudo('yum -y remove %s' % package)


def ps_x():
    run('ps x')


def df_hv():
    run('df -hv')


def echo(s):
    run('echo "%s"' % s)


def mpstat():
    sudo('mpstat -P ALL 5 1')


def copy(src, dest):
    put(src, dest)


def ln_sf(src, dest):
    if exists(dest):
        run('rm -rf %s' % dest)
    with cd(os.path.dirname(dest)):
        run('ln -sf %s %s' % (src, os.path.basename(dest)))


def cp_rp(src, dest):
    run('cp -rp %s %s' % (src, dest))


def cp_rp_exists(src, dest):
    if exists(src):
        run('cp -rp %s %s' % (src, dest))


def rm_rf(path):
    run('rm -rf %s' % path)


def sudo_rm_rf(path):
    run('sudo rm -rf %s' % path)


def send_template(tmpl, dest, tmpl_dir=None, node_type=None):
    if tmpl_dir is None:
        tmpl_dir = get_user_files_path()
    else:
        tmpl_dir = os.path.expanduser(tmpl_dir)
    upload_template(tmpl, dest, use_jinja=True, context=get_context(node_type),
                    template_dir=tmpl_dir)


def send_template_user_override(tmpl, dest, tmpl_dir=None, node_type=None):
    """
    Write filled-out template to destination using the template found in a specified template directory.
    If template exists in the user files (i.e. ~/.sds/files), that template will be used.
    :param tmpl: template file name
    :param dest: output file name
    :param tmpl_dir: nominal directory containing the template
    :param node_type: node type/role
    :return: None
    """
    if tmpl_dir is None:
        tmpl_dir = get_user_files_path()
    else:
        tmpl_dir = os.path.expanduser(tmpl_dir)
    upload_template(tmpl, dest, use_jinja=True, context=get_context(node_type),
                    template_dir=resolve_files_dir(tmpl, tmpl_dir))


def set_spyddder_settings():
    upload_template('settings.json.tmpl', '~/verdi/ops/spyddder-man/settings.json', use_jinja=True,
                    context=get_context(), template_dir=os.path.join(ops_dir, 'mozart/ops/spyddder-man'))


def rsync_code(node_type, dir_path=None):
    if dir_path is None:
        dir_path = node_type
    rm_rf('%s/ops/osaka' % dir_path)
    rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/osaka'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)
    rm_rf('%s/ops/hysds_commons' % dir_path)
    rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/hysds_commons'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)
    rm_rf('%s/ops/hysds' % dir_path)
    rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/hysds'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)
    rm_rf('%s/ops/prov_es' % dir_path)
    rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/prov_es'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)
    rm_rf('%s/ops/sciflo' % dir_path)
    rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/sciflo'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)
    rm_rf('%s/ops/chimera' % dir_path)
    rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/chimera'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)
    rm_rf('%s/ops/container-builder' % dir_path)
    rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/container-builder'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)
    rm_rf('%s/ops/lightweight-jobs' % dir_path)
    rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/lightweight-jobs'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)
    rm_rf('%s/ops/hysds-dockerfiles' % dir_path)
    rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/hysds-dockerfiles'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)

    if node_type == 'mozart':
        rm_rf('%s/ops/mozart' % dir_path)
        rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/mozart'), extra_opts=extra_opts,
                      ssh_opts=ssh_opts)

    if node_type == 'verdi':
        rm_rf('%s/ops/spyddder-man' % dir_path)
        rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/spyddder-man'), extra_opts=extra_opts,
                      ssh_opts=ssh_opts)

    if node_type == 'factotum':
        rm_rf('%s/ops/spyddder-man' % dir_path)
        rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/spyddder-man'), extra_opts=extra_opts,
                      ssh_opts=ssh_opts)

    if node_type == 'grq':
        rm_rf('%s/ops/grq2' % dir_path)
        rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/grq2'), extra_opts=extra_opts,
                      ssh_opts=ssh_opts)

        rm_rf('%s/ops/pele' % dir_path)
        rsync_project('%s/ops/' % dir_path, os.path.join(ops_dir, 'mozart/ops/pele'), extra_opts=extra_opts,
                      ssh_opts=ssh_opts)


def svn_co(path, svn_url):
    if not exists(path):
        with cd(os.path.dirname(path)):
            run('svn co --non-interactive --trust-server-cert %s' % svn_url)


def svn_rev(rev, path):
    run('svn up -r %s %s' % (rev, path))


def ls(path):
    run('ls -al {}'.format(path))


def cat(path):
    run('cat {}'.format(path))


def tail(path):
    run('tail {}'.format(path))


def tail_f(path):
    run('tail -f {}'.format(path))


def grep(grep_str, dir_path):
    try:
        run('grep -r %s %s' % (grep_str, dir_path))
    except:
        pass


def chmod(perms, path):
    run('chmod -R %s %s' % (perms, path))


def reboot():
    sudo('reboot')


def mkdir(d, o, g):
    # sudo('mkdir -p %s' % d)
    # sudo('chown -R %s:%s %s' % (o, g, d))
    run("mkdir -p %s" % d)


def untar(tarfile, chdir):
    with cd(chdir):
        run('tar xvfj %s' % tarfile)


def untar_gz(cwd, tar_file):
    with cd(cwd):
        run('tar xvfz %s' % tar_file)


def untar_bz(cwd, tar_file):
    with cd(cwd):
        run('tar xvfj %s' % tar_file)


def mv(src, dest):
    sudo('mv -f %s %s' % (src, dest))


def rsync(src, dest):
    rsync_project(dest, src, extra_opts=extra_opts, ssh_opts=ssh_opts)


def remove_docker_images():
    run('docker rmi -f $(docker images -q)')


def remove_running_containers():
    run('docker rm -f $(docker ps -aq)')


def remove_docker_volumes():
    run('docker volume rm $(docker volume ls -q)')


def list_docker_images():
    run('docker images')


def stop_docker_containers():
    run('docker stop $(docker ps -aq)')


def systemctl(cmd, service):
    with settings(warn_only=True):
        with hide('everything'):
            return run('sudo systemctl %s %s' % (cmd, service), pty=False)


def status():
    role, hysds_dir, hostname = resolve_role()
    if exists('%s/run/supervisor.sock' % hysds_dir):
        with prefix('source %s/bin/activate' % hysds_dir):
            run('supervisorctl status')
    else:
        print((blink(highlight("Supervisord is not running on %s." % role, 'red'))))


def ensure_venv(hysds_dir, update_bash_profile=True, system_site_packages=True, install_supervisor=True):
    act_file = "~/%s/bin/activate" % hysds_dir
    if system_site_packages:
        venv_cmd = "virtualenv --system-site-packages %s" % hysds_dir
    else:
        venv_cmd = "virtualenv %s" % hysds_dir
    if not exists(act_file):
        run(venv_cmd)
        with prefix('source %s/bin/activate' % hysds_dir):
            run('pip install -U pip')
            run('pip install -U setuptools')
            if install_supervisor:
                run('pip install --ignore-installed supervisor')
    mkdir('%s/etc' % hysds_dir,
          context['OPS_USER'], context['OPS_USER'])
    mkdir('%s/log' % hysds_dir,
          context['OPS_USER'], context['OPS_USER'])
    mkdir('%s/run' % hysds_dir,
          context['OPS_USER'], context['OPS_USER'])
    if update_bash_profile:
        append('.bash_profile',
               "source $HOME/{}/bin/activate".format(hysds_dir), escape=True)
        append('.bash_profile',
               "export FACTER_ipaddress=$(/usr/sbin/ifconfig $(/usr/sbin/route | awk '/default/{print $NF}') | grep 'inet ' | sed 's/addr://' | awk '{print $2}')",
               escape=True)


def install_pkg_es_templates():
    role, hysds_dir, hostname = resolve_role()
    if role not in ('grq', 'mozart'):
        raise RuntimeError("Invalid fabric function for %s." % role)
    with prefix('source %s/bin/activate' % hysds_dir):
        run('%s/ops/mozart/scripts/install_es_template.sh' % (hysds_dir))


def install_base_es_template():
    role, hysds_dir, hostname = resolve_role()

    send_template(
        "es_template-base.json",
        "/tmp/es_template-base.json"
    )
    dir = role
    if role == "grq":
        dir = "grq2"
    with prefix('source %s/bin/activate' % hysds_dir):
        run(f'{hysds_dir}/ops/{dir}/scripts/install_base_es_template.sh /tmp/es_template-base.json')


def install_es_policy():
    # run(f"curl -XPUT 'localhost:9200/_ilm/policy/ilm_policy_mozart?pretty' -H 'Content-Type: application/json' -d@{target_file}")
    if mozart_es_engine == "opensearch":
        ism_policy_file_name = "opensearch_ism_policy_mozart.json"
        ism_target_file = f"{ops_dir}/mozart/etc/{ism_policy_file_name}"
        send_template(ism_policy_file_name, ism_target_file)

        with cd('~/mozart/ops/hysds/scripts'):
            run(f"python install_ilm_policy.py --ism-policy {ism_target_file}")
    else:
        ilm_policy_file_name = "es_ilm_policy_mozart.json"
        ilm_target_file = f"{ops_dir}/mozart/etc/{ilm_policy_file_name}"
        send_template(ilm_policy_file_name, ilm_target_file)

        with cd('~/mozart/ops/hysds/scripts'):
            run(f"python install_ilm_policy.py --ilm-policy {ilm_target_file}")


def install_mozart_es_templates():
    # install index templates
    # Only job_status.template has ILM policy attached
    # HC-451 will focus on adding ILM to worker, task, and event status indices
    role, hysds_dir, hostname = resolve_role()

    # template files located in ~/.sds/files
    templates = [
        "job_status.template",
        "worker_status.template",
        "task_status.template",
        "event_status.template"
    ]
    target_dir = f"{ops_dir}/mozart/etc"
    for template in templates:
        # Copy templates to etc/ directory
        target_path = f"{ops_dir}/mozart/etc/{template}"
        send_template(template, target_path)
        template_doc_name = template.replace(".template", '')
        print(f"Creating ES index template for {template}")
        # run(f"curl -XPUT 'localhost:9200/_index_template/{template_doc_name}?pretty' "
        #     f"-H 'Content-Type: application/json' -d@{target_path}")
        with cd('~/mozart/ops/hysds/scripts'):
            run(f"python install_job_status_template.py {template_doc_name} {target_path}")


##########################
# grq functions
##########################
def grqd_start(force=False):
    mkdir('sciflo/run', context['OPS_USER'], context['OPS_USER'])
    if not exists('sciflo/run/supervisord.pid') or force:
        with prefix('source sciflo/bin/activate'):
            run('supervisord', pty=False)


def grqd_clean_start():
    run('rm -rf %s/sciflo/log/*' % ops_dir)
    # with prefix('source %s/sciflo/bin/activate' % ops_dir):
    #    with cd(os.path.join(ops_dir, 'sciflo/ops/grq2/scripts')):
    #        run('./reset_dumby_indices.sh')
    grqd_start(True)


def grqd_stop():
    if exists('sciflo/run/supervisor.sock'):
        with prefix('source sciflo/bin/activate'):
            run('supervisorctl shutdown')


def install_es_template():
    with prefix('source sciflo/bin/activate'):
        run('sciflo/ops/grq2/scripts/install_es_template.sh')


def clean_hysds_ios():
    with prefix('source sciflo/bin/activate'):
        run('sciflo/ops/grq2/scripts/clean_hysds_ios_indexes.sh https://localhost:9200')


def create_grq_user_rules_index():
    with prefix('source ~/sciflo/bin/activate'):
        with cd('~/sciflo/ops/grq2/scripts'):
            run('./create_user_rules_index.py')


def create_hysds_ios_grq_index():
    with prefix('source ~/sciflo/bin/activate'):
        with cd('~/sciflo/ops/grq2/scripts'):
            run('./create_hysds_ios_index.py')


def install_ingest_pipeline():
    with cd('~/sciflo/ops/grq2/scripts'):
        run('python install_ingest_pipeline.py')


##########################
# mozart functions
##########################
def mozartd_start(force=False):
    if not exists('mozart/run/supervisord.pid') or force:
        with prefix('source mozart/bin/activate'):
            run('supervisord', pty=False)


def mozartd_clean_start():
    run('rm -rf %s/mozart/log/*' % ops_dir)
    mozartd_start(True)


def mozartd_stop():
    if exists('mozart/run/supervisor.sock'):
        with prefix('source mozart/bin/activate'):
            run('supervisorctl shutdown')


def redis_flush():
    role, hysds_dir, hostname = resolve_role()
    ctx = get_context()
    if role == 'mozart' and ctx['MOZART_REDIS_PASSWORD'] != '':
        cmd = 'redis-cli -a {MOZART_REDIS_PASSWORD} flushall'.format(**ctx)
    elif role == 'metrics' and ctx['METRICS_REDIS_PASSWORD'] != '':
        cmd = 'redis-cli -a {METRICS_REDIS_PASSWORD} flushall'.format(**ctx)
    else:
        cmd = 'redis-cli flushall'.format(**ctx)
    run(cmd)


def mozart_redis_flush():
    ctx = get_context()
    if ctx['MOZART_REDIS_PASSWORD'] != '':
        run('redis-cli -a {MOZART_REDIS_PASSWORD} -h {MOZART_REDIS_PVT_IP} flushall'.format(**ctx))
    else:
        run('redis-cli -h {MOZART_REDIS_PVT_IP} flushall'.format(**ctx))


def rabbitmq_queues_flush():
    ctx = get_context()

    # Create a session and mount the adapter
    session = requests.Session()
    session.mount("https://", CustomCipherAdapter())

    url = 'https://%s:15672/api/queues' % ctx['MOZART_RABBIT_FQDN']

    r = session.get('%s?columns=name' % url,
                     auth=(ctx['MOZART_RABBIT_USER'], ctx['MOZART_RABBIT_PASSWORD']),
                     verify='/etc/pki/tls/certs/ca-bundle.crt')
    r.raise_for_status()
    res = r.json()
    for i in res:
        r = requests.delete('%s/%%2f/%s' % (url, i['name']),
                            auth=(ctx['MOZART_RABBIT_USER'], ctx['MOZART_RABBIT_PASSWORD']))
        r.raise_for_status()
        logger.debug("Deleted queue %s." % i['name'])


def mozart_es_flush():
    ctx = get_context()
    # run('curl -XDELETE http://{MOZART_ES_PVT_IP}:9200/_index_template/*_status'.format(**ctx))
    run('~/mozart/ops/hysds/scripts/clean_indices_from_alias.py job_status-current'.format(**ctx))
    run('~/mozart/ops/hysds/scripts/clean_indices_from_alias.py task_status-current'.format(**ctx))
    run('~/mozart/ops/hysds/scripts/clean_indices_from_alias.py event_status-current'.format(**ctx))
    run('~/mozart/ops/hysds/scripts/clean_indices_from_alias.py worker_status-current'.format(**ctx))
    # run('~/mozart/ops/hysds/scripts/clean_job_spec_container_indexes.sh http://{MOZART_ES_PVT_IP}:9200'.format(**ctx))


def npm_install_package_json(dest):
    with cd(dest):
        run('npm install --silent')


##########################
# metrics functions
##########################
def metricsd_start(force=False):
    if not exists('metrics/run/supervisord.pid') or force:
        with prefix('source metrics/bin/activate'):
            run('supervisord', pty=False)


def metricsd_clean_start():
    run('rm -rf /home/ops/metrics/log/*')
    metricsd_start(True)


def metricsd_stop():
    if exists('metrics/run/supervisor.sock'):
        with prefix('source metrics/bin/activate'):
            run('supervisorctl shutdown')


##########################
# verdi functions
##########################

def kill_hung():
    try:
        run(
            'ps x | grep [j]ob_worker | awk \'{print $1}\' | xargs kill -TERM', quiet=True)
    except:
        pass
    try:
        run(
            'ps x | grep [s]flExec | awk \'{print $1}\' | xargs kill -TERM', quiet=True)
    except:
        pass
    try:
        run(
            'ps x | grep [s]flExec | awk \'{print $1}\' | xargs kill -KILL', quiet=True)
    except:
        pass
    ps_x()


def import_kibana(path):
    with cd(path):
        run("./import_dashboard.sh")


def verdid_start(force=False):
    if not exists('verdi/run/supervisord.pid') or force:
        with prefix('source verdi/bin/activate'):
            run('supervisord', pty=False)


def verdid_clean_start():
    run('rm -rf /data/work/scifloWork-ops/* /data/work/jobs/* /data/work/cache/* %s/verdi/log/*' % ops_dir)
    verdid_start(True)


def verdid_stop():
    if exists('verdi/run/supervisor.sock'):
        with prefix('source verdi/bin/activate'):
            run('supervisorctl shutdown')


def supervisorctl_up():
    with prefix('source verdi/bin/activate'):
        run('supervisorctl reread')
        run('supervisorctl update')


def supervisorctl_status():
    with prefix('source verdi/bin/activate'):
        run('supervisorctl status')


def pip_install(pkg, node_type='verdi'):
    with prefix('source ~/%s/bin/activate' % node_type):
        run('pip install %s' % pkg)


def pip_upgrade(pkg, node_type='verdi'):
    with prefix('source ~/%s/bin/activate' % node_type):
        run('pip install -U %s' % pkg)


def pip_uninstall(pkg, node_type='verdi'):
    with prefix('source ~/%s/bin/activate' % node_type):
        run('pip uninstall -y %s' % pkg)


def pip_install_with_req(node_type, dest):
    with prefix('source ~/%s/bin/activate' % node_type):
        with cd(dest):
            run('pip install -e .')


def pip_install_with_req(node_type, dest, ndeps):
    with prefix('source ~/%s/bin/activate' % node_type):
        with cd(dest):
            if ndeps:
                logger.debug("ndeps is set, so running pip with --no-deps")
                run('pip install --no-deps -e .')
            else:
                logger.debug(
                    "ndeps is NOT set, so running pip without --no-deps")
                run('pip install -e .')


def python_setup_develop(node_type, dest):
    with prefix('source ~/%s/bin/activate' % node_type):
        with cd(dest):
            run('python setup.py develop')


##########################
# ci functions
##########################


def get_ci_job_info(repo, branch=None):
    ctx = get_context()
    match = repo_re.search(repo)
    if not match:
        raise RuntimeError("Failed to parse repo owner and name: %s" % repo)
    owner, name = match.groups()
    if branch is None:
        job_name = "%s_container-builder_%s_%s" % (ctx['VENUE'], owner, name)
        config_tmpl = 'config.xml'
    else:
        job_name = "%s_container-builder_%s_%s_%s" % (
            ctx['VENUE'], owner, name, branch)
        config_tmpl = 'config-branch.xml'
    return job_name, config_tmpl


def add_ci_job(repo, proto, branch=None, release=False):
    with settings(sudo_user=context["JENKINS_USER"]):
        job_name, config_tmpl = get_ci_job_info(repo, branch)
        ctx = get_context()
        ctx['PROJECT_URL'] = repo
        ctx['BRANCH'] = branch
        job_dir = '%s/jobs/%s' % (ctx['JENKINS_DIR'], job_name)
        dest_file = '%s/config.xml' % job_dir
        mkdir(job_dir, None, None)
        chmod('777', job_dir)
        if release:
            ctx['BRANCH_SPEC'] = "origin/tags/release-*"
        else:
            ctx['BRANCH_SPEC'] = "**"
        if proto in ('s3', 's3s'):
            ctx['STORAGE_URL'] = "%s://%s/%s/" % (
                proto, ctx['S3_ENDPOINT'], ctx['CODE_BUCKET'])
        elif proto == 'gs':
            ctx['STORAGE_URL'] = "%s://%s/%s/" % (
                proto, ctx['GS_ENDPOINT'], ctx['CODE_BUCKET'])
        elif proto in ('dav', 'davs'):
            ctx['STORAGE_URL'] = "%s://%s:%s@%s/repository/products/containers/" % \
                                 (proto, ctx['DAV_USER'],
                                  ctx['DAV_PASSWORD'], ctx['DAV_SERVER'])
        else:
            raise RuntimeError(
                "Unrecognized storage type for containers: %s" % proto)
        upload_template(config_tmpl, "tmp-jenkins-upload", use_jinja=True, context=ctx,
                        template_dir=get_user_files_path())
        cp_rp("tmp-jenkins-upload", dest_file)
        run("rm tmp-jenkins-upload")


def add_ci_job_release(repo, proto):
    add_ci_job(repo, proto, release=True)


def run_jenkins_cli(cmd):
    ctx = get_context()
    juser = ctx.get("JENKINS_API_USER", "").strip()
    jkey = ctx.get("JENKINS_API_KEY", "").strip()
    if juser == "" or jkey == "":
        raise RuntimeError(
            "An API user/key is needed for Jenkins.  Reload manually or specify one.")
    with prefix('source verdi/bin/activate'):
        run('java -jar %s/war/WEB-INF/jenkins-cli.jar -s http://localhost:8080 -http -auth %s:%s %s' %
            (ctx['JENKINS_DIR'], juser, jkey, cmd))


def reload_configuration():
    run_jenkins_cli('reload-configuration')


def build_ci_job(repo, branch=None):
    job_name, config_tmpl = get_ci_job_info(repo, branch)
    run_jenkins_cli('build %s -s -v' % job_name)


def remove_ci_job(repo, branch=None):
    job_name, config_tmpl = get_ci_job_info(repo, branch)
    run_jenkins_cli('delete-job %s' % job_name)


##########################
# logstash functions
##########################

def send_shipper_conf(node_type, log_dir, cluster_jobs, redis_ip_job_status,
                      cluster_metrics, redis_ip_metrics):
    role, hysds_dir, hostname = resolve_role()

    ctx = get_context(node_type)
    ctx.update({'cluster_jobs': cluster_jobs,
                'cluster_metrics': cluster_metrics})
    if node_type == 'mozart':
        upload_template('indexer.conf.mozart', '~/mozart/etc/indexer.conf', use_jinja=True, context=ctx,
                        template_dir=os.path.join(ops_dir, 'mozart/ops/hysds/configs/logstash'))
        upload_template('sdswatch_client.conf', '~/mozart/etc/sdswatch_client.conf', use_jinja=True,
                        context=ctx, template_dir=os.path.join(ops_dir, 'mozart/ops/hysds/configs/logstash'))
        if mozart_es_engine == "opensearch":
            send_template("run_sdswatch_client_opensearch.sh", "~/mozart/bin/run_sdswatch_client.sh")
        else:
            send_template("run_sdswatch_client.sh", "~/mozart/bin/run_sdswatch_client.sh")
        run("chmod 755 ~/mozart/bin/run_sdswatch_client.sh")
        send_template("watch_supervisord_services.py", "~/mozart/bin/watch_supervisord_services.py")
        run("chmod 755 ~/mozart/bin/watch_supervisord_services.py")
        send_template("watch_systemd_services.py", "~/mozart/bin/watch_systemd_services.py")
        run("chmod 755 ~/mozart/bin/watch_systemd_services.py")
    elif node_type == 'metrics':
        upload_template('indexer.conf.metrics', '~/metrics/etc/indexer.conf', use_jinja=True, context=ctx,
                        template_dir=os.path.join(ops_dir, 'mozart/ops/hysds/configs/logstash'))
        upload_template('sdswatch_client.conf', '~/metrics/etc/sdswatch_client.conf', use_jinja=True,
                        context=ctx, template_dir=os.path.join(ops_dir, 'mozart/ops/hysds/configs/logstash'))
        if metrics_es_engine == "opensearch":
            send_template("run_sdswatch_client_opensearch.sh", "~/metrics/bin/run_sdswatch_client.sh")
        else:
            send_template("run_sdswatch_client.sh", "~/metrics/bin/run_sdswatch_client.sh")
        run("chmod 755 ~/metrics/bin/run_sdswatch_client.sh")
        send_template("watch_supervisord_services.py", "~/metrics/bin/watch_supervisord_services.py")
        run("chmod 755 ~/metrics/bin/watch_supervisord_services.py")
        send_template("watch_systemd_services.py", "~/metrics/bin/watch_systemd_services.py")
        run("chmod 755 ~/metrics/bin/watch_systemd_services.py")
    elif node_type == 'grq':
        upload_template('sdswatch_client.conf', '~/sciflo/etc/sdswatch_client.conf', use_jinja=True,
                        context=ctx, template_dir=os.path.join(ops_dir, 'mozart/ops/hysds/configs/logstash'))
        if grq_es_engine == "opensearch":
            send_template("run_sdswatch_client_opensearch.sh", "~/sciflo/bin/run_sdswatch_client.sh")
        else:
            send_template("run_sdswatch_client.sh", "~/sciflo/bin/run_sdswatch_client.sh")
        run("chmod 755 ~/sciflo/bin/run_sdswatch_client.sh")
        send_template("watch_supervisord_services.py", "~/sciflo/bin/watch_supervisord_services.py")
        run("chmod 755 ~/sciflo/bin/watch_supervisord_services.py")
        send_template("watch_systemd_services.py", "~/sciflo/bin/watch_systemd_services.py")
        run("chmod 755 ~/sciflo/bin/watch_systemd_services.py")
    elif node_type in ('verdi', 'verdi-asg', 'factotum'):
        upload_template('sdswatch_client.conf', '~/verdi/etc/sdswatch_client.conf', use_jinja=True,
                        context=ctx, template_dir=os.path.join(ops_dir, 'mozart/ops/hysds/configs/logstash'))
        if metrics_es_engine == "opensearch":
            send_template("run_sdswatch_client_opensearch.sh", "~/verdi/bin/run_sdswatch_client.sh")
        else:
            send_template("run_sdswatch_client.sh", "~/verdi/bin/run_sdswatch_client.sh")
        run("chmod 755 ~/verdi/bin/run_sdswatch_client.sh")
        send_template("watch_supervisord_services.py", "~/verdi/bin/watch_supervisord_services.py")
        run("chmod 755 ~/verdi/bin/watch_supervisord_services.py")
        send_template("watch_systemd_services.py", "~/verdi/bin/watch_systemd_services.py")
        run("chmod 755 ~/verdi/bin/watch_systemd_services.py")
    else:
        raise RuntimeError("Unknown node type: %s" % node_type)


def send_logstash_jvm_options(node_type):
    ctx = get_context(node_type)
    ram_size_gb = int(get_ram_size_bytes()) // 1024 ** 3
    echo("instance RAM size: {}GB".format(ram_size_gb))
    ram_size_gb_half = int(ram_size_gb // 2)
    ctx['LOGSTASH_HEAP_SIZE'] = 8 if ram_size_gb_half >= 8 else ram_size_gb_half
    echo("configuring logstash heap size: {}GB".format(ctx['LOGSTASH_HEAP_SIZE']))
    upload_template('jvm.options', '~/logstash/config/jvm.options',
                    use_jinja=True, context=ctx, template_dir=get_user_files_path())


##########################
# hysds config functions
##########################

def send_celeryconf(node_type):
    ctx = get_context(node_type)
    template_dir = os.path.join(ops_dir, 'mozart/ops/hysds/configs/celery')
    if node_type == 'mozart':
        base_dir = "mozart"
    elif node_type == 'metrics':
        base_dir = "metrics"
    elif node_type in ('verdi', 'verdi-asg'):
        base_dir = "verdi"
    elif node_type == 'grq':
        base_dir = "sciflo"
    else:
        raise RuntimeError("Unknown node type: %s" % node_type)
    tmpl = 'celeryconfig.py.tmpl'
    user_path = get_user_files_path()
    if node_type == 'verdi-asg':
        tmpl_asg = 'celeryconfig.py.tmpl.asg'
        if os.path.exists(os.path.join(user_path, tmpl_asg)):
            tmpl = tmpl_asg
    dest_file = '~/%s/ops/hysds/celeryconfig.py' % base_dir
    upload_template(tmpl, dest_file, use_jinja=True, context=ctx,
                    template_dir=resolve_files_dir(tmpl, template_dir))


def send_mozartconf():
    dest_file = '~/mozart/ops/mozart/settings.cfg'
    upload_template('settings.cfg.tmpl', dest_file, use_jinja=True, context=get_context('mozart'),
                    template_dir=os.path.join(ops_dir, 'mozart/ops/mozart/settings'))
    with prefix('source ~/mozart/bin/activate'):
        with cd('~/mozart/ops/mozart'):
            mkdir('~/mozart/ops/mozart/data',
                  context['OPS_USER'], context['OPS_USER'])
            run('./db_create.py')


def send_hysds_ui_conf():
    dest_file = '~/mozart/ops/hysds_ui/src/config/index.js'
    upload_template('index.template.js', dest_file, use_jinja=True, context=get_context('mozart'),
                    template_dir=os.path.join(ops_dir, 'mozart/ops/hysds_ui/src/config'))

    user_path = get_user_files_path()

    tosca_cfg = '~/mozart/etc/tosca.js'
    if os.path.exists(os.path.join(user_path, 'tosca.js')):
        print('using custom tosca configuration in .sds/files')
        send_template_user_override('tosca.js', tosca_cfg, node_type='mozart')
    else:
        print('using default tosca configuration')
        send_template_user_override('tosca.template.js', tosca_cfg,
                                    tmpl_dir=os.path.join(ops_dir, 'mozart/ops/hysds_ui/src/config'),
                                    node_type='mozart')

    figaro_cfg = '~/mozart/etc/figaro.js'
    if os.path.exists(os.path.join(user_path, 'figaro.js')):
        print('using custom figaro configuration in .sds/files')
        send_template_user_override('figaro.js', figaro_cfg, node_type='mozart')
    else:
        print('using default figaro configuration')
        send_template_user_override('figaro.template.js', figaro_cfg,
                                    tmpl_dir=os.path.join(ops_dir, 'mozart/ops/hysds_ui/src/config'),
                                    node_type='mozart')

    # symlink to ~/mozart/ops/hysds_ui/src/config/
    ln_sf(tosca_cfg, os.path.join(ops_dir, 'mozart/ops/hysds_ui/src/config', 'tosca.js'))
    ln_sf(figaro_cfg, os.path.join(ops_dir, 'mozart/ops/hysds_ui/src/config', 'figaro.js'))


def send_grq2conf():
    dest_file = '~/sciflo/ops/grq2/settings.cfg'
    upload_template('settings.cfg.tmpl', dest_file, use_jinja=True, context=get_context('grq'),
                    template_dir=os.path.join(ops_dir, 'mozart/ops/grq2/config'))


def send_peleconf(send_file='settings.cfg.tmpl', template_dir=get_user_files_path()):
    tmpl_dir = os.path.expanduser(template_dir)
    dest_file = '~/sciflo/ops/pele/settings.cfg'
    upload_template(send_file, dest_file, use_jinja=True, context=get_context('grq'),
                    template_dir=tmpl_dir)
    with prefix('source ~/sciflo/bin/activate'):
        with cd('~/sciflo/ops/pele'):
            run('flask create-db')
            run('flask db init', warn_only=True)
            run('flask db migrate', warn_only=True)


def build_hysds_ui():
    with cd('~/mozart/ops/hysds_ui'):
        run('npm run build')


def create_user_rules_index():
    with prefix('source ~/mozart/bin/activate'):
        with cd('~/mozart/ops/mozart/scripts'):
            run('./create_user_rules_index.py')


def create_hysds_ios_index():
    with prefix('source ~/mozart/bin/activate'):
        with cd('~/mozart/ops/mozart/scripts'):
            run('./create_hysds_ios_index.py')


def send_hysds_scripts(node_type):
    role, hysds_dir, hostname = resolve_role()

    if node_type == 'mozart':
        send_template("run_docker_registry.sh", "~/mozart/bin/run_docker_registry.sh")
        run("chmod 755 ~/mozart/bin/run_docker_registry.sh")
    elif node_type == 'metrics':
        send_template("run_docker_registry.sh", "~/metrics/bin/run_docker_registry.sh")
        run("chmod 755 ~/metrics/bin/run_docker_registry.sh")
    elif node_type == 'grq':
        send_template("run_docker_registry.sh", "~/sciflo/bin/run_docker_registry.sh")
        run("chmod 755 ~/sciflo/bin/run_docker_registry.sh")
    elif node_type in ('verdi', 'verdi-asg', 'factotum'):
        send_template("run_docker_registry.sh", "~/verdi/bin/run_docker_registry.sh")
        run("chmod 755 ~/verdi/bin/run_docker_registry.sh")
    else:
        raise RuntimeError("Unknown node type: %s" % node_type)


##########################
# self-signed SSL certs
##########################

def ensure_ssl(node_type):
    ctx = get_context(node_type)
    if node_type == "grq":
        commonName = ctx['GRQ_FQDN']
    elif node_type == "mozart":
        commonName = ctx['MOZART_FQDN']
    else:
        raise RuntimeError("Unknown node type: %s" % node_type)
    if not exists('ssl/server.key') or not exists('ssl/server.pem'):
        mkdir('ssl', context['OPS_USER'], context['OPS_USER'])
        upload_template('ssl_server.cnf', 'ssl/server.cnf', use_jinja=True,
                        context={'commonName': commonName},
                        template_dir=get_user_files_path())
        with cd('ssl'):
            run('openssl genrsa -des3 -passout pass:hysds -out server.key 1024', pty=False)
            run('OPENSSL_CONF=server.cnf openssl req -passin pass:hysds -new -key server.key -out server.csr',
                pty=False)
            run('cp server.key server.key.org')
            run('openssl rsa -passin pass:hysds -in server.key.org -out server.key', pty=False)
            run('chmod 600 server.key*')
            run('openssl x509 -passin pass:hysds -req -days 99999 -in server.csr -signkey server.key -out server.pem',
                pty=False)


##########################
# ship code
##########################
def ship_code(cwd, tar_file, encrypt=False):
    ctx = get_context()
    with cd(cwd):
        run('tar --exclude-vcs -cvjf %s *' % tar_file)
    if encrypt is False:
        run('aws s3 cp %s s3://%s/' % (tar_file, ctx['CODE_BUCKET']))
    else:
        run('aws s3 cp --sse %s s3://%s/' % (tar_file, ctx['CODE_BUCKET']))


##########################
# ship creds
##########################
def send_awscreds(suffix=None):
    ctx = get_context()
    if suffix is None:
        aws_dir = '.aws'
        boto_file = '.boto'
        s3cfg_file = '.s3cfg'
    else:
        aws_dir = '.aws{}'.format(suffix)
        boto_file = '.boto{}'.format(suffix)
        s3cfg_file = '.s3cfg{}'.format(suffix)
    if exists(aws_dir):
        run('rm -rf {}'.format(aws_dir))
    mkdir(aws_dir, context['OPS_USER'], context['OPS_USER'])
    run('chmod 700 {}'.format(aws_dir))
    upload_template('aws_config', '{}/config'.format(aws_dir), use_jinja=True, context=ctx,
                    template_dir=get_user_files_path())
    if ctx['AWS_ACCESS_KEY'] not in (None, ""):
        upload_template('aws_credentials', '{}/credentials'.format(aws_dir), use_jinja=True, context=ctx,
                        template_dir=get_user_files_path())
    run('chmod 600 {}/*'.format(aws_dir))
    if exists(boto_file):
        run('rm -rf {}'.format(boto_file))
    upload_template('boto', boto_file, use_jinja=True, context=ctx,
                    template_dir=get_user_files_path())
    run('chmod 600 {}'.format(boto_file))
    if exists(s3cfg_file):
        run('rm -rf {}'.format(s3cfg_file))
    upload_template('s3cfg', s3cfg_file, use_jinja=True, context=ctx,
                    template_dir=get_user_files_path())
    run('chmod 600 {}'.format(s3cfg_file))


##########################
# ship verdi code bundle
##########################
def send_queue_config(queue):
    ctx = get_context()
    ctx.update({'queue': queue})
    upload_template('install.sh', '~/verdi/ops/install.sh', use_jinja=True, context=ctx,
                    template_dir=get_user_files_path())
    upload_template('datasets.json.tmpl.asg', '~/verdi/etc/datasets.json',
                    use_jinja=True, context=ctx, template_dir=get_user_files_path())
    upload_template('supervisord.conf.tmpl', '~/verdi/etc/supervisord.conf.tmpl',
                    use_jinja=True, context=ctx, template_dir=get_user_files_path())


##########################
# ship s3-bucket style
##########################
def ship_style(bucket=None, encrypt=False):
    ctx = get_context()
    if bucket is None:
        bucket = ctx['DATASET_BUCKET']
    else:
        ctx.update({'DATASET_BUCKET': bucket})
    repo_dir = os.path.join(ops_dir, 'mozart/ops/s3-bucket-listing')
    index_file = os.path.join(repo_dir, 'tmp_index.html')
    list_js = os.path.join(repo_dir, 'list.js')
    index_style = os.path.join(repo_dir, 'index-style')
    upload_template('s3-bucket-listing.html.tmpl', index_file, use_jinja=True,
                    context=ctx, template_dir=get_user_files_path())
    if encrypt is False:
        run('aws s3 cp %s s3://%s/index.html' % (index_file, bucket))
        run('aws s3 cp %s s3://%s/' % (list_js, bucket))
        run('aws s3 sync %s s3://%s/index-style' % (index_style, bucket))
    else:
        run('aws s3 cp --sse %s s3://%s/index.html' % (index_file, bucket))
        run('aws s3 cp --sse %s s3://%s/' % (list_js, bucket))
        run('aws s3 sync --sse %s s3://%s/index-style' % (index_style, bucket))


##########################
# create cloud function zip
##########################
def create_zip(zip_dir, zip_file):
    if exists(zip_file):
        run('rm -rf %s' % zip_file)
    with cd(zip_dir):
        run('zip -r -9 {} *'.format(zip_file))


##########################
# container orchestration
##########################
def rsync_sdsadm():
    role, hysds_dir, hostname = resolve_role()
    rm_rf('%s/ops/sdsadm' % hysds_dir)
    rsync_project('%s/ops/' % hysds_dir, os.path.join(ops_dir, 'mozart/ops/sdsadm'),
                  extra_opts=extra_opts, ssh_opts=ssh_opts)


def init_sdsadm():
    role, hysds_dir, hostname = resolve_role()
    with cd(os.path.join(hysds_dir, 'ops', 'sdsadm')):
        with prefix('source ~/%s/bin/activate' % hysds_dir):
            run("./sdsadm init {} -f".format(role))


def start_sdsadm(release):
    role, hysds_dir, hostname = resolve_role()
    with cd(os.path.join(hysds_dir, 'ops', 'sdsadm')):
        with prefix('source ~/%s/bin/activate' % hysds_dir):
            run("./sdsadm -r {} start {} -d".format(release, role))


def stop_sdsadm():
    role, hysds_dir, hostname = resolve_role()
    with cd(os.path.join(hysds_dir, 'ops', 'sdsadm')):
        with prefix('source ~/%s/bin/activate' % hysds_dir):
            run("./sdsadm stop {}".format(role))


def logs_sdsadm(follow=False):
    role, hysds_dir, hostname = resolve_role()
    with cd(os.path.join(hysds_dir, 'ops', 'sdsadm')):
        with prefix('source ~/%s/bin/activate' % hysds_dir):
            if follow:
                run("./sdsadm logs {} -f".format(role))
            else:
                run("./sdsadm logs {}".format(role))


def ps_sdsadm():
    role, hysds_dir, hostname = resolve_role()
    with cd(os.path.join(hysds_dir, 'ops', 'sdsadm')):
        with prefix('source ~/%s/bin/activate' % hysds_dir):
            run("./sdsadm ps {}".format(role))


def run_sdsadm(cmd):
    role, hysds_dir, hostname = resolve_role()
    with cd(os.path.join(hysds_dir, 'ops', 'sdsadm')):
        with prefix('source ~/%s/bin/activate' % hysds_dir):
            run("./sdsadm run {} {}".format(role, cmd))


def conf_sdsadm(tmpl, dest, shared=False):
    role, hysds_dir, hostname = resolve_role()
    if shared:
        tmpl_dir = os.path.join(get_user_files_path(), 'orch')
    else:
        if role in ('factotum', 'ci'):
            tmpl_dir = os.path.join(get_user_files_path(), 'orch', 'verdi')
        else:
            tmpl_dir = os.path.join(get_user_files_path(), 'orch', role)
    upload_template(tmpl, dest, use_jinja=True, context=get_context(role), template_dir=tmpl_dir)
