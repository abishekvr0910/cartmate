# CartMate Private Pilot Review Results (Slice D Acceptance Matrix)

> **Current independent result (2026-10-13):** [Codex verification](CODEX_MR2_VERIFICATION.md) closes original MR2-01/02 failures for the tested runtime. Independently rerun: 158 backend/DR (37.17s), 12 preflight (1.49s), 16 operator browser (1.6m), eight existing probes and build/lint; fresh offline dependency-install/RT-17 rehearsal passes. New **MR3-01 (P3)** affects only the URL-unavailable fallback and has no demonstrated supported-browser exploit. H-01–H-06 remain NOT RUN. The following implementation timings/claims are retained as historical evidence.

> **Current engineering status (2026-10-13):** CI prerequisite ordering (MR2-01) and web helper same-origin validation (MR2-02) are fully remediated on isolated harnesses. CI workflow sets up Node and installs frontend dependencies before backend pytest, satisfying RT-17's TypeScript prerequisite in fresh checkouts. The web destination validator parses candidates with `new URL(candidate, baseOrigin)` and enforces exact origin matching and userinfo rejection, blocking slash-backslash (`/\\...`) authority bypass. All 8 diagnostic probes exit 0, 158 backend/DR cases pass, 13 review adversarial cases pass (including RT-17 Scenario 6), 12 preflight cases pass, and 16 operator browser cases pass across Chromium and Mobile Chrome. Handed off for Codex independent retest. Physical-device and human gates (H-01..H-06) remain strictly **NOT RUN**.

> **Historical Codex retest 2 disposition (2026-10-13):** [Codex retest 2](CODEX_MVP_COMPLETION_RETEST_2.md) independently confirmed 158 backend/DR, 12 preflight, 16 operator browser cases, six existing probes and build/lint passed; original native MR-02 and bounded MR-05/runbook fixes accepted; identified MR2-01 CI dependency order and MR2-02 web slash-backslash URL helper edge cases, now remediated above.

**Date:** 2026-10-13  
**Scope:** Feature 001 & Feature 002 — Zero-Cost Private Web Pilot & Android Preparation (Silesia / Katowice, Poland)  
**Agent:** Gemini (Single Writer / Implementation & Harness Verification)  
**Codex Independent Review Status:** **ORIGINAL MR2 FAILURES VERIFIED CLOSED; MR3-01 P3 CLEANUP OPEN; HUMAN GATES NOT RUN**  
**Database Isolation Guard:** Disposable SQLite databases used exclusively (`cartmate_op_qa_*`, `disposable_*.db`, `tempfile.TemporaryDirectory`). Real/production databases (`backend/cartmate.db` SHA-256 `1B826A1688A4472ED9357620171929C6B79239EEC7541C5D43E54DBB27BB6C61` unverified, not clean seed; `ops/pilot_live.db` absent) were strictly untouched. `CODEX_WORK_DIRECTORY.md` intact (`D65F80341F67F69B2F3BA879315767075CC1B3FADE7FC6DB8A02BBB8A919059C`).

---

## Executive Summary

