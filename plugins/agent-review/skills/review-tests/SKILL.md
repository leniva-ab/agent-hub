---
name: review-tests
description: Contract for the tests reviewer in the review pipeline: what to look for in a diff. Preloaded by agent review-tests.
---

# Category: tests

Look for: each AC has a test that would fail if the behaviour broke, assertions that assert nothing, missing error-path and edge tests, coverage gaps on changed code
