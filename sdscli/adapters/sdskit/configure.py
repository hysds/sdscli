"""Configuration for SDSKit cluster."""
from future import standard_library
standard_library.install_aliases()

from sdscli.log_utils import logger
from sdscli.conf_utils import SettingsConf


def configure():
    """Configure SDS config file for SDSKit."""

    logger.debug("Got here for SDSKit")
    conf = SettingsConf()
    logger.debug(conf)