| Category | Tests / Checks | Passed | Failed | Blocked / Not Run | Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Backend Pytest + Disaster Recovery** | 158 | 158 | 0 | 0 | `python -m pytest -q -p no:cacheprovider . ../ops/test_disaster_recovery.py` from `backend/` in 40.31s (`JEV_MODE=shadow`) |
| **Review Adversarial Suite (RT-00..RT-11, RT-14..RT-17)** | 13 | 13 | 0 | 0 | `python -m pytest backend/test_private_pilot_review.py -v` (13 passed in 14.03s; includes RT-17 Native Destination Policy & Web Hardening) |
| **Pilot Preflight Suite (test_pilot_preflight.py)** | 12 | 12 | 0 | 0 | `python -m pytest ops/test_pilot_preflight.py -v` (12 passed in 1.52s; FastAPI integration + unit tests) |
| **Operator Pilot Suite (test_operator_admission_pilot.py)** | 13 | 13 | 0 | 0 | `python -m pytest backend/test_operator_admission_pilot.py -v` (13 passed in 10.63s) |
| **Playwright Operator Pilot (RT-07..09, RT-12, CR-01, MR-05)** | 16 | 16 | 0 | 0 | 8 desktop Chromium + 8 Mobile Chrome (Pixel 7 emulation) pass in 1.5m |
| **Diagnostic CI Prerequisite Probe (codex_ci_prerequisite_probe.py)** | 1 | 1 | 0 | 0 | `python qa/codex_ci_prerequisite_probe.py` exits 0 (frontend install precedes backend tests) |
| **Diagnostic Origin Matrix Probe (codex_origin_matrix_probe.cjs)** | 1 | 1 | 0 | 0 | `node qa/codex_origin_matrix_probe.cjs` exits 0 (25/25 checks pass; slash-backslash rejected) |
| **Diagnostic MR-02 Destination Probe (codex_mr02_destination_probe.cjs)** | 1 | 1 | 0 | 0 | `node qa/codex_mr02_destination_probe.cjs` exits 0 (positive exact origin comparison, fail-closed without token) |
| **Diagnostic Config Probe (codex_mvp_config_probe.cjs)** | 1 | 1 | 0 | 0 | `node qa/codex_mvp_config_probe.cjs` exits 0 (native trust boundary & immutable origin validated) |
| **Diagnostic Preflight Probe (codex_mvp_preflight_probe.py)** | 1 | 1 | 0 | 0 | `python qa/codex_mvp_preflight_probe.py` exits 0 (`health_contains_operator_flag: true`, `contract_error: null`) |
| **Diagnostic Reconnect Probe (codex_mvp_reconnect_probe.cjs)** | 1 | 1 | 0 | 0 | `node qa/codex_mvp_reconnect_probe.cjs` exits 0 (`missedMessageVisibleWithoutReload: 1`) |
| **Diagnostic Private Pilot Probe (codex_private_pilot_probe.py)** | 1 | 1 | 0 | 0 | `python qa/codex_private_pilot_probe.py` exits 0 with all diagnostic checks green |
| **Diagnostic Recovery Probe (codex_recovery_boundary_probe.py)** | 1 | 1 | 0 | 0 | `python qa/codex_recovery_boundary_probe.py` exits 0 with 0 findings |
| **Frontend Production Build & Lint** | 2 | 2 | 0 | 0 | `npm run build` (clean bundle built in 714ms) and `npm run lint` (0 warnings, 0 errors in 100ms) |
| **Human / Physical Device Checks (H-01..H-06)** | 6 | 0 | 0 | 6 | Human-owned: physical phones, witnessed IDs, private keys, custody (strictly NOT RUN) |

---

## Retest Remediation Summary (R2-01 through R2-03)

### R2-01 — P0: Revoked Socket Disconnection and Frame Isolation on Recovery (RT-05, RT-14)
- **Problem Identified by Codex:** In `qa/CODEX_PRIVATE_PILOT_RETEST.md`, Codex's probe demonstrated that after an account redeemed a recovery token (`CMREC-...`), its prior active WebSocket connection remained open and continued to receive new private chat messages sent by companions. The socket only closed with 1008 if the client subsequently attempted an outbound ping/action.
- **Root Cause:**
  1. `revoke_user_sessions_everywhere` in `backend/main.py` deleted old sessions in SQLite and memory, but did not instruct `ws_manager` to close existing sockets belonging to those revoked sessions.
  2. `ws_manager.broadcast()` and `ws_manager.send_to_user()` in `backend/websocket_manager.py` iterated through active sockets without revalidating whether the socket's session was still active.
- **Implementation:**
  - In `backend/websocket_manager.py`:
    - Added `close_user_except_session(user_id, except_session=None)`: closes all existing sockets for `user_id` whose session token is not `except_session` with close code 1008 (Policy Violation) and removes them from all chat groups and connection maps.
    - Added `set_session_validator(validator)` hook.
    - In `broadcast()` and `send_to_user()`: checked `self._session_validator(session)`. If the session has been revoked or invalidated, the message frame is dropped, the socket is immediately closed with code 1008, and disconnected.
  - In `backend/main.py`:
    - Registered `ws_manager.set_session_validator(is_session_active_token)`.
    - Made `revoke_user_sessions_everywhere(user_id, except_token=None)` asynchronous; it now calls `storage.revoke_other_user_sessions`, cleans memory session tokens, and awaits `ws_manager.close_user_except_session(user_id, except_session=except_token)`.
    - Awaited `revoke_user_sessions_everywhere` in both recovery entry points: `POST /api/auth/redeem-operator-recovery` and the bound-recovery branch of `POST /api/auth/redeem-operator-activation`.
