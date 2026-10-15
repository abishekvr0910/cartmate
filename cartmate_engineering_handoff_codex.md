# CartMate Polska — Engineering Handoff Codex & Safety Architecture

> **Historical engineering handoff, 2026-10-01:** Current execution is the zero-cost private website pilot described in `GEMINI_HANDOFF.md` and `context/feature-specs/001-zero-cost-private-web-pilot.md`. Older test counts, Render/SMS assumptions and statements about no Git metadata below are superseded. `LAUNCH_READINESS.md` is the release board.

> **Current completion backlog (2026-09-29):** [NEXT_MODEL_EXECUTION_PLAN.md](NEXT_MODEL_EXECUTION_PLAN.md) records new reproduced defects and the ordered work for the next model. Green local suites do not cover the discovered Jev audit/follow-up disclosures, group-blocking/region bypasses or Profile/report contract failures. Those findings remain open. Follow [LAUNCH_READINESS.md](LAUNCH_READINESS.md) for release status.

> **Repository Root:** `S:\APPs\cartmate`  
> **Backend:** `S:\APPs\cartmate\backend` (FastAPI, Python 3.11, SQLite WAL, WebSockets)  
> **Frontend:** `S:\APPs\cartmate\frontend` (React 19, TypeScript, Vite 8, Tailwind CSS, MapLibre GL)  
> **Mobile Packaging:** `S:\APPs\cartmate\frontend\capacitor.config.ts` (Capacitor 8)  
> **Quality Assurance:** `S:\APPs\cartmate\qa` (Playwright E2E across Desktop Chromium & Mobile Chrome)  
> **Disaster Recovery:** `S:\APPs\cartmate\ops` (Online SQLite WAL backups & deterministic restore)  
> **Initial Launch Market:** Silesia (Śląsk), Poland — Hub: Katowice & GZM Metropolia  
> **Current status (2026-09-29):** 108/108 backend tests, frontend build/lint, 32/32 development plus 4/4 no-demo staging-style browser cases pass locally. Six-digit durable OTP challenges/abuse budgets, post-block contact redaction, optional/neutral review and meet-again choices, and trip-dialog keyboard focus are implemented. The 2/2 sample-schema recovery mechanics drill passes locally but does not cover every real table or hosted recovery. Hosted staging, carrier SMS, independent reviews, and launch gates remain open. Historical sections below retain older sprint snapshots; use `LAUNCH_READINESS.md` and `GEMINI_HANDOFF.md` for current evidence.  

---

## 1. Executive Summary & Verification Matrix

The implemented core has local automated evidence, but launch-readiness and some proposed integrations remain open:

| Domain | Invariants Enforced | Automated Verification |
| :--- | :--- | :---: |
| **Backend & Security** | Server-enforced authorization, token revocation, single-use WebSocket tickets, active-socket closure on revocation, bidirectional blocking, coarsened coordinates, pre-send PII scrubbing, PIN attempt limits, durable six-digit OTP challenges/abuse budgets, durable join requests, atomic host acceptance, minimized city events, outsider object-denial checks, and hashed one-use pilot invites. | **108/108 local Pytest cases passed** |
| **Browser E2E Journeys** | Playwright covers OTP login, session revocation, radar, plan HUD, cancellation, truthful direct-112 SOS, moderator queue, trip-dialog ARIA/focus/neutral-choice checks, and live two-party plan/chat/PIN/ledger/SOS interactions. The separate no-demo, capture-only OTP suite proves ordinary publishing, second-account discovery, PII shielding, women-only denial, and one-use invite registration against a production React bundle. | **32/32 development + 4/4 no-demo cases passed locally** across Desktop Chromium & Pixel 7 Mobile. |
| **Disaster Recovery** | SQLite WAL-compatible online snapshotting via `conn.backup()`, SHA-256 manifests, integrity verification, pre-restore rollback snapshot. The sample drill is not an encrypted offsite production restore. | **2/2 sample drill tests pass** |
| **Frontend Production Build** | TypeScript compilation (`tsc -b`), Vite 8 bundler, MapLibre GL chunking, oxlint linter across 23 components. `capacitor.config.ts` included in `tsconfig.node.json` type-check. | **`tsc -b` passes; `oxlint` 0 errors, 0 warnings.** Vite emits standard chunk size warning for `maplibre-gl` (>500 kB). |
| **Mobile App Native Packaging** | Capacitor 8 starter configuration with `appId: 'pl.cartmate.app'`, `appName: 'CartMate'`, and `webDir: 'dist'`. `bundledWebRuntime` removed to fix typecheck. Native projects (`ios/`, `android/`) are **not yet generated**; native relative API URL strategy needed. | **Starter Config Verified via `tsc -b`** (No native projects or store approval yet) |
| **Open-Source Architectural Patterns** | MapLibre GL opt-in map with Silesia POIs (OpenFreeMap vector tiles); Spliit-style 50/50 decimal math ledger with manual BLIK contact copy; Discourse-inspired FIFO human moderation queue. Overpass dynamic POIs, 1-tap automated BLIK rails, and Jev arbitration remain **proposals / not implemented**. | **Fully Grounded in Code** |
| **Staging & Launch Gates** | Multi-stage Docker container serving React + FastAPI + WebSockets on one HTTPS/WSS origin, staging phone allowlist (`CARTMATE_STAGING_ALLOWED_PHONES`), direct 112 calling fallback, missing gateway 503 response. Hosted Render rehearsal, carrier SMSAPI test, named human moderation, age policy, and privacy/accessibility review remain **open release blockers** in `LAUNCH_READINESS.md`. ID-only features stay disabled rather than blocking ordinary outings. | **Local Contract Smoke Tests Passed; Hosted Gates Open** |

