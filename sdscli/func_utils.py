from sdscli.log_utils import logger
from importlib import import_module
import logging
import argparse
import traceback
import yaml
import json
import importlib
import sys
import os
from future import standard_library
standard_library.install_aliases()


def get_module(mod_name):
    """Import module and return."""

    try:
        return import_module(mod_name)
    except ImportError:
        logger.error('Failed to import module "%s".' % mod_name)
        logger.error(traceback.format_exc())
        raise


def get_func(mod_name, func_name):
    """Import function and return."""

    mod = get_module(mod_name)
    logger.debug("mod: %s" % mod)
    logger.debug("func_name: %s" % func_name)
    try:
        return getattr(mod, func_name)
    except AttributeError:
        logger.error('Failed to get function "%s" from module "%s".' %
                     (func_name, mod_name))
        logger.error(traceback.format_exc())
        raise
