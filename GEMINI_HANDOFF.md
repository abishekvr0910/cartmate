# CartMate — Comprehensive Engineering & Architecture Handoff

**Update (2026-11-15, later — the working tree on `ba030ce` is no longer clean):** features 14 and 17 of [the friends pilot hardening scope](docs/scope/claude-hardening.md) are implemented locally and uncommitted; see [the progress tracker](context/progress-tracker.md).
- Feature 14: `DurableStorage._cancel_expired_forming_pods` commits the expiry sweep on its own (`backend/storage.py`, `backend/test_pod_expiry.py`).
- Feature 17: `voice_manager.describe_voice_window()` and `window_state` on `GET /api/voice/status`; the voice screen renders it in four languages (`backend/voice_manager.py`, `backend/main.py`, `frontend/src/types.ts`, `frontend/src/components/VoiceCallHUD.tsx`, `backend/test_voice_window_policy.py`, `qa/tests/voice-window-policy.spec.ts`).
- Observed after review follow-ups (`get_pod` sweeps; the call button is disabled until the policy is known; Playwright keeps failure traces): root pytest 287 passed, development browser suite 68 passed, frontend lint and build clean, no-demo 4 passed, the five CI probes exit 0. Not run: Docker, hosted CI.
- **UNRESOLVED:** operator-pilot failed one test in the first of six runs, then passed five times. Test name and artifacts were not kept. Save the full output and `qa/test-results` of every operator-pilot run until it is explained.
- Feature 16 is a design only, revision 2: [004 — explicit venue verification](context/feature-specs/004-explicit-venue-verification.md). The founder accepted its seven decisions on 2026-11-15; it is not built yet.

