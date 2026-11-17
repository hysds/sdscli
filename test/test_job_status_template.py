"""job_status.template carries the workflow-orchestration mappings (ADR-003)."""

import json
import os

import sdscli.adapters.hysds as hysds_adapter

TEMPLATE = os.path.join(
    os.path.dirname(hysds_adapter.__file__), "files", "job_status.template"
)


def _props():
    with open(TEMPLATE) as f:
        return json.load(f)["template"]["mappings"]["properties"]


def test_workflow_tags():
    wf = _props()["workflow"]["properties"]
    for field in ("run_id", "step_id", "spec_id"):
        assert wf[field]["type"] == "keyword"
    assert wf["child_index"]["type"] == "integer"
    assert wf["child_total"]["type"] == "integer"


def test_workflow_outputs_nested_typed_slots():
    out = _props()["job"]["properties"]["job_info"]["properties"]["workflow_outputs"]
    assert out["type"] == "nested"
    assert {k: v["type"] for k, v in out["properties"].items()} == {
        "name": "keyword",
        "value_s": "keyword",
        "value_d": "double",
        "value_b": "boolean",
    }


def test_error_class_keyword():
    # hysds v2 stamps error_class on every job-failed/job-offline doc, top level and in
    # job.job_info; map it explicitly so it is never dynamically mapped as text.
    props = _props()
    job_info = props["job"]["properties"]["job_info"]["properties"]
    for field in (props["error_class"], job_info["error_class"]):
        assert field["type"] == "keyword"
        assert "fields" not in field
