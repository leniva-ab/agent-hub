"""Tests for agent-gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import agent_gate as g

COBERTURA = """<coverage><packages><package><classes>
<class filename="app/service.py"><lines>
<line number="1" hits="1"/><line number="2" hits="0"/><line number="3" hits="1" condition-coverage="50% (1/2)"/>
</lines></class></classes></package></packages></coverage>"""
JACOCO = """<report name="x"><package name="com/acme"><sourcefile name="Service.java">
<line nr="1" mi="0" ci="3" mb="0" cb="0"/><line nr="2" mi="2" ci="0" mb="0" cb="0"/><line nr="3" mi="0" ci="2" mb="1" cb="1"/>
</sourcefile></package></report>"""
LCOV = "TN:\nSF:src/app/service.py\nDA:1,1\nDA:2,0\nDA:3,1\nBRDA:3,0,0,1\nBRDA:3,0,1,-\nend_of_record\n"
GO = "mode: set\nexample.com/m/src/app/service.go:1.1,2.5 1 1\nexample.com/m/src/app/service.go:2.1,3.5 1 0\n"


def test_parse_diff(diff) -> None:
    assert g.parse_diff(diff) == {"src/app/service.py": {1, 2, 3}, "tests/test_service.py": {1, 2}}


def test_parse_diff_skips_deleted_files() -> None:
    assert g.parse_diff("--- a/x.py\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-a\n") == {}


@pytest.mark.parametrize(
    ("parser", "text", "key", "expected"),
    [
        (g.parse_lcov, LCOV, "src/app/service.py", {1: True, 2: False, 3: False}),
        (g.parse_go, GO, "example.com/m/src/app/service.go", {1: True, 2: False, 3: False}),
    ],
)
def test_text_parsers(parser, text, key, expected) -> None:
    assert parser(text)[key] == expected


def test_xml_parsers(tmp_path: Path) -> None:
    for name, text, key in (("c.xml", COBERTURA, "app/service.py"), ("j.xml", JACOCO, "com/acme/Service.java")):
        path = tmp_path / name
        path.write_text(text)
        assert g.load_report(path)[key] == {1: True, 2: False, 3: False}


def test_unknown_format(tmp_path: Path) -> None:
    path = tmp_path / "r.xml"
    path.write_text("<other/>")
    with pytest.raises(ValueError):
        g.load_report(path)


def test_gate_fails_on_uncovered_and_partial_branch() -> None:
    result = g.gate({"src/app/service.py": {1, 2, 3}}, g.parse_lcov(LCOV), [])
    assert result["uncovered"] == {"src/app/service.py": [2, 3]}
    assert result["percent"] == 33.33 and not result["pass"]


def test_gate_passes_when_fully_covered() -> None:
    report = {"app/service.py": {1: True, 2: True}}
    result = g.gate({"src/app/service.py": {1, 2}}, report, [])
    assert result["pass"] and result["percent"] == 100.0


def test_unreported_source_file_fails_but_tests_and_docs_are_ignored() -> None:
    changed = {"src/new.py": {1}, "tests/test_x.py": {1}, "README.md": {1}}
    result = g.gate(changed, {}, g.DEFAULT_EXCLUDES)
    assert result["unreported_files"] == ["src/new.py"] and not result["pass"]


def test_non_executable_lines_are_not_measured() -> None:
    result = g.gate({"src/a.py": {1, 2}}, {"a.py": {1: True}}, [])
    assert result["measured_lines"] == 1 and result["pass"]


def test_threshold_below_100() -> None:
    result = g.gate({"src/a.py": {1, 2}}, {"a.py": {1: True, 2: False}}, [], threshold=50)
    assert result["pass"]


def test_main_end_to_end(tmp_path, diff, capsys) -> None:
    (tmp_path / "d.diff").write_text(diff)
    (tmp_path / "r.lcov").write_text("SF:src/app/service.py\nDA:1,1\nDA:2,1\nDA:3,1\n")
    code = g.main(["--report", str(tmp_path / "r.lcov"), "--diff-file", str(tmp_path / "d.diff")])
    assert code == 0 and json.loads(capsys.readouterr().out)["pass"]
    (tmp_path / "r.lcov").write_text("SF:src/app/service.py\nDA:1,1\nDA:2,0\nDA:3,1\n")
    assert g.main(["--report", str(tmp_path / "r.lcov"), "--diff-file", str(tmp_path / "d.diff")]) == 1


def test_main_bad_input(tmp_path) -> None:
    assert g.main(["--report", str(tmp_path / "missing"), "--diff-file", str(tmp_path / "missing")]) == 2
