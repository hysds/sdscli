"""
Configuration for HySDS cluster.
"""


import os
import yaml
import pwd
import shutil
import hashlib
import traceback
from importlib.resources import files
from glob import glob

from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator, ValidationError
from pygments.token import Token

from sdscli.log_utils import logger
from sdscli.conf_utils import get_user_config_path, get_user_files_path, SettingsConf
from sdscli.os_utils import validate_dir
from sdscli.prompt_utils import YesNoValidator


prompt_style = Style.from_dict({
    Token.Alert: 'bg:#D8060C',
    Token.Username: '#D8060C',
    Token.Param: '#3CFF33',
})


CFG_TMPL = """# HySDS config
TYPE: hysds

# mozart
MOZART_PVT_IP: {MOZART_PVT_IP}
MOZART_PUB_IP: {MOZART_PUB_IP}
MOZART_FQDN: {MOZART_FQDN}

# mozart rabbitmq
MOZART_RABBIT_PVT_IP: {MOZART_RABBIT_PVT_IP}
MOZART_RABBIT_PUB_IP: {MOZART_RABBIT_PUB_IP}
MOZART_RABBIT_FQDN: {MOZART_RABBIT_FQDN}
MOZART_RABBIT_USER: {MOZART_RABBIT_USER}
MOZART_RABBIT_PASSWORD: {MOZART_RABBIT_PASSWORD}

# mozart redis
MOZART_REDIS_PVT_IP: {MOZART_REDIS_PVT_IP}
MOZART_REDIS_PUB_IP: {MOZART_REDIS_PUB_IP}
MOZART_REDIS_FQDN: {MOZART_REDIS_FQDN}
MOZART_REDIS_PASSWORD: {MOZART_REDIS_PASSWORD}

# mozart ES
MOZART_ES_PVT_IP: {MOZART_ES_PVT_IP}
MOZART_ES_PUB_IP: {MOZART_ES_PUB_IP}
MOZART_ES_FQDN: {MOZART_ES_FQDN}

OPS_USER: {OPS_USER}
OPS_HOME: {OPS_HOME}
OPS_PASSWORD_HASH: {OPS_PASSWORD_HASH}
LDAP_GROUPS: {LDAP_GROUPS}
KEY_FILENAME: {KEY_FILENAME}
JENKINS_USER: {JENKINS_USER}
JENKINS_DIR: {JENKINS_DIR}

# metrics
METRICS_PVT_IP: {METRICS_PVT_IP}
METRICS_PUB_IP: {METRICS_PUB_IP}
METRICS_FQDN: {METRICS_FQDN}

# metrics redis
METRICS_REDIS_PVT_IP: {METRICS_REDIS_PVT_IP}
METRICS_REDIS_PUB_IP: {METRICS_REDIS_PUB_IP}
METRICS_REDIS_FQDN: {METRICS_REDIS_FQDN}
METRICS_REDIS_PASSWORD: {METRICS_REDIS_PASSWORD}

# metrics ES
METRICS_ES_PVT_IP: {METRICS_ES_PVT_IP}
METRICS_ES_PUB_IP: {METRICS_ES_PUB_IP}
METRICS_ES_FQDN: {METRICS_ES_FQDN}

# grq
GRQ_PVT_IP: {GRQ_PVT_IP}
GRQ_PUB_IP: {GRQ_PUB_IP}
GRQ_FQDN: {GRQ_FQDN}
GRQ_PORT: {GRQ_PORT}

# grq ES
GRQ_ES_PVT_IP: {GRQ_ES_PVT_IP}
GRQ_ES_PUB_IP: {GRQ_ES_PUB_IP}
GRQ_ES_FQDN: {GRQ_ES_FQDN}

# factotum
FACTOTUM_PVT_IP: {FACTOTUM_PVT_IP}
FACTOTUM_PUB_IP: {FACTOTUM_PUB_IP}
FACTOTUM_FQDN: {FACTOTUM_FQDN}

# continuous integration server
CI_PVT_IP: {CI_PVT_IP}
CI_PUB_IP: {CI_PUB_IP}
CI_FQDN: {CI_FQDN}
JENKINS_API_USER: {JENKINS_API_USER}
JENKINS_API_KEY: {JENKINS_API_KEY}

# verdi build
VERDI_PVT_IP: {VERDI_PVT_IP}
VERDI_PUB_IP: {VERDI_PUB_IP}
VERDI_FQDN: {VERDI_FQDN}

# other non-autoscale verdi hosts (optional)
OTHER_VERDI_HOSTS:
  - VERDI_PVT_IP:
    VERDI_PUB_IP:
    VERDI_FQDN:

# WebDAV product server
DAV_SERVER: {DAV_SERVER}
DAV_USER: {DAV_USER}
DAV_PASSWORD: {DAV_PASSWORD}

# AWS settings for product bucket
DATASET_AWS_ACCESS_KEY: {DATASET_AWS_ACCESS_KEY}
DATASET_AWS_SECRET_KEY: {DATASET_AWS_SECRET_KEY}
DATASET_AWS_REGION: {DATASET_AWS_REGION}
DATASET_S3_ENDPOINT: {DATASET_S3_ENDPOINT}
DATASET_S3_WEBSITE_ENDPOINT: {DATASET_S3_WEBSITE_ENDPOINT}
DATASET_BUCKET: {DATASET_BUCKET}

# AWS settings for autoscale workers
AWS_ACCESS_KEY: {AWS_ACCESS_KEY}
AWS_SECRET_KEY: {AWS_SECRET_KEY}
AWS_REGION: {AWS_REGION}
S3_ENDPOINT: {S3_ENDPOINT}
CODE_BUCKET: {CODE_BUCKET}
VERDI_PRIMER_IMAGE: {VERDI_PRIMER_IMAGE}
VERDI_TAG: {VERDI_TAG}
VERDI_UID: {VERDI_UID}
VERDI_GID: {VERDI_GID}
VENUE: {VENUE}
QUEUES:
  - QUEUE_NAME: dumby-job_worker-small
    INSTANCE_TYPES:
      - t2.medium
      - t3a.medium
      - t3.medium
  - QUEUE_NAME: dumby-job_worker-large
    INSTANCE_TYPES:
      - t2.medium
      - t3a.medium
      - t3.medium

# git oauth token
GIT_OAUTH_TOKEN: {GIT_OAUTH_TOKEN}

# container registry
CONTAINER_REGISTRY: {CONTAINER_REGISTRY}
CONTAINER_REGISTRY_BUCKET: {CONTAINER_REGISTRY_BUCKET}

# DO NOT EDIT ANYTHING BELOW THIS

# user_rules_dataset
PROVES_URL: https://prov-es.jpl.nasa.gov/beta
PROVES_IMPORT_URL: https://prov-es.jpl.nasa.gov/beta/api/v0.1/prov_es/import/json
DATASETS_CFG: {DATASETS_CFG}

# system jobs queue
SYSTEM_JOBS_QUEUE: system-jobs-queue

MOZART_ES_CLUSTER: resource_cluster
METRICS_ES_CLUSTER: metrics_cluster
DATASET_QUERY_INDEX: grq
USER_RULES_DATASET_INDEX: user_rules
"""