---

## 2. Gemini Engineering Contributions & Sync Notes for Codex

During this sprint, Gemini completed the following tasks in `qa/`, `backend/`, and `frontend/`:

### 1. Multi-User Browser Automation Suite (`qa/tests/multi-user-trip.spec.ts`)
* **Dynamic API Path & No Hardcoded Ports:** Removed hardcoded `http://127.0.0.1:8000`. Test now uses relative `/api/testing/reset-seeded-trip` resolving against Playwright's `baseURL`, eliminating port collision hazards.
* **Expanded Full Multi-User Journey:** Expanded test coverage simulating **Host Jakub** and **Companion Zuzanna** concurrently across independent browser contexts:
  1. **Plan Terms Inspection:** Both participants view agreed plan terms at *Makro Cash & Carry Katowice* under a 50/50 split policy (200 PLN ceiling). Host sees status waiting for companion confirmation.
  2. **Mutual Plan Acceptance:** Companion accepts terms via `POST /api/trips/trip_makro_01/accept-plan`, satisfying the mutual agreement invariant.
  3. **Host Check-in:** Host performs in-store check-in (`POST /api/trips/trip_makro_01/checkin`).
  4. **In-App Coordination Chat:** Browser journey sends messages and checks persistence after reload. A separate backend test verifies that a subscribed companion receives a WebSocket event without reload; zero-refresh browser delivery is not yet asserted.
  5. **Dual PIN Rendezvous Handshake:** Host inspects a per-trip generated 4-digit PIN. Companion attempts an invalid PIN and receives a rejection, then enters the host's actual code; no static PIN is used.
  6. **50/50 Ledger Calculation & Item Addition:** Host adds a grocery item (`Kawa ziarnista Lavazza 1kg` for 50.00 PLN). Total split updates to 189.90 zł ($139.90 + 50.00$), and Companion's calculated share updates to 94.95 zł.
  7. **Contact Number Copy for BLIK:** Companion clicks the copy button to copy Jakub's contact number; receives clear toast feedback advising manual transfer in their banking app.
* Runs and passes on both **Chromium Desktop** and **Mobile Chrome (Pixel 7)** (`32/32 development + 4/4 no-demo passed`).

### 2. Backend Enhancements
* **Reset Endpoint for Test Isolation (`backend/main.py`):** Added `POST /api/testing/reset-seeded-trip`, strictly gated behind `if is_production(): raise HTTPException(403)`. Completely resets `trip_makro_01` (plan acceptance, check-in, rendezvous, split items, and chat messages) between E2E runs.
* **Phone Number Exposure on Mutual Acceptance (`backend/main.py:136`):** In `build_trip_response`, when both `host_accepted` and `companion_accepted` are true, hydrates `resp.host.phone` and `resp.companion.phone` from `database.USERS` so `settlementCreditor.phone` is never null for manual BLIK transfer.
* **Seeded Chat Room Hydration (`backend/database.py`):** Seeded `chat_room_id="chat_trip_makro_01"` on `trip_makro_01` and added initial room messages; updated `hydrate_from_storage()` to safely preserve trip chat rooms across local runs.
* **Bilingual PIN Error Messaging (`backend/main.py:1824`):** Updated PIN error detail to `f"Nieprawidłowy kod PIN. Incorrect PIN. Attempts remaining: {trip.pin_attempts_left}."` satisfying Polish UI localized assertions and backwards compatibility.