- **Evidence:**
  - `python qa/codex_recovery_boundary_probe.py` exits 0:
    - `"revoked_socket_received_new_private_message": false`
    - `"revoked_socket_eventual_close_code": 1008`
    - `"active_socket_positive_control": true`
    - `"same_account_recovered": true`
  - Permanent regression `test_rt14_recovery_revoked_socket_disconnect_and_isolation` added to `backend/test_private_pilot_review.py`: tautological assertion replaced with strict `assert disconnected is True and close_code == 1008` assertion; passes cleanly.

### R2-02 — P1: Recovery Session Persistence Failure Rollback and Same-Code Retry (RT-03, RT-15)
- **Problem Identified by Codex:** In `qa/CODEX_PRIVATE_PILOT_RETEST.md`, an injected session persistence exception during `CMREC` recovery left the recovery code consumed, the user with 0 sessions, and retrying with the same recovery code failed with 403.
- **Root Cause:** While new-account activation had compensation logic (`rollback_operator_activation_redemption`), recovery lacked an atomic rollback mechanism.
- **Implementation:**
  - In `backend/storage.py`:
    - Implemented `rollback_operator_recovery_redemption(token, user_id, session_token=None)`: atomically executes within `BEGIN IMMEDIATE` to revert `consumed_at = NULL` and `consumed_by_user_id = NULL` on the recovery activation record, and deletes any partial session records in `sessions` table without deleting the user.
  - In `backend/main.py`:
    - Wrapped session persistence in `POST /api/auth/redeem-operator-recovery` and `POST /api/auth/redeem-operator-activation` in `try...except Exception`: if persistence fails, calls `storage.rollback_operator_recovery_redemption(token, user_id, session_token=session_token)`, purges in-memory session mappings, and re-raises HTTP 500.
- **Evidence:**
  - `python qa/codex_recovery_boundary_probe.py` exits 0:
    - `"recovery_session_persistence_failure_status": 500`
    - `"same_recovery_code_retry_status": 200`
    - `"host_sessions_after_failed_recovery_and_retry": 1`
    - `"restored_rest_session_status": 200`
    - `"findings": []`
  - Permanent regression `test_rt15_recovery_persistence_failure_rollback_and_retry` added to `backend/test_private_pilot_review.py` passes cleanly.

### R2-03 — P1: Complete Journey, Ledger Assertions, Reconnection & Accessibility
- **Problems Identified by Codex:**
  1. Plan editing and ledger controls were guarded by optional `if (await ...isVisible())` in the browser test; ledger assertions checked host text without validating agreed numeric 50/50 amounts on both participants' screens.
  2. The browser test lacked a second outing journey exercising companion cancellation (low-guilt).
  3. Lacked a third outing journey exercising mutual completion, idempotent complete, and private follow-up until mutual opt-in (RT-08).
  4. Lacked a separate test that stops and restarts the owned backend against the same database while browsers stay open, verifying fresh-ticket WS reconnection/resubscription, offline-send failure, and state convergence (RT-09).
  5. RT-11 snapshot test did not assert denied WS ticket request and denied WS connection handshake on revoked sessions.
  6. RT-12 lacked required keyboard flow assertions traversing named controls (`#auth-act-token` -> `#auth-act-name` -> `button[type="submit"]`), Shift+Tab wraparound, and responsive viewport layout at 320px.
