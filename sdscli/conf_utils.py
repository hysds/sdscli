from future import standard_library
standard_library.install_aliases()
import os
import yaml
import logging
import traceback

from sdscli.log_utils import logger


def get_user_config_path():
    """Return path to user configuration."""

    return os.path.expanduser(os.path.join('~', '.sds', 'config'))


def get_user_files_path():
    """Return path to user configuration templates and files."""

    return os.path.expanduser(os.path.join('~', '.sds', 'files'))


class YamlConfError(Exception):
    """Exception class for YamlConf class."""
    pass


class YamlConf:
    """YAML configuration class."""

    def __init__(self, file):
        """Construct YamlConf instance."""

        logger.debug(f"file: {file}")
        self._file = file
        with open(self._file) as f:
            self._cfg = yaml.load(f, Loader=yaml.FullLoader)

    @property
    def file(self):
        return self._file

    @property
    def cfg(self):
        return self._cfg

    def get(self, key):
        try:
            return self._cfg[key]
        except KeyError as e:
            raise YamlConfError(f"Configuration '{key}' doesn't exist in {self._file}.")


class SettingsConf(YamlConf):
    """Settings YAML configuration class."""

    def __init__(self, file=None):
        "Construct SettingsConf instance."""

        if file is None:
            file = get_user_config_path()
        super().__init__(file)
