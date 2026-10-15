# CartMate local browser smoke tests

**2026-10-14 activity-first verification (42/42 full development passed):** The development Playwright suite was re-executed and verified 42/42 cases passed (Desktop Chromium + Pixel 7 emulation) against a fresh disposable server configured with `CARTMATE_MODERATOR_USER_IDS=usr_zuzanna`, `SOS_PROVIDER=disabled`, and loopback Vite dev client on port 5280. Tests confirm study/fitness/walk/food/social outing creation/discovery, two-person mutual plan coordination, active-trip PIN handshake, live chat, 50/50 balance calculation, cross-tab quiet cues, cancellation, SOS 112 guidance, moderator triage, and accessibility reflow at 320px without horizontal overflow. Run the development suite on a **new disposable database for each full run** (`disposable_dev_e2e.db`), as it consumes single-use rate limits and mutates session state. This is automated browser evidence, not a physical-device or complete WCAG 2.2 AA certification. The isolated operator suite (`operator-pilot.spec.ts`) passed 16/16 and no-demo (`no-demo-publishing.spec.ts`) passed 4/4 against the production bundle.

**Current independent operator-pilot retest (2026-10-13):** 16 operator browser cases pass (desktop Chromium + Pixel 7 emulation). See [Codex verification](CODEX_MR2_VERIFICATION.md) for commands, original MR2-01/02 closure and the P3 parser-unavailable cleanup. Backend RT-17 requires installed frontend TypeScript dependencies before pytest; a fresh offline install + RT-17 passed. Older development/no-demo evidence below was not rerun. No physical handset or WCAG conformance claim is supported by the browser suite.

**2026-09-30 group slice:** 40/40 development browser cases and 4/4 isolated no-demo cases pass locally. The new desktop/mobile group test proves a vote cannot read chat, explicit join permits chat, a sender-bound group-message report succeeds, and leaving revokes access. A separate 320px dialog test checks spot/group names, labels, focus containment and Escape restoration. The full suite was run against a WebSocket-capable Python interpreter (the local `backend/venv` lacks `websockets` despite the pinned deployment requirements). See `PRE_PILOT_REVIEW.md` for open manual/independent accessibility and security checks and `USABILITY_REHEARSAL.md` for human-session tasks. Previous test counts below are historical.

**2026-09-30 update:** 36/36 development and 4/4 isolated no-demo desktop/mobile cases pass on the current tree. New development cases cover populated blocked-user Profile and “other devices” session preservation; the no-demo journey checks empty-avatar vote ownership. The no-demo harness first asserts that SMS-confirmed accounts are denied live access without 18+ proof, then uses a `qa/`-only local age-proof adapter to test the remaining outing journey. That adapter is not in the shipped backend and does not represent a reviewed real provider. Do not run or expose `staging_harness.py` on a shared host. The deployed source trusts no age provider and remains closed.

This standalone Playwright suite keeps its dependencies in `qa/`. It uses development-only demo tokens, so it must run only against a dedicated local test database, never staging or production.

**Integration review (2026-09-29):** 32/32 desktop/mobile test cases pass on an isolated local app. Tests cover OTP login and server-side logout revocation; seeded radar and plan-term display; six cancellation reasons and modal dismissal; SOS consent/112 UI; moderator access, FIFO triage, decision note enforcement, and report resolution; dialog ARIA attributes, labeled auth/publisher/trip fields, trip-dialog focus containment/Escape restoration, neutral meet-again default, and navigation labels; plus concurrent two-party mutual coordination, fail-closed 4-digit PIN verification, and 50/50 balance settlement (`tests/multi-user-trip.spec.ts`). The two-party test captures actual WebSocket frames and verifies no-refresh plan acceptance, chat, check-in/PIN handshake, shared-item balance, cancellation, and SOS updates on both device profiles. Browser CI sets `SOS_PROVIDER=disabled`, so these tests never dispatch SOS SMS.

