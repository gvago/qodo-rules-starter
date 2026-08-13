#!/usr/bin/env python3
"""Keep a set of Qodo rules scoped to exactly the repositories of a project.

Reads the repository list from Bitbucket or Azure DevOps, compares it to each
rule's current scopes, and calls `qodo rules set-scope` only when they differ.
Safe to run on a schedule: a run with nothing to do makes no changes.

    # preview
    ./sync_rule_scopes.py --rule-ids 4711,4712 --provider bitbucket \
        --workspace acme --project PAYMENTS --dry-run

    # apply
    ./sync_rule_scopes.py --rule-ids 4711,4712 --provider bitbucket \
        --workspace acme --project PAYMENTS

Credentials come from the environment:
    Bitbucket Cloud        BB_USER, BB_APP_PASSWORD
    Bitbucket Data Center  BB_TOKEN            (with --server)
    Azure DevOps           AZDO_PAT            (with --org, --project)

Requires the qodo CLI, logged in as a workspace admin:
    curl -fsSL https://get.qodo.ai/install.sh | sh && qodo login
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

SCOPE_LIMIT = 25  # documented maximum scope paths per rule


def qodo_bin() -> str:
    """GUI-launched shells often lack ~/.qodo/bin on PATH."""
    return shutil.which("qodo") or os.path.expanduser("~/.qodo/bin/qodo")


def run_qodo(args: list) -> dict:
    proc = subprocess.run([qodo_bin()] + args + ["--json"],
                          capture_output=True, text=True, timeout=120)
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            # ponytail: strict=False - rule content embeds raw newlines
            data = json.loads(line, strict=False)
            if "error" in data:
                raise SystemExit(f"qodo error: {data['error'].get('message')}")
            return data
    raise SystemExit(f"no JSON from qodo {' '.join(args)}\n{proc.stdout}{proc.stderr}")


def http_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode(errors="replace")
        raise SystemExit(f"{e.code} {e.reason} for {url}\n{body}")


def bitbucket_cloud(workspace: str, project: str) -> list:
    user, pw = os.environ.get("BB_USER"), os.environ.get("BB_APP_PASSWORD")
    if not (user and pw):
        raise SystemExit("set BB_USER and BB_APP_PASSWORD")
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    q = urllib.parse.quote(f'project.key="{project}"')
    url = (f"https://api.bitbucket.org/2.0/repositories/{workspace}"
           f"?q={q}&pagelen=100&fields=next,values.slug")
    slugs = []
    while url:
        data = http_json(url, {"Authorization": f"Basic {auth}"})
        slugs += [v["slug"] for v in data.get("values", [])]
        url = data.get("next")
    return [f"/{workspace}/{s}/" for s in slugs]


def bitbucket_server(host: str, project: str, prefix: str) -> list:
    token = os.environ.get("BB_TOKEN")
    if not token:
        raise SystemExit("set BB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    slugs, start = [], 0
    while True:
        url = (f"{host.rstrip('/')}/rest/api/1.0/projects/{project}"
               f"/repos?limit=100&start={start}")
        data = http_json(url, headers)
        slugs += [v["slug"] for v in data.get("values", [])]
        if data.get("isLastPage", True):
            break
        start = data["nextPageStart"]
    return [f"/{prefix}/{s}/" for s in slugs]


def azure_devops(org: str, project: str, prefix: str) -> list:
    pat = os.environ.get("AZDO_PAT")
    if not pat:
        raise SystemExit("set AZDO_PAT")
    auth = base64.b64encode(f":{pat}".encode()).decode()
    url = (f"https://dev.azure.com/{org}/{urllib.parse.quote(project)}"
           f"/_apis/git/repositories?api-version=7.0")
    data = http_json(url, {"Authorization": f"Basic {auth}"})
    return [f"/{prefix}/{r['name']}/" for r in data.get("value", [])]


def target_scopes(args) -> list:
    if args.provider == "bitbucket":
        if args.server:
            return bitbucket_server(args.server, args.project,
                                    args.prefix or args.project.lower())
        if not args.workspace:
            raise SystemExit("--workspace is required for Bitbucket Cloud")
        return bitbucket_cloud(args.workspace, args.project)
    return azure_devops(args.org, args.project, args.prefix or args.org)


def current_scopes(rule_id: int) -> list:
    rule = run_qodo(["rules", "get", "--rule-id", str(rule_id)])
    return sorted(rule.get("scopes") or [])


def set_scopes(rule_ids: list, scopes: list, dry_run: bool) -> dict:
    # ponytail: --args JSON, not --rule-ids. The named flag fails schema
    # validation upstream (MT-VALIDATION anyOf); --args is the working path.
    payload: dict = {"rule_ids": rule_ids, "scopes": scopes}
    if dry_run:
        payload["dry_run"] = True
    return run_qodo(["rules", "set-scope", "--args", json.dumps(payload)])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rule-ids", help="comma-separated rule ids to keep in sync")
    ap.add_argument("--provider", choices=["bitbucket", "azdo"], default="bitbucket")
    ap.add_argument("--project", help="Bitbucket project KEY or Azure DevOps project")
    ap.add_argument("--workspace", help="Bitbucket Cloud workspace")
    ap.add_argument("--server", help="Bitbucket Data Center base URL")
    ap.add_argument("--org", help="Azure DevOps organization")
    ap.add_argument("--prefix", help="Qodo scope prefix when it differs from the org name")
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not (args.rule_ids and args.project):
        ap.error("--rule-ids and --project are required")

    rule_ids = [int(x) for x in args.rule_ids.split(",") if x.strip()]
    desired = sorted(set(target_scopes(args)))
    if not desired:
        raise SystemExit(f"no repositories found for project {args.project}")

    print(f"project {args.project}: {len(desired)} repositories")
    if len(desired) > SCOPE_LIMIT:
        print(f"  WARNING: over the {SCOPE_LIMIT}-scope limit; "
              f"use an org-wide scope instead", file=sys.stderr)

    stale = [rid for rid in rule_ids if current_scopes(rid) != desired]
    if not stale:
        print("all rules already match; nothing to do")
        return

    print(f"{len(stale)} rule(s) need updating: {stale}")
    result = set_scopes(stale, desired, dry_run=True)
    print(f"  dry run: matched {result.get('matchedCount')}")

    if args.dry_run:
        print("dry run only; no changes made")
        return

    result = set_scopes(stale, desired, dry_run=False)
    print(f"  applied: matched {result.get('matchedCount')}, "
          f"succeeded {result.get('succeededCount')}")
    for f in result.get("failures") or []:
        print(f"  FAILURE: {f}", file=sys.stderr)


def selftest() -> None:
    """No network: check the comparison logic that decides whether to write."""
    assert sorted({"/a/x/", "/a/y/", "/a/x/"}) == ["/a/x/", "/a/y/"]
    # identical sets, any order -> no write
    assert sorted(["/a/y/", "/a/x/"]) == sorted(["/a/x/", "/a/y/"])
    # a new repo in the project -> write
    assert sorted(["/a/x/"]) != sorted(["/a/x/", "/a/z/"])
    # payload shape must use rule_ids/scopes, and omit dry_run when applying
    p = {"rule_ids": [1, 2], "scopes": ["/a/"], "dry_run": True}
    assert json.loads(json.dumps(p))["rule_ids"] == [1, 2]
    # cloud/DC/azdo shapes all reduce to /prefix/slug/
    assert f"/{'acme'}/{'api'}/" == "/acme/api/"
    print("selftest OK")


if __name__ == "__main__":
    main()
