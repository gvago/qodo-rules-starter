---
name: qodo-security-standards-setup
description: Use when a user wants to start, install, or finish a GitHub-managed Qodo Security Review Standards repository and walkthrough.
---

# qodo-security-standards-setup skill

Guide the user from an empty or existing GitHub repository to one working, repository-scoped security standard. Do the work with them rather than handing them a checklist.

## Rules

- Ask only for missing information. Perform safe local and read-only checks yourself; never ask the user to discover whether Qodo, Git access, or repository files exist.
- When the user gives a hypothetical or not-yet-resolvable repository such as `acme/payments`, do not substitute unrelated local accounts, repositories, credentials, deployment endpoints, or customer data.
- Ask one question at a time when the answer changes the next step. Otherwise run independent read-only discovery together and keep moving.
- Reuse an existing standards repository and target repository when provided.
- Get approval before installing software, creating a repository, handling a secret, committing, pushing, opening a pull request, merging, or changing a live Qodo rule.
- Never ask the user to paste a token into chat. Have them create the protected Git secret in their provider UI or approved secret manager, then confirm completion.
- Keep Security Agent and Review Standards distinct: both should be ready for the target repository.
- Local `qodo review` is optional early feedback. Qodo's Git pull-request review is the shared gate.
- **GitHub only:** this starter workflow configures GitHub Actions, GitHub repository variables, and a protected GitHub environment. For GitLab, Bitbucket, Azure DevOps, or another provider, stop and say the CI and secret-management adapter is not included; do not translate it ad hoc.
- Stop safely on partial setup and report the exact completed step and next action.

## Guided workflow

### 1. Choose the repositories

Ask for the GitHub repository that will hold the standards. Ask one decision question first: **"Do you already have a standards repository? If yes, send its full GitHub URL; otherwise say create."**

- If it exists, clone or open it and inspect before changing anything.
- If it does not exist, ask for owner, name, visibility, and approval to create and clone it.

Then ask for the exact non-production GitHub repository used for the first walkthrough if it was not already provided. Require a full URL. Verify both repositories exist and are accessible. Portal readiness is confirmed in step 3. Do not create the walkthrough repository unless the user asks.

### 2. Prepare Qodo

Ask whether this is Qodo Cloud or a single-tenant/on-premises deployment. For non-cloud deployments, obtain the exact organization-provided installer or authentication endpoint before any setup command.

Check `qodo --version`, then `$HOME/.qodo/bin/qodo --version`. Check authentication and installed agent skills with the working executable.

If Qodo is missing, first ask approval to install the current Qodo CLI. Read `https://get.qodo.ai/version.json`, resolve the selected channel's version, relative artifact URL, and SHA-256 digest, then download that exact artifact from `https://get.qodo.ai/` and verify its digest before running it. Fail closed on any mismatch. Use the official installer only when it is checksum-pinned by the user's organization.

Use the exact organization-provided installer or `--auth-url` command for single-tenant or on-premises deployments. Never redirect those users to Qodo Cloud.

After the installer or guided setup finishes, verify the version, authenticated identity, managed tool catalog, and installed agent skills using the current CLI help and machine-readable output. The core package should provide:

- `qodo-setup`
- `qodo-review`
- `qodo-review-resolver`

This workflow also needs the optional Qodo Standards package:

- `qodo-get-rules`
- `qodo-manage-standards`

If any required skill is absent, use the current CLI's read-only agent discovery and help to get the exact repair or install action, then ask approval before running it. `qodo-setup` is the agent skill; `qodo setup` is the CLI command. Do not conflate them or guess mutable commands.

### 3. Confirm portal readiness

Ask the user to open **Qodo portal > Configurations > Context**, select the walkthrough repository instead of **All repositories**, enable **Security Agent**, and save. Then have them confirm all of the following:

- The repository appears under **Repositories**.
- Connection health is **Healthy**.
- **Code review** is enabled.
- **Security Agent** is enabled for that repository and the save confirmation appears.

If Security Agent is unavailable, ask the user's Qodo administrator or representative to enable it. Do not continue to the walkthrough until the user explicitly confirms readiness for the named repository.

### 4. Install the starter

Get the starter source from the same public repository or package that supplied this skill. For this package, use `https://github.com/gvago/qodo-rules-starter`. The `starter-kit/` directory is not necessarily beside a globally installed `SKILL.md`; clone or download the public repository read-only when needed and record the exact commit used.

Before copying, require a clean standards-repository working tree and produce a source-to-destination collision manifest. Copy only paths that do not exist. Show every collision and ask what to preserve or replace; never overwrite silently. Exclude `skills/` when the skill is installed separately.

Discover and protect the repository's default branch. The publication job selects it from the GitHub event, so no branch name needs to be hardcoded in the copied workflow.

Inspect the copied README, workflow, rule template, demo rule, and sync helper. Ask for:

1. Confirmation that Qodo Cloud is correct. For single-tenant or on-premises deployments, stop and use the administrator-supplied publication login command rather than modifying the workflow ad hoc.
2. The initial scope in `/owner/repository/` form, using the walkthrough repository.

Replace the placeholder in `rule-scopes.txt` with the initial scope. Create the protected `qodo-sync` environment and restrict it to the default branch. Require pull requests and the helper check on that branch so publication always follows reviewed content. Ask which workspace admin will own publication; have that admin store the workspace admin key as `QODO_API_KEY` in the protected environment through the Git provider UI or approved secret manager, then confirm completion. If no admin key is available, stop before publication and report that exact dependency.

Run the helper check and sync preview. Optionally run local Qodo review. Show the diff and preview before asking approval for Git writes.

### 5. Put Qodo in the loop

After approval, create a branch, commit, push, and open a pull request. First confirm code review is enabled on the standards repository too, because that is where this pull request lives. Use the installed Qodo Review Resolver's current help and structured read path, not rendered-comment scraping. Wait for the review status to be complete and its reviewed commit to equal the current pull-request head. Apply sound findings, rerun checks, and repeat until the current head is ready.

Ask for approval before merge. After merge, verify the publication workflow succeeded. Inspect the current Qodo rules help, then use a filtered structured rules read to verify the exact rule name, active state, and walkthrough-repository scope. Do not treat workflow success alone as proof that the rule is live.

### 6. Complete the walkthrough

In a temporary branch of the walkthrough repository, add the demo rule's small planted violation as a non-production fixture, push it, and open a pull request only after approval. If the walkthrough repository contains production code, prefer a disposable test file or sandbox repository rather than changing an executable path. Confirm Qodo review applies the standard and Security Agent runs. Apply the safe correction, confirm the updated review, then close the demonstration pull request without merging the planted issue.

This is one-time onboarding. Do not turn it into a recurring test matrix.

### 7. Create the first real rule

Ask for one security requirement. Then collect only what is needed: applicability, unsafe behavior, accepted behavior, legitimate exceptions, severity, one unsafe example, one safe example, and final scope.

Create one rule from `_template.yaml`, preview it, optionally review locally, and use the same Git review, Review Resolver, merge, publish, and read-back path. Finish by showing the short steady-state workflow:

```text
edit rule -> pull request -> Qodo review -> Review Resolver -> merge -> publish
```

## Done means

- Qodo CLI and required skills are ready.
- Code review is confirmed for both repositories, and Security Agent is confirmed for the walkthrough repository.
- The starter repository is configured and reviewed in Git.
- The demo rule is active with the intended scope.
- The walkthrough produced a Qodo standard finding and Security Agent run.
- The user knows the next action for writing or expanding a real rule.
