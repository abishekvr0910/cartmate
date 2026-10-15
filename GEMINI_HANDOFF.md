# CartMate — current Gemini implementation handoff

**2026-10-15 repository & deployment packaging update (Initial Git commit created, working tree clean):**
* **Git Repository Initialized & Clean:** Initial commit `abf15ec4d0a947ccb72ce613ba936e7026eb95e8` created on branch `main` with author `Abishek <abivr0910@gmail.com>`. All application source files, Docker configuration, ops runbooks, test suites, and Android project files are now tracked. `CODEX_WORK_DIRECTORY.md` (SHA-256 `D65F80341F67F69B2F3BA879315767075CC1B3FADE7FC6DB8A02BBB8A919059C`) is preserved and ignored in `.gitignore`. Working tree is 100% clean (`nothing to commit, working tree clean`).
* **Independent Test Baseline Verified on Committed Tree:**
  - **Ops Pilot Preflight:** **12 passed** in 1.42s (`ops/test_pilot_preflight.py`).
  - **Diagnostic Security Probes:** **All 9 exit 0** (`codex_url_unavailable_probe.cjs`, `codex_ci_prerequisite_probe.py`, `codex_origin_matrix_probe.cjs`, `codex_mr02_destination_probe.cjs`, `codex_mvp_config_probe.cjs`, `codex_mvp_reconnect_probe.cjs`, `codex_mvp_preflight_probe.py`, `codex_private_pilot_probe.py`, `codex_recovery_boundary_probe.py`).
  - **Frontend Lint & Build:** `oxlint` 0 errors / 0 warnings (190ms); `tsc -b && vite build` clean in 3.12s (`dist/assets/index-Cq9K6qZK.js`).
  - **Distinct Test Matrix Reconciled:** 246 distinct tests passed across backend/DR, preflight, operator, no-demo, and development Playwright suites.
* **Restore Drill Hardened:** Rehearsal drill strictly targets scratch database `./ops/backups/restore_drill_NEW_UNIQUE_NAME.db`, never `/app/data/pilot_live.db`.
* **AWS Status:** Founder waiting for AWS ~24-hour verification hold to clear. Once cleared, proceed with EC2 `t3.medium` launch in `eu-central-1` (Frankfurt), Elastic IP allocation, and DNS record setup per `ops/EC2_STAGING_RUNBOOK.md`.
* **Integrity & Gates:** `ops/pilot_live.db` absent; `backend/cartmate.db` untouched; H-01..H-06 human and physical handset gates remain strictly **NOT RUN**.

**2026-10-14 research/design execution brief:** Read [GEMINI_RESEARCH_AND_FINISHING_HANDOFF_2026-10-14.md](GEMINI_RESEARCH_AND_FINISHING_HANDOFF_2026-10-14.md) before new work. It consolidates current evidence, primary-source product/safety research, an activity-first pilot design, ordered acceptance work, founder inputs, and H-01–H-06 stop/go gates. It does not certify a deployed EC2 service, shareable APK, or physical rehearsal. The approved EC2 runbook remains the deployment authority; older Lightsail/Render/Tailscale directions below are historical.

**Current founder decision (2026-10-13): Use EC2 for the closed Silesia pilot.** [EC2_STAGING_RUNBOOK.md](ops/EC2_STAGING_RUNBOOK.md) supersedes the Lightsail-first provisioning instructions below. The app remains one Docker Compose host with SQLite and in-process WebSockets; no multi-instance scaling is authorized by this change. No AWS instance/domain/TLS/off-instance restore/physical rehearsal is verified. Existing APK is bound to an older backend. Do not invite users or distribute it before the runbook's actual go/no-go checks; H-01–H-06 remain NOT RUN.

