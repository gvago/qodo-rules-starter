# Audit-log queries

Two questions security teams ask about rule enforcement, and the exact queries
that answer them. Replace `<PROJECT>` with your GCP project and `<ORG/REPO>`
with the repository. The filter body also pastes directly into the Logs
Explorer.

## 1. Which PRs were merged with rule violations still open?

There is no single log line that says "merged with open violations". It is a
correlation of three records that share one `request_id`, all emitted when the
merge webhook is processed.

### Step 1 — find the merge event

```bash
gcloud logging read '
  resource.labels.namespace_name=~"qodo-merge"
  AND jsonPayload.text="pr_closed_event"
  AND jsonPayload.record.extra.repo=~"<ORG/REPO>"' \
  --project=<PROJECT> --freshness=1d --format=json
```

Key fields: `extra.artifact.is_merged` (`true` = merged), `extra.artifact.pr_url`,
`extra.merge_commit_sha`, `extra.sender` (who merged), `extra.request_id`.

### Step 2 — pull everything emitted for that merge

```bash
gcloud logging read '
  resource.labels.namespace_name=~"qodo-merge"
  AND jsonPayload.record.extra.request_id="<REQUEST_ID>"' \
  --project=<PROJECT> --freshness=1d --format=json
```

Look for:

- `"Patching N finding(s) as not_implemented on platform"` — the findings still
  open at merge time. `extra.artifact.finding_ids` is the list. `N > 0` means
  the PR was merged with open violations.
- `"Parsed compliance findings to statistics"` — the per-rule breakdown in
  `extra.artifacts.violated_rules` / `compliant_rules` / `custom_count`.

### One-shot filter for the Logs Explorer

```
resource.labels.namespace_name=~"qodo-merge"
(jsonPayload.text="pr_closed_event" OR
 jsonPayload.text=~"Patching .* finding" OR
 jsonPayload.text=~"Parsed compliance findings")
```

Group by `jsonPayload.record.extra.request_id`.

## 2. Who changed a rule?

### Rules edited in the portal

Find the update:

```bash
gcloud logging read '
  resource.labels.namespace_name="qodo-platform"
  AND jsonPayload.text="RuleUpdated"' \
  --project=<PROJECT> --freshness=1d --format=json
```

Take `jsonPayload.record.extra.request_id`. Portal edits also carry
`entry_point: "PUT /rules/v1/rule/<id>"` and `qodo_client_type: "portal"`.

Then resolve the actor from the same request:

```bash
gcloud logging read '
  resource.labels.namespace_name="qodo-platform"
  AND jsonPayload.record.extra.request_id="<REQUEST_ID>"
  AND jsonPayload.text="User authentication context configured"' \
  --project=<PROJECT> --freshness=1d \
  --format="value(jsonPayload.record.extra.email)"
```

That returns the email address of the user who made the change.

### Rules coming from the repository file

When the rules come from `pr_compliance_checklist.yaml`, ingestion is logged as
`RuleCreated` in the `qodo-platform` namespace, performed by the system
reconciler:

```bash
gcloud logging read '
  resource.labels.namespace_name="qodo-platform"
  AND jsonPayload.text="RuleCreated"' \
  --project=<PROJECT> --freshness=1d --format=json
```

Key fields: `extra.rule_id`, `extra.name` (the rule title from the YAML),
`extra.category`.

There is no portal actor in this path, because the change was made in git. The
"who" is the commit author of the rule file, with the full review and approval
history of that commit alongside it.

## Notes

- Rule ingestion happens during the first review of a PR, not as a separate
  step. `RuleCreated` and the findings appear in the same run.
- Findings left open on a merged PR are patched to `not_implemented` on the
  platform. That is the durable record of a merge over open violations.
- A `--freshness` window combined with a future timestamp filter silently
  returns zero rows. Check the window first when a query looks empty.
