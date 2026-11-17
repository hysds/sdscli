"""WORKFLOWS_ENABLED opt-in: update_mozart installs mozart[workflows] only when on; mozart settings template."""

import importlib
import os
import sys
import types
import unittest.mock as umock

import jinja2
import pytest

import sdscli.adapters.hysds as hysds_adapter

FILES = os.path.join(os.path.dirname(hysds_adapter.__file__), "files")


@pytest.fixture
def update_mod(monkeypatch):
    # fabfile reads ~/.sds/config at import time; replace it with a mock
    fab = umock.MagicMock()
    monkeypatch.setitem(sys.modules, "sdscli.adapters.hysds.fabfile", fab)
    monkeypatch.delitem(sys.modules, "sdscli.adapters.hysds.update", raising=False)
    monkeypatch.setattr(hysds_adapter, "fabfile", fab, raising=False)
    mod = importlib.import_module("sdscli.adapters.hysds.update")
    monkeypatch.setattr(mod, "execute", umock.MagicMock())
    monkeypatch.setattr(mod, "tqdm", umock.MagicMock())
    monkeypatch.setattr(mod, "set_bar_desc", umock.MagicMock())
    yield mod
    sys.modules.pop("sdscli.adapters.hysds.update", None)


def _mozart_install_calls(mod):
    out = {}
    for c in mod.execute.call_args_list:
        a = c.args
        if a and a[0] is mod.fab.pip_install_with_req:
            out[a[2]] = a[3:]
    return out


@pytest.mark.parametrize("cfg,extras", [({"WORKFLOWS_ENABLED": True}, "workflows"),
                                        ({"WORKFLOWS_ENABLED": False}, None),
                                        ({}, None)])
@pytest.mark.parametrize("ndeps", [False, True])
def test_update_mozart_extras(update_mod, cfg, extras, ndeps):
    conf = types.SimpleNamespace(cfg=cfg, get=lambda k: cfg.get(k, "x"))
    update_mod.update_mozart(conf, ndeps=ndeps)
    calls = _mozart_install_calls(update_mod)
    assert calls["~/mozart/ops/mozart"] == (ndeps, extras)
    # only mozart gets the extra
    for dest, rest in calls.items():
        if dest != "~/mozart/ops/mozart":
            assert rest == (ndeps,)


def _render_settings(**ctx):
    with open(os.path.join(FILES, "orch", "mozart", "settings.cfg")) as f:
        text = jinja2.Environment().from_string(f.read()).render(**ctx)
    # only the flag line matters; the rest of the template needs a full sds config
    line = [l for l in text.splitlines() if l.startswith("WORKFLOWS_ENABLED")]
    assert len(line) == 1
    ns = {}
    exec(line[0], ns)
    return ns


@pytest.mark.parametrize("ctx,expected", [({"WORKFLOWS_ENABLED": True}, True),
                                          ({"WORKFLOWS_ENABLED": False}, False),
                                          ({}, False)])
def test_mozart_settings_template_flag(ctx, expected):
    assert _render_settings(**ctx)["WORKFLOWS_ENABLED"] is expected