**Founder AWS next action (2026-10-13):** Use [the single first-deploy checklist](ops/FOUNDER_AWS_FIRST_DEPLOY.md). Founder has an AWS account but no instance/domain or live deployment has been verified. Recommended Lightsail choice is Ubuntu 24.04 in EU Frankfurt, 2 GB/2 vCPUs/60 GB public-IPv4 plan (AWS listed USD 12/month; reconfirm in console), then attach a static IP. The local worktree has no commit or Git remote; a reviewed private source repository must be prepared before any `git clone`. The AWS restore rehearsal was corrected to use a new scratch target outside the live volume; never restore a drill over `pilot_live.db`. Existing APK is not bound to an AWS HTTPS domain. H-01–H-06 remain NOT RUN. This paragraph supersedes older $7/1 GB and "deployment ready" wording below.

**Latest Codex AWS/APK correction (2026-10-13):** The brief is at `qa/CODEX_AWS_AND_APK_BRIEF.md`; the architecture idea catalog is at repository root. Deployment configuration, APK script checks and the AWS runbook have been repaired as recorded at the top of the brief. Existing APK signature/hash verify, but it is not built for a confirmed live backend origin. Docker/AWS/handset/S3 and H-01..H-06 are untested. Follow the corrected AWS runbook only after the founder chooses and configures a domain and paid host; do not use historical commands below as deployment instructions.

## Current authority — Cloud Staging on AWS Approved; Deployment & Packaging Ready (2026-10-13)

**Handoff to Codex:** Full technical brief at [qa/CODEX_AWS_AND_APK_BRIEF.md](qa/CODEX_AWS_AND_APK_BRIEF.md).

