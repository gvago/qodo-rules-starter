# Central rules repo: writing rules Qodo imports, and mapping them to the right repos

This guide covers the second way to enforce standards with Qodo: the Review
Standards rule system, fed from files in your repositories. Use it when you
keep rules in a dedicated rules repository (per-language rules, global
security rules) and want them applied to the right repositories.

The `pr_compliance_checklist.yaml` approach in this repo's README works
without the rule system and is always repo-scoped. The rule system adds
central management, scoping, and analytics on top.

## 1. How Qodo picks up rules from files

When Qodo is installed on your Git organization, and again on every merged
push, it scans repositories for supported files and imports rules from them:

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `copilot-instructions.md`
- `best_practices.md`
- `RULE.md`
- files under `.cursor/rules/` (including `.cursorrules` and `.mdc` files)
- skills directories (for example `skills/<skill-name>/SKILL.md`)
- `pr_compliance_checklist.yaml`

Imported rules are normalized and enriched with a category, severity, scope,
and examples, then appear in the Rules tab of the portal and are enforced on
future pull requests.

Two behaviors to know up front:

- **Only new rules are synced.** After the initial import, merging changes to
  a supported file adds new rules, but edits to or deletions of already
  imported rules are not reflected. Manage those in the portal.
- **Scope comes from file location.** Rules extracted from a file are scoped
  to the folder containing that file. `src/payments/AGENTS.md` governs only
  changes under `src/payments/`. A file at the repository root governs that
  repository only, never the whole organization.

## 2. Writing rules that import cleanly

Extraction is automated, so structure the file for it:

- **One rule per heading or bullet.** Imperative voice, one to three
  sentences: "Never build SQL with string concatenation. Always use
  parameterized queries."
- **Put a good and a bad code snippet directly under the rule.** The importer
  keeps them as the rule's examples instead of generating its own.
- **Signal severity in the wording.** "Must" and "never" read as errors,
  "should" as warnings, "prefer" as recommendations.
- **Keep enforceable review rules separate from agent instructions.** A
  `CLAUDE.md` that mixes "how to run the tests" with review rules produces
  noisy imports. Give rules their own file or folder.
- **Split per-language rules into their own files** (`java/AGENTS.md`,
  `python/AGENTS.md`). Cleaner extraction, and much easier to re-scope each
  set to the right repositories later.

Example rule that imports well:

````markdown
## No raw SQL string concatenation
Never build SQL with string concatenation or interpolation.
Always use parameterized queries.

Bad:
```java
stmt.execute("SELECT * FROM users WHERE id = " + userId);
```

Good:
```java
ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
ps.setLong(1, userId);
```
````

## 3. Mapping central-repo rules to the right repositories

Because scope is derived from file location, rules imported from a central
rules repository are initially scoped to the rules repository itself. Getting
them applied to the rest of the organization is one deliberate step in the
portal, done once per rule set.

A layout that keeps this step simple:

```
your-org/engineering-rules/
├── global/AGENTS.md      # security and org-wide rules
├── java/AGENTS.md        # Java rules
├── python/AGENTS.md      # Python rules
└── go/AGENTS.md          # Go rules
```

After the import, open the Rules tab in the portal and re-scope each set in
bulk:

1. Filter the table by source so you see only the rules imported from one
   file (each rule shows the path it came from).
2. Select them all with the header checkbox.
3. Choose **Define scope**:
   - **Global** for the security set, applying it organization-wide.
   - **Specific repositories** for each language set, selecting the
     repositories it governs. Up to 25 organizations and repositories can be
     selected per rule, each with an optional path pattern.

Rules are enforced according to the new scope from the next review onward.
The Rules tab shows the effective scope on every rule, so the mapping is
auditable at a glance.

### Mapping scopes with the qodo CLI

Everything the portal does above can be scripted with the `qodo` CLI
(install: `curl -fsSL https://get.qodo.ai/install.sh | sh`, then
`qodo login`). This is the right tool when the mapping is a matrix you want
in version control, for example "the Java set applies to these 14 repos".