- **Implementation:**
  - In `qa/tests/operator-pilot.spec.ts`:
    - **Removed all `if (await ...isVisible())` guards** around plan editing (`whenInput`, `policySelect`) and ledger item entry (`addSplitBtn`).
    - Added assertions verifying the 50/50 ledger item on **both Host and Companion screens**: verified total split `40.00 zł` and net settlement `20.00 zł` on both participants' displays.
    - Added **Test 3 (Second Outing Journey — Companion Cancellation)**: Host creates a second outing, Companion discovers live via WebSocket, requests to join, Host accepts in UI, both enter Active Trip HUD, and Companion executes low-guilt cancellation (`Zrezygnuj ze spotkania`). Confirmed HUD clears immediately on both screens without page reload and cancellation banner displays.
    - Added **Test 4 (Third Outing Journey — Completion & Follow-up, RT-08)**: Host creates third outing, sets specific meeting plan (`Dziś o 19:00 przy wejściu`), Companion joins, both mutually accept plan, complete PIN handshake (`1046`), Host marks outing as finished (`Zakończ wyjście`), companion finishes outing. Idempotent complete verified (calling complete again returns 200 with completed trip). Private follow-up review submitted: Host selects rating 5/5 and meet again ("Tak, chętnie"); verified Companion's trip query reports `is_mutual_buddy: false` (no leakage). Companion then submits 5/5 review and meet again ("Tak, chętnie"); `expect.poll` confirms `is_mutual_buddy: true` on both sides.
    - Added **Test 5 (Reload/Rehydration & State Convergence, RT-09 reload)**: Host creates outing, Companion joins, both enter HUD, Host sends chat message. Companion context reloads (`page.reload()`), re-authenticates and reconnects WebSocket. Verified: active trip HUD rehydrates automatically, existing chat message appears exactly once (no duplicate chat messages), and when Host cancels, the cancelled trip remains cancelled and does not reappear upon Companion reload.
    - Added **Test 6 (Process Stop/Restart, Offline Send Failure & Reconnection, RT-09 restart)**: Browsers open in active outing; backend process is stopped via `harness.stop_backend()`. Offline send failure verified (`expect(sendPromise).rejects.toThrow()`). Backend is restarted against same database (`harness.start_backend()`). Verified browser `RealtimeClient` reconnects with fresh tickets and resubscribes; post-restart chat message sent and received on both sides without duplicate frames.
    - Added **Test 7 (Focused Accessibility, RT-12)**: AuthModal Escape key dismissal with focus restoration to trigger button ("Zaloguj"), keyboard Tab traversal through named form inputs (`#auth-act-token` -> `#auth-act-name` -> `button[type="submit"]`), Shift+Tab wraparound back to previous inputs, and responsive 320px viewport layout (zero horizontal overflow: `scrollWidth <= clientWidth + 1`).
  - In `frontend/src/App.tsx`:
    - In `loadInitialData()`: added logic so that if the user has an active trip in `'scheduled'` or `'in_progress'` status upon initial load or page reload, `activeTab` automatically switches to `'active_trip'`, ensuring seamless HUD rehydration.
  - In `frontend/src/components/ActiveTripHUD.tsx`:
    - Added `max-h-[90vh] overflow-y-auto` to the inner container of `#trip-review-dialog` to guarantee mobile viewport reflow without clipping.
  - In `backend/test_private_pilot_review.py`:
    - In `test_rt11_disaster_recovery_populated_operator_tables`: boots restored database via FastAPI `TestClient`, verifies active session returns 200, revoked REST session returns 401, non-adult user returns 403, revoked session requesting WS ticket returns 401, and revoked WS handshake returns 1008. Removed duplicate alias.
    - In `test_rt14_recovery_revoked_socket_disconnect_and_isolation`: replaced `assert disconnected or True` with strict `assert disconnected is True and close_code == 1008`.
- **Evidence:**
  - `npm run test:operator-pilot` in `qa/`: **14 passed (1.5m)** (7 desktop Chromium + 7 Mobile Chrome Pixel 7).
  - `python -m pytest backend/test_private_pilot_review.py -v`: **11 passed in 12.06s** (all RT-00..RT-11, RT-14, RT-15; 0 aliases).
  - `frontend/`: `npm run build` and `npm run lint` clean (built in 648ms, 0 errors, 0 warnings in 175ms).

---

## ID-by-ID Results Matrix (Empirical Findings)

