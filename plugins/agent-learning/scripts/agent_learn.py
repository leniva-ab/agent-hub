"""A log of corrections and where each one was promoted, so repeat corrections can be counted.

The idea: every time the developer corrects the agent, the correction is logged. A correction that
keeps coming back means the lesson was never stored in a place the agent reads, or was stored in the
wrong place. The log is append-only JSONL, so it is easy to diff and back up.

Commands:

``log TEXT [--tag TAG] [--project CODE]``
    Record one correction. A tag groups corrections that are the same lesson in different words.

``promote ID --to TARGET [--ref PATH]``
    Record that a correction was written into a lasting place.

``list [--open]``
    Show correction groups, most repeated first. ``--open`` hides the ones already promoted.

``status``
    Show the repeat rate and which promoted lessons still recur.

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

TARGETS = ("user-claude-md", "project-claude-md", "rule", "skill", "hook", "permission-deny")
NON_WORD = re.compile(r"[^\w\s]")
SPACES = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Correction:
    """One logged correction.

    Attributes:
        id: Sequence number, starting at 1.
        ts: UTC timestamp, ISO 8601.
        project: Project code, may be empty.
        tag: Group tag, may be empty.
        text: What the developer corrected.
        key: Group key: the tag when set, else the normalised text.
    """

    id: int
    ts: str
    project: str
    tag: str
    text: str
    key: str


@dataclass(frozen=True, slots=True)
class Promotion:
    """Where a correction was stored.

    Attributes:
        id: Id of the correction.
        ts: UTC timestamp, ISO 8601.
        to: One of TARGETS.
        ref: File or note that holds the lesson, may be empty.
    """

    id: int
    ts: str
    to: str
    ref: str


@dataclass(frozen=True, slots=True)
class Group:
    """Corrections that are the same lesson.

    Attributes:
        key: Group key.
        count: Number of corrections.
        last_text: Text of the latest correction.
        promoted_at: Timestamp of the first promotion, or None.
        promoted_to: Target of the first promotion, or None.
        after_promotion: Corrections logged after the first promotion.
    """

    key: str
    count: int
    last_text: str
    promoted_at: str | None
    promoted_to: str | None
    after_promotion: int


def normalise(text: str) -> str:
    """Make a group key from free text.

    Args:
        text: The correction.

    Returns:
        Lower-case text with punctuation removed and spaces collapsed.
    """
    return SPACES.sub(" ", NON_WORD.sub(" ", text.lower())).strip()


def log_path(environ: Mapping[str, str], home: Path) -> Path:
    """Return the log file path.

    Args:
        environ: Environment, read for ``AGENT_LEARN_DIR``.
        home: Home directory.

    Returns:
        Path of ``corrections.jsonl``.
    """
    base = Path(environ["AGENT_LEARN_DIR"]) if environ.get("AGENT_LEARN_DIR") else home / ".agent-learning"
    return base / "corrections.jsonl"


def load(path: Path) -> tuple[list[Correction], list[Promotion]]:
    """Read the log.

    Args:
        path: The JSONL file. A missing file is an empty log.

    Returns:
        Corrections and promotions in file order. Bad lines are skipped.
    """
    corrections: list[Correction] = []
    promotions: list[Promotion] = []
    if not path.is_file():
        return corrections, promotions
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
                if row["type"] == "correction":
                    corrections.append(
                        Correction(row["id"], row["ts"], row["project"], row["tag"], row["text"], row["key"])
                    )
                elif row["type"] == "promotion":
                    promotions.append(Promotion(row["id"], row["ts"], row["to"], row["ref"]))
            except (ValueError, KeyError, TypeError):
                continue
    return corrections, promotions


def _append(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def add_correction(path: Path, text: str, tag: str = "", project: str = "", now: datetime | None = None) -> Correction:
    """Append a correction.

    Args:
        path: The log file.
        text: What the developer corrected.
        tag: Optional group tag.
        project: Optional project code.
        now: Timestamp, defaults to the current UTC time.

    Returns:
        The new correction.

    Raises:
        ValueError: If the text is empty.
    """
    if not text.strip():
        msg = "correction text is empty"
        raise ValueError(msg)
    existing, _ = load(path)
    key = normalise(tag) if tag else normalise(text)
    item = Correction(
        id=max((c.id for c in existing), default=0) + 1,
        ts=(now or datetime.now(UTC)).isoformat(),
        project=project,
        tag=tag,
        text=text.strip(),
        key=key,
    )
    _append(path, {"type": "correction", **{f: getattr(item, f) for f in item.__slots__}})
    return item


def add_promotion(path: Path, correction_id: int, to: str, ref: str = "", now: datetime | None = None) -> Promotion:
    """Append a promotion.

    Args:
        path: The log file.
        correction_id: Id of the correction that was stored.
        to: One of TARGETS.
        ref: File or note that holds the lesson.
        now: Timestamp, defaults to the current UTC time.

    Returns:
        The new promotion.

    Raises:
        ValueError: If the target is unknown or the correction does not exist.
    """
    if to not in TARGETS:
        msg = f"target must be one of: {', '.join(TARGETS)}"
        raise ValueError(msg)
    corrections, _ = load(path)
    if all(c.id != correction_id for c in corrections):
        msg = f"no correction with id {correction_id}"
        raise ValueError(msg)
    item = Promotion(correction_id, (now or datetime.now(UTC)).isoformat(), to, ref)
    _append(path, {"type": "promotion", **{f: getattr(item, f) for f in item.__slots__}})
    return item


def groups(corrections: Sequence[Correction], promotions: Sequence[Promotion]) -> list[Group]:
    """Group corrections by key and attach promotion state.

    Args:
        corrections: All corrections.
        promotions: All promotions.

    Returns:
        Groups, most repeated first, then by key.
    """
    key_of = {c.id: c.key for c in corrections}
    first_promotion: dict[str, Promotion] = {}
    for promotion in promotions:
        key = key_of.get(promotion.id)
        if key is not None and (key not in first_promotion or promotion.ts < first_promotion[key].ts):
            first_promotion[key] = promotion
    members: dict[str, list[Correction]] = {}
    for correction in corrections:
        members.setdefault(correction.key, []).append(correction)
    result: list[Group] = []
    for key, items in members.items():
        first = first_promotion.get(key)
        after = sum(1 for c in items if first is not None and c.ts > first.ts)
        result.append(
            Group(
                key=key,
                count=len(items),
                last_text=items[-1].text,
                promoted_at=first.ts if first else None,
                promoted_to=first.to if first else None,
                after_promotion=after,
            )
        )
    return sorted(result, key=lambda g: (-g.count, g.key))


def repeat_rate(corrections: Sequence[Correction]) -> float | None:
    """Share of corrections whose lesson had already been corrected before.

    Args:
        corrections: All corrections, in time order.

    Returns:
        A number from 0 to 1, or None when there are no corrections.
    """
    if not corrections:
        return None
    seen: set[str] = set()
    repeats = 0
    for correction in corrections:
        if correction.key in seen:
            repeats += 1
        seen.add(correction.key)
    return repeats / len(corrections)


def format_status(corrections: Sequence[Correction], promotions: Sequence[Promotion]) -> str:
    """Format the status report.

    Args:
        corrections: All corrections.
        promotions: All promotions.

    Returns:
        Report text.
    """
    rate = repeat_rate(corrections)
    items = groups(corrections, promotions)
    failed = [g for g in items if g.after_promotion]
    lines = [
        f"corrections {len(corrections)}  lessons {len(items)}  "
        f"repeat_rate {'n/a' if rate is None else f'{rate:.2f}'}  "
        f"promoted_but_recurring {len(failed)}",
    ]
    lines += [
        f"recurring after {g.promoted_to}: {g.key} ({g.after_promotion}x). Wrong place, or not specific enough."
        for g in failed
    ]
    return "\n".join(lines)


def format_list(items: Sequence[Group], only_open: bool) -> str:
    """Format the group list.

    Args:
        items: Groups from ``groups``.
        only_open: Hide groups that have a promotion.

    Returns:
        One tab-separated line per group.
    """
    rows = [g for g in items if not (only_open and g.promoted_at)]
    return "\n".join(f"{g.count}\t{g.promoted_to or 'open'}\t{g.key}\t{g.last_text}" for g in rows)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-learn")
    sub = parser.add_subparsers(dest="command", required=True)
    log = sub.add_parser("log")
    log.add_argument("text", nargs="+")
    log.add_argument("--tag", default="")
    log.add_argument("--project", default="")
    promote = sub.add_parser("promote")
    promote.add_argument("id", type=int)
    promote.add_argument("--to", required=True, choices=TARGETS)
    promote.add_argument("--ref", default="")
    show = sub.add_parser("list")
    show.add_argument("--open", action="store_true")
    sub.add_parser("status")
    return parser


def main(argv: Sequence[str] | None = None, environ: Mapping[str, str] | None = None, home: Path | None = None) -> int:
    """Entry point.

    Args:
        argv: Arguments after the program name, defaults to sys.argv.
        environ: Environment, defaults to os.environ.
        home: Home directory, defaults to the user's home.

    Returns:
        Process exit code.
    """
    env = os.environ if environ is None else environ
    path = log_path(env, Path.home() if home is None else home)
    try:
        args = _parser().parse_args(list(sys.argv[1:] if argv is None else argv))
    except SystemExit as stop:
        return int(stop.code) if isinstance(stop.code, int) else 64
    try:
        if args.command == "log":
            project = args.project or env.get("AGENT_PROJECT", "")
            item = add_correction(path, " ".join(args.text), args.tag, project)
            print(f"logged {item.id} [{item.key}]")
        elif args.command == "promote":
            add_promotion(path, args.id, args.to, args.ref)
            print(f"promoted {args.id} to {args.to}")
        else:
            corrections, promotions = load(path)
            if args.command == "list":
                print(format_list(groups(corrections, promotions), args.open))
            else:
                print(format_status(corrections, promotions))
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