### 3. Capacitor Mobile Native Configuration (`frontend/`)
* **Fixed Typecheck Failure:** Removed unsupported `bundledWebRuntime: false` from [`frontend/capacitor.config.ts`](frontend/capacitor.config.ts) (incompatible with Capacitor 8).
* **Strict Build Verification:** Added `"capacitor.config.ts"` to `frontend/tsconfig.node.json` `"include"` array so `npm run build` (`tsc -b && vite build`) validates the config on every build.
* **Current Status & Honest Limitations:**
  - This is a **starter configuration only**. Native platform folders (`android/`, `ios/`) have **not** been generated yet (`npx cap add ios` / `npx cap add android` have not been executed).
  - The web application currently relies on relative API URLs (`/api/...`). When running natively on Android/iOS outside of Vite/Render reverse proxy, a mobile base URL configuration strategy (e.g. `VITE_API_URL` or Capacitor HTTP plugin) is required.
  - Repackaging React alone does not guarantee store approval. Recheck current official store requirements before any native submission; native packaging is not on the closed web-pilot critical path.

### 4. Git & Workspace Hygiene
* Hardened [`.gitignore`](.gitignore) and [`.dockerignore`](.dockerignore) to protect against accidental commits of local databases (`*.db`, `*.db-wal`, `*.db-shm`), `venv/`, `__pycache__`, `dist/`, `test-results/`, and `.pytest-run-*`.
* Cleaned up test artifacts and maintained zero untracked runtime cruft.

---

## 3. Social & Safety Invariants Architecture

### 1. Specific Plans & Mutual Acceptance
* Accepted outings convert to explicit `PlanDetailsSchema`:
  * `what`: Purpose (e.g. "Wspólne zakupy hurtowe Makro Katowice")
  * `when`: Timeframe (e.g. "Dzisiaj, 18:30")
  * `estimated_duration_minutes`: Bounded time commitment (15–240 min)
  * `cost_policy`: Financial clarity (`split_strictly_50_50`, `buyer_pays_own`, `host_treats`, `companion_treats`, `no_purchase_browse_only`)
  * `estimated_cost_pln`: Agreed budget ceiling
* **Mutual Acceptance Invariant:** Both host and companion must confirm agreement. Check-in and PIN verification fail closed (HTTP 400) until both accept.

### 2. Decimal-Safe 50/50 Settlement (Spliit Architecture)
* Work in Python `Decimal` / whole grosze to eliminate IEEE-754 floating point rounding drift.
* Net balance calculation between host and companion.
* **Truth in Disclosures:** Copying the contact number is for manual peer-to-peer BLIK phone transfer in the user's banking app. CartMate does not connect directly to banking payment rails.

### 3. Dual-Handshake Physical Rendezvous (PIN)
* Host receives 4-digit code to verbally disclose upon meeting.
* Companion enters code into app to verify physical presence.
* Max 5 attempts before locking out the trip (rate-limited fail closed).
* Disclosures clearly state that PIN verifies code knowledge, not background GPS tracking.

### 4. Human Moderation Queue (Discourse Model)
* Reports are routed to `GET /api/moderation/queue` in FIFO (oldest-first) order.
* Server enforces non-empty moderator notes before resolution.
* Double-action conflict protection returns HTTP 409.
* Suspending or banning immediately revokes all active session tokens.

### 5. Truthful Safety Disclosures & Direct 112 Fallback
* Deployed environments hard-disable SMS SOS dispatch (`SOS_PROVIDER=disabled`).
* Emergency actions route directly to native emergency call fallback (`tel:112`).
* Zero false claims regarding automated police dispatch or background location surveillance.

---

## 4. Verification Commands for Codex

