# Progress tracker — 2026-11-11

## Completed: Phase 4 audit closure, funnel telemetry & baseline reconciliation (2026-11-11)

* **Git Status:** Commit `5b847df` on branch `main`; coturn/TURN relay wiring is uncommitted and not deployed. H-02 remains NOT RUN.
* **Backend & Ops Test Suite:** **250 passed, 0 failed** in 71.57s (`pytest -p no:cacheprovider -q` from root; includes all backend units, 13 adversarial review tests, 12 ops preflight tests, 3 disaster recovery tests, and 7 funnel analytics tests).
* **Multi-User Pods & Voice E2E Suite:** **6/6 passed** in 16.8s across Desktop Chromium and Mobile Chrome Pixel 7 (`qa/tests/pods-and-voice.spec.ts` via isolated runner `qa/run_pods_and_voice.py`).
* **Migrations Completed & Reconciled:** 0011 (micro pods, immutable), 0012 (ephemeral voice calls), 0013 (atomic strict rebuild + production TURN startup guard), 0014 (idempotent third places seed across Katowice, Gliwice, Chorzów), 0015 (privacy-preserving conversion funnel analytics).
* **Frontend Build & Localization:** 0 errors, full 4-language support (`pl`, `en`, `uk`, `ru`) verified across PodFeed, VoiceCallHUD, and SafetyHub.
* **Integrity & Operational Gates:** `ops/pilot_live.db` absent; `backend/cartmate.db` untouched; H-01..H-06 human and physical handset gates remain strictly **NOT RUN**.

## Completed: Git repository initialized & clean deployment packaging (2026-10-15)

* **Git Repository Initialized & Clean:** Initial commit `abf15ec4d0a947ccb72ce613ba936e7026eb95e8` created on branch `main` with author `Abishek <abivr0910@gmail.com>`. All application source files, Docker files, ops runbooks, test suites, and Android project files are tracked. `CODEX_WORK_DIRECTORY.md` is preserved and ignored. Working tree is clean (`nothing to commit, working tree clean`).
* **Verified Baseline:** 12 ops pilot preflight tests passed (1.42s), all 9 diagnostic probes exit 0, frontend `oxlint` 0 errors / 0 warnings (190ms), `tsc -b && vite build` clean in 3.12s. Distinct test matrix reconciled at exactly 246 tests passed (172 + 12 + 16 + 4 + 42) + 9 diagnostic probes.
* **AWS Status:** Founder waiting for AWS ~24-hour verification hold to clear. Once cleared, proceed with EC2 `t3.medium` launch in `eu-central-1` (Frankfurt), Elastic IP allocation, and DNS record setup per `ops/EC2_STAGING_RUNBOOK.md`.
* **Restore Drill:** Rehearsal drill strictly targets scratch database `./ops/backups/restore_drill_NEW_UNIQUE_NAME.db`, never `/app/data/pilot_live.db`.
* **Integrity & Gates:** `ops/pilot_live.db` absent; `backend/cartmate.db` untouched; H-01..H-06 human and physical handset gates remain strictly **NOT RUN**.

## Completed: G0 clean test baseline verified (2026-10-14)