CFG_DEFAULTS = {
    "mozart": [
        ["MOZART_PVT_IP", ""],
        ["MOZART_PUB_IP", ""],
        ["MOZART_FQDN", ""],
    ],

    "mozart-rabbit": [
        ["MOZART_RABBIT_PVT_IP", ""],
        ["MOZART_RABBIT_PUB_IP", ""],
        ["MOZART_RABBIT_FQDN", ""],
        ["MOZART_RABBIT_USER", "guest"],
        ["MOZART_RABBIT_PASSWORD", "guest"],
    ],

    "mozart-redis": [
        ["MOZART_REDIS_PVT_IP", ""],
        ["MOZART_REDIS_PUB_IP", ""],
        ["MOZART_REDIS_FQDN", ""],
        ["MOZART_REDIS_PASSWORD", ""],
    ],

    "mozart-es": [
        ["MOZART_ES_PVT_IP", ""],
        ["MOZART_ES_PUB_IP", ""],
        ["MOZART_ES_FQDN", ""],
    ],

    "ops": [
        ["OPS_USER", pwd.getpwuid(os.getuid())[0]],
        ["OPS_HOME", os.path.expanduser('~')],
        ["OPS_PASSWORD_HASH", ""],
        ["LDAP_GROUPS", ""],
        ["KEY_FILENAME", ""],
        ["DATASETS_CFG", os.path.join(os.path.expanduser(
            '~'), 'verdi', 'etc', 'datasets.json')],
    ],

    "metrics": [
        ["METRICS_PVT_IP", ""],
        ["METRICS_PUB_IP", ""],
        ["METRICS_FQDN", ""],
    ],

    "metrics-redis": [
        ["METRICS_REDIS_PVT_IP", ""],
        ["METRICS_REDIS_PUB_IP", ""],
        ["METRICS_REDIS_FQDN", ""],
        ["METRICS_REDIS_PASSWORD", ""],
    ],

    "metrics-es": [
        ["METRICS_ES_PVT_IP", ""],
        ["METRICS_ES_PUB_IP", ""],
        ["METRICS_ES_FQDN", ""],
    ],

    "grq": [
        ["GRQ_PVT_IP", ""],
        ["GRQ_PUB_IP", ""],
        ["GRQ_FQDN", ""],
        ["GRQ_PORT", 8878],
    ],

    "grq-es": [
        ["GRQ_ES_PVT_IP", ""],
        ["GRQ_ES_PUB_IP", ""],
        ["GRQ_ES_FQDN", ""],
    ],

    "factotum": [
        ["FACTOTUM_PVT_IP", ""],
        ["FACTOTUM_PUB_IP", ""],
        ["FACTOTUM_FQDN", ""],
    ],

    "ci": [
        ["CI_PVT_IP", ""],
        ["CI_PUB_IP", ""],
        ["CI_FQDN", ""],
        ["JENKINS_USER", "jenkins"],
        ["JENKINS_DIR", os.path.join(os.path.expanduser('~'), 'jenkins')],
        ["JENKINS_API_USER", ""],
        ["JENKINS_API_KEY", ""],
        ["GIT_OAUTH_TOKEN", ""],
    ],

    "verdi": [
        ["VERDI_PVT_IP", ""],
        ["VERDI_PUB_IP", ""],
        ["VERDI_FQDN", ""],
        ["CONTAINER_REGISTRY", ""],
        ["CONTAINER_REGISTRY_BUCKET", ""],
    ],

    "webdav": [
        ["DAV_SERVER", ""],
        ["DAV_USER", ""],
        ["DAV_PASSWORD", ""],
    ],

    "aws-dataset": [
        ["DATASET_AWS_ACCESS_KEY", ""],
        ["DATASET_AWS_SECRET_KEY", ""],
        ["DATASET_AWS_REGION", "us-west-2"],
        ["DATASET_S3_ENDPOINT", "s3-us-west-2.amazonaws.com"],
        ["DATASET_S3_WEBSITE_ENDPOINT", "s3-website-us-west-2.amazonaws.com"],
        ["DATASET_BUCKET", ""],
    ],

    "aws-asg": [
        ["AWS_ACCESS_KEY", ""],
        ["AWS_SECRET_KEY", ""],
        ["AWS_REGION", "us-west-2"],
        ["S3_ENDPOINT", "s3-us-west-2.amazonaws.com"],
        ["CODE_BUCKET", ""],
        ["VERDI_PRIMER_IMAGE", ""],
        ["VERDI_TAG", ""],
        ["VERDI_UID", os.getuid()],
        ["VERDI_GID", os.getgid()],
        ["VENUE", "ops"],
    ]
}