Scope paths are hierarchical: `/` is everything, `/acme/` is a Git
organization, `/acme/orders-svc/` is a repository, and
`/acme/orders-svc/src/payments/` is a folder. A rule matches a change when
any of its scopes is an ancestor of the changed file's path. Each rule holds
up to 25 scope paths.

```bash
# Find the imported rules and their ids (filter by name or current scope)
qodo rules list --name-contains "SQL" --json
qodo rules list --scopes "/acme/engineering-rules/" --json

# Inspect one rule before changing it
qodo rules get --rule-id 4711 --json

# Global security set: scope to everything (empty list = universal scope /)
qodo rules set-scope --rule-ids 4711,4712,4713 --scopes "" --dry-run
qodo rules set-scope --rule-ids 4711,4712,4713 --scopes ""

# Java set: scope to the Java repositories
qodo rules set-scope --rule-ids 4720,4721 \
  --scopes "/acme/orders-svc/","/acme/billing-svc/","/acme/gateway/"

# Create a rule directly with the mapping baked in (skips file import)
qodo rules create \
  --name "No raw SQL string concatenation" \
  --category Security --severity error \
  --content "Never build SQL with string concatenation or interpolation. Always use parameterized queries." \
  --good-examples 'ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?")' \
  --bad-examples 'stmt.execute("SELECT * FROM users WHERE id = " + userId)' \
  --scopes "/acme/orders-svc/","/acme/billing-svc/"
```

Three things to know before scripting:

- `set-scope` REPLACES the rule's full scope list, it does not merge. To add
  a repository, pass the union of the current scopes and the new one.
- Scope changes and rule creation require workspace admin permission. A
  non-admin `create` lands as a pending suggestion an admin must approve.
- Run any multi-rule `set-scope` with `--dry-run` first and check the
  matched count before the real call.

**If `--rule-ids` is rejected**, pass the arguments as JSON instead. On some
CLI versions the named flag fails with
`MT-VALIDATION: argument 'rule_ids' failed schema validation (anyOf)`
for every value, including a single id. The `--args` form works:

```bash
qodo rules set-scope --args '{"rule_ids":[4711,4712],"scopes":["/acme/orders-svc/"],"dry_run":true}' --json
qodo rules set-scope --args '{"rule_ids":[4711,4712],"scopes":["/acme/orders-svc/"]}' --json
```

## 3a. Keeping the mapping consistent as repositories are added

Everything above is a one-time mapping. A rule holds an explicit list of scope
paths, so a repository created next month is not covered until someone widens
the scope again.

There are three ways to keep it consistent, in increasing order of effort.
Choose the first one that fits.

### Option A: scope to the organization (no automation)

If the honest answer to "which repositories should this rule cover" is "all of
them", set the scope once to `/your-org/` and there is nothing to keep in sync.
New repositories are covered the moment they exist.

```bash
qodo rules set-scope --args '{"rule_ids":[4711,4712],"scopes":["/acme/"]}' --json
```

This is the right answer for organization-wide security and compliance rules,
and it is the option to reach for first. Only enumerate repositories when a
rule genuinely applies to a subset.

### Option B: a scheduled reconcile (a subset of repositories)

When a rule set maps to a project rather than the whole organization, run
`tools/sync_rule_scopes.py` on a schedule. It reads the repository list from
Bitbucket or Azure DevOps, compares it to each rule's current scopes, and calls
`set-scope` only when they differ.

```bash
# preview
python3 tools/sync_rule_scopes.py --rule-ids 4711,4712 \
    --provider bitbucket --workspace acme --project PAYMENTS --dry-run

# apply
python3 tools/sync_rule_scopes.py --rule-ids 4711,4712 \
    --provider bitbucket --workspace acme --project PAYMENTS
```

