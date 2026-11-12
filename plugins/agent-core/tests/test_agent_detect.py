"""Tests for agent-detect."""

from __future__ import annotations

import json

import agent_detect as d

TABLE = """| Setting | Command or value |
|---|---|
| build | `./gradlew build` |
| unit tests | |
| e2e | `make e2e-local` |
| tracker | none |
"""


def test_agents_md_is_trusted_and_confirmed(project) -> None:
    (project / "AGENTS.md").write_text(TABLE)
    (project / "go.mod").write_text("module x")
    result = d.detect(project)
    assert result["build"] == {"command": "./gradlew build", "source": "AGENTS.md", "confirmed": True}
    assert result["e2e"]["command"] == "make e2e-local"
    assert result["test"]["command"] == "go test ./..." and result["test"]["confirmed"] is False


def test_makefile_targets(project) -> None:
    (project / "Makefile").write_text("build:\n\tx\ncheck:\n\ty\nVAR := 1\n")
    result = d.detect(project)
    assert result["build"]["command"] == "make build" and result["test"]["command"] == "make check"
    assert result["lint"] is None


def test_node_uses_lockfile_runner(project) -> None:
    (project / "package.json").write_text(json.dumps({"scripts": {"test": "x", "lint": "y", "test:e2e": "z"}}))
    (project / "pnpm-lock.yaml").write_text("")
    result = d.detect(project)
    assert result["test"]["command"] == "pnpm test"
    assert result["lint"]["command"] == "pnpm run lint" and result["e2e"]["command"] == "pnpm run test:e2e"


def test_python_with_uv_and_ruff(project) -> None:
    (project / "pyproject.toml").write_text("[tool.ruff]\nline-length=100\n")
    (project / "uv.lock").write_text("")
    result = d.detect(project)
    assert result["test"]["command"] == "uv run pytest"
    assert "ruff check" in result["lint"]["command"] and result["build"]["command"] == "uv build"


def test_java_gradle_and_maven(project) -> None:
    (project / "gradlew").write_text("")
    assert d.detect(project)["coverage"]["command"] == "./gradlew test jacocoTestReport"
    other = project / "m"
    other.mkdir()
    (other / "pom.xml").write_text("<project/>")
    assert d.detect(other)["build"]["command"] == "mvn -B verify"


def test_nothing_found_reports_none(project, capsys) -> None:
    assert all(v is None for v in d.detect(project).values())
    assert d.main(["--root", str(project), "test"]) == 1
    assert d.main(["--root", str(project)]) == 0
    assert "NOT FOUND" in capsys.readouterr().out


def test_single_key_and_json(project, capsys) -> None:
    (project / "go.mod").write_text("module x")
    assert d.main(["--root", str(project), "build"]) == 0
    assert capsys.readouterr().out.strip() == "go build ./..."
    assert d.main(["--root", str(project), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["build"]["source"] == "go.mod"
