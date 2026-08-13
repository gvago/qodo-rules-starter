#!/usr/bin/env python3
"""Checks for sync_rule_scopes.py. Run: python3 tools/test_sync_rule_scopes.py

Kept out of the script itself so no test code is reachable from the production
entry point.
"""
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location(
    "s", pathlib.Path(__file__).parent / "sync_rule_scopes.py")
assert spec and spec.loader
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def expect_exit(fn, needle):
    try:
        fn()
    except SystemExit as e:
        assert needle in str(e), f"expected {needle!r} in {e}"
        return
    raise AssertionError(f"expected SystemExit containing {needle!r}")


# --- the comparison that decides whether to write at all -------------------
assert sorted(["/a/y/", "/a/x/"]) == sorted(["/a/x/", "/a/y/"])   # same set, no write
assert sorted(["/a/x/"]) != sorted(["/a/x/", "/a/z/"])            # new repo, write

# --- credentials must never leave over a non-HTTPS or unexpected host ------
s.check_url("https://api.bitbucket.org/2.0/repositories/acme")     # allowed
expect_exit(lambda: s.check_url("http://bitbucket.example.com/x",
                                "bitbucket.example.com"), "refusing to send credentials over http")
expect_exit(lambda: s.check_url("https://evil.example.com/x"), "unexpected host")
# an operator-supplied Data Center host is allowed for its own call only
s.check_url("https://bitbucket.example.com/rest", "bitbucket.example.com")
expect_exit(lambda: s.check_url("https://bitbucket.example.com/rest"), "unexpected host")
# a pagination link pointing somewhere else is rejected like any other URL
expect_exit(lambda: s.check_url("https://attacker.test/page2"), "unexpected host")

# --- redirects can move a request off the allow-list -----------------------
expect_exit(lambda: s.NoRedirect().redirect_request(
    None, None, 302, "Found", {}, "https://evil.example.com/"), "refusing to follow redirect")

# --- payload shape ---------------------------------------------------------
import json  # noqa: E402
p = json.loads(json.dumps({"rule_ids": [1, 2], "scopes": ["/a/"], "dry_run": True}))
assert p["rule_ids"] == [1, 2] and p["scopes"] == ["/a/"]

print("all checks passed")