Bitbucket Data Center uses `--server https://bitbucket.example.com`, and Azure
DevOps uses `--provider azdo --org acme`. Credentials come from the
environment: `BB_USER` + `BB_APP_PASSWORD`, `BB_TOKEN`, or `AZDO_PAT`.

The script is idempotent. A run where the repository list has not changed
reports `all rules already match; nothing to do` and writes nothing, which is
what makes it safe to schedule:

```
0 6 * * *  cd /opt/qodo-rules && python3 tools/sync_rule_scopes.py \
             --rule-ids 4711,4712 --provider bitbucket \
             --workspace acme --project PAYMENTS >> sync.log 2>&1
```

Daily is enough for a repository list that changes weekly. Run it in CI on a
schedule if you would rather not host a cron host.

### Option C: event-driven (minutes instead of hours)

If a new repository must be governed within minutes, trigger the same script
from a repository-creation event instead of a timer:

| Provider | Event |
|---|---|
| Bitbucket Cloud | `repo:created` (workspace-level webhook) |
| Bitbucket Data Center | `project:modified` plus repository lifecycle events |
| Azure DevOps | Service hook on repository created |

The handler runs the same command as the cron entry. This costs you an
endpoint to host and monitor, so it is worth it only when the delay actually
matters. A daily reconcile covers most organizations.

**Keep the timer even if you add the webhook.** A missed or failed webhook
delivery leaves a repository ungoverned silently; a nightly reconcile closes
that gap.

### Reference skill in this repository

This repository also ships `skills/security-review/SKILL.md`, a skill that
teaches the reviewer the same five SEC rules with a full-coverage contract
(every rule checked against every changed file, a coverage summary, and a
false-positive gate). Qodo imports skills from `skills/<name>/SKILL.md` on
push and scopes their extracted rules to this repository automatically. Copy
the directory into your own repository and swap in your rules table; the file
itself explains what to keep.

### When to put the file in the target repo instead

If a rule set genuinely belongs to one repository or one folder (a service's
local conventions, a monorepo package), put the supported file there rather
than in the central repo. Scoping is then automatic from the file's location,
new rules keep flowing in as the file grows, and there is nothing to
configure in the portal. Use the central repository only for rules that span
repositories.

### Avoiding duplicates

If a rule also exists in a target repository's own `AGENTS.md` or
`CLAUDE.md`, Qodo imports both copies as separate rules. The portal's
similarity detection flags such pairs as identical or overlapping so you can
deactivate one. To avoid the situation entirely, keep shared rules only in
the central repository and keep target-repo files limited to rules unique to
that repository.

## 4. Quick reference: which mechanism for which rule

| Rule class | Where the file lives | How scope is set |
|---|---|---|
| Global (security, compliance) | Central rules repo | Bulk re-scope to Global in the portal |
| Per-language, many repos | Central rules repo, one file per language | Bulk re-scope to the repository list |
| Per-repo or per-folder conventions | The target repo, at the folder it governs | Automatic from file location |
| Hard pass/fail policy checks | `pr_compliance_checklist.yaml` in each target repo | Automatic, repo-scoped |

## 5. Quick reference: keeping scope current

| Situation | Approach |
|---|---|
| Rule applies to every repo in the org | Scope `/your-org/` once, no automation |
| Rule applies to one project's repos | `tools/sync_rule_scopes.py` on a daily schedule |
| A new repo must be governed within minutes | Repo-creation webhook running the same script, plus the daily timer as a backstop |
| Rule applies to one repo or folder | Put the file there, scope is automatic |

## References

- How Qodo builds your Review Standards (supported files, folder scoping):
  https://docs.qodo.ai/governance/rule-enforcement/building-review-standards
- Generate and manage rules (editing, bulk scope actions):
  https://docs.qodo.ai/governance/rule-enforcement/generate-and-manage-rules
- Rule enforcement without the rule system:
  https://docs.qodo.ai/governance/rule-enforcement/without-rule-system
