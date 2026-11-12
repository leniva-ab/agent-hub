"""Local telemetry for Claude Code: settings, a receiving sink, and a report.

Claude Code can export OpenTelemetry metrics and events. This tool needs no backend:

``env``
    Prints the ``env`` block for ``settings.json`` that turns the export on and tags it with the project
    and a config version.

``sink``
    Runs a small local OTLP/HTTP receiver that appends every JSON request to a JSONL file.

``report``
    Reads that file and totals token usage and cost, grouped by config version, project or model.

Standard library only. The sink takes OTLP over HTTP with a JSON body. It refuses protobuf bodies.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import zlib
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TOKEN_METRIC = "claude_code.token.usage"
COST_METRIC = "claude_code.cost.usage"
TOKEN_TYPES = ("input", "output", "cacheRead", "cacheCreation")
UNTAGGED = "(untagged)"
GROUP_KEYS = {"config": "config.version", "project": "project", "model": "model"}
DEFAULT_ENDPOINT = "http://127.0.0.1:4318"
DEFAULT_OUT = Path.home() / ".agent-telemetry" / "otlp.jsonl"


def build_env(project: str, config_version: str, endpoint: str = DEFAULT_ENDPOINT) -> dict[str, str]:
    """Build the environment that turns on the export.

    Args:
        project: Short project code, put in the resource attributes.
        config_version: Label for the current way of working, for example ``2026-11-a``.
        endpoint: Base URL of the OTLP receiver.

    Returns:
        Environment variable names and values.
    """
    return {
        "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
        "OTEL_METRICS_EXPORTER": "otlp",
        "OTEL_LOGS_EXPORTER": "otlp",
        "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json",
        "OTEL_EXPORTER_OTLP_ENDPOINT": endpoint,
        "OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE": "delta",
        "OTEL_RESOURCE_ATTRIBUTES": f"project={project},config.version={config_version}",
    }


@dataclass(frozen=True, slots=True)
class Point:
    """One metric data point.

    Attributes:
        metric: Metric name.
        cumulative: True when the value is a running total, False when it is a delta.
        resource: Resource attributes.
        attrs: Data point attributes.
        start: Series start time in nanoseconds.
        time: Data point time in nanoseconds.
        value: The value.
    """

    metric: str
    cumulative: bool
    resource: Mapping[str, str]
    attrs: Mapping[str, str]
    start: int
    time: int
    value: float


@dataclass(slots=True)
class Totals:
    """Sums for one group.

    Attributes:
        tokens: Tokens by type.
        cost: Cost in US dollars as reported by Claude Code, an approximation.
    """

    tokens: dict[str, float] = field(default_factory=lambda: dict.fromkeys(TOKEN_TYPES, 0.0))
    cost: float = 0.0

    @property
    def cache_read_share(self) -> float | None:
        """Share of input-side tokens served from cache, or None when there are none."""
        side = self.tokens["input"] + self.tokens["cacheRead"] + self.tokens["cacheCreation"]
        return self.tokens["cacheRead"] / side if side else None


def _attrs(items: object) -> dict[str, str]:
    result: dict[str, str] = {}
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict) or "key" not in item:
            continue
        value = item.get("value")
        if isinstance(value, dict) and value:
            result[str(item["key"])] = str(next(iter(value.values())))
    return result


def _int(value: object) -> int:
    try:
        return int(str(value))
    except ValueError:
        return 0


def _is_cumulative(value: object) -> bool:
    return value == 2 or (isinstance(value, str) and "CUMULATIVE" in value.upper())


def iter_points(body: Mapping[str, object]) -> Iterator[Point]:
    """Yield the data points of one OTLP JSON metrics request.

    Args:
        body: Parsed request body.

    Yields:
        One Point per number data point on a sum or gauge.
    """
    resource_metrics = body.get("resourceMetrics")
    for resource_entry in resource_metrics if isinstance(resource_metrics, list) else []:
        if not isinstance(resource_entry, dict):
            continue
        resource_block = resource_entry.get("resource")
        resource = _attrs(resource_block.get("attributes") if isinstance(resource_block, dict) else None)
        for scope in resource_entry.get("scopeMetrics") or []:
            for metric in scope.get("metrics") or [] if isinstance(scope, dict) else []:
                if not isinstance(metric, dict):
                    continue
                data = metric.get("sum") or metric.get("gauge") or {}
                if not isinstance(data, dict):
                    continue
                cumulative = _is_cumulative(data.get("aggregationTemporality"))
                for point in data.get("dataPoints") or []:
                    if not isinstance(point, dict):
                        continue
                    raw = point.get("asDouble", point.get("asInt", 0))
                    yield Point(
                        metric=str(metric.get("name", "")),
                        cumulative=cumulative,
                        resource=resource,
                        attrs=_attrs(point.get("attributes")),
                        start=_int(point.get("startTimeUnixNano")),
                        time=_int(point.get("timeUnixNano")),
                        value=float(raw or 0),
                    )


def read_points(path: Path) -> Iterator[Point]:
    """Yield every metric point recorded in a sink file.

    Args:
        path: JSONL file written by the sink.

    Yields:
        Points from all metrics requests. Lines that are not valid JSON are skipped.
    """
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            body = record.get("body") if isinstance(record, dict) else None
            if isinstance(body, dict):
                yield from iter_points(body)


def _group(point: Point, group_by: str) -> str:
    key = GROUP_KEYS[group_by]
    return point.attrs.get(key) or point.resource.get(key) or UNTAGGED


def totals(points: Sequence[Point] | Iterator[Point], group_by: str = "config") -> dict[str, Totals]:
    """Total token usage and cost per group.

    A delta point is added. For a cumulative series only the latest point counts, so a running total is
    not counted again on every export.

    Args:
        points: Data points.
        group_by: One of ``config``, ``project`` or ``model``.

    Returns:
        Totals by group name.
    """
    latest: dict[tuple[object, ...], Point] = {}
    deltas: list[Point] = []
    for point in points:
        if point.metric not in {TOKEN_METRIC, COST_METRIC}:
            continue
        if not point.cumulative:
            deltas.append(point)
            continue
        series = (point.metric, tuple(sorted(point.resource.items())), tuple(sorted(point.attrs.items())), point.start)
        if series not in latest or point.time >= latest[series].time:
            latest[series] = point
    result: dict[str, Totals] = defaultdict(Totals)
    for point in [*deltas, *latest.values()]:
        group = result[_group(point, group_by)]
        if point.metric == COST_METRIC:
            group.cost += point.value
        else:
            kind = point.attrs.get("type", "")
            if kind in group.tokens:
                group.tokens[kind] += point.value
    return dict(result)


def format_report(groups: Mapping[str, Totals], group_by: str) -> str:
    """Format totals as a table.

    Args:
        groups: Totals by group name.
        group_by: Name of the grouping, used as the first column title.

    Returns:
        The table as text.
    """
    header = [group_by, *TOKEN_TYPES, "cache_read_share", "cost_usd"]
    rows = [header]
    for name in sorted(groups):
        item = groups[name]
        share = item.cache_read_share
        rows.append(
            [
                name,
                *(f"{item.tokens[t]:.0f}" for t in TOKEN_TYPES),
                "n/a" if share is None else f"{share:.2f}",
                f"{item.cost:.4f}",
            ]
        )
    widths = [max(len(row[i]) for row in rows) for i in range(len(header))]
    return "\n".join("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip() for row in rows)


MAX_BODY_BYTES = 8 * 1024 * 1024
"""Largest request body accepted, compressed or not. Bigger posts get 413."""


def make_server(host: str, port: int, out: Path) -> ThreadingHTTPServer:
    """Create the receiving server.

    Args:
        host: Address to bind. Use ``127.0.0.1`` so only local processes can post.
        port: Port to bind, 0 picks a free one.
        out: JSONL file to append to. Its folder is created if missing.

    Returns:
        A server that is bound but not yet serving.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        """Accepts OTLP JSON posts and appends them to the file."""

        def do_POST(self) -> None:
            """Store one request."""
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            if length <= 0:
                self._reply(411)
                return
            if length > MAX_BODY_BYTES:
                self._reply(413)
                return
            raw = self.rfile.read(length)
            try:
                if self.headers.get("Content-Encoding") == "gzip":
                    inflater = zlib.decompressobj(wbits=31)
                    raw = inflater.decompress(raw, MAX_BODY_BYTES + 1)
                    if len(raw) > MAX_BODY_BYTES or inflater.unconsumed_tail:
                        self._reply(413)
                        return
                body = json.loads(raw)
            except (zlib.error, ValueError):
                self._reply(415)
                return
            line = json.dumps({"ts": datetime.now(UTC).isoformat(), "path": self.path, "body": body})
            with lock, out.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def _reply(self, status: int) -> None:
            """Send a bodiless response."""
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            """Stay quiet."""

    return ThreadingHTTPServer((host, port), Handler)