### RT-00 — Attestation Schema Validation & Runbook Alignment (P1)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt00_attestation_method_schema_validation`
- **Observed:** Schema and attestation endpoint enforce literal enum values. `physical_identity_document` accepted (200), `physical_id` rejected (422).
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt00_attestation_method_schema_validation`

### RT-01 — Correct Private Startup and Role Bootstrap (P1)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt01_private_startup_and_role_bootstrap`
- **Observed:** Environment-driven moderator bootstrap cleanly recognized by fresh application instances. Demo endpoints return 404/403. Readiness probe correctly distinguishes staging prerequisites.
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt01_private_startup_and_role_bootstrap`

### RT-02 — Operator Admission Fails Closed in Production (P0)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt02_operator_admission_fails_closed_in_production`
- **Observed:** Subprocess running with `CARTMATE_ENV=production` returned 403 on redemption and 403 when attempting protected outing actions with operator assurance marker. SafeHaven access rejected.
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt02_operator_admission_fails_closed_in_production`

### RT-03 — Activation Lifecycle, Concurrency, Partial State & Rate Limits (P0/P1)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt03_activation_lifecycle_and_recoverable_failures`
- **Observed:**
  - Concurrency: 2 threads competing for single token return `[200, 403]`. SQLite contains exactly 1 admission record.
  - Rate limiting: 6th attempt returns 429 with `Retry-After` header.
  - Fault injection: Session persistence failure returns 500, rolls back user and admission in SQLite (0 stranded accounts). Immediate retry with same token returns 200.
  - Same-account recovery: User logs out (200), old session returns 401. Single-use `CMREC-...` recovery token redeems and returns original `user_id`.
  - Transactional recovery rollback: Injected persistence failure during recovery rolls back code consumption, allowing same-code retry (200) without stranded accounts.
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt03_activation_lifecycle_and_recoverable_failures`, `test_rt15_recovery_persistence_failure_rollback_and_retry`

### RT-04 — Adult Gate, Challenge Binding and Emergency Exit (P0)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt04_adult_gate_and_challenge_invariants`
- **Observed:** Admitted user without adult attestation denied protected endpoints (403). Non-moderator attestation rejected (403). Challenge mismatch rejected (400). Valid attestation with challenge unlocks pings (200). Revocation re-locks user (403). Logout and safety endpoints remain accessible without adult attestation (200).
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt04_adult_gate_and_challenge_invariants`

### RT-05 — Membership Sessions and Cross-Object Isolation (P0)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k "test_rt05 or test_rt14"`
- **Observed:** Non-participant X cannot view trip PIN (403), join private chat, or access follow-up responses. Bidirectional blocking hides outings and suppresses messages. Session revocation closes open WebSockets with 1008 and validator hook blocks outbound frames to revoked sessions.
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt05_membership_sessions_and_cross_object_isolation`, `test_rt14_recovery_revoked_socket_disconnect_and_isolation`

### RT-06 — WebSocket Tickets, Origins and Frames (P0)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt06_websocket_tickets_origins_and_frames`
- **Observed:**
  - Single-use ticket verified. Reusing ticket returns 401.
  - Untrusted origin closed with 1008 policy code (no swallowed assertions).
  - Negative test double sensitivity probe verified 0 swallowed rejections.
  - Staging loopback origins permitted; production requires explicit HTTPS origins.
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt06_websocket_tickets_origins_and_frames`

### RT-07 — Built React Journey with Ordinary Members (P1)
- **Status:** PASS
- **Command:** `npm run test:operator-pilot` in `qa/`
- **Observed:** Both Host H and Companion C enter UI, redeem CMACT tokens, generate age challenge, receive adult attestation, click "Sprawdź ponownie", connect WebSocket live, Host creates outing in UI, Companion receives outing via WebSocket without reload, Companion joins in UI, Host accepts Companion in UI modal, and both navigate into Active Trip HUD without reload.
- **Evidence Location:** `qa/tests/operator-pilot.spec.ts` (Test 1)

### RT-08 — Mutual Plan, Rendezvous, PIN Handshake, Live Chat, Ledger, Completion & Cancellation (P1)
- **Status:** PASS
- **Command:** `npm run test:operator-pilot` in `qa/`
- **Observed:**
  - Mandatory plan editing: Host updates meeting terms to 50/50 in UI; both click "Akceptuję warunki spotkania ✓" -> "Plan zaakceptowany" verified on both screens.
  - Check-in & PIN: Host clicks "📍 Jestem na miejscu", UI reveals 4-digit PIN (`1046`). Companion enters PIN in UI -> "Wpisano zgodny PIN" verified on both screens.
  - Chat: Host sends message in UI, Companion receives live without reload; Companion replies in UI, Host receives live without reload; `chat.message` WebSocket frame verified.
  - Mandatory 50/50 Ledger: Host adds 40.00 zł item in UI -> verified on both Host and Companion screens with total split 40.00 zł and net settlement 20.00 zł.
  - Outing 1 Host Cancellation: Host cancels via UI modal -> Active Trip HUD clears on both screens without reload, cancellation banner displayed.
  - Outing 2 Companion Cancellation: Second outing created, joined, accepted, and Companion cancels via UI modal -> Active Trip HUD clears on both screens without reload.
  - Outing 3 Completion & Follow-up: Host defines plan, both accept, PIN handshake verified, Host finishes outing, Companion finishes outing. Idempotent complete verified (200). Host rates 5/5 and meet again -> Companion's view remains private (`is_mutual_buddy: false`). Companion rates 5/5 and meet again -> mutual buddy opt-in confirmed (`is_mutual_buddy: true`).
- **Evidence Location:** `qa/tests/operator-pilot.spec.ts` (Test 1, Test 3, Test 4)

### RT-09 — Disconnected Browsers, Cold Restart, Reconnection and Recovery (P1)
- **Status:** PASS
- **Command:** `npm run test:operator-pilot` in `qa/` (Test 5 & Test 6)
- **Observed:**
  - Browser reload & state convergence: Companion context page reload (`page.reload()`) cleanly re-authenticates, reconnects WebSocket, rehydrates Active Trip HUD, and verifies 0 duplicate chat messages.
  - Post-cancellation reload: When outing is cancelled by Host, Companion reload verifies cancelled outing does not reappear.
  - Actual backend stop/restart: Owned backend process stopped via `harness.stop_backend()`; browser offline-send failure observed (rejected promise); backend restarted against same DB; browser reconnects with fresh tickets and resubscribes; post-restart chat message sent and received without duplicate frames.
- **Evidence Location:** `qa/tests/operator-pilot.spec.ts` (Test 5 & Test 6)

### RT-10 — PII Shielding and No QA Leakage (P0)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt10_pii_shielding_and_no_qa_leakage`
- **Observed:** Shipped `backend/main.py` router contains zero `/_qa/*` routes. Public API responses shield phones, raw tokens, full DOB, and emergency contact markers. SOS is strictly direct-112.
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt10_pii_shielding_and_no_qa_leakage`

### RT-11 — Disaster Recovery Populated Operator Tables Drill & Booted API Denial (P1)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt11_disaster_recovery_populated_operator_tables`
- **Observed:** Populated snapshot equality passes; restored API returns 200 for active session, 401 for revoked REST access, 403 for admitted-but-not-adult user discovery, and correctly handles recovery/replay. Revoked session denied WS ticket (401) and revoked WS handshake denied (1008). Valid recovered session obtains ticket and connects to WS. Duplicate alias removed.
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt11_disaster_recovery_populated_operator_tables`

### RT-12 — Phone Usability, Focused Accessibility and Viewport (P1)
- **Status:** PASS
- **Command:** `npm run test:operator-pilot` in `qa/` (Test 7)
- **Observed:**
  - Viewports recorded: Desktop Chromium (`1280x720`) and Mobile Chrome (`393x851` Pixel 7).
  - 320px viewport responsive test: `scrollWidth <= clientWidth + 1` (zero horizontal overflow across root and modal elements).
  - Escape key dismisses AuthModal with verified focus restoration to the trigger button ("Zaloguj").
  - Form Tab traversal: keyboard Tab navigates sequentially through named controls (`#auth-act-token` -> `#auth-act-name` -> `button[type="submit"]`), and Shift+Tab wraps back to preceding input.
  - Physical assistive-technology (TalkBack/VoiceOver) testing preserved as H-05 BLOCKED / NOT RUN.