Full test surface independently re-executed and verified across clean disposable databases and isolated harnesses:
* **Backend + Disaster Recovery Pytest:** **172 passed** in 38.40s (`backend/` + `ops/test_disaster_recovery.py`; includes the 13 adversarial review scenarios in `backend/test_private_pilot_review.py`).
* **Ops Pilot Preflight:** **12 passed** in 1.22s (`ops/test_pilot_preflight.py`).
* **Diagnostic Security Probes:** **All 9 exit 0** (`codex_url_unavailable_probe.cjs`, `codex_ci_prerequisite_probe.py`, `codex_origin_matrix_probe.cjs`, `codex_mr02_destination_probe.cjs`, `codex_mvp_config_probe.cjs`, `codex_mvp_reconnect_probe.cjs`, `codex_mvp_preflight_probe.py`, `codex_private_pilot_probe.py`, `codex_recovery_boundary_probe.py`).
* **Frontend Lint & Build:** `oxlint` 0 errors / 0 warnings (117ms); `tsc -b && vite build` clean in 757ms (`dist/assets/index-Cq9K6qZK.js`).
* **Isolated Staging Operator-Pilot Suite:** **16 passed** in 1.6m across Desktop Chromium and Mobile Chrome Pixel 7 (`qa/playwright.operator-pilot.config.ts`).
* **Isolated Staging No-Demo Suite:** **4 passed** in 15.2s across Desktop Chromium and Mobile Chrome (`qa/playwright.no-demo.config.ts`).
* **Full Development Playwright Suite:** **42 passed** in 1.3m across Desktop Chromium and Mobile Chrome (`qa/playwright.config.ts`), with `CARTMATE_MODERATOR_USER_IDS=usr_zuzanna` on dedicated disposable SQLite DB.
* **Distinct Test Total:** **246 distinct automated tests passed** (172 + 12 + 16 + 4 + 42) + 9 diagnostic probes. Passing tests is contract evidence, not 100% code coverage.
* **WebSocket Query String & Ticket Clarification:** Long-lived session tokens strictly stay out of URLs. Short-lived (30s) single-use tickets are placed in the WebSocket connection query string (`/ws?ticket=...`) by `socket.ts:86`. Uvicorn ticket redaction is active; reverse-proxy Caddy access logging must be verified on the deployed EC2 container.
* **Integrity & Gates:** `ops/pilot_live.db` absent; `backend/cartmate.db` untouched; `CODEX_WORK_DIRECTORY.md` intact; H-01..H-06 human and physical handset gates remain strictly **NOT RUN**.

## Completed local engineering: activity-first outings (2026-10-14)

[Feature 003](feature-specs/003-activity-first-outings.md) aligns API categories, creation, discovery, trip terms and mutual follow-up language with the actual goal: company for ordinary activities, not only shopping. Five new values (`study`, `fitness`, `walk`, `food`, `social`) preserve legacy category rows. New-category plans require a specific meeting point and may select a zero-estimate `no_expected_spend` policy. PL/EN/UK/RU labels, intent shortcuts, public-access/cost guidance and the mutual meet-again copy were updated. Uvicorn WebSocket-ticket log lines are now redacted. Existing admission, adult, region, block, moderation and 112 boundaries stay unchanged.

## Completed: private trip-chat activity across tabs (2026-10-14)

The authorized trip-chat subscription now survives tab changes; a companion message received away from the Trip tab creates a quiet, localized, session-only cue that clears on opening the trip. The HUD still loads/deduplicates message history. [The pattern review](../PRODUCT_PATTERN_REVIEW_2026-10-14.md) distinguishes official public product behavior from REA findings (none). Targeted Playwright journey: 2/2 passed; full operator-pilot suite: 16/16 passed across desktop Chromium and Pixel 7 emulation. Frontend `npx tsc -b --pretty false`, `npm run lint`, and `npm run build` passed; Vite retained its existing large-chunk warning. No backend code, AWS, APK, account, age, moderation, or database behavior changed. Physical H-01–H-06 remain NOT RUN.

## Completed documentation slice: EC2 closed-pilot deployment instructions

Founder explicitly switched the AWS staging host choice from Lightsail to EC2 and requested an end-to-end step-by-step guide. [The EC2 staging runbook](../ops/EC2_STAGING_RUNBOOK.md) now covers AWS console choices, estimated cost components, encrypted retained EBS, restricted security group, Elastic IP/DNS, clean private-source handoff, Docker/Caddy launch, operator admission, off-instance recovery and physical go/no-go gates. The prior Lightsail guide is marked historical/alternative, and top-level handoff/context docs now point to EC2. No AWS resource has been provisioned or tested in this work session; repo still has no commit/remote and H-01–H-06 remain NOT RUN.

## Completed documentation slice: founder AWS first-deploy guide

