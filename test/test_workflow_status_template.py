"""workflow_status.template: daily-index template, aliases, ISM coverage."""

import fnmatch
import json
import os

import sdscli.adapters.hysds as hysds_adapter

FILES = os.path.join(os.path.dirname(hysds_adapter.__file__), "files")


def _load(name):
    with open(os.path.join(FILES, name)) as f:
        return json.load(f)


def test_template_shape():
    t = _load("workflow_status.template")
    assert t["index_patterns"] == ["workflow_status-*"]
    assert set(t["template"]["aliases"]) == {"workflow_status", "workflow_status-current"}
    props = t["template"]["mappings"]["properties"]
    assert props["run_id"]["type"] == "keyword"
    assert props["version"]["type"] == "long"
    assert props["nodes"]["enabled"] is False


def test_ism_policy_covers_daily_indices():
    pol = _load("opensearch_ism_policy_mozart.json")["policy"]["ism_template"]["index_patterns"]
    assert any(fnmatch.fnmatch("workflow_status-2026.11.16", p) for p in pol)


def test_template_installed_by_fabfile():
    with open(os.path.join(FILES, "..", "fabfile.py")) as f:
        assert '"workflow_status.template"' in f.read()
