"""Find the project's build, test, lint, coverage and e2e commands without guessing.

Order of trust: the AGENTS.md settings table (confirmed), Makefile targets, then
ecosystem files. Only the first two-or-three sources are read, never the whole repo.
Anything not found is reported as null so the agent asks instead of inventing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

KEYS = ("build", "test", "lint", "coverage", "e2e")
LABELS = {"build": "build", "unit": "test", "test": "test", "lint": "lint", "coverage": "coverage", "e2e": "e2e"}
type Found = dict[str, dict[str, object]]


def _entry(command: str, source: str, confirmed: bool) -> dict[str, object]:
    return {"command": command, "source": source, "confirmed": confirmed}


def from_agents_md(root: Path) -> Found:
    """Read commands from the settings table in AGENTS.md.

    Args:
        root: Project root.

    Returns:
        Entries marked confirmed, for rows whose value is non-empty.
    """
    path = root / "AGENTS.md"
    if not path.is_file():
        return {}
    found: Found = {}
    for line in path.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or not cells[1] or set(cells[1]) <= {"-", ":"}:
            continue
        label = cells[0].lower()
        key = next((v for k, v in LABELS.items() if label.startswith(k)), None)
        value = cells[1].strip("`").strip()
        if key and key not in found and value and not value.startswith(("none", "n/a")):
            found[key] = _entry(value, "AGENTS.md", True)
    return found


def from_makefile(root: Path) -> Found:
    """Map Makefile targets named like the keys to ``make <target>``."""
    path = root / "Makefile"
    if not path.is_file():
        return {}
    targets = set(re.findall(r"^([A-Za-z0-9_.-]+)\s*:(?!=)", path.read_text(), re.MULTILINE))
    names = {
        "build": ["build"],
        "test": ["test", "check"],
        "lint": ["lint"],
        "coverage": ["coverage", "cov"],
        "e2e": ["e2e"],
    }
    found: Found = {}
    for key, options in names.items():
        target = next((t for t in options if t in targets), None)
        if target:
            found[key] = _entry(f"make {target}", "Makefile", False)
    return found


def _node(root: Path) -> Found:
    package = root / "package.json"
    if not package.is_file():
        return {}
    scripts = json.loads(package.read_text()).get("scripts", {})
    runner = (
        "pnpm"
        if (root / "pnpm-lock.yaml").exists()
        else "yarn"
        if (root / "yarn.lock").exists()
        else "bun"
        if (root / "bun.lock").exists() or (root / "bun.lockb").exists()
        else "npm"
    )
    names = {
        "build": ["build"],
        "test": ["test"],
        "lint": ["lint"],
        "coverage": ["test:coverage", "coverage"],
        "e2e": ["test:e2e", "e2e"],
    }
    out: Found = {}
    for key, options in names.items():
        for name in options:
            if name in scripts:
                out[key] = _entry(f"{runner} run {name}" if name != "test" else f"{runner} test", "package.json", False)
                break
    return out


def _python(root: Path) -> Found:
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return {}
    data = tomllib.loads(pyproject.read_text())
    prefix = "uv run " if (root / "uv.lock").exists() else "poetry run " if "poetry" in data.get("tool", {}) else ""
    out: Found = {
        "test": _entry(f"{prefix}pytest", "pyproject.toml", False),
        "coverage": _entry(f"{prefix}pytest --cov --cov-branch --cov-report=xml", "pyproject.toml", False),
    }
    if "ruff" in data.get("tool", {}):
        out["lint"] = _entry(f"{prefix}ruff check . && {prefix}ruff format --check .", "pyproject.toml", False)
    if prefix == "uv run " and (root / "uv.lock").exists():
        out["build"] = _entry("uv build", "pyproject.toml", False)
    elif prefix == "poetry run ":
        out["build"] = _entry("poetry build", "pyproject.toml", False)
    return out


def _simple(root: Path) -> Found:
    if (root / "go.mod").is_file():
        return {
            "build": _entry("go build ./...", "go.mod", False),
            "test": _entry("go test ./...", "go.mod", False),
            "lint": _entry("go vet ./...", "go.mod", False),
            "coverage": _entry("go test -coverprofile=coverage.out ./...", "go.mod", False),
        }
    if (root / "Cargo.toml").is_file():
        return {
            "build": _entry("cargo build", "Cargo.toml", False),
            "test": _entry("cargo test", "Cargo.toml", False),
            "lint": _entry("cargo clippy -- -D warnings", "Cargo.toml", False),
        }
    if (root / "gradlew").is_file():
        return {
            "build": _entry("./gradlew build", "gradlew", False),
            "test": _entry("./gradlew test", "gradlew", False),
            "coverage": _entry("./gradlew test jacocoTestReport", "gradlew", False),
        }
    if (root / "pom.xml").is_file():
        return {"build": _entry("mvn -B verify", "pom.xml", False), "test": _entry("mvn -B test", "pom.xml", False)}
    return {}


def detect(root: Path) -> dict[str, dict[str, object] | None]:
    """Detect commands for every key, trusting AGENTS.md first.

    Args:
        root: Project root.

    Returns:
        A mapping from each key to an entry, or None when nothing was found.
    """
    merged: Found = {}
    for source in (from_agents_md, from_makefile, _node, _python, _simple):
        for key, entry in source(root).items():
            merged.setdefault(key, entry)
    return {key: merged.get(key) for key in KEYS}


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Exit 0 always; a null entry means "ask the human"."""
    parser = argparse.ArgumentParser(prog="agent-detect", description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    parser.add_argument("key", nargs="?", choices=KEYS, help="print only this command (exit 1 if unknown)")
    args = parser.parse_args(argv)
    result = detect(args.root)
    if args.key:
        entry = result[args.key]
        if entry is None:
            print(f"no {args.key} command found: ask the human and add it to AGENTS.md", file=sys.stderr)
            return 1
        print(entry["command"])
        return 0
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    for key, entry in result.items():
        text = (
            "NOT FOUND (ask the human)"
            if entry is None
            else f"{entry['command']}  [{entry['source']}{'' if entry['confirmed'] else ', unconfirmed'}]"
        )
        print(f"{key:9}{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
