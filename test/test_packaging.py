"""Test packaging configuration and metadata."""
import sys
from importlib.metadata import version, requires

import pytest


def test_version_starts_with_7():
    """Verify package version starts with 7."""
    v = version("hysds-sdscli")
    assert v.startswith("7."), f"Expected version 7.x, got {v}"


def test_core_modules_importable():
    """Verify core sdscli modules can be imported."""
    import sdscli
    assert hasattr(sdscli, "__version__")
    assert hasattr(sdscli, "__url__")
    assert hasattr(sdscli, "__description__")


def test_python_version_requirement():
    """Verify running on Python 3.12+."""
    assert sys.version_info >= (3, 12), "Requires Python 3.12+"


def test_package_name_is_hysds_sdscli():
    """Verify package is published as hysds-sdscli."""
    v = version("hysds-sdscli")
    assert v is not None, "Package 'hysds-sdscli' not found"


def test_import_name_is_sdscli():
    """Verify import name remains 'sdscli' (not hysds_sdscli)."""
    import sdscli
    assert sdscli.__name__ == "sdscli"


def test_console_script_defined():
    """Verify sds console script is defined."""
    from importlib.metadata import entry_points
    
    scripts = entry_points()
    if hasattr(scripts, 'select'):
        # Python 3.10+
        console_scripts = scripts.select(group='console_scripts')
    else:
        # Python 3.9
        console_scripts = scripts.get('console_scripts', [])
    
    script_names = [ep.name for ep in console_scripts]
    assert "sds" in script_names, "sds console script not found"


def test_prompt_toolkit_upgraded():
    """Verify prompt-toolkit upgraded to 3.x."""
    deps = requires("hysds-sdscli")
    assert deps is not None
    
    pt_deps = [d for d in deps if "prompt-toolkit" in d or "prompt_toolkit" in d]
    assert pt_deps, "prompt-toolkit dependency not found"
    
    for dep in pt_deps:
        # Should have >=3.0 and <4.0
        assert ">=3" in dep or ">=3.0" in dep, \
            f"prompt-toolkit should be >=3.0, found: {dep}"
