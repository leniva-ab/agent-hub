"""Shared fixtures for the agent-telemetry tests."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def _attr(key: str, value: str) -> dict[str, Any]:
    return {"key": key, "value": {"stringValue": value}}


@pytest.fixture
def metrics_body() -> Callable[..., dict[str, Any]]:
    """Build an OTLP JSON metrics request with one token point and one cost point."""

    def _make(
        config: str = "v1",
        project: str = "ord",
        token_type: str = "input",
        tokens: int = 100,
        cost: float = 0.5,
        temporality: int | str = 1,
        time: int = 10,
        start: int = 1,
        model: str = "claude-sonnet-5-5",
    ) -> dict[str, Any]:
        point_attrs = [_attr("type", token_type), _attr("model", model)]
        return {
            "resourceMetrics": [
                {
                    "resource": {"attributes": [_attr("config.version", config), _attr("project", project)]},
                    "scopeMetrics": [
                        {
                            "metrics": [
                                {
                                    "name": "claude_code.token.usage",
                                    "sum": {
                                        "aggregationTemporality": temporality,
                                        "dataPoints": [
                                            {
                                                "attributes": point_attrs,
                                                "startTimeUnixNano": str(start),
                                                "timeUnixNano": str(time),
                                                "asInt": str(tokens),
                                            }
                                        ],
                                    },
                                },
                                {
                                    "name": "claude_code.cost.usage",
                                    "sum": {
                                        "aggregationTemporality": temporality,
                                        "dataPoints": [
                                            {
                                                "attributes": [_attr("model", model)],
                                                "startTimeUnixNano": str(start),
                                                "timeUnixNano": str(time),
                                                "asDouble": cost,
                                            }
                                        ],
                                    },
                                },
                                {"name": "something.else", "sum": {"dataPoints": [{"asInt": "5"}]}},
                            ]
                        }
                    ],
                }
            ]
        }

    return _make
