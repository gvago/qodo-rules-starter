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

## References

- How Qodo builds your Review Standards (supported files, folder scoping):
  https://docs.qodo.ai/governance/rule-enforcement/building-review-standards
- Generate and manage rules (editing, bulk scope actions):
  https://docs.qodo.ai/governance/rule-enforcement/generate-and-manage-rules
- Rule enforcement without the rule system:
  https://docs.qodo.ai/governance/rule-enforcement/without-rule-system
