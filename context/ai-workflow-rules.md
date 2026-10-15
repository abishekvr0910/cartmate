# AI coding workflow rules

**Current hosting exception (2026-10-13):** The founder explicitly selected paid EC2 staging for the closed Silesia pilot. Use [the EC2 runbook](../ops/EC2_STAGING_RUNBOOK.md) for this bounded host choice. The historical zero-paid-host rule below is superseded only for EC2; no paid SMS, unreviewed extra AWS resources, or public-user invitation is implied. Inspect costs before creating resources.

Read `AGENTS.md` and the six context files before an implementation session. Work one numbered feature spec/acceptance slice at a time; mark it in progress in `progress-tracker.md` before code changes and update that file after verification. Do not expand scope from a vague instruction such as "make it launch-ready".

Preserve user-owned changes. The local Git repository is not yet committed or pushed; avoid concurrent edits to the same files. `CODEX_WORK_DIRECTORY.md` is untracked and belongs to another actor until reviewed. Read current source before touching it, and review the diff before staging. Do not commit or push private databases, `.env` files, credentials, real phone numbers, identity images or backup contents.

Ask about a missing choice if it materially affects cost, privacy, identity, public exposure or pilot scope. The founder has ruled out new paid services for this friend test. Do not buy anything, use a public tunnel, turn on production age bypasses, enable console OTP on a shared host, or claim a site is shareable without permission and a real access test.

For non-trivial defects, document the reproduction and boundary first, add a failing regression, then fix narrowly. If a scratch issue file is used, remove or ignore it before committing. Keep `LAUNCH_READINESS.md`, `GEMINI_HANDOFF.md`, this context and the feature spec synchronized with observed results. Hand off unfinished external/human gates explicitly.