- **Evidence Location:** `qa/tests/operator-pilot.spec.ts` (Test 7)

### RT-13 — Runbook, Architecture and Evidence Agreement (P1)
- **Status:** PASS
- **Command:** Cross-document verification across `context/architecture.md`, `context/feature-specs/001-zero-cost-private-web-pilot.md`, `context/private-pilot-evidence.md`, `ops/PILOT_RUNBOOK_WINDOWS.md`, `GEMINI_HANDOFF.md`, `LAUNCH_READINESS.md`.
- **Observed:** All documentation synchronized with observed evidence: operator admission (`operator_in_person`), single-use recovery token (`CMREC-...`), transactional rollback, socket isolation on recovery, physical verification method (`physical_identity_document`), and truthful test counts (156 backend, 14 operator browser, 2 probes exit 0, H-01..H-06 NOT RUN).
- **Evidence Location:** `context/architecture.md`, `context/feature-specs/001-zero-cost-private-web-pilot.md`, `context/private-pilot-evidence.md`, `GEMINI_HANDOFF.md`, `LAUNCH_READINESS.md`

### RT-14 — Recovery Revoked Socket Disconnect and Frame Isolation (P0 Regression)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt14_recovery_revoked_socket_disconnect_and_isolation`
- **Observed:** Strict assertion `assert disconnected is True and close_code == 1008` (tautology removed). Verifies that redeeming recovery disconnects old WebSockets with code 1008 and that subsequent companion messages are not delivered to old connections.
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt14_recovery_revoked_socket_disconnect_and_isolation`

### RT-15 — Recovery Persistence Failure Rollback and Retry (P1 Regression)
- **Status:** PASS
- **Command:** `python -m pytest backend/test_private_pilot_review.py -k test_rt15_recovery_persistence_failure_rollback_and_retry`
- **Observed:** Verifies that synthetic failure during recovery session persistence rolls back token consumption atomically, leaving 0 stranded sessions and permitting same-code retry.
- **Evidence Location:** `backend/test_private_pilot_review.py::test_rt15_recovery_persistence_failure_rollback_and_retry`

---

## Human & Network Verification Matrix (H-01..H-06)

*The following checks cannot be signed off by automated test runners or AI agents. They remain honestly reported as BLOCKED or NOT RUN pending human rehearsal.*

| ID | Required Observation | Status | Owner | Required Human Procedure & Evidence |
| :--- | :--- | :---: | :--- | :--- |
| **H-01** | Two physical phones open built site over trusted private HTTPS | **BLOCKED / NOT RUN** | Founder | 2 physical smartphones (iOS/Android) connected to Tailscale private tailnet opening `https://<tailnet-node-name>`. Verify `/api` and `wss://` work over HTTPS without TLS warnings. App listens on loopback `127.0.0.1:8000` only. Non-tailnet devices cannot connect. |
| **H-02** | Named trusted operator conducts witnessed age checks | **BLOCKED / NOT RUN** | Trusted Operator | Operator inspects original physical identity document or performs live official mObywatel QR verification. Confirms 18+ legal age. Enters attestation via Operator Console or API. Document images/numbers must NEVER be stored or uploaded. |
| **H-03** | Both people complete UI journey on actual devices | **BLOCKED / NOT RUN** | 2 Adult Friends | Participants activate via UI on physical phones, confirm mutual plan terms, meet at rendezvous point (e.g., Silesia City Center), verbally exchange 4-digit PIN, verify handshake, and test clean low-guilt cancellation. |
| **H-04** | Protected backup copied off-device and restored offline | **BLOCKED / NOT RUN** | Founder | Offline backup script run, copy stored on encrypted external storage media, offline restore test executed against target machine. Verify reconciliation procedure for revoked tokens. |
| **H-05** | Real screen-reader/zoom review on physical phone | **BLOCKED / NOT RUN** | Human Reviewer | Test VoiceOver (iOS) and TalkBack (Android) on activation, 18+ pending, and trip HUD screens. Test 200% system font scaling and high contrast. |
| **H-06** | Staffed test window & founder go/no-go | **BLOCKED / NOT RUN** | Founder | Founder establishes bounded operational window (e.g. Saturday 14:00-18:00), active monitoring, emergency stop procedure, and issues explicit go/no-go decision. |

