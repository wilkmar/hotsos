---
name: conclusion-message-pr-reviewer
description: >-
  Read-only PR reviewer for hotsos scenario conclusion (raises) messages. Reviews
  ONLY the messages ADDED or MODIFIED in the pull request diff (against main) and
  flags just the ones failing the quality bar: missing a short problem description
  and/or not actionable. Never edits scenarios, test fixtures, or any file, and
  never proposes rewrites. ALWAYS use this when reviewing, approving, or
  commenting on a PR that touches hotsos/defs/scenarios/ (new or changed checks
  and conclusions), or when asked to "review the conclusion messages", "check the
  raises messages in this PR", "are the new check messages actionable", or to
  validate new/changed check conclusions before approving.
metadata:
  author: marcin.wilk@canonical.com
  version: "1.0"
---

## Goal
Review the `conclusions/<name>/raises/message` values that are **added or modified
in the pull request under review** and report only the ones that fail the quality
criteria. This skill is **read-only** and **scoped to the PR diff** — it proposes
nothing and modifies nothing.

A good conclusion message must satisfy both criteria:
1. It has a short problem description (what is wrong, where relevant, in one or two sentences).
2. It is actionable (clear next step such as upgrade, verify config, fix service state, investigate a known bug/CVE, or collect specific evidence).

## What This Skill Does NOT Do
- It does not rewrite, edit, or suggest replacement text for messages.
- It does not modify scenario files under `../../../hotsos/defs/scenarios/`.
- It does not modify test fixtures under `../../../hotsos/defs/tests/scenarios/`.
- It does not touch any other file, run formatters, or apply fixes.
- Its only output is a review verdict listing messages that fail the criteria.

If the user explicitly wants the messages fixed or rewritten, that is out of scope
here — this skill only reviews and reports.

## Scope: only the PR's added or modified conclusion messages
Evaluate a message only if it is part of the change set of the PR being reviewed.
Determine the change set from the diff rather than scanning the whole repository.

1. Identify the scenario files changed in the PR. Prefer the review context's diff
   if provided. Otherwise derive it from git, comparing the PR head against the
   `main` branch using its merge base:
   - `git diff --name-only --diff-filter=AMR origin/main...HEAD -- 'hotsos/defs/scenarios/**/*.yaml' 'hotsos/defs/scenarios/**/*.yml'`
   - Use `origin/main` as the base (fall back to local `main` if `origin/main` is
     unavailable) and `HEAD` as the head. The `...` merge-base form ensures only
     changes introduced by the PR — not unrelated commits already on `main` — are
     considered.
2. For each changed scenario file, inspect the diff hunks and evaluate a
   `conclusions/<name>/raises/message` only when the message text itself is added
   or modified in the diff. A newly added conclusion inherently adds a new
   message, so it is in scope; an edited message is in scope.
3. Do not evaluate a message whose text is unchanged in the diff, even if the
   check/decision logic feeding its conclusion changed, and even if it would fail
   the criteria — this review is strictly about the messages the PR introduces or
   edits, and unchanged messages belong to a separate cleanup.

If the PR touches no in-scope conclusion messages, say so and stop.

## Detection Logic
Apply the following issue-type awareness and strict, high-confidence policy when
deciding whether an in-scope message fails the criteria. The parts that matter for
a review verdict:

### Supported issue types
Issue type names come from `hotsos/core/issues/issue_types.py`.

Bug/CVE types map to an online resource that supplies remediation context:
- `LaunchpadBug` + `bug-id` -> `https://bugs.launchpad.net/bugs/<bug-id>`
- `Bugzilla` + `bug-id` -> `https://bugzilla.redhat.com/show_bug.cgi?id=<bug-id>`
- `StoryBoardBug` + `bug-id` -> `https://storyboard.openstack.org/#!/story/<bug-id>`
- `CephTrackerBug` + `bug-id` -> `https://tracker.ceph.com/issues/<bug-id>`
- `UbuntuCVE` + `cve-id` -> `https://ubuntu.com/security/<cve-id>`
- `MitreCVE` + `cve-id` -> `https://www.cve.org/CVERecord?id=<cve-id>`

Non-bug operational warning/error types (for example `MemoryWarning`,
`CephWarning`, `OpenstackWarning`, `KernelWarning`, `NetworkWarning`,
`SmartCtlWarning`, and the other types listed in `issue_types.py`) are evaluated
on the rendered problem-statement + action, using scenario context and message
variables (package/version placeholders, services, thresholds, host roles).

### Strictness policy
Prefer false negatives over false positives. Flag a message only when there is
strong evidence it fails the criteria. If evidence is weak or ambiguous, treat it
as passing and do not report it. Style-only nitpicks are out of scope.

Treat evidence as strong when one or more of these hold:
1. The message is generic and non-descriptive (for example "known bug identified").
2. The message is bug/CVE related and gives neither a specific problem detail nor
   any remediation cue. A bug/CVE message that already names a specific problem is
   usually adequate because the attached resource URL supplies the remediation
   path; only flag it if adding a short action verb would materially help.
3. The message is composed mostly of placeholders and does not itself communicate
   problem + action — after expanding placeholder meaning from
   `raises/format-dict` and referenced `vars`. Messages whose placeholders resolve
   (via `format-dict`/`vars`) to a full, actionable sentence PASS; do not flag them.
4. The message is clearly missing either a short problem statement or an actionable
   next step.

### Placeholder awareness (avoid false positives)
Many messages are intentionally placeholder-composed (for example
`{version} {msg_common}`) where the meaning lives in `format-dict` or `vars`.
Before deciding, expand those placeholders. If the rendered text is a complete,
actionable sentence, the message passes and must not be flagged.

## Required Output
Output must be Markdown only. Do not output JSON, YAML, CSV, or HTML.

Report only in-scope messages that FAIL the criteria. Keep each finding to a clear,
concise statement of which criterion is unmet and why — no proposed rewrite.

When there are findings, use this structure:

```markdown
## Conclusion Message Review
- file: <relative yaml path>
  conclusion: <conclusion key>
  issue_type: <raises.type>
  change: <added | modified>
  message: <the new/changed message as written in the PR>
  unmet_criteria: <one or more of: "no short problem description", "not actionable">
  reason: <one or two sentences explaining precisely what is missing>
  resource: <bug/CVE URL if applicable, otherwise "n/a">
```

If the PR changes conclusion messages but all of them pass, output exactly:

```markdown
## Conclusion Message Review
All new or changed conclusion messages meet the criteria.
```

If the PR does not add or change any conclusion message, output exactly:

```markdown
## Conclusion Message Review
No new or changed conclusion messages in this PR.
```

## Examples

### Fails — no short problem description and not actionable
```
type: LaunchpadBug
bug-id: 1888395
message: known nova bug identified
```
Finding: unmet_criteria = "no short problem description", "not actionable";
reason = states only that a bug exists, with no symptom, impact, or next step.

### Passes — placeholder-composed but renders to an actionable sentence
```
type: MitreCVE
cve-id: CVE-2024-3250
message: "{version} {msg_common}"
```
With `msg_common` resolving (via `vars`) to "... is affected by a known security
vulnerability. Please upgrade to the latest version to get the fix.", the rendered
message states the problem and the action, so it passes and is not reported.

### Passes — concise but specific and actionable
```
type: OpenstackWarning
message: >-
  OpenStack Nova has vGPUs enabled and the installed version ({version}) has a
  known bug that can critically impact the nova-compute service. Please upgrade
  to resolve this issue.
```
