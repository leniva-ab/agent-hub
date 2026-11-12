"""Create and validate the evidence JSON that gates "done".

``new`` writes a skeleton with every check marked ``not_verified``. ``check`` validates a
file: required fields, known results, evidence on every pass, and ``verified`` true only
when everything passes. Exit 0 valid, 1 invalid.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_CHECKS = ("build and lint", "unit tests", "diff coverage", "mutation", "e2e", "review")
type Json = dict[str, Any]
RESULTS = {"pass", "fail", "not_verified"}


def skeleton(task: str, commit: str) -> Json:
    """Build an evidence document with nothing verified yet."""
    return {
        "task": task,
        "verified": False,
        "criteria": [],
        "checks": [{"name": name, "result": "not_verified", "evidence": ""} for name in REQUIRED_CHECKS],
        "exclusions": [],
        "models": {"orchestrator": "", "implementer": "", "verifier": ""},
        "commit": commit,
    }


def validate(doc: Json) -> list[str]:
    """Return a list of problems, empty when the evidence is valid.

    Args:
        doc: Parsed evidence JSON.

    Returns:
        Human-readable problems.
    """
    errors = [
        f"missing field: {key}"
        for key in ("task", "verified", "criteria", "checks", "exclusions", "models", "commit")
        if key not in doc
    ]
    if errors:
        return errors
    results: list[str] = []
    for item in doc["criteria"]:
        results.append(item.get("result", ""))
        if item.get("result") not in RESULTS:
            errors.append(f"criterion {item.get('id')}: result must be one of {sorted(RESULTS)}")
        if item.get("result") == "pass" and not item.get("unit"):
            errors.append(f"criterion {item.get('id')}: passes with no unit test named")
    names = {c.get("name") for c in doc["checks"]}
    errors += [f"missing check: {name}" for name in REQUIRED_CHECKS if name not in names]
    for item in doc["checks"]:
        results.append(item.get("result", ""))
        if item.get("result") not in RESULTS:
            errors.append(f"check {item.get('name')}: result must be one of {sorted(RESULTS)}")
        elif item["result"] == "pass" and not str(item.get("evidence", "")).strip():
            errors.append(f"check {item.get('name')}: pass without evidence")
    if not doc["commit"]:
        errors.append("commit is empty")
    all_pass = bool(doc["checks"]) and all(r == "pass" for r in results)
    if doc["verified"] and not all_pass:
        errors.append("verified is true but not every criterion and check passes")
    if not doc["verified"] and all_pass and not errors:
        errors.append("every criterion and check passes but verified is false")
    return errors


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(prog="agent-evidence", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new")
    new.add_argument("--task", required=True)
    new.add_argument("--commit", required=True)
    check = sub.add_parser("check")
    check.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    if args.command == "new":
        print(json.dumps(skeleton(args.task, args.commit), indent=2))
        return 0
    try:
        doc = json.loads(args.file.read_text())
    except (OSError, json.JSONDecodeError) as error:
        print(f"agent-evidence: {error}", file=sys.stderr)
        return 1
    errors = validate(doc)
    for line in errors:
        print(line, file=sys.stderr)
    print("valid" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