The separate no-demo staging-style suite passes 4/4 desktop/mobile cases against the built production React bundle. It starts its own loopback FastAPI harness with an ephemeral SQLite database and capture-only OTP adapter, tests ordinary publishing and second-account discovery plus server-enforced one-use invite registration/replay denial, and never sends a real SMS. Run it after `npm run build` in `frontend/` with `npm run test:no-demo` in `qa/`. The default `npm test` intentionally excludes this spec because it runs against a separate staging-like harness. CI runs both suites. Passing these local suites does not prove carrier delivery, hosted Render configuration, server-restart browser recovery, or full accessibility.

## Run locally

Install dependencies once from `qa/`:

```powershell
npm ci
npx playwright install chromium
```

Start the backend with a **new, disposable** database and the test moderator configured. In PowerShell:

```powershell
$env:CARTMATE_ENV='development'
$env:CARTMATE_DATABASE_PATH='S:\APPs\cartmate\qa\your_unique_disposable_e2e.db'
$env:CARTMATE_MODERATOR_USER_IDS='usr_zuzanna'
$env:OTP_PROVIDER='console'
$env:SOS_PROVIDER='disabled'
cd S:\APPs\cartmate\backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

In a second terminal, run `npm run dev -- --host 127.0.0.1` from `frontend/` (port 5280). In a third terminal, run:

```powershell
cd S:\APPs\cartmate\qa
$env:CARTMATE_BASE_URL='http://127.0.0.1:5280'
$env:CARTMATE_E2E_ISOLATED='1'
npm test
```

The configuration refuses non-loopback URLs or runs without the explicit isolated-database acknowledgement. This suite does not start or reset its own database; the operator must ensure the path is genuinely disposable. Its browser assertions should be extended with dedicated fixtures before CI or staging use.

## Operator Pilot Staging Suite (Slice D & M01 Acceptance)

The isolated operator pilot suite (`qa/tests/operator-pilot.spec.ts`) tests the full no-SMS friend pilot journey against the production built React bundle and a dedicated disposable FastAPI harness (`qa/operator_pilot_harness.py`).

It exercises 7 distinct scenarios across Desktop Chromium and Mobile Chrome (14 total test instances):
1. **Full Journey:** Operator admission, witnessed 18+ attestation, outing creation, discovery, join, mutual plan terms, PIN handshake, live bidirectional chat, 50/50 ledger (40.00 zł / 20.00 zł settlement), and host cancellation.
2. **Account Recovery (CR-01):** Operator token recovery restores same account ID after session logout or storage loss.
3. **Low-Guilt Cancellation (R2-03):** Second outing creation, join, and companion-initiated cancellation with immediate real-time UI reset and cancellation banner.
4. **Mutual Completion & Follow-up (RT-08):** Third outing mutual plan agreement, PIN handshake, completion, idempotent complete, and private review submissions keeping follow-up confidential until mutual opt-in (`is_mutual_buddy`).
5. **Reload/Rehydration (RT-09 reload):** Active Trip HUD rehydrates upon browser reload, pre-reload chat persists without duplicates, and post-cancellation reload confirms cancelled trips do not resurrect.
6. **Backend Process Restart & Offline Failure (RT-09 restart):** Offline send rejection, harness process stop/restart against the exact same database, fresh-ticket WebSocket reconnect and resubscription, post-restart messaging, and non-resurrection of cancelled trips across cold restarts.
7. **Focused Accessibility (RT-12):** Modal Escape key dismissal with focus restoration to trigger ("Zaloguj"), sequential keyboard Tab traversal through named controls (`#auth-act-token` -> `#auth-act-name` -> submit), Shift+Tab wraparound, and 320px responsive viewport layout (zero horizontal overflow).

Run after building the frontend (`npm run build` in `frontend/`):

```powershell
cd S:\APPs\cartmate\qa
npm run test:operator-pilot
```

Runs on Desktop Chromium and Mobile Chrome (Pixel 7 emulation). Uses an isolated disposable database and never accesses `cartmate.db` or `pilot_live.db`.

## Independent Diagnostic Probes

Two standalone diagnostic probes verify recovery security boundaries and environment invariants without touching production state:

```powershell
# From repository root:
python qa/codex_private_pilot_probe.py
python qa/codex_recovery_boundary_probe.py
```

Both probes run in isolated subprocesses against temporary SQLite databases and must exit 0.
