# CartMate agent entry point

Before changing CartMate, read these files in order, completely:

1. `context/project-overview.md`
2. `context/architecture.md`
3. `context/ui-context.md`
4. `context/code-standards.md`
5. `context/ai-workflow-rules.md`
6. `context/progress-tracker.md`

Then read the active numbered spec in `context/feature-specs/` and the latest top section of `LAUNCH_READINESS.md`. For the current Gemini assignment, also read `GEMINI_HANDOFF.md`. Older handoffs are historical evidence, not current release authority. If any file conflicts with code, verify the code and update the documentation; never infer a released feature from a green test count.

One writer owns shared application files at a time. Preserve the existing local database, ignored artifacts, untracked files and other agents' work. Use a disposable database for tests. The founder explicitly authorized **one AWS EC2 staging host** for the closed Silesia pilot; follow `ops/EC2_STAGING_RUNBOOK.md` and verify cost before provisioning. This does **not** authorize paid SMS, extra cloud services without a specific need, public user invitations, an age-gate bypass, or collection of identity-document images/numbers. Do not claim real human/device gates passed until observed.