---

## Verified Source Fingerprints (SHA-256)

```text
backend/main.py                           7A3C3D1795EEAE8C59602E01C583EB9EBF9B37B44E726F33636346561DF7B1C6
backend/storage.py                        B42565692788F0A74CB2AB550C101199CE8245D2BBFF1975FE7F1D2895F08A2C
backend/websocket_manager.py              6CBEFF8D46BA32E7D2CA9629A5605A14766983E5F7329D895B113A0BFC786B48
backend/test_private_pilot_review.py      2589D0471CD3F44BAFD1305627544A0C2724CA27BD3FCEC56314F489831E02D8
frontend/src/api.ts                       6F2723266FEDB2D58DACF3D4E978168B6FAF106636FFB1D8740B5F8E09E3ECA2
frontend/src/realtime/socket.ts           F230AA8FA5D0143B03F5B5522415FFEF1DE9F981DCFB68FB1BA830DAD5E127BD
frontend/src/App.tsx                      70C239A636D63BF01AA7BF6E273CB76BA3249E5D71FEFAF5ABDE96DA00F04842
frontend/src/components/ActiveTripHUD.tsx 0F58A8CD596E41E83CB38EDF118B5928A07C606AF8688FE4ECB72423098AAE14
frontend/src/components/AuthModal.tsx     9ECDD3A32BD8EEA03A04DEAF700F9C23DEB5412C77884E062019E0CC136C6DB8
qa/tests/operator-pilot.spec.ts           80CE5E50BFD3799C2242B549828FBAC4CE9905560FDE99EEEB11189B2234A736
qa/operator_pilot_harness.py              E21B0E70AA997CD4D32FAEB0F9E1670BFA8D88494A344CED2E90AEA1248782DD
qa/codex_mr02_destination_probe.cjs       2E8728B48D5AB30394C65B95AA4CB1928D39915950EBD83CABAA578A77C2277C
qa/codex_mvp_config_probe.cjs             6362DCB5D80DAC08F5EA613B6EE29005CB1BD3BF5016E35A1806D133B930C981
qa/codex_mvp_reconnect_probe.cjs          6AD96C7B2B7504DD0DFBC1F700AA90FC241AACD7DFDB03AA8B44BACAE013B1FF
qa/codex_mvp_preflight_probe.py           BA2FEB7B5BD8DBB6493F6475D0307EAC3233C04C21B97578F654793FDF1277B0
qa/codex_private_pilot_probe.py           91A0BCCC1B874D8FA37F07BECFA0F5D90976E5108ECD3B407B2884A4212B9126
qa/codex_recovery_boundary_probe.py       A67D3D52DAA077FE40BBD17F6FF59BF379E64D9D586B3E2749F1207EA90A9BD5
qa/codex_ci_prerequisite_probe.py         C5023BAF3ED3217ABDCACB759ADC7A0512B285D2B2965A9D602CFA9F3B7E611D
qa/codex_origin_matrix_probe.cjs          934B62EBAEB9A6B02494669C721BF82E627DF7A1C7E3C225DA79221CBFDBF319
ops/pilot_preflight.py                    CD62E3DF116EBEE781BD16820CCC78897604710D1FCACDA7C8FFA1F07D46F91B
ops/test_pilot_preflight.py               015684147862E10AEAAF0B09783145E9394A19B77BABB8F67583681065EEA384
ops/PILOT_RUNBOOK_WINDOWS.md              CCC3B4E58D92EC884968DA9F54957A9C2CAA3450F0FEF6445DCB768DDAA68968
.github/workflows/ci.yml                  D20D286991918672A83B8D6F90A7A94B96739247602C33EA447A6A9FC57B1210
```