def _option(args: list[str], name: str, default: str) -> str:
    if name in args:
        index = args.index(name)
        if index + 1 < len(args):
            return args[index + 1]
    return default


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Arguments after the program name, defaults to sys.argv.

    Returns:
        Process exit code.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    command = args[0] if args else ""
    out = Path(_option(args, "--file", str(DEFAULT_OUT)))
    if command == "env":
        project = _option(args, "--project", os.environ.get("AGENT_PROJECT", "unknown"))
        version = _option(args, "--config-version", "unversioned")
        endpoint = _option(args, "--endpoint", DEFAULT_ENDPOINT)
        print(json.dumps({"env": build_env(project, version, endpoint)}, indent=2))
        return 0
    if command == "sink":
        port = int(_option(args, "--port", "4318"))
        server = make_server("127.0.0.1", port, out)
        print(f"listening on 127.0.0.1:{server.server_address[1]}, writing {out}", file=sys.stderr)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.server_close()
        return 0
    if command == "report":
        group_by = _option(args, "--group-by", "config")
        if group_by not in GROUP_KEYS:
            print(f"--group-by must be one of: {', '.join(GROUP_KEYS)}", file=sys.stderr)
            return 64
        if not out.is_file():
            print(f"no data file at {out}", file=sys.stderr)
            return 1
        print(format_report(totals(read_points(out), group_by), group_by))
        return 0
    print("usage: agent-telemetry env | sink | report [--group-by config|project|model] [--file F]", file=sys.stderr)
    return 64


if __name__ == "__main__":
    sys.exit(main())
