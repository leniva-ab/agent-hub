"""Tests for agent-evidence."""

from __future__ import annotations

import json
from pathlib import Path

import agent_evidence as e


def passing() -> dict:
    doc = e.skeleton("PROJ-1", "abc123")
    for check in doc["checks"]:
        check.update(result="pass", evidence="ok")
    doc["criteria"] = [{"id": "AC1", "unit": "T.x", "e2e": "", "result": "pass"}]
    doc["verified"] = True
    return doc


def test_skeleton_is_not_verified_and_invalid_to_claim_otherwise() -> None:
    doc = e.skeleton("P-1", "abc")
    assert doc["verified"] is False and e.validate(doc) == []
    doc["verified"] = True
    assert any("not every" in p for p in e.validate(doc))


def test_valid_passing_document() -> None:
    assert e.validate(passing()) == []


def test_pass_without_evidence_is_invalid() -> None:
    doc = passing()
    doc["checks"][0]["evidence"] = " "
    assert any("without evidence" in p for p in e.validate(doc))


def test_criterion_pass_needs_unit_test() -> None:
    doc = passing()
    doc["criteria"][0]["unit"] = ""
    assert any("no unit test" in p for p in e.validate(doc))


def test_missing_field_and_missing_check() -> None:
    assert e.validate({"task": "x"})[0].startswith("missing field")
    doc = passing()
    doc["checks"] = doc["checks"][1:]
    assert any(p.startswith("missing check") for p in e.validate(doc))


def test_bad_result_value_and_empty_commit() -> None:
    doc = passing()
    doc["checks"][0]["result"] = "maybe"
    doc["commit"] = ""
    problems = e.validate(doc)
    assert any("must be one of" in p for p in problems) and "commit is empty" in problems


def test_all_pass_but_verified_false_is_flagged() -> None:
    doc = passing()
    doc["verified"] = False
    assert any("verified is false" in p for p in e.validate(doc))


def test_cli(tmp_path: Path, capsys) -> None:
    assert e.main(["new", "--task", "P-1", "--commit", "abc"]) == 0
    skeleton = capsys.readouterr().out
    path = tmp_path / "e.json"
    path.write_text(skeleton)
    assert e.main(["check", str(path)]) == 0
    path.write_text(json.dumps({**json.loads(skeleton), "verified": True}))
    assert e.main(["check", str(path)]) == 1
    assert e.main(["check", str(tmp_path / "none.json")]) == 1
