from future import standard_library
standard_library.install_aliases()
import os
import re

from prompt_toolkit.validation import Validator, ValidationError

from sdscli.log_utils import logger


COLOR_CODE = {
    "default": "{};39",
    "black": "{};30",
    "red": "{};31",
    "green": "{};32",
    "yellow": "{};33",
    "blue": "{};34",
    "magenta": "{};35",
    "cyan": "{};36",
    "light_gray": "{};37",
    "dark_gray": "{};90",
    "light_red": "{};91",
    "light_green": "{};92",
    "light_yellow": "{};93",
    "light_blue": "{};94",
    "light_magenta": "{};95",
    "light_cyan": "{};96",
    "white": "{};97",
}


class YesNoValidator(Validator):
    def validate(self, document):
        text = document.text.lower()
        if not text in ('yes', 'no', 'y', 'n'):
            raise ValidationError(message='Input needs to be "y" or "n"',
                                  cursor_position=len(text))


class IpAddressValidator(Validator):
    def validate(self, document):
        text = document.text.lower()
        match = re.search(
            r'^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$', text)
        if not match:
            raise ValidationError(message='Input needs to be valid IP address',
                                  cursor_position=len(text))


class SelectionValidator(Validator):
    def validate(self, document):
        text = document.text.lower()
        match = re.search(r'^\s*\d+\s*$', text)
        if not match:
            raise ValidationError(message='Input needs to be integer',
                                  cursor_position=len(text))


class MultipleSelectionValidator(Validator):
    def validate(self, document):
        text = document.text.lower()
        match = re.search(r'^\s*(\d+\s*)+$', text)
        if not match:
            raise ValidationError(message='Inputs need to be integer[s] separated by space',
                                  cursor_position=len(text))


class Ec2InstanceTypeValidator(Validator):
    def validate(self, document):
        text = document.text.lower()
        match = re.search(r'^\s*\w+\.\w+\s*$', text)
        if not match:
            raise ValidationError(message='Input needs to be EC2 instance type',
                                  cursor_position=len(text))


class PriceValidator(Validator):
    def validate(self, document):
        text = document.text.lower()
        match = re.search(r'^\s*\d*\.\d+\s*$', text)
        if not match:
            raise ValidationError(message='Input needs to be dollar amount e.g. 0.001',
                                  cursor_position=len(text))


def set_bar_desc(bar, message):
    """Set bar description."""

    bar.set_description(f"{message: >20.20}")


def highlight(s, color="green", bold=True):
    """Return colored string."""

    color_code = COLOR_CODE[color].format("1" if bold else "0")
    return f"\033[{color_code};40m{s}\033[0m"


def blink(s):
    """Return blinking string."""

    return f"\033[5;40m{s}\033[25m"


def print_component_header(comp):
    """Print component header."""

    print(highlight("#" * 40, 'cyan'))
    print(highlight(comp, 'cyan', True))
    print(highlight("#" * 40, 'cyan'))


def print_tps_header(comp):
    """Print tps header."""

    print(highlight("-" * 40, 'cyan'))
    print(highlight('third-party services', 'cyan', True))
    print(highlight("-" * 40, 'cyan'))


def print_supervisor_header(comp):
    """Print supervisor header."""

    print(highlight("-" * 40, 'cyan'))
    print(highlight('supervised services', 'cyan', True))
    print(highlight("-" * 40, 'cyan'))
