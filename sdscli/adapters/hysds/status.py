"""
Status of HySDS components.
"""


from future import standard_library
standard_library.install_aliases()
import os
import yaml
import pwd
import hashlib
import traceback
import requests
import re
from fabric.api import execute, hide
from tqdm import tqdm

from prompt_toolkit.shortcuts import prompt, print_tokens
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.validation import Validator, ValidationError
from pygments.token import Token

import kombu
import redis
import elasticsearch

from sdscli.log_utils import logger
from sdscli.conf_utils import get_user_files_path, SettingsConf
from sdscli.os_utils import validate_dir
from sdscli.prompt_utils import (highlight, blink, print_component_header,
                                 print_tps_header, print_supervisor_header)

from . import fabfile as fab

from hysds.es_util import get_mozart_es, get_metrics_es, get_grq_es
from hysds.es_util import get_mozart_es_engine, get_metrics_es_engine, get_grq_es_engine


prompt_style = style_from_dict({
    Token.Alert: 'bg:#D8060C',
    Token.Username: '#D8060C',
    Token.Param: '#3CFF33',
})


def print_rabbitmq_status(user, password, host):
    """Print status of RabbitMQ server."""

    amqp_url = "amqp://{user}:{password}@{host}:5672//".format(
        user=user,
        password=password,
        host=host)
    logger.debug(f"amqp_url: {amqp_url}")
    try:
        conn = kombu.Connection(amqp_url)
        conn.ensure_connection(max_retries=3)
        print(("RabbitMQ: ", highlight("RUNNING")))
    except Exception as e:
        print(("RabbitMQ: ", blink(highlight("NOT RUNNING", 'red', True))))
        print(e)


def print_redis_status(password, host):
    """Print status of redis server."""

    try:
        r = redis.StrictRedis(host, password=password)
        r.ping()
        print(("Redis: ", highlight("RUNNING")))
    except Exception as e:
        print(("Redis: ", blink(highlight("NOT RUNNING", 'red', True))))
        print(e)


def print_es_status(host, component):
    """Print status of ES server."""
    if component == "mozart":
        service = get_mozart_es_engine()
        es = get_mozart_es()
    elif component == "metrics":
        service = get_metrics_es_engine()
        es = get_metrics_es()
    elif component == "grq":
        service = get_grq_es_engine()
        es = get_grq_es()
    else:
        service = "Unknown Search Engine"
        es = None

    print(f"[{host}] Pinging {service.title()}")
    status = "inactive"
    try:
        if es:
            result = es.es.ping()
            if result is True:
                status = "active"
        else:
            status = "unknown"
    except Exception as e:
        # Should we print the exception here?
        print(f"Error while getting {service} status:\n{str(e)}")
        pass

    if status == 'active':
        print(f"{service}: {highlight(status.upper())}")
    else:
        print("{}: {}".format(service, blink(highlight(status.upper(), 'red'))))


def print_http_status(server, url):
    """Print status of HTTP-based server."""

    try:
        r = requests.get(url, verify=False)
        r.raise_for_status()
        print("{}: {}".format(server, highlight("RUNNING")))
    except Exception as e:
        print("{}: {}".format(server, blink(highlight("NOT RUNNING", 'red', True))))
        print(e)


def print_service_status(service, ret, debug=False):
    """Print status of service based on systemctl status message."""

    stdout = ret[list(ret.keys())[0]]
    status_match = re.search(r'Active:\s+(.+?)\s+', stdout)
    if not status_match:
        raise RuntimeError(
            f"Failed to extract status of {service} from stdout:\n{stdout}")
    status = status_match.group(1)
    if status == 'active':
        print(f"{service}: {highlight(status.upper())}")
    else:
        print("{}: {}".format(service, blink(highlight(status.upper(), 'red'))))
    if debug:
        print(stdout)


def print_tps_status(conf, comp, debug=False):
    """Print status of third-party services."""

    if comp == 'mozart':
        print_tps_header(comp)
        # print_rabbitmq_status(conf.get('MOZART_RABBIT_USER'),
        #                      conf.get('MOZART_RABBIT_PASSWORD'),
        #                      conf.get('MOZART_RABBIT_PVT_IP'))
        ret = execute(fab.systemctl, 'status', 'rabbitmq-server', use_sudo=False, roles=[comp])
        print_service_status('rabbitmq-server', ret, debug)
        # print_redis_status(conf.get('MOZART_REDIS_PASSWORD'),
        #                   conf.get('MOZART_REDIS_PVT_IP'))
        ret = execute(fab.systemctl, 'status', 'redis', use_sudo=False, roles=[comp])
        print_service_status('redis', ret, debug)
        print_es_status(conf.get('MOZART_ES_PVT_IP'), comp)
        # ret = execute(fab.systemctl, 'status', 'elasticsearch', roles=[comp])
        # print_service_status('elasticsearch', ret, debug)
    elif comp == 'metrics':
        print_tps_header(comp)
        # print_redis_status(conf.get('METRICS_REDIS_PASSWORD'),
        #                   conf.get('METRICS_REDIS_PVT_IP'))
        ret = execute(fab.systemctl, 'status', 'redis', use_sudo=False, roles=[comp])
        print_service_status('redis', ret, debug)
        print_es_status(conf.get('METRICS_ES_PVT_IP'), comp)
        # ret = execute(fab.systemctl, 'status', 'elasticsearch', roles=[comp])
        # print_service_status('elasticsearch', ret, debug)
    elif comp == 'grq':
        print_tps_header(comp)
        print_es_status(conf.get('GRQ_ES_PVT_IP'), comp)
        # ret = execute(fab.systemctl, 'status', 'elasticsearch', roles=[comp])
        # print_service_status('elasticsearch', ret, debug)
    elif comp == 'ci':
        print_tps_header(comp)
        # print_http_status("Jenkins", "http://{}:8080".format(conf.get('CI_PVT_IP')))
        ret = execute(fab.systemctl, 'status', 'jenkins', use_sudo=False, roles=[comp])
        print_service_status('jenkins', ret, debug)


def print_status(conf, comp, debug=False):
    """"Status of component."""

    print_component_header(comp)
    if len(fab.env.roledefs[comp]) == 1 and "None" not in fab.env.roledefs[comp]:
        print_tps_status(conf, comp, debug)
        print_supervisor_header(comp)
        execute(fab.status, roles=[comp])
    else:
        print(f"No configured host(s) for role: {comp}. Skipping.")


def status_comp(comp, conf, debug=False):
    """Update component."""

    if comp in ('all', 'grq'):
        print_status(conf, 'grq', debug)
    if comp in ('all', 'mozart'):
        print_status(conf, 'mozart', debug)
    if comp in ('all', 'metrics'):
        print_status(conf, 'metrics', debug)
    if comp in ('all', 'factotum'):
        print_status(conf, 'factotum', debug)
    if comp in ('all', 'ci'):
        print_status(conf, 'ci', debug)
    if comp in ('all', 'verdi'):
        print_status(conf, 'verdi', debug)


def status(comp, debug=False):
    """Component status."""

    # get user's SDS conf settings
    conf = SettingsConf()

    logger.debug("Status for %s component(s)" % comp)

    status_comp(comp, conf, debug)