**Local verification on this machine** (this Windows checkout):
- Use `C:/Users/moham/AppData/Local/hermes/hermes-agent/venv/Scripts/python` as the interpreter.
- Always set `CARTMATE_DATABASE_PATH` to a fresh temp file for test/e2e runs (cross-link `qa/README.md` as the authoritative run book).
- Verify ports 8000/5280 are free and the responding pid is yours before browser suites (stale-server hazard, documented in `qa/README.md`).
- Full verification commands cross-reference `qa/README.md` for run books.

Codex can reproduce the full verification suite using these commands:

```powershell
# 1. Backend Pytest Suite (116 passed + 2 skipped at current verification:
#    108 original + 8 E01 completion regressions in test_completion_regressions.py)
cd S:\APPs\cartmate\backend
python -m pytest -q

# 2. Disaster Recovery Verification Drill
cd S:\APPs\cartmate\ops
python test_disaster_recovery.py

# 3. Frontend Production Build & Lint
cd S:\APPs\cartmate\frontend
cmd /c "npm run build && npm run lint"

# 4. Existing Playwright browser suite (32/32 development + 4/4 no-demo at current verification)
# Prerequisite: Backend running on 127.0.0.1:8000 (with CARTMATE_MODERATOR_USER_IDS=usr_zuzanna)
#               Frontend running on http://127.0.0.1:5280
cd S:\APPs\cartmate\qa
cmd /c "set CARTMATE_E2E_ISOLATED=1&& npx playwright test"

# 5. Separate no-demo staging-style journey (4/4 at latest local snapshot)
cd S:\APPs\cartmate\qa
npm run test:no-demo
```

---

## 5. Next Steps & Explicit Release Gates

1. **Hard Launch Gates (Cannot Be Bypassed by Code):**
   - **Hosted Render Rehearsal:** Deploy single-instance web service with persistent disk in Render Frankfurt using `render.yaml` and `Dockerfile`. Verify same-origin serving and liveness.
   - **Real Carrier SMS OTP Verification:** Configure `SMSAPI_API_TOKEN` and `SMSAPI_SENDER` privately and execute `staging/otp_rehearsal.py` with an approved Polish test handset.
   - **Publishing Trust Policy (approved):** Silesia-first closed pilot. An account with persisted SMS OTP phone provenance may publish an ordinary outing, even at Bronze tier; this does not claim identity verification. Women-only/SafeHaven outings remain unavailable without genuine external ID verification. `/api/ready` reports this limited scope and still requires operational configuration; it is not public launch approval.
   - **Named Human Moderation Coverage:** Assign accountable human moderators to monitor `GET /api/moderation/queue`. AI agents cannot legally or ethically serve as emergency or safety moderators.
2. **Private Repository and Hosted CI:**
   Establish a private Git repository and run the existing CI workflow in the host; this checkout still lacks Git metadata and no hosted CI pass has been observed.
3. **Mobile Native Packaging Path:**
   - Define runtime API base URL strategy for native apps (e.g. `VITE_API_URL` or Capacitor HTTP plugin) since native apps do not run behind the web server reverse proxy.
   - Run `npx cap add ios` and `npx cap add android` in `frontend/` to generate platform-specific native projects.
   - Prepare native device features to satisfy Apple App Store Guideline 4.2 (Minimum Functionality).
   - Fulfill Google Play closed-testing requirement (14 days with 12 opt-in testers) before submitting for production release.
4. **Proposed Features Boundary (Not Implemented):**
   - Dynamic Overpass API POIs, automated 1-tap BLIK payment rails, and autonomous Jev arbitration remain **future proposals / not implemented**.
   - Keep user-facing documentation and UI strictly grounded in verified features.

## 6. Gemini QA handoff (2026-09-28)

[`GEMINI_HANDOFF.md`](GEMINI_HANDOFF.md) is the current, scoped assignment. Its first task is an isolated **no-demo Silesia publisher browser journey** proving SMS-authenticated Bronze publishing, second-account discovery, PII shielding, and women-only denial against the built React bundle with staging-like backend guards. It must not use a real SMS gateway or expose OTPs through API responses. After that, prove zero-refresh WebSocket chat and restart recovery in separate claims. The existing 24-case demo-session browser suite passed locally, but it does not prove this deployed policy. Hosted carrier delivery, independent accessibility review, and human release decisions remain open.