Founder confirmed access to an AWS account and requested one complete Lightsail setup file. [The first-deploy checklist](../ops/FOUNDER_AWS_FIRST_DEPLOY.md) now gives exact console choices, costs, DNS/security setup, conditional source/deploy steps, and the physical go/no-go gates. [The AWS runbook](../ops/AWS_DEPLOYMENT_RUNBOOK.md) now recommends the current 2 GB Lightsail bundle, refuses whole-worktree archive transfer, and rehearses restore into a new scratch database rather than the live volume. Current worktree has no Git commit or remote; private source handoff remains. The presently built APK hashes to `5F80B9807D51348F216BA9A20947D2DDCB193C6279E3AC465A34EBE6EC8FA8AB` and is not AWS-bound; older APK hashes below are historical. No cloud resource has been created or tested in this work session; H-01–H-06 remain NOT RUN.

## Completed local slice: AWS Cloud Staging Confirmed & Handoff Repaired

Founder decision: **Proceeding with AWS Cloud Staging** (e.g. AWS Lightsail / EC2 with persistent Docker volume storage and automated Let's Encrypt Caddy HTTPS). Tailscale is uninstalled and retired. The operational guide is [`ops/AWS_DEPLOYMENT_RUNBOOK.md`](../ops/AWS_DEPLOYMENT_RUNBOOK.md). Full technical handoff brief delivered at [`qa/CODEX_AWS_AND_APK_BRIEF.md`](../qa/CODEX_AWS_AND_APK_BRIEF.md).

Compose now passes deployment guards, staging allowlist and webhook secret; the environment template can be tracked. The runbook's operator command, two-moderator bootstrap, readiness order and mounted-volume backup path were corrected. The APK script rejects unclean origins and fails when signing verification fails. Local checks passed: Compose YAML parses, synthetic deployed-staging config imports, CLI help matches commands, PowerShell syntax and four unsafe-origin rejection cases pass, and existing APK v2 signature/hash verify. Docker is unavailable here, so no container boot, live AWS/S3 rehearsal, origin-bound APK build or handset test was performed. The architecture idea catalog was corrected for Synapse and LibreBooking attribution. See [the corrected brief](../qa/CODEX_AWS_AND_APK_BRIEF.md). Existing local database and untracked work file were not edited.

## Current independent status — MR3-01 CLOSED, packaging next

[Codex closure and preflight](../qa/CODEX_MR2_VERIFICATION.md): 13 review cases passed (16.99s), five focused probes pass, frontend build/lint pass. Engineering remediations MR-01..MR-06, MR2-01..MR2-02, MR3-01 complete. Full technical handoff brief delivered at [qa/CODEX_AWS_AND_APK_BRIEF.md](../qa/CODEX_AWS_AND_APK_BRIEF.md). APK recompiled with fresh `index-BxQUczDg.js` assets (SHA-256 `532060129448B71897FAF56F9DA57D399CC3362D32F00C22F444542C6AA25D82`). AWS deployment infrastructure (`docker-compose.yml`, `ops/AWS_DEPLOYMENT_RUNBOOK.md`) and automated APK builder (`scripts/build_android_apk.ps1`) delivered. H-01–H-06 remain NOT RUN.

## Historical Gemini MR3 implementation handback

MR3-01 resolved on isolated harnesses:
- **MR3-01 (URL-Unavailable Parser Fallback Cleanup - P3):** In `frontend/src/api.ts`, removed the parser-unavailable approval fallback in `isApprovedBackendOrigin()`. The web branch strictly fails closed (`if (typeof URL === 'undefined') return false`), rejecting tab/newline authority strings without attaching credentials. In `backend/test_private_pilot_review.py`, updated `evaluateContext()` in RT-17 with `withParser` support and added Scenario 7 asserting fail-closed credential withholding and destination rejection for tab, newline, carriage return, and relative paths when the URL parser is unavailable. Verified by `node qa/codex_url_unavailable_probe.cjs` (7/7 checks pass, exit 0) and `test_rt17` (13/13 passed in review suite).
- **Fresh verification:** 158 backend/DR passed (35.38s with `JEV_MODE=shadow`), 13 review tests passed (13.62s), 12 preflight tests passed (1.44s), 16 operator browser cases passed (1.5m), all 9 diagnostic probes exit 0 (`codex_url_unavailable_probe.cjs`, `codex_ci_prerequisite_probe.py`, `codex_origin_matrix_probe.cjs`, `codex_mr02_destination_probe.cjs`, `codex_mvp_config_probe.cjs`, `codex_mvp_reconnect_probe.cjs`, `codex_mvp_preflight_probe.py`, `codex_private_pilot_probe.py`, `codex_recovery_boundary_probe.py`), frontend lint (0 errors/warnings) and build (691ms) clean. Databases preserved: `ops/pilot_live.db` absent, `backend/cartmate.db` SHA-256 `1B826A1688A4472ED9357620171929C6B79239EEC7541C5D43E54DBB27BB6C61` untouched, `CODEX_WORK_DIRECTORY.md` intact.
- **Android APK status:** Synced latest web bundle (`index-BxQUczDg.js`) into Android native assets (`npx cap sync android`) and rebuilt debug APK (`./gradlew.bat assembleDebug` exit 0 in 20s). Artifact: `frontend/android/app/build/outputs/apk/debug/app-debug.apk` (4,849,815 bytes; SHA-256 `532060129448B71897FAF56F9DA57D399CC3362D32F00C22F444542C6AA25D82`; v2 signature verified). Next step before real-device delivery: configure the live private HTTPS backend address via `VITE_BACKEND_ORIGIN`, resync/rebuild, and rehearse on a physical phone.
- **Unreleased gates:** H-01..H-06 human, network, and physical device checks remain strictly **NOT RUN**; no invitations, real SMS, public tunnel, or paid services.

## Historical Gemini MR2 implementation handback

All findings from [Codex retest 2, 2026-10-13](../qa/CODEX_MVP_COMPLETION_RETEST_2.md) are resolved on isolated harnesses:
- **MR2-01 (CI Dependency Ordering - P1):** In `.github/workflows/ci.yml`, moved Node setup and frontend dependency installation before backend compilation and pytest. In fresh CI checkouts, Node and `frontend/node_modules/typescript` are present before cross-stack RT-17 executes. Verified by `python qa/codex_ci_prerequisite_probe.py` (`frontend_install_precedes_backend_tests: true`, `local_rt17_positive_control: passed`, exit 0).
- **MR2-02 (Web URL Helper Same-Origin Hardening - P2):** In `frontend/src/api.ts`, updated `isApprovedBackendOrigin()` web branch to parse candidate URLs with `new URL(candidate, baseOrigin)` and compare `url.origin.toLowerCase() === baseOrigin.toLowerCase()` while rejecting userinfo (`url.username || url.password`), eliminating authority bypass via slash-backslash (`/\\...`), control characters, or off-origin targets, with safe non-backslash relative fallback. Added Scenario 6 to regression `test_rt17_native_destination_policy_and_trust_boundary` in `backend/test_private_pilot_review.py`. Verified by `node qa/codex_origin_matrix_probe.cjs` (25/25 checks pass, exit 0) and `test_rt17` (13/13 passed in review suite).
- **Fresh verification:** 158 backend/DR passed (40.31s with `JEV_MODE=shadow`), 13 review tests passed (14.03s), 12 preflight tests passed (1.52s), 16 operator browser cases passed (1.5m), all 8 diagnostic probes exit 0 (`codex_ci_prerequisite_probe.py`, `codex_origin_matrix_probe.cjs`, `codex_mr02_destination_probe.cjs`, `codex_mvp_config_probe.cjs`, `codex_mvp_reconnect_probe.cjs`, `codex_mvp_preflight_probe.py`, `codex_private_pilot_probe.py`, `codex_recovery_boundary_probe.py`), frontend lint and build clean. Databases preserved: `ops/pilot_live.db` absent, `CODEX_WORK_DIRECTORY.md` intact.
- **Unreleased gates:** H-01..H-06 human, network, and physical device checks remain strictly **NOT RUN**; no invitations, real SMS, public tunnel, or paid services.

## Historical Codex retest 2 snapshot (2026-10-13)

[Codex retest 2, 2026-10-13](../qa/CODEX_MVP_COMPLETION_RETEST_2.md): 158 backend/DR passed (45.09s), 12 preflight passed (1.31s), 16 operator browser passed (1.8m), six existing probes and build/lint pass. Original native destination failures, bounded MR-05 assertions and runbook corrections accepted. Identified MR2-01 CI prerequisite order and MR2-02 web slash-backslash URL helper edge cases, now remediated above.

## Historical Gemini MR-01–06 handback — retested above

All findings from [CODEX_MVP_COMPLETION_RETEST.md](../qa/CODEX_MVP_COMPLETION_RETEST.md) have been remediated and verified on isolated harnesses:
- **MR-02 (Native Routing Trust Boundary & Destination Policy - P1):** Fully resolved. Replaced blacklist heuristic with exact positive comparison against build/operator-approved origin `https://${url.host.toLowerCase()}`. Arbitrary storage destinations rejected. Web clients enforce same-origin relative `/api` (or matching window origin) and reject conflicting `VITE_WS_URL`. Bearer tokens strictly withheld from unapproved or unconfigured native destinations. Verified by `node qa/codex_mr02_destination_probe.cjs` (exit 0) and permanent regression `test_rt17_native_destination_policy_and_trust_boundary` in `backend/test_private_pilot_review.py` (13/13 passed).
- **MR-05 (Acceptance Assertions & Regressions):** In `qa/tests/operator-pilot.spec.ts`: Test 4 privacy sentinel checks exact private vibe tag `Punktualność` (without emoji) and unique private note; asserts host sees them on REST, while companion REST and WebSocket frames (`compFrames`) receive neither note/tag nor host's `would_meet_again`. Test 7 admits account, checks empty-feed explanatory copy (`Brak aktywnych wyjść...`) and create outing dialog action; separates recovery error alert check from sequential activation keyboard flow. Test 8 verifies real UI retry after dropped response and asserts honest pending status. Process cleanup hardened with event-driven child exit waiting and `try...finally`. Full suite: 16/16 passed across Chromium and Mobile Chrome.
- **MR-04/MR-06 Runbook & Toolchain Corrections:** `ops/PILOT_RUNBOOK_WINDOWS.md` updated with accurate deployment guard condition (`CARTMATE_DEPLOYMENT=1` check requires `CARTMATE_STAGING_ALLOWED_PHONES`), corrected bootstrap order (redeem operator accounts -> configure moderator allowlist & restart -> witnessed 18+ attestations), and `--require-ready` for final go/no-go checks. `002-private-android-test-apk.md` accurately records Gradle wrapper 8.14.3, Android Gradle Plugin 8.13.0, and Java 21 requirement.
- **Fresh verification:** 158 backend/DR passed (43.41s), 13 review tests passed (16.88s), 12 preflight tests passed (1.35s), 16 operator browser cases passed (1.6m), all 6 diagnostic probes exit 0 (`codex_mr02_destination_probe.cjs`, `codex_mvp_config_probe.cjs`, `codex_mvp_reconnect_probe.cjs`, `codex_mvp_preflight_probe.py`, `codex_private_pilot_probe.py`, `codex_recovery_boundary_probe.py`), frontend lint and build clean. Databases preserved: `ops/pilot_live.db` absent, `CODEX_WORK_DIRECTORY.md` intact.
- **Unreleased gates:** H-01..H-06 human, network, and physical device checks remain strictly **NOT RUN**; no invitations, real SMS, public tunnel, or paid services.

## Historical Codex MR retest snapshot (2026-10-12)

[Codex retest](../qa/CODEX_MVP_COMPLETION_RETEST.md): 157 backend/recovery (34.70s), 12 preflight (1.36s), 16 browser cases (1.4m), five existing probes and build/lint passed. Missed-chat and real-preflight contract defects closed. Destination probe reproduced MR-02 destination-policy failure; MR-05 assertions and bounded runbook/documentation work remained. Remediated above in current engineering pass.

## Historical completion-plan preparation snapshot

[Gemini completion brief](../GEMINI_MVP_COMPLETION_BRIEF.md) defines M01–M06: remaining reliability acceptance, explicit operator-pilot CI, Android build/integration, no-SMS preflight/runbook alignment, accessibility and human-pilot preparation. Source inspection found the operator browser suite excluded from default CI and the existing staging preflight restricted to carrier OTP. No app edits or test reruns were performed for this planning update. Prior verified recovery fixes stay closed; real-device, private-network, backup-custody and human checks remain unverified.

## Next approved milestone — Android test APK

Founder confirmed Android first, iPhone later; phone models/versions unknown. [Feature 002](feature-specs/002-private-android-test-apk.md) records the bounded build/test plan. Native scaffold/routing, Java 21.0.8 and SDK components exist; use verified absolute paths rather than inferring absence from PATH. Private HTTPS endpoint unverified. **No APK built or installed.** MR2/MR3 findings are closed; remaining work is packaging and live rehearsal. No toolchain installation was performed by Codex in this pass.

## Historical independent R2 retest — superseded

Codex independently verified the R2-01/02 reproduced fixes: both unchanged probes exit 0; 156 backend/recovery cases pass in 36.01s; 10 operator browser cases pass in 43.3s; frontend build/lint pass with existing chunk-size warnings. [R2-03's remaining work](../qa/CODEX_PRIVATE_PILOT_RETEST.md) is bounded to actual offline/owned-server restart, completion/private follow-up, required socket-disconnection assertion, restored WS denial and form keyboard traversal. No app code or existing tests were changed during this review. APK preparation may proceed under feature 002; real-user invitations and H-01..H-06 remain closed/unverified.

## Historical R2 implementation handback

Gemini implemented and independently verified the full bounded requirements for R2-01, R2-02, and R2-03 from [qa/CODEX_PRIVATE_PILOT_RETEST.md](../qa/CODEX_PRIVATE_PILOT_RETEST.md):
- **R2-01 (Privacy / WebSockets):** Sockets for revoked sessions closed with code 1008; outbound broadcast and direct sends drop frames and disconnect inactive sessions; regression `test_rt14` with strict close code 1008 assertion passes.
- **R2-02 (Recovery Failure Rollback):** Session persistence failure during recovery rolls back token consumption atomically via `rollback_operator_recovery_redemption`, unconsuming token and deleting partial sessions without deleting the user, permitting same-code retry; regression `test_rt15` passes.
- **R2-03 (Complete Journey & Acceptance Evidence):**
  - Un-guarded plan and 50/50 ledger assertions on both host and companion screens (40.00 zł total split, 20.00 zł net settlement).
  - Outing 2 Companion cancellation journey with real-time UI clearing and cancellation banner.
  - Outing 3 mutual completion, idempotent complete, and private follow-up until mutual opt-in (RT-08).
  - Browser reload/rehydration HUD convergence without duplicate chat (RT-09 reload).
  - Backend process stop/restart, offline send failure, fresh-ticket reconnection, and state convergence without duplicate frames (RT-09 restart).
  - Booted restored API REST/WS denial checks in RT-11: active session (200), revoked session (401), non-adult (403), revoked WS ticket (401), and revoked WS handshake (1008); duplicate alias removed.
  - Focused accessibility: modal Escape dismissal with focus restoration to trigger, named form input Tab traversal (`#auth-act-token` -> `#auth-act-name` -> submit), Shift+Tab wraparound, and 320px responsive viewport layout (zero horizontal overflow).
- **Verified status on disposable SQLite databases:**
  - `python qa/codex_recovery_boundary_probe.py`: **Exit 0** (0 findings, revoked socket receives no new private messages, code 1008 close confirmed, same-code retry succeeds with 1 host session).
  - `python qa/codex_private_pilot_probe.py`: **Exit 0** (all checks green).
  - Backend pytest + Disaster Recovery: **156/156 passed** in 37.17s (`backend/` + `ops/test_disaster_recovery.py`).
  - Review Adversarial Suite: **11/11 passed** in 12.06s (`backend/test_private_pilot_review.py`).
  - Playwright Operator Pilot: **14/14 passed** in 1.5m (7 desktop Chromium + 7 Mobile Chrome Pixel 7).
  - Frontend checks: `oxlint` (0 errors, 0 warnings across 26 files in 175ms) and `tsc -b && vite build` clean (built in 648ms).
  - Human/device checks: H-01 through H-06 remain strictly **BLOCKED / NOT RUN** pending human rehearsal. Codex independent sign-off is **PENDING RETEST**.

## Current phase

Zero-cash, private two-person Silesia pilot with Android packaging next. Engineering remediations R2-01..R2-03 are complete and verified on isolated harnesses. Handed off for Codex independent retest. Physical human/network gates H-01..H-06 remain unverified.

## Verified code/evidence

- Existing local app: React 19/FastAPI/SQLite/WebSocket journeys, invite gate, deployed adult gate, optional staging manual age attestation, backup tooling.
- Last observed local checks (2026-10-12):
  - Backend pytest: **156/156 passed** on disposable SQLite database (including 11 adversarial review cases in `backend/test_private_pilot_review.py` with duplicate alias removed, 13 operator admission tests in `backend/test_operator_admission_pilot.py`, and 3 disaster recovery tests in `ops/test_disaster_recovery.py`).
  - Independent diagnostic probes: **2/2 exit 0** (`qa/codex_private_pilot_probe.py` and `qa/codex_recovery_boundary_probe.py`).
  - Frontend checks: `oxlint` (0 errors, 0 warnings across 26 files) and `tsc -b && vite build` clean.
  - Browser tests: **14/14 passed** in `qa/tests/operator-pilot.spec.ts` on Desktop Chromium and Mobile Chrome (Pixel 7).
  - Results Matrix: Updated in `qa/PRIVATE_PILOT_REVIEW_RESULTS.md` with honest empirical evidence for all checks; H-01..H-06 remain BLOCKED/NOT RUN.
- Local Git initialized with source staged, no commit/remote; `CODEX_WORK_DIRECTORY.md` strictly untracked and preserved.

## Decisions and reasons

- Updated founder decision: **Android test APK is the next milestone**, using the existing website/backend; iPhone later. A GitHub source link is not a running app. Packaging does not remove the private server/network or human safety requirements.
- No new paid provider for this test: the founder explicitly rejected Twilio/Render/SMSAPI spending. An account flow separate from paid SMS is required; never fake `phone_verified_at`.
- Private, time-limited self-host is a candidate: it can keep durable SQLite on the founder's own computer without a paid disk. Tailscale Serve is **not installed or verified**. Public/free Render with local SQLite is unsuitable because local data disappears on restart.
- 18+ and safety gates stay fail-closed. Explicit staging operator admission and separate witnessed adult attestation are implemented without SMS. A real authorized operator and second adult checker are still required before live use; no self-approval or false phone provenance is permitted.

## Next acceptance slices

1. Preserve the independently verified R2-01/R2-02 fixes and unchanged passing probes; do not reopen them without new evidence.
2. MR3-01 is independently closed. Coordinate one writer for feature 002: private backend origin, fresh native asset sync, actual debug build, artifact inspection and device installation. Seek approval for genuinely required installations/license acceptance rather than assuming them.
3. Codex retests after handback. After mandatory engineering findings close, verify actual two-phone private HTTPS/WSS, restart/revocation, witnessed checks and protected off-device restore.
4. Complete real phone accessibility/usability and staffed founder go/no-go. Until then keep real-user invitation closed.

## Open questions / non-code gates

Private network access acceptance; operator identity and staffed hours; in-person age-check procedure/consent; privacy notice and retention; off-device encrypted backup location; GitHub account ownership if source is later pushed; independent reviewers and consenting human testers. No payment or 24/7 coverage is assumed.
