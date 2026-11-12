"""Tests for env, sink and report."""

from __future__ import annotations

import gzip
import json
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import agent_telemetry as at

type Body = Callable[..., dict[str, Any]]


def test_build_env_tags_project_and_version() -> None:
    env = at.build_env("ord", "2026-11-a")
    assert env["CLAUDE_CODE_ENABLE_TELEMETRY"] == "1"
    assert env["OTEL_RESOURCE_ATTRIBUTES"] == "project=ord,config.version=2026-11-a"
    assert env["OTEL_EXPORTER_OTLP_PROTOCOL"] == "http/json"
    assert env["OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE"] == "delta"


def test_delta_points_are_added(metrics_body: Body) -> None:
    points = [*at.iter_points(metrics_body(tokens=100)), *at.iter_points(metrics_body(tokens=50, time=20))]
    result = at.totals(points)
    assert result["v1"].tokens["input"] == 150
    assert result["v1"].cost == pytest.approx(1.0)


def test_cumulative_series_counts_latest_only(metrics_body: Body) -> None:
    points = [
        *at.iter_points(metrics_body(tokens=100, temporality=2, time=10)),
        *at.iter_points(metrics_body(tokens=160, temporality=2, time=20)),
        *at.iter_points(metrics_body(tokens=130, temporality=2, time=15)),
    ]
    assert at.totals(points)["v1"].tokens["input"] == 160


def test_cumulative_restart_adds_series(metrics_body: Body) -> None:
    points = [
        *at.iter_points(metrics_body(tokens=100, temporality=2, time=10, start=1)),
        *at.iter_points(metrics_body(tokens=30, temporality=2, time=12, start=11)),
    ]
    assert at.totals(points)["v1"].tokens["input"] == 130


def test_temporality_as_enum_string(metrics_body: Body) -> None:
    body = metrics_body(tokens=100, temporality="AGGREGATION_TEMPORALITY_CUMULATIVE", time=10)
    later = metrics_body(tokens=120, temporality="AGGREGATION_TEMPORALITY_CUMULATIVE", time=20)
    points = [*at.iter_points(body), *at.iter_points(later)]
    assert at.totals(points)["v1"].tokens["input"] == 120


def test_group_by_config_project_model(metrics_body: Body) -> None:
    points = [
        *at.iter_points(metrics_body(config="v1", project="a", tokens=10, model="m1")),
        *at.iter_points(metrics_body(config="v2", project="b", tokens=20, model="m2")),
    ]
    assert set(at.totals(points, "config")) == {"v1", "v2"}
    assert set(at.totals(points, "project")) == {"a", "b"}
    assert set(at.totals(points, "model")) == {"m1", "m2"}


def test_untagged_when_attribute_missing() -> None:
    body = {
        "resourceMetrics": [
            {
                "resource": {"attributes": []},
                "scopeMetrics": [
                    {
                        "metrics": [
                            {
                                "name": at.TOKEN_METRIC,
                                "sum": {
                                    "aggregationTemporality": 1,
                                    "dataPoints": [
                                        {
                                            "attributes": [{"key": "type", "value": {"stringValue": "output"}}],
                                            "asInt": "7",
                                        }
                                    ],
                                },
                            }
                        ]
                    }
                ],
            }
        ]
    }
    assert at.totals(at.iter_points(body))[at.UNTAGGED].tokens["output"] == 7


def test_cache_read_share(metrics_body: Body) -> None:
    points = [
        *at.iter_points(metrics_body(token_type="cacheRead", tokens=900)),
        *at.iter_points(metrics_body(token_type="input", tokens=50)),
        *at.iter_points(metrics_body(token_type="cacheCreation", tokens=50)),
        *at.iter_points(metrics_body(token_type="output", tokens=999)),
    ]
    assert at.totals(points)["v1"].cache_read_share == pytest.approx(0.9)
    assert at.Totals().cache_read_share is None


def test_unknown_token_type_ignored(metrics_body: Body) -> None:
    result = at.totals(at.iter_points(metrics_body(token_type="weird", tokens=5)))
    assert sum(result["v1"].tokens.values()) == 0


@pytest.mark.parametrize("body", [{}, {"resourceMetrics": "x"}, {"resourceMetrics": [1]}, {"resourceMetrics": [{"scopeMetrics": [1]}]}])
def test_malformed_bodies_yield_nothing(body: dict[str, Any]) -> None:
    assert list(at.iter_points(body)) == []


def test_format_report_table(metrics_body: Body) -> None:
    text = at.format_report(at.totals(at.iter_points(metrics_body())), "config")
    lines = text.splitlines()
    assert lines[0].startswith("config")
    assert lines[1].startswith("v1")
    assert "0.00" in lines[1]
    assert "0.5000" in lines[1]


def _post(url: str, data: bytes, headers: dict[str, str] | None = None) -> int:
    request = urllib.request.Request(url, data=data, headers=headers or {}, method="POST")  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return int(response.status)
    except urllib.error.HTTPError as error:
        return error.code


def test_sink_roundtrip_and_report(tmp_path: Path, metrics_body: Body, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "data" / "otlp.jsonl"
    server = at.make_server("127.0.0.1", 0, out)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/v1/metrics"
        payload = json.dumps(metrics_body(tokens=42)).encode()
        assert _post(url, payload) == 200
        assert _post(url, gzip.compress(payload), {"Content-Encoding": "gzip"}) == 200
        assert _post(url, b"\x0a\x02protobuf") == 415
        assert _post(url, gzip.compress(b"not json"), {"Content-Encoding": "gzip"}) == 415
        assert _post(url, b"not gzip", {"Content-Encoding": "gzip"}) == 415
    finally:
        server.shutdown()
        server.server_close()
    assert len(out.read_text().splitlines()) == 2
    assert at.main(["report", "--file", str(out)]) == 0
    assert "84" in capsys.readouterr().out


def test_sink_bounds_body_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(at, "MAX_BODY_BYTES", 1024)
    out = tmp_path / "otlp.jsonl"
    server = at.make_server("127.0.0.1", 0, out)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/v1/metrics"
    try:
        assert _post(url, b"") == 411
        assert _post(url, b"x" * 2048) == 413
        assert _post(url, gzip.compress(b"0" * 100_000), {"Content-Encoding": "gzip"}) == 413
    finally:
        server.shutdown()
        server.server_close()
    assert not out.exists()


def test_read_points_skips_bad_lines(tmp_path: Path, metrics_body: Body) -> None:
    path = tmp_path / "f.jsonl"
    good = json.dumps({"body": metrics_body(tokens=3)})
    path.write_text(f"garbage\n[1]\n{json.dumps({'body': 'x'})}\n{good}\n")
    assert at.totals(at.read_points(path))["v1"].tokens["input"] == 3


def test_main_env_report_errors_and_usage(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AGENT_PROJECT", "bil")
    assert at.main(["env", "--config-version", "x1"]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["env"]["OTEL_RESOURCE_ATTRIBUTES"] == "project=bil,config.version=x1"
    assert at.main(["report", "--file", str(tmp_path / "missing")]) == 1
    assert at.main(["report", "--group-by", "nope"]) == 64
    assert at.main([]) == 64