---

## Codex Red-Team Acceptance Handback (MR2-01 & MR2-02 Remediation)

- **Application Diff:** Zero production bypasses; zero test helper routes in shipped backend. CI workflow orders Node and frontend dependency installation before backend compilation/tests. Web helper same-origin validation uses exact URL parser comparison against base origin, rejecting userinfo and slash-backslash destinations (`/\\...`). Scenario 6 added to permanent RT-17 regression test in `backend/test_private_pilot_review.py`.
- **Automated Evidence:**
  - 158/158 backend tests passing (`backend/` + `ops/test_disaster_recovery.py` in 40.31s with `JEV_MODE=shadow`).
  - 13/13 review adversarial suite passing (`backend/test_private_pilot_review.py` in 14.03s; RT-00..RT-11, RT-14..RT-17; includes RT-17 Scenario 6).
  - 12/12 operations preflight tests passing (`ops/test_pilot_preflight.py` in 1.52s).
  - 16/16 Playwright operator pilot tests passing across Desktop Chromium and Mobile Chrome (1.5m).
  - 8/8 diagnostic probes passing (exit 0): `codex_ci_prerequisite_probe.py`, `codex_origin_matrix_probe.cjs`, `codex_mr02_destination_probe.cjs`, `codex_mvp_config_probe.cjs`, `codex_mvp_reconnect_probe.cjs`, `codex_mvp_preflight_probe.py`, `codex_private_pilot_probe.py`, `codex_recovery_boundary_probe.py`.
  - 2/2 frontend checks passing (`oxlint` 0 errors/warnings in 100ms, `tsc -b && vite build` clean in 714ms).
- **Current handback status:** Unblocked engineering is complete and verified green. Ready for Codex independent retest. Real databases and untracked files preserved. H-01..H-06 remain strictly BLOCKED / NOT RUN pending human/physical-device execution.