**Update (2026-11-15, PR #1 merged into `main` at `ba030ce` — branch `fix/pilot-readiness-hardening` deleted locally and on GitHub; local `main` is level with `origin/main` and clean):** PR #1 (commits `880fe7b` and `4c4aeea`) merged into `main` at `ba030ce` (`2026-11-15T18:31:50Z`), returning `main` to green after the `2026-11-13` (`1402870`) failure. See [the progress tracker](context/progress-tracker.md) for details.
- **Verified hosted CI on `main` (`ba030ce`, run `43747274188`, `2026-11-15`):** all **22** workflow steps passed (`239` backend pytest + `3` disaster recovery + `12` preflight = **254** Python tests passed; `oxlint` 0 errors/0 warnings; Vite build clean; Playwright **50** dev + **4** no-demo + **16** operator-pilot passed; **5** CI probes passed; Docker build + REST/WS 403 smoke test passed). Pre-merge PR #1 runs (`43745905875` and `43746504284`) also passed.
- **Failure-continuation untested:** `.github/workflows/ci.yml` gates post-install steps on `DEPS_OK` and `!cancelled()`, but the failure-continuation path itself remains **untested** because no step failed on any of the hosted runs (`43745900361`, `43745905875`, `43746499691`, `43746504284`, `43747274188`).
- **E2E heading fix:** `qa/tests/safety-and-sos.spec.ts` now asserts the voice screen heading rather than the cooldown-dependent connect label (development suite: **50 passed**, up from 49 passed / 1 failed at `1402870`).
- **Voice hours (staging open all day):** `backend/voice_manager.py` fails closed when `Europe/Warsaw` cannot be loaded (`tzdata==2026.6` pinned), and production still enforces 18:00–23:00 Warsaw time. On staging, `CARTMATE_VOICE_WINDOW_ENFORCED` stays unset per founder decision for the friends test, so **staging voice calls are open all day**.
- **Seeded venues require a recorded in-person visit:** Migration **0016** withdraws the placeholder `verified_at` from all nine seeded Third Places; `GET /api/pods/places` returns verified places only; pod creation against an unverified seeded place fails (HTTP 400); and `ops/seed_third_places.py` exposes `seed_pilot_third_places`. A fresh database has **zero** usable pod venues until a recorded in-person visit updates a seeded row or a moderator adds an in-person-visited place (`POST /api/pods/places`; no UI screen exists).
- **External / runtime / human gates remain unverified:** EC2 provisioning/deploy, coturn TURN runtime/relay traversal, real-device tests (domain-bound Android APK, handset mic permissions, `setSinkId`), and human pilot gates (`H-01..H-06`) remain **NOT RUN / unverified**.
- **Environment & DB preservation:** The QA harnesses resolve `backend/.venv` (junction to rebuilt `backend/venv` on this Windows laptop). Local `backend/cartmate.db` remains preserved untouched during this post-merge check (SHA-256 `B042AC2665EF5B6DEC6703298DB4A38F64BEB0C63C8A20F2325AFD8823C27424`). **Hazard:** importing `backend/storage.py` outside pytest without `CARTMATE_DATABASE_PATH` opens and migrates `backend/cartmate.db`—always set `CARTMATE_DATABASE_PATH` to a disposable path for ad-hoc scripts.
- Founder decisions (2026-11-15, full list in the progress tracker): friends test first (three or more people), then about 100 people and the app stores; moderators are the founder plus one backup; staging voice stays open all day (`CARTMATE_VOICE_WINDOW_ENFORCED` unset) for the friends test; the nine seeded venues stay unverified until visited and a moderator adds a place they have personally been to; automated monitoring is deferred to the 100-person stage.

**Historical baseline snapshot below (2026-11-13, `1402870` local pre-hardening pass — superseded by `ba030ce` above):**
The `2026-11-13` snapshot below records the prior Phase 4 audit closure, test-suite database isolation, voice-manager security hardening, operator E2E stabilization, and Handy/FlowPilot audio adaptation on `origin/main` ([github.com/abishekvr0910/cartmate.git](https://github.com/abishekvr0910/cartmate.git)).

---

## 1. Verified Automated Test Matrix

```
========================================================================================
Test Suite                           Target Directory / Config      Result        Duration
----------------------------------------------------------------------------------------
Backend & Ops Root Pytest Suite      pytest -p no:cacheprovider -q  250 passed    92.17s
Playwright Operator-Pilot Suite      qa/playwright.operator-pilot   16 passed     1.9m
Playwright Pods & Voice Suite        qa/run_pods_and_voice.py       6 passed      22.9s
Playwright Staging No-Demo Suite     qa/playwright.no-demo          4 passed      24.3s
Diagnostic Security Probes           qa/codex_* (9 probes)          All 9 exit 0  Clean
Frontend Static Linter               npx oxlint (29 files)          0 err, 0 warn 193ms
Frontend Production Build            tsc -b && vite build           Clean build   1.55s
Database File Integrity Check        backend/cartmate.db            SHA-256 match 0 byte drift
========================================================================================
Total Automated Matrix: 276 automated tests passed + 9 security probes exit 0
```

### Breakdown of Test Suites
* **Backend + Disaster Recovery + Ops (250 tests passed):**
  - Core API & trip lifecycle: `test_activity_first_outings.py`, `test_completion_regressions.py`, `test_group_edge_cases.py`, `test_launch_core_durability_and_privacy.py`.
  - Micro-Pods & Verified Third Places: `test_micro_pods_api.py`, `test_migration_0011_micro_pods.py`, `test_real_cartmate_migration_11.py`.
  - Ephemeral 10-Minute Voice Calls: `test_voice_calls.py` (12 tests covering matching, 12s disconnect grace, STRICT table rebuild, duplicate ratings 409/200, daily limits, cooldowns, and staging/production TURN secret fail-closed lifespan startup guard).
  - Funnel & Telemetry: `test_funnel_analytics.py` (7 tests covering signup tracking, attendance gating, quorum reach, repeat rate, and PII sanitization).
  - Closed Pilot Invites & Operator Admission: `test_pilot_invites.py`, `test_operator_admission_pilot.py`, `test_manual_age_pilot.py`.
  - Adversarial Review Scenarios: `test_private_pilot_review.py` (13 scenarios: RT-00..RT-11, RT-14..RT-17).
  - Ops Preflight & Disaster Recovery: `ops/test_pilot_preflight.py` (12 tests), `ops/test_disaster_recovery.py` (3 tests).
* **Browser Journeys (26 tests passed across Desktop Chromium and Mobile Chrome Pixel 7):**
  - **Operator Pilot (16 passed):** Full admission, witnessed 18+ attestation, outing creation, join, mutual trip, live chat, 50/50 cost split ledger, cancellation, account recovery (CR-01), second outing cancellation (R2-03), third outing completion and private follow-up (RT-08), reload convergence (RT-09 reload), process restart recovery (RT-09 restart), and focused WCAG 2.2 AA accessibility (RT-12).
  - **Micro-Pods & Voice (6 passed):** Quorum unlock (3/5), real-time chat, Escape focus trap, two-user WebRTC voice call connection, in-call mute toggle with synthetic earcons, speakerphone output toggle (`setSinkId`), hangup, rating submission, and PL -> EN -> UK -> RU locale switching with zero residual Polish.
  - **Staging No-Demo (4 passed):** Outing publishing, PII shielding, women-only ID denial, and one-use pilot invite gating.
* **Diagnostic Security Probes (All 9 exit 0):**
  - `codex_url_unavailable_probe.cjs`: Fail-closed credential withholding when URL parser is unavailable.
  - `codex_ci_prerequisite_probe.py`: CI dependency ordering validation.
  - `codex_origin_matrix_probe.cjs`: Same-origin and slash-backslash (`/\\...`) authority bypass rejection (25 checks).
  - `codex_mr02_destination_probe.cjs`: Native and Web destination policy enforcement.
  - `codex_mvp_config_probe.cjs`: Configuration parsing and port isolation.
  - `codex_mvp_reconnect_probe.cjs`: Reconnection message replay and deduplication.
  - `codex_mvp_preflight_probe.py`: Preflight health and operator mode assertions.
  - `codex_private_pilot_probe.py`: Single-use activation token replay and session persistence boundaries.
  - `codex_recovery_boundary_probe.py`: Recovery code rollback on persistence error and close code 1008 on revoked sockets.

---

## 2. Architectural Hardening & Bug Remediations

### A. Test Suite Database Isolation (Triple Guard)
- **Problem:** `storage.py` previously evaluated `DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "cartmate.db")` at module load time. Running `pytest` without explicitly setting `CARTMATE_DATABASE_PATH` persisted test users, sessions, and reports directly into `backend/cartmate.db`.
- **Solution:**
  1. [conftest.py](file:///C:/Users/user/cartmate/conftest.py) (root): Automatically forces an ephemeral temp directory and unique test database before test discovery.
  2. [backend/conftest.py](file:///C:/Users/user/cartmate/backend/conftest.py#L8-L19): Enforces the same isolation when pytest is invoked directly inside `backend/`.
  3. [backend/storage.py](file:///C:/Users/user/cartmate/backend/storage.py#L19-L26): Actively checks `sys.modules` for `"pytest"` or `PYTEST_CURRENT_TEST` and refuses to fall back to `DEFAULT_DB_PATH`.
  4. Restored `backend/cartmate.db` to a pristine, unseeded baseline (15 migrations, 0 users, 9 third places, 4 activity templates).
  5. **Verified:** SHA-256 `4C6E08033FFF4BD6C819452E86EE621EBCDCEB3ABAA5148FB8229C9405CC840D` remained identical with **0 byte drift** across full 250-test pytest execution.

### B. Operator E2E Flakiness Remediation
- **Problem:** In `qa/tests/operator-pilot.spec.ts`, tests 1 and 4 intermittently timed out waiting for `Plan zaakceptowany`. Host clicked `Zapisz plan i poproś o akceptację` (`PUT /api/trips/.../plan`), incrementing `plan_version` on the server. If companion clicked accept before the WebSocket `trip.plan_updated` frame arrived, the companion sent the old `plan_version`, triggering an HTTP 409 conflict and leaving mutual acceptance incomplete.
- **Solution:**
  - Awaited the host's `PUT` network response before proceeding.
  - Awaited UI appearance of the updated plan text on the companion's page, ensuring the companion client has received the latest `plan_version` before clicking accept.
  - Increased `waitForHarness` max timeout to 30s to allow backend restart tests adequate initialization time on Windows.
  - Result: **16/16 passed deterministically** in 1.9m.

### C. Voice Manager Staging Fail-Closed Guard
- **Problem:** `voice_manager.py:78` withheld TURN credentials on default secrets only when `CARTMATE_ENV == "production"`. Staging instances run outside Compose could still issue credentials with the default development secret.
- **Solution:** Updated `backend/voice_manager.py` to fail closed for both `staging` and `production`. Added regression assertions in `backend/test_voice_calls.py`.

---

## 3. Handy & FlowPilot Audio Architecture Dissection & Adaptations

See detailed companion document: [docs/HANDY_AND_FLOWPILOT_AUDIO_ANALYSIS.md](file:///C:/Users/user/cartmate/docs/HANDY_AND_FLOWPILOT_AUDIO_ANALYSIS.md).

We dissected the architecture and resolved issues of **Handy** ([cjpais/handy](https://github.com/cjpais/handy)) and cross-referenced them with **FlowPilot** ([flowpilot](file:///D:/Software%20by%20Abi/flowpilot)):

1. **Digital Silence & Hardware Mute Detection (Handy #2486 vs FlowPilot Energy VAD):**
   - Added `isMicSilent` tracking in [VoiceCallHUD.tsx](file:///C:/Users/user/cartmate/frontend/src/components/VoiceCallHUD.tsx). If frequency power is `< 10` for > 90 frames (~1.5s) while unmuted, a live accessible alert banner (`role="alert"`) notifies the user.
2. **Bluetooth / AirPods Profile Switching (Handy #2472, #2387 vs FlowPilot Feature 28):**
   - Separated speakerphone output switching (`setSinkId`) from the microphone input stream (`localStreamRef.current`), preventing Bluetooth SCO/HFP profile re-negotiation stalls during call output toggles.
3. **Monotonic Session Guards (Handy #2097 vs FlowPilot Hardware Timestamps):**
   - `callSessionRef.current` monotonic counter guards all asynchronous WebRTC callbacks (`getUserMedia`, `onicecandidate`, `ontrack`, `onconnectionstatechange`), preventing delayed network frames from corrupting active or subsequent calls.
4. **Pure Web Audio API Earcons (Handy `audio_feedback.rs` vs FlowPilot Chimes):**
   - Implemented zero-asset Web Audio synthesis (`AudioContext` sine and triangle oscillators) for tactile audio feedback:
     - Connect: rising major-third chime (`523 Hz -> 659 Hz`, 300ms decay).
     - Disconnect: gentle descending chime (`659 Hz -> 440 Hz`, 320ms decay).
     - Mute toggle: dual-frequency tactile click (`320 Hz / 640 Hz`, 80ms decay).
5. **9-Bar Logarithmic Speech Visualizer:**
   - 9 logarithmic speech frequency bands (`[1..2]`, `[2..4]`, ..., `[37..48]`), calibrated dB range (`-68 dB` to `-25 dB`), `Math.pow(lvl, 0.7)` power curve shaping, exponential temporal smoothing, and 3-point spatial smoothing.

---

## 4. Current Deployment Authority & Operational Status

- **Host Architecture:** Single EC2 `t3.medium` instance in `eu-central-1` (Frankfurt) running Ubuntu 24.04 with encrypted retained gp3 EBS volume.
- **Services in Docker Compose:**
  - FastAPI backend (`web:8000`, single worker for SQLite WAL safety).
  - Caddy reverse proxy (`caddy:80`, `caddy:443` with automated Let's Encrypt TLS).
  - coturn STUN/TURN relay (`turn:3478` UDP/TCP, relay range `49160-49200/udp`, host networking, secret auth, EC2 public/private 1:1 NAT mapping).
- **Environment Variables Required on EC2:**
  - `DOMAIN`: Target registered domain (e.g. `cartmate.pl`).
  - `CARTMATE_TURN_SECRET`: Unique high-entropy secret.
  - `CARTMATE_TURN_EXTERNAL_IP`: EC2 Elastic IP.
  - `CARTMATE_TURN_PRIVATE_IP`: EC2 internal private IPv4.
- **Operational Verification Boundary:**
  - Runtime Docker/coturn startup on live AWS and cellular handset gates **H-01 through H-06 remain strictly NOT RUN** until AWS provisioning clears and physical test devices are connected.

---

## 5. Next Steps for Incoming Agent / Operator

1. **When AWS Account Hold Clears:**
   - Provision Ubuntu 24.04 `t3.medium` in `eu-central-1` per [ops/EC2_STAGING_RUNBOOK.md](file:///C:/Users/user/cartmate/ops/EC2_STAGING_RUNBOOK.md).
   - Allocate Elastic IP and bind domain DNS A record.
   - Clone repo, configure `.env`, and execute `docker compose up -d --build`.
2. **Bootstrap Operator Accounts:**
   - Run `python /app/ops/pilot_invites.py --db /app/data/pilot_live.db issue-activation` for 2 human moderators.
   - Conduct mutual in-person witnessed 18+ attestation.
3. **Build Target-Bound Android APK:**
   - Run `.\scripts\build_android_apk.ps1 -BackendOrigin "https://<DOMAIN>"`.
4. **Execute Cellular Handset Gates (H-01..H-06):**
   - H-01: Adult age-gate verification.
   - H-02: Cellular TURN relay connection across symmetric mobile NATs.
   - H-03: Micro-pod quorum reach and live coordination chat.
   - H-04: Outing plan mutual consent and PIN rendezvous handshake.
   - H-05: Direct-112 SOS voice call triggering.
   - H-06: Off-instance backup custody and recovery rehearsal.
