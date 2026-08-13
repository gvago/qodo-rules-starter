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
    Bitbucket Cloud        BB_EMAIL, BB_API_TOKEN
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


ALLOWED_API_HOSTS = {"api.bitbucket.org", "dev.azure.com"}


def check_url(url: str, extra_host: str = "") -> str:
    """Reject anything that would leak the Authorization header.

    Credentials ride on every request, so the destination is a trust boundary:
    HTTPS only, and the host must be one we intended to talk to. Applied to
    pagination links too, since those come from the API response body.
    """
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https":
        raise SystemExit(f"refusing to send credentials over {parts.scheme or 'no'}://: {url}")
    allowed = ALLOWED_API_HOSTS | ({extra_host} if extra_host else set())
    if parts.hostname not in allowed:
        raise SystemExit(f"refusing to send credentials to unexpected host {parts.hostname}")
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect can move the request to a host the allow-list never saw."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SystemExit(f"refusing to follow redirect to {newurl}")


_opener = urllib.request.build_opener(NoRedirect)


def http_json(url: str, headers: dict, extra_host: str = "") -> dict:
    req = urllib.request.Request(check_url(url, extra_host), headers=headers)
    try:
        with _opener.open(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode(errors="replace")
        raise SystemExit(f"{e.code} {e.reason} for {url}\n{body}")


def bitbucket_cloud(workspace: str, project: str) -> list:
    # Atlassian removed app passwords on 2026-07-28; API tokens use the
    # Atlassian account email as the username, not the Bitbucket username.
    email = os.environ.get("BB_EMAIL")
    token = os.environ.get("BB_API_TOKEN")
    if not (email and token):
        raise SystemExit("set BB_EMAIL (Atlassian account email) and BB_API_TOKEN")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
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
    # The operator supplies this host, so it joins the allow-list for this call
    # only; check_url still enforces HTTPS on it.
    self_hosted = urllib.parse.urlsplit(host).hostname or ""
    headers = {"Authorization": f"Bearer {token}"}
    slugs, start = [], 0
    while True:
        url = (f"{host.rstrip('/')}/rest/api/1.0/projects/{project}"
               f"/repos?limit=100&start={start}")
        data = http_json(url, headers, extra_host=self_hosted)
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
    if not args.org:
        raise SystemExit("--org is required for Azure DevOps")
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
    args = ap.parse_args()

    if not (args.rule_ids and args.project):
        ap.error("--rule-ids and --project are required")

    rule_ids = [int(x) for x in args.rule_ids.split(",") if x.strip()]
    desired = sorted(set(target_scopes(args)))
    if not desired:
        raise SystemExit(f"no repositories found for project {args.project}")

    print(f"project {args.project}: {len(desired)} repositories")
    if len(desired) > SCOPE_LIMIT:
        # Fail before any write: the platform rejects an oversized list, so a
        # scheduled run would otherwise retry a known-invalid mutation forever.
        raise SystemExit(
            f"{len(desired)} repositories exceeds the {SCOPE_LIMIT}-scope limit "
            f"that applies to each rule individually. Scope these rules to the "
            f"whole organization instead, or duplicate each rule so every copy "
            f"covers at most {SCOPE_LIMIT} of the repositories.")

    stale = [rid for rid in rule_ids if current_scopes(rid) != desired]
    if not stale:
        print("all rules already match; nothing to do")
        return

    print(f"{len(stale)} rule(s) need updating: {stale}")
    result = set_scopes(stale, desired, dry_run=True)
    matched = result.get("matchedCount")
    print(f"  dry run: matched {matched}")

    # The preflight is only a safeguard if a mismatch stops the run. A short
    # match means some ids do not resolve, so applying would update part of the
    # set and leave the rest silently stale.
    if matched != len(stale):
        raise SystemExit(
            f"preflight mismatch: asked for {len(stale)} rule(s), matched {matched}. "
            f"Check the rule ids and permissions; nothing was changed.")

    if args.dry_run:
        print("dry run only; no changes made")
        return

    result = set_scopes(stale, desired, dry_run=False)
    succeeded = result.get("succeededCount")
    print(f"  applied: matched {result.get('matchedCount')}, succeeded {succeeded}")
    failures = result.get("failures") or []
    for f in failures:
        print(f"  FAILURE: {f}", file=sys.stderr)
    # Exit non-zero so cron and CI surface a partial failure instead of
    # reporting a broken reconcile as a success.
    if failures or succeeded != len(stale):
        raise SystemExit(
            f"sync incomplete: {succeeded} of {len(stale)} rule(s) updated")


if __name__ == "__main__":
    main()