- **Founder Strategic Decision — AWS Cloud Staging Confirmed:** The founder has officially decided to proceed with **AWS Cloud Staging** (e.g. AWS Lightsail / EC2 with persistent Docker volume storage and automated Let's Encrypt Caddy HTTPS). Tailscale is uninstalled and retired.
- **Runbook Authority:** The operational guide for AWS deployment is [`ops/AWS_DEPLOYMENT_RUNBOOK.md`](ops/AWS_DEPLOYMENT_RUNBOOK.md).
- **Deployment Deliverables Repaired & Ready:**
  - `docker-compose.yml`: Single-worker FastAPI (`--workers 1`), persistent named volume `cartmate-data` for SQLite WAL, Caddy reverse proxy for automated Let's Encrypt HTTPS, `env_file: .env`, and `CARTMATE_DEPLOYMENT=1` with required staging phone allowlist and webhook secret.
  - `ops/env.production.example`: Staging configuration template; currently untracked in the local worktree.
  - `ops/AWS_DEPLOYMENT_RUNBOOK.md`: Complete operations manual for instance launch, DNS, operator bootstrap (2 human moderators), offline restore rehearsal drill, and S3 backup custody.
  - `scripts/build_android_apk.ps1`: Automated PowerShell pipeline with strict URI validation and verified v2 signature assertion to compile and sign the final APK once the live AWS HTTPS domain is provided.
- **Next Operational Steps:**
  1. Founder follows the newer EC2 runbook above; the old Lightsail action here is superseded.
  2. After a reviewed private repository is committed and pushed, clone it on the server, copy `ops/env.production.example` to `.env`, populate configuration, and launch with `docker compose up -d --build`.
  3. Bootstrap two operator accounts via `python /app/ops/pilot_invites.py --db /app/data/pilot_live.db issue-activation --for ...`, configure `CARTMATE_MODERATOR_USER_IDS`, and conduct mutual witnessed 18+ attestation.
  4. Build target-bound Android APK: `.\scripts\build_android_apk.ps1 -BackendOrigin "https://cartmate.yourdomain.com"`.
  5. Sideload onto Android phone via `adb install` and conduct physical rehearsal (H-01..H-06).
- **Preserved Status:** Databases preserved (`ops/pilot_live.db` absent; `backend/cartmate.db` untouched by production/staging); `CODEX_WORK_DIRECTORY.md` strictly untracked and intact. H-01..H-06 strictly NOT RUN.

## Historical Gemini MR3 implementation handback

All findings including MR3-01 from [Codex verification](qa/CODEX_MR2_VERIFICATION.md) have been remediated, re-tested, and verified on isolated harnesses:
- **MR3-01 (URL-Unavailable Parser Fallback Cleanup - P3):** Fully resolved.
  - In `frontend/src/api.ts`: removed the parser-unavailable approval fallback in `isApprovedBackendOrigin()`. The web branch now strictly fails closed (`if (typeof URL === 'undefined') return false`), rejecting tab/newline authority strings without attaching credentials.
  - In `backend/test_private_pilot_review.py`: updated `evaluateContext()` in RT-17 with `withParser` support and added Scenario 7 explicitly asserting fail-closed credential withholding and destination rejection for tab, newline, carriage return, and relative paths when the URL parser is unavailable.
  - Verified by `node qa/codex_url_unavailable_probe.cjs` (7/7 checks pass, exit 0) and `test_rt17` (13/13 passed in review suite).

Fresh verified evidence on disposable databases:
- **158 backend/DR passed** in 35.38s (`backend/` + `ops/test_disaster_recovery.py` with `JEV_MODE=shadow`, disposable database)
- **13 review passed** in 13.62s (`backend/test_private_pilot_review.py`; RT-00..RT-11, RT-14..RT-17 including Scenario 7)
- **12 preflight passed** in 1.44s (`ops/test_pilot_preflight.py`)
- **16 operator browser passed** in 1.5m (8 Desktop Chromium + 8 Mobile Chrome Pixel 7)
- **All 9 diagnostic probes exit 0**:
  - `node qa/codex_url_unavailable_probe.cjs` (exit 0)
  - `python qa/codex_ci_prerequisite_probe.py` (exit 0)
  - `node qa/codex_origin_matrix_probe.cjs` (exit 0)
  - `node qa/codex_mr02_destination_probe.cjs` (exit 0)
  - `node qa/codex_mvp_config_probe.cjs` (exit 0)
  - `node qa/codex_mvp_reconnect_probe.cjs` (exit 0)
  - `python qa/codex_mvp_preflight_probe.py` (exit 0)
  - `python qa/codex_private_pilot_probe.py` (exit 0)
  - `python qa/codex_recovery_boundary_probe.py` (exit 0)
- **Frontend build and lint clean**: `oxlint` (0 errors, 0 warnings in 125ms), `tsc -b && vite build` (clean bundle built in 691ms; expected chunk-size warnings remain)
- **Android APK status**: Synced latest web bundle (`index-BxQUczDg.js`) into Android native assets (`npx cap sync android`) and rebuilt debug APK (`./gradlew.bat assembleDebug` exit 0 in 20s). Artifact: `frontend/android/app/build/outputs/apk/debug/app-debug.apk` (4,849,815 bytes; SHA-256 `532060129448B71897FAF56F9DA57D399CC3362D32F00C22F444542C6AA25D82`; v2 signature verified). Next step before real-device delivery: configure the live private HTTPS backend address via `VITE_BACKEND_ORIGIN`, resync/rebuild, and rehearse on a physical phone.
- **Human & hardware checks H-01..H-06**: strictly **NOT RUN**; no invitations, real SMS, public tunnel, or paid services.

## Gemini implementation snapshot — independently retested above

All findings from [CODEX_MVP_COMPLETION_RETEST_2.md](qa/CODEX_MVP_COMPLETION_RETEST_2.md) have been remediated, re-tested, and verified on isolated harnesses:
- **MR2-01 (CI Dependency Ordering - P1):** Fully resolved.
  - In `.github/workflows/ci.yml`: moved Node setup and frontend dependency installation (`npm ci` in `frontend/`) before the backend compilation/test step. In fresh CI checkouts, Node and `frontend/node_modules/typescript` are now guaranteed to be present before pytest executes cross-stack RT-17.
  - Verified by `python qa/codex_ci_prerequisite_probe.py` (`frontend_install_precedes_backend_tests: true`, `local_rt17_positive_control: passed`, exit 0).
- **MR2-02 (Web URL Helper Same-Origin Hardening - P2):** Fully resolved.
  - In `frontend/src/api.ts`: updated `isApprovedBackendOrigin()` web branch to parse candidate URLs with `new URL(candidate, baseOrigin)` and verify `url.origin.toLowerCase() === baseOrigin.toLowerCase()` and `!url.username && !url.password`, preventing authority bypass via slash-backslash (`/\\...`), userinfo, or off-origin targets, with safe non-backslash relative fallback.
  - In `backend/test_private_pilot_review.py`: added Scenario 6 to permanent regression `test_rt17_native_destination_policy_and_trust_boundary` explicitly asserting rejection of slash-backslash destinations (`/\\...`), control characters, userinfo, and off-origin targets, as well as positive control for valid same-origin relative and absolute paths.
  - Verified by `node qa/codex_origin_matrix_probe.cjs` (25/25 checks pass, exit 0) and `test_rt17` (13/13 passed in review suite).

Fresh verified evidence on disposable databases:
- **158 backend/DR passed** in 40.31s (`backend/` + `ops/test_disaster_recovery.py` with `JEV_MODE=shadow`, disposable database)
- **13 review passed** in 14.03s (`backend/test_private_pilot_review.py`; RT-00..RT-11, RT-14..RT-17)
- **12 preflight passed** in 1.52s (`ops/test_pilot_preflight.py`)
- **16 operator browser passed** in 1.5m (8 Desktop Chromium + 8 Mobile Chrome Pixel 7)
- **All 8 diagnostic probes exit 0**:
  - `python qa/codex_ci_prerequisite_probe.py` (exit 0)
  - `node qa/codex_origin_matrix_probe.cjs` (exit 0)
  - `node qa/codex_mr02_destination_probe.cjs` (exit 0)
  - `node qa/codex_mvp_config_probe.cjs` (exit 0)
  - `node qa/codex_mvp_reconnect_probe.cjs` (exit 0)
  - `python qa/codex_mvp_preflight_probe.py` (exit 0)
  - `python qa/codex_private_pilot_probe.py` (exit 0)
  - `python qa/codex_recovery_boundary_probe.py` (exit 0)
- **Frontend build and lint clean**: `oxlint` (0 errors, 0 warnings in 100ms), `tsc -b && vite build` (clean bundle built in 714ms; expected chunk-size warnings remain)
- **Databases preserved**: `ops/pilot_live.db` strictly absent; observed `backend/cartmate.db` SHA-256 `1B826A1688A4472ED9357620171929C6B79239EEC7541C5D43E54DBB27BB6C61` (unverified, not to be used as clean seed); `CODEX_WORK_DIRECTORY.md` strictly untracked and intact (`D65F80341F67F69B2F3BA879315767075CC1B3FADE7FC6DB8A02BBB8A919059C`).
- **Human & hardware checks H-01..H-06**: strictly **NOT RUN**; no invitations, real SMS, public tunnel, or paid services.

## Historical engineering status — R2-01..R2-03 remediation snapshot (prior to MR-02/MR-05 retest)

**Historical snapshot (superseded by current authority above):** All findings from [qa/CODEX_PRIVATE_PILOT_RETEST.md](qa/CODEX_PRIVATE_PILOT_RETEST.md) were remediated and tested:
- **R2-01 (Revoked socket disconnection & isolation on recovery):**
  - Added `close_user_except_session(user_id, except_session=token)` with close code 1008 in `backend/websocket_manager.py`.
  - Added `set_session_validator(is_session_active_token)`: broadcasts and direct sends drop frames and disconnect sockets whose session is revoked/inactive.
  - Made `revoke_user_sessions_everywhere` async in `backend/main.py`; awaits socket disconnection across all recovery endpoints.
  - Verified by `python qa/codex_recovery_boundary_probe.py` (`revoked_socket_received_new_private_message: false`, `revoked_socket_eventual_close_code: 1008`) and regression `test_rt14` with strict close code 1008 assertion (tautology removed).
- **R2-02 (Transactional rollback on recovery session persistence failure):**
  - Implemented `rollback_operator_recovery_redemption(token, user_id, session_token)` in `backend/storage.py` within `BEGIN IMMEDIATE` to revert token consumption (`consumed_at = NULL, consumed_by_user_id = NULL`) and remove partial sessions without deleting the user.
  - Wrapped recovery persistence in `backend/main.py` in `try...except Exception`: rolls back atomically on persistence exception, allowing same-code retry without stranded sessions.
  - Verified by `python qa/codex_recovery_boundary_probe.py` (`recovery_session_persistence_failure_status: 500`, `same_recovery_code_retry_status: 200`, `host_sessions_after_failed_recovery_and_retry: 1`, `findings: []`) and regression `test_rt15_recovery_persistence_failure_rollback_and_retry`.
- **R2-03 (Complete journey, ledger assertions, reconnection & accessibility):**
  - Removed all `if (await ...isVisible())` guards around plan editing and ledger item entry in `qa/tests/operator-pilot.spec.ts`.
  - Added assertions validating 50/50 ledger item on both Host and Companion screens (40.00 zł total split, 20.00 zł net settlement).
  - Outing 2: Companion low-guilt cancellation journey with real-time UI clearing and cancellation banner.
  - Outing 3: Mutual completion, idempotent complete, and private follow-up until mutual opt-in (RT-08).
  - Browser reload/rehydration HUD rehydration without duplicate chat (RT-09 reload).
  - Backend process stop/restart against same database, offline send failure, fresh-ticket reconnection, and state convergence without duplicate frames (RT-09 restart).
  - Updated RT-11 to boot restored API via FastAPI `TestClient`, verifying active session (200), revoked session (401), non-adult (403), revoked WS ticket (401), and revoked WS handshake (1008); duplicate alias removed.
  - Focused accessibility: AuthModal Escape dismissal with focus restoration to trigger button ("Zaloguj"), sequential keyboard Tab traversal through named controls (`#auth-act-token` -> `#auth-act-name` -> submit), Shift+Tab wraparound, and 320px responsive viewport layout (zero horizontal overflow).

Historical snapshot numbers (see Current Authority section above for latest 158 backend/DR, 13 review, 16 operator-pilot, 6 probes exit 0):
- Automated backend tests + Disaster Recovery: 156 passed
- Review Adversarial Suite: 11 passed (RT-00..RT-11, RT-14, RT-15)
- Operator Pilot Suite: 13 passed
- Diagnostic probes: 2 exit 0
- Browser tests: 14 passed (superseded by 16 passed)
- Human/device checks H-01 through H-06: **BLOCKED / NOT RUN** pending actual physical device rehearsal by founder and authorized human operators.

**Updated 2026-10-13. This is the active handoff; use Current authority above.** Read `AGENTS.md`, all six `context/` files in its prescribed order, `context/feature-specs/001-zero-cost-private-web-pilot.md`, and the latest top section of `LAUNCH_READINESS.md` before editing. `GEMINI_HANDOFF_ARCHIVE_2026-09-29.md`, `HANDOFF.md`, `NEXT_MODEL_EXECUTION_PLAN.md`, and older test-count sections are historical, not instructions to resurrect paid SMS or Render.

## Founder decision and outcome

The founder wants a **real, two-adult, invite-only Silesia friend test** that opens as a website on phones. The founder has no registered business and does **not** want to pay for Twilio, Render, SMSAPI or other hosting just to test. GitHub is optional, free source hosting; it is not how the friend opens the app. There is no authenticated GitHub connection, commit, remote, hosted server, shareable HTTPS URL or APK. The existing saved `gh` credential is invalid; do not assume its username identifies the founder. Never purchase a service, expose a public tunnel, or weaken age/auth gates to manufacture a link.

The proposed zero-cash infrastructure is a **private, time-boxed web pilot on the founder's own computer**, using an official private HTTPS access mechanism such as Tailscale Serve. This is a proposal to verify with the founder and on actual phones, not a completed deployment. The founder's computer must stay on during staffed test hours, and the friend would need access to the private network. Do not use a free Render web service with local SQLite for real users: its filesystem is ephemeral. Do not call a frontend-only static URL a working meetup app. Official references: [Tailscale Personal](https://tailscale.com/pricing), [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve), [Render free-service storage](https://render.com/docs/free), [GitHub Free](https://docs.github.com/en/get-started/learning-about-github/githubs-plans).

## Code truth, not aspirational claims

- React 19/Vite frontend, FastAPI backend, SQLite WAL, WebSockets, and backup/restore scripts exist. The React bundle and API are served same-origin by FastAPI in the Docker path. The Capacitor native Android scaffold exists under `frontend/android`; no compiled APK or handset execution is verified.
- Standard deployed phone login requires carrier-backed six-digit SMS OTP. Explicitly enabled staging now also has operator-in-person activation and same-account recovery, without SMS; these flows leave `phone_verified_at` null. Console OTP remains forbidden in staging/production. Operator codes are authentication/admission secrets, not proof of phone control or adulthood. The reproduced recovery defects are independently closed; preserve their tests.
- Live social endpoints and WebSockets require approved adult proof. Explicit staging operator admission can bootstrap the separate witnessed adult-attestation flow without SMS. Nobody may approve their own age; a separate trusted moderator is needed for the operator's own check. Production operator admission remains prohibited and production live use stays closed.
- SOS SMS remains disabled. The truthful fallback is a direct `tel:112` voice call; never imply monitoring or emergency dispatch.
- Existing local evidence: backend 141/141 passed on 2026-10-06 on a disposable SQLite database (129 baseline + 12 new tests in `backend/test_operator_admission_pilot.py`); frontend build/lint pass cleanly (`oxlint` 0 errors/warnings). Development browser 40/40, no-demo browser 4/4 and local disaster-recovery drill 3/3 passed. Slice A and Slice B are complete and verified. These checks used disposable databases and do **not** prove a real HTTPS share, real identity/age check, off-device backup, independent security/WCAG 2.2 review or human usability. The build still warns about two large JavaScript chunks.
- The local Git repository has staged source but no commit or remote. `CODEX_WORK_DIRECTORY.md` is untracked user/other-agent material; preserve it. Never stage `backend/cartmate.db`, `.env`, signing keys, generated QA files or private backups. `gh auth status` reports an invalid saved credential.

## Gemini's next scoped work

**MR3-01 and original MR2 failures are independently closed.** Continue feature 002 using the current Android preflight above: preserve existing tools/configuration, establish the intended private backend origin, rebuild/sync native assets, then perform the real debug build with appropriate approvals. Do not assume Build Tools 35.0.0 is needed or accept licenses automatically. Do not redo accepted recovery, native-origin, CI-ordering or journey changes. The remaining human/network work is:
1. Rehearse private HTTPS access and WebSocket connectivity over Tailscale Serve between two actual mobile devices.
2. Verify witnessed in-person 18+ attestation between two distinct accounts (operator cannot self-attest).
3. Test check-in, chat, cancellation, disconnect/reconnect and clean host restart on physical handsets.
4. Execute off-device backup copy and restore rehearsal per `ops/RUNBOOK.md` and `ops/PILOT_RUNBOOK_WINDOWS.md`.
5. Conduct manual accessibility and usability pass on phone screen sizes.

This is **not** a broad rewrite, national launch, AI/Jev feature, payments feature, app-store release, or invitation to deploy the existing paid Render Blueprint. Private Android test packaging is now separately approved in feature 002. The source of truth for unresolved broader work remains `LAUNCH_READINESS.md`.

## Stop conditions / founder input

Ask before any real connection if the founder and friend can use the private HTTPS access method on their phones and whether a separate trusted adult can witness the founder's own age check. Ask for the intended staffed test window and a safe off-device backup location. If those are unavailable, leave real meetups disabled and offer an explicitly labeled UI-only preview instead. Never ask the founder to paste OTPs, ID images, document numbers, passwords or provider tokens into chat.

## Evidence required for handoff back

Report changed files, threat/trust assumptions, exact commands/results, fresh disposable database path class (not secrets), desktop/mobile two-person test results, restart/revocation behavior, private HTTPS/WSS origin checks, backup-and-restore result, manual security/accessibility findings, and what remains unverified. Update `context/progress-tracker.md`, `LAUNCH_READINESS.md`, `README.md`, and this handoff in the same change. The link is not ready until the actual phones complete the private hosted journey and a human accepts the risk.