def copy_files():
    """Copy templates and files to user config files."""

    files_path = get_user_files_path()
    logger.debug('files_path: %s' % files_path)
    validate_dir(files_path, mode=0o700)
    sds_files_path = str(files('sdscli').joinpath('adapters', 'hysds', 'files'))
    sds_files = glob(os.path.join(sds_files_path, '*'))
    for sds_file in sds_files:
        if os.path.basename(sds_file) == 'cluster.py':
            user_file = os.path.join(os.path.dirname(
                get_user_config_path()), os.path.basename(sds_file))
            if not os.path.exists(user_file):
                shutil.copy(sds_file, user_file)
        else:
            user_file = os.path.join(files_path, os.path.basename(sds_file))
            if os.path.isdir(sds_file) and not os.path.exists(user_file):
                shutil.copytree(sds_file, user_file)
                logger.debug(f"Copying dir {sds_file} to {user_file}")
            elif os.path.isfile(sds_file) and not os.path.exists(user_file):
                shutil.copy(sds_file, user_file)
                logger.debug(f"Copying file {sds_file} to {user_file}")


def configure():
    """Configure SDS config file for HySDS."""

    # copy templates/files
    copy_files()

    # config file
    cfg_file = get_user_config_path()
    if os.path.exists(cfg_file):
        cont = prompt(get_prompt_tokens=lambda x: [(Token, cfg_file),
                                                   (Token, " already exists. "),
                                                   (Token.Alert,
                                                    "Customizations will be lost or overwritten!"),
                                                   (Token, " Continue [y/n]: ")],
                      validator=YesNoValidator(), style=prompt_style) == 'y'
        # validator=YesNoValidator(), default='n', style=prompt_style) == 'y'
        if not cont:
            return 0
        with open(cfg_file) as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
    else:
        cfg = {}

    # mozart
    for k, d in CFG_DEFAULTS['mozart']:
        v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                (Token.Param, "%s" % k),
                                                (Token, ": ")],
                   default=str(cfg.get(k, d)),
                   style=prompt_style)
        cfg[k] = v

    # mozart components
    comps = [('mozart-rabbit', 'rabbitMQ'), ('mozart-redis', 'redis'),
             ('mozart-es', 'elasticsearch')]
    for grp, comp in comps:
        reuse = prompt("Is mozart %s on a different IP [y/n]: " % comp,
                       validator=YesNoValidator(), default='n') == 'n'
        for k, d in CFG_DEFAULTS[grp]:
            if reuse:
                if k.endswith('_PVT_IP'):
                    cfg[k] = cfg['MOZART_PVT_IP']
                    continue
                elif k.endswith('_PUB_IP'):
                    cfg[k] = cfg['MOZART_PUB_IP']
                    continue
                elif k.endswith('_FQDN'):
                    cfg[k] = cfg['MOZART_FQDN']
                    continue
            if k == 'MOZART_RABBIT_PASSWORD':
                while True:
                    p1 = prompt(get_prompt_tokens=lambda x: [(Token, "Enter RabbitMQ password for user "),
                                                             (Token.Username, "%s" %
                                                              cfg['MOZART_RABBIT_USER']),
                                                             (Token, ": ")],
                                default=str(cfg.get(k, d)),
                                style=prompt_style,
                                is_password=True)
                    p2 = prompt(get_prompt_tokens=lambda x: [(Token, "Re-enter RabbitMQ password for user "),
                                                             (Token.Username, "%s" %
                                                              cfg['MOZART_RABBIT_USER']),
                                                             (Token, ": ")],
                                default=str(cfg.get(k, d)),
                                style=prompt_style,
                                is_password=True)
                    if p1 == p2:
                        if p1 == "":
                            print("Password can't be empty.")
                            continue
                        v = p1
                        break
                    print("Passwords don't match.")
            elif k == 'MOZART_REDIS_PASSWORD':
                while True:
                    p1 = prompt(get_prompt_tokens=lambda x: [(Token, "Enter Redis password: ")],
                                default=str(cfg.get(k, d)),
                                style=prompt_style,
                                is_password=True)
                    p2 = prompt(get_prompt_tokens=lambda x: [(Token, "Re-enter Redis password: ")],
                                default=str(cfg.get(k, d)),
                                style=prompt_style,
                                is_password=True)
                    if p1 == p2:
                        v = p1
                        break
                    print("Passwords don't match.")
            else:
                v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                        (Token.Param, "%s" % k),
                                                        (Token, ": ")],
                           default=str(cfg.get(k, d)),
                           style=prompt_style)
            cfg[k] = v

    # ops
    for k, d in CFG_DEFAULTS['ops']:
        if k == 'OPS_PASSWORD_HASH':
            while True:
                p1 = prompt(get_prompt_tokens=lambda x: [(Token, "Enter web interface password for ops user "),
                                                         (Token.Username, "%s" %
                                                          cfg['OPS_USER']),
                                                         (Token, ": ")],
                            default="",
                            style=prompt_style,
                            is_password=True)
                p2 = prompt(get_prompt_tokens=lambda x: [(Token, "Re-enter web interface password for ops user "),
                                                         (Token.Username, "%s" %
                                                          cfg['OPS_USER']),
                                                         (Token, ": ")],
                            default="",
                            style=prompt_style,
                            is_password=True)
                if p1 == p2:
                    if p1 == "":
                        print("Password can't be empty.")
                        continue
                    v = hashlib.sha224(p1.encode()).hexdigest()
                    break
                print("Passwords don't match.")
        else:
            v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                    (Token.Param, "%s" % k),
                                                    (Token, ": ")],
                       default=str(cfg.get(k, d)),
                       style=prompt_style)
        cfg[k] = v

    # metrics
    for k, d in CFG_DEFAULTS['metrics']:
        v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                (Token.Param, "%s" % k),
                                                (Token, ": ")],
                   default=str(cfg.get(k, d)),
                   style=prompt_style)
        cfg[k] = v

    # metrics components
    comps = [('metrics-redis', 'redis'), ('metrics-es', 'elasticsearch')]
    for grp, comp in comps:
        reuse = prompt("Is metrics %s on a different IP [y/n]: " % comp,
                       validator=YesNoValidator(), default='n') == 'n'
        for k, d in CFG_DEFAULTS[grp]:
            if reuse:
                if k.endswith('_PVT_IP'):
                    cfg[k] = cfg['METRICS_PVT_IP']
                    continue
                elif k.endswith('_PUB_IP'):
                    cfg[k] = cfg['METRICS_PUB_IP']
                    continue
                elif k.endswith('_FQDN'):
                    cfg[k] = cfg['METRICS_FQDN']
                    continue
            if k == 'METRICS_REDIS_PASSWORD':
                while True:
                    p1 = prompt(get_prompt_tokens=lambda x: [(Token, "Enter Redis password: ")],
                                default=str(cfg.get(k, d)),
                                style=prompt_style,
                                is_password=True)
                    p2 = prompt(get_prompt_tokens=lambda x: [(Token, "Re-enter Redis password: ")],
                                default=str(cfg.get(k, d)),
                                style=prompt_style,
                                is_password=True)
                    if p1 == p2:
                        v = p1
                        break
                    print("Passwords don't match.")
            else:
                v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                        (Token.Param, "%s" % k),
                                                        (Token, ": ")],
                           default=str(cfg.get(k, d)),
                           style=prompt_style)
            cfg[k] = v

    # grq
    for k, d in CFG_DEFAULTS['grq']:
        v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                (Token.Param, "%s" % k),
                                                (Token, ": ")],
                   default=str(cfg.get(k, d)),
                   style=prompt_style)
        cfg[k] = v

    # grq components
    comps = [('grq-es', 'elasticsearch')]
    for grp, comp in comps:
        reuse = prompt("Is grq %s on a different IP [y/n]: " % comp,
                       validator=YesNoValidator(), default='n') == 'n'
        for k, d in CFG_DEFAULTS[grp]:
            if reuse:
                if k.endswith('_PVT_IP'):
                    cfg[k] = cfg['GRQ_PVT_IP']
                    continue
                elif k.endswith('_PUB_IP'):
                    cfg[k] = cfg['GRQ_PUB_IP']
                    continue
                elif k.endswith('_FQDN'):
                    cfg[k] = cfg['GRQ_FQDN']
                    continue
            v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                    (Token.Param, "%s" % k),
                                                    (Token, ": ")],
                       default=str(cfg.get(k, d)),
                       style=prompt_style)
            cfg[k] = v

    # factotum
    for k, d in CFG_DEFAULTS['factotum']:
        v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                (Token.Param, "%s" % k),
                                                (Token, ": ")],
                   default=str(cfg.get(k, d)),
                   style=prompt_style)
        cfg[k] = v

    # ci
    for k, d in CFG_DEFAULTS['ci']:
        if k in ('JENKINS_API_KEY', 'GIT_OAUTH_TOKEN'):
            while True:
                p1 = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                         (Token.Param, "%s" % k),
                                                         (Token, ": ")],
                            default=str(cfg.get(k, d)),
                            style=prompt_style,
                            is_password=True)
                p2 = prompt(get_prompt_tokens=lambda x: [(Token, "Re-enter value for "),
                                                         (Token.Param, "%s" % k),
                                                         (Token, ": ")],
                            default=str(cfg.get(k, d)),
                            style=prompt_style,
                            is_password=True)
                if p1 == p2:
                    v = p1
                    break
                print("Values don't match.")
        else:
            v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                    (Token.Param, "%s" % k),
                                                    (Token, ": ")],
                       default=str(cfg.get(k, d)),
                       style=prompt_style)
        cfg[k] = v

    # verdi
    for k, d in CFG_DEFAULTS['verdi']:
        v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                (Token.Param, "%s" % k),
                                                (Token, ": ")],
                   default=str(cfg.get(k, d)),
                   style=prompt_style)
        cfg[k] = v

    # webdav
    for k, d in CFG_DEFAULTS['webdav']:
        if k == 'DAV_PASSWORD':
            while True:
                p1 = prompt(get_prompt_tokens=lambda x: [(Token, "Enter webdav password for user "),
                                                         (Token.Username, "%s" %
                                                          cfg['DAV_USER']),
                                                         (Token, ": ")],
                            default=str(cfg.get(k, d)),
                            style=prompt_style,
                            is_password=True)
                p2 = prompt(get_prompt_tokens=lambda x: [(Token, "Re-enter webdav password for ops user "),
                                                         (Token.Username, "%s" %
                                                          cfg['DAV_USER']),
                                                         (Token, ": ")],
                            default=str(cfg.get(k, d)),
                            style=prompt_style,
                            is_password=True)
                if p1 == p2:
                    v = p1
                    break
                print("Passwords don't match.")
        else:
            v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                    (Token.Param, "%s" % k),
                                                    (Token, ": ")],
                       default=str(cfg.get(k, d)),
                       style=prompt_style)
        cfg[k] = v

    # aws-dataset
    for k, d in CFG_DEFAULTS['aws-dataset']:
        if k == 'DATASET_AWS_SECRET_KEY':
            if cfg['DATASET_AWS_ACCESS_KEY'] == "":
                cfg['DATASET_AWS_SECRET_KEY'] = ""
                continue
            while True:
                p1 = prompt(get_prompt_tokens=lambda x: [(Token, "Enter AWS secret key for "),
                                                         (Token.Username, "%s" %
                                                          cfg['DATASET_AWS_ACCESS_KEY']),
                                                         (Token, ": ")],
                            default=str(cfg.get(k, d)),
                            style=prompt_style,
                            is_password=True)
                p2 = prompt(get_prompt_tokens=lambda x: [(Token, "Re-enter AWS secret key for "),
                                                         (Token.Username, "%s" %
                                                          cfg['DATASET_AWS_ACCESS_KEY']),
                                                         (Token, ": ")],
                            default=str(cfg.get(k, d)),
                            style=prompt_style,
                            is_password=True)
                if p1 == p2:
                    v = p1
                    break
                print("Keys don't match.")
        elif k == 'DATASET_AWS_ACCESS_KEY':
            v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                    (Token.Param, "%s" % k),
                                                    (Token, ". If using instance roles, just press enter"),
                                                    (Token, ": ")],
                       default=str(cfg.get(k, d)),
                       style=prompt_style)
        else:
            v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                    (Token.Param, "%s" % k),
                                                    (Token, ": ")],
                       default=str(cfg.get(k, d)),
                       style=prompt_style)
        cfg[k] = v

    # aws-asg
    for k, d in CFG_DEFAULTS['aws-asg']:
        if k == 'AWS_SECRET_KEY':
            if cfg['AWS_ACCESS_KEY'] == "":
                cfg['AWS_SECRET_KEY'] = ""
                continue
            while True:
                p1 = prompt(get_prompt_tokens=lambda x: [(Token, "Enter AWS secret key for "),
                                                         (Token.Username, "%s" %
                                                          cfg['AWS_ACCESS_KEY']),
                                                         (Token, ": ")],
                            default=str(cfg.get(k, d)),
                            style=prompt_style,
                            is_password=True)
                p2 = prompt(get_prompt_tokens=lambda x: [(Token, "Re-enter AWS secret key for "),
                                                         (Token.Username, "%s" %
                                                          cfg['AWS_ACCESS_KEY']),
                                                         (Token, ": ")],
                            default=str(cfg.get(k, d)),
                            style=prompt_style,
                            is_password=True)
                if p1 == p2:
                    v = p1
                    break
                print("Keys don't match.")
        elif k == 'AWS_ACCESS_KEY':
            v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                    (Token.Param, "%s" % k),
                                                    (Token, ". If using instance roles, just press enter"),
                                                    (Token, ": ")],
                       default=str(cfg.get(k, d)),
                       style=prompt_style)
        else:
            v = prompt(get_prompt_tokens=lambda x: [(Token, "Enter value for "),
                                                    (Token.Param, "%s" % k),
                                                    (Token, ": ")],
                       default=str(cfg.get(k, d)),
                       style=prompt_style)
        cfg[k] = v

    # ensure directory exists
    validate_dir(os.path.dirname(cfg_file), mode=0o700)
    yml = CFG_TMPL.format(**cfg)
    with open(cfg_file, 'w') as f:
        f.write(yml)
