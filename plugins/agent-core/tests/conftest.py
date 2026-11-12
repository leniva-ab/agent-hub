"""Shared fixtures for agent-core script tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

DIFF = """\
diff --git a/src/app/service.py b/src/app/service.py
--- a/src/app/service.py
+++ b/src/app/service.py
@@ -0,0 +1,3 @@
+a
+b
+c
diff --git a/tests/test_service.py b/tests/test_service.py
--- a/tests/test_service.py
+++ b/tests/test_service.py
@@ -1 +1,2 @@
+x
+y
"""


@pytest.fixture
def diff() -> str:
    """A diff adding 3 source lines and 2 test lines."""
    return DIFF


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """An empty project directory."""
    return tmp_path
