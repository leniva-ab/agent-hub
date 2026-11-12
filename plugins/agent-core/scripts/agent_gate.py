"""Diff coverage gate: are all changed lines covered, measured from a real report.

Reads a unified diff (from ``git diff``) and a coverage report (Cobertura XML, JaCoCo XML,
lcov or a Go cover profile, auto-detected) and prints JSON. A changed source file missing
from the report is listed in ``unreported_files`` and fails the gate, so unmeasured code
cannot pass by being invisible. Exit 0 pass, 1 fail, 2 bad input.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SOURCE_SUFFIXES = {".py", ".java", ".kt", ".go", ".rs", ".ts", ".tsx", ".js", ".jsx", ".cs", ".rb", ".php", ".scala"}
DEFAULT_EXCLUDES = ["*test*", "*Test*", "*/tests/*", "*/test/*", "*.config.*", "*conftest*"]
type Json = dict[str, Any]
type LineMap = dict[str, dict[int, bool]]  # file -> line -> fully covered (lines and branches)


def parse_diff(text: str) -> dict[str, set[int]]:
    """Return added line numbers per file from a zero-context unified diff.

    Args:
        text: Output of ``git diff -U0``.

    Returns:
        Mapping of new-file path to its added line numbers. Deleted files are skipped.
    """
    changed: dict[str, set[int]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("+++ "):
            current = None if line.endswith("/dev/null") else line[4:].removeprefix("b/")
        elif line.startswith("@@") and current:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                start, count = int(match.group(1)), int(match.group(2) or 1)
                changed.setdefault(current, set()).update(range(start, start + count))
    return changed


def parse_cobertura(root: ET.Element) -> LineMap:
    """Parse Cobertura XML. A line with partial condition coverage counts as uncovered."""
    lines: LineMap = {}
    for cls in root.iter("class"):
        target = lines.setdefault(cls.get("filename", ""), {})
        for el in cls.iter("line"):
            number = int(el.get("number", "0"))
            partial = "condition-coverage" in el.attrib and not el.get("condition-coverage", "").startswith("100%")
            target[number] = target.get(number, True) and int(el.get("hits", "0")) > 0 and not partial
    return lines


def parse_jacoco(root: ET.Element) -> LineMap:
    """Parse JaCoCo XML. Missed instructions or branches make a line uncovered."""
    lines: LineMap = {}
    for pkg in root.iter("package"):
        for source in pkg.iter("sourcefile"):
            target = lines.setdefault(f"{pkg.get('name', '')}/{source.get('name', '')}".lstrip("/"), {})
            for el in source.iter("line"):
                target[int(el.get("nr", "0"))] = int(el.get("mi", "0")) == 0 and int(el.get("mb", "0")) == 0
    return lines


def parse_lcov(text: str) -> LineMap:
    """Parse lcov. A DA hit of 0, or any untaken BRDA on a line, makes it uncovered."""
    lines: LineMap = {}
    target: dict[int, bool] = {}
    for raw in text.splitlines():
        if raw.startswith("SF:"):
            target = lines.setdefault(raw[3:], {})
        elif raw.startswith("DA:"):
            number, hits, *_ = raw[3:].split(",")
            target[int(number)] = target.get(int(number), True) and int(hits) > 0
        elif raw.startswith("BRDA:"):
            number, _block, _branch, taken = raw[5:].split(",")
            if taken in ("-", "0"):
                target[int(number)] = False
    return lines


def parse_go(text: str) -> LineMap:
    """Parse a Go cover profile. A line is covered only if every block touching it ran."""
    lines: LineMap = {}
    for raw in text.splitlines()[1:]:
        match = re.match(r"(.+):(\d+)\.\d+,(\d+)\.\d+ \d+ (\d+)$", raw)
        if match:
            target = lines.setdefault(match.group(1), {})
            for number in range(int(match.group(2)), int(match.group(3)) + 1):
                target[number] = target.get(number, True) and int(match.group(4)) > 0
    return lines


def load_report(path: Path) -> LineMap:
    """Detect the report format from its content and parse it."""
    text = path.read_text()
    head = text.lstrip()[:300]
    if head.startswith("mode:"):
        return parse_go(text)
    if text.startswith("TN:") or text.startswith("SF:"):
        return parse_lcov(text)
    root = ET.fromstring(text)
    if root.tag == "report":
        return parse_jacoco(root)
    if root.tag == "coverage":
        return parse_cobertura(root)
    raise ValueError(f"unrecognised coverage report format: {path}")


def find_entry(report: LineMap, changed: str) -> dict[int, bool] | None:
    """Match a changed path to a report path by path suffix (reports use varying roots)."""
    for name, lines in report.items():
        if name and (changed == name or changed.endswith("/" + name) or name.endswith("/" + changed)):
            return lines
    return None


def gate(changed: dict[str, set[int]], report: LineMap, excludes: list[str], threshold: float = 100.0) -> Json:
    """Compare changed lines with coverage.

    Args:
        changed: Added lines per file.
        report: Coverage per file and line.
        excludes: Glob patterns for files not subject to the gate (tests, config).
        threshold: Required percentage of measurable changed lines covered.

    Returns:
        A result dict with percent, uncovered lines, unreported files and ``pass``.
    """
    covered = total = 0
    uncovered: dict[str, list[int]] = {}
    unreported: list[str] = []
    for path, numbers in sorted(changed.items()):
        if Path(path).suffix not in SOURCE_SUFFIXES or any(fnmatch.fnmatch(path, g) for g in excludes):
            continue
        entry = find_entry(report, path)
        if entry is None:
            unreported.append(path)
            continue
        for number in sorted(numbers & entry.keys()):
            total += 1
            if entry[number]:
                covered += 1
            else:
                uncovered.setdefault(path, []).append(number)
    percent = 100.0 if total == 0 else round(100 * covered / total, 2)
    return {
        "threshold": threshold,
        "percent": percent,
        "measured_lines": total,
        "covered_lines": covered,
        "uncovered": uncovered,
        "unreported_files": unreported,
        "pass": percent >= threshold and not unreported,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(prog="agent-gate", description=__doc__.split("\n\n")[0])
    parser.add_argument("--report", type=Path, required=True, help="coverage report file")
    parser.add_argument("--base", default="origin/main", help="git base ref for the diff")
    parser.add_argument("--diff-file", type=Path, help="read a unified diff from a file instead of git")
    parser.add_argument("--threshold", type=float, default=100.0)
    parser.add_argument("--exclude", action="append", default=[], help="extra glob to skip (repeatable)")
    args = parser.parse_args(argv)
    try:
        if args.diff_file:
            diff = args.diff_file.read_text()
        else:
            diff = subprocess.run(
                ["git", "diff", "-U0", f"{args.base}...HEAD"], capture_output=True, text=True, check=True
            ).stdout
        result = gate(parse_diff(diff), load_report(args.report), DEFAULT_EXCLUDES + args.exclude, args.threshold)
    except (OSError, ValueError, ET.ParseError, subprocess.CalledProcessError) as error:
        print(f"agent-gate: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
