# CODEX FIX HANDOFF — Post-Review Remediation Ticket (2026-09-29)

> **STATUS UPDATE (2026-09-29, later — Hermes post-verification):** OpenCode executed P0-1, P0-3, P1, P2-3; the P0-2 CI smoke step it wrote had two defects and was corrected and re-verified by Hermes. All acceptance criteria now pass. See "Verification record" at the end. The ticket body below is kept as the original spec; treat the status table as authoritative.

**Item status:**

| Item | Applied by | State | Verification |
| :--- | :--- | :--- | :--- |
| P0-1 websockets dependency | OpenCode | DONE | Clean-venv `pip install -r backend/requirements.txt` → `websockets` 17.1 importable (via `uvicorn[standard]==0.41.0`); local server serves WS upgrades (`[accepted]` in logs) |
| P0-2 CI image smoke test | OpenCode (defective) → **corrected by Hermes** | DONE | Container env now includes `CARTMATE_STAGING_ALLOWED_PHONES` (staging boots fail-closed without it); WS assertion rewritten to expect **HTTP 403 on an invalid ticket** (empirically: 403 = WS layer alive and correctly rejecting; 404 = no WS library = P0-1 regression). YAML re-parsed OK, heredoc intact |
| P0-3 host_checked_in symmetry | OpenCode | DONE | `test_security_baseline.py` 18/18 and full suite **108/108 against the live `backend/cartmate.db`** (previously 400-vs-429 failure), and 108/108 on fresh disposable DB |
| P1-1/P1-2 docs | OpenCode | DONE | §4 now documents the Hermes-venv interpreter, disposable-DB discipline, port ownership, and carries current counts (108/108, 32/32, 4/4, 2/2) |
| P2-3 ops cleanup | OpenCode | DONE | Scratch dirs removed; DR drill re-run: **2/2 pass** |

**Post-fix full-matrix re-verification (Hermes, on the fixed tree):** 108/108 backend (live DB and fresh DB), 32/32 dev browser, 4/4 no-demo browser, DR 2/2, YAML parses, clean-venv websockets import passes. No gate in LAUNCH_READINESS.md was relaxed; hosted CI/Render/SMS remain unexercised.

**Original acceptance criteria status:** all P0 criteria met after correction. OpenCode's P0-2 as first written would have failed CI twice over even with healthy code: (1) the container would crash on boot — staging mode requires `CARTMATE_STAGING_ALLOWED_PHONES` (config.py line 159 raises RuntimeError without it) and OpenCode's env omitted it; (2) the WS assertion expected a successful frame after connecting with a bogus ticket, but the server correctly closes invalid-ticket sockets before accepting — `ws.recv()` would raise `ConnectionClosed` on every run. Corrected assertion and rationale documented in the workflow file itself.

**From:** Hermes (independent post-review verification, 2026-09-29)
**Owner:** Codex (production application code, backend/security, shared dependencies, CI, final integration)
**Status board:** [LAUNCH_READINESS.md](LAUNCH_READINESS.md) — source of truth. This ticket does not override or relax any release gate.
**Related:** [GEMINI_HANDOFF.md](GEMINI_HANDOFF.md) § "Local environment pitfalls", [cartmate_engineering_handoff_codex.md](cartmate_engineering_handoff_codex.md), [PRODUCT_NARRATIVE_AND_ROLLOUT.md](PRODUCT_NARRATIVE_AND_ROLLOUT.md)

---

## 0. Context — where this came from

An independent post-cutoff verification of the 2026-09-29 tree was run by Hermes after the prior session ended mid-turn. Results on the current tree:

- Backend pytest: **108/108 pass** on a fresh disposable DB (`CARTMATE_DATABASE_PATH` set to a new temp file).
- Frontend: `npm run lint` clean, `npm run build` passes (known maplibre-gl chunk-size warning only).
- Browser suite: **32/32** (desktop + mobile) with the correct interpreter and fresh ports.
- No-demo production-bundle suite: **4/4**.
- The 14:11 Silesia read/subscription boundary edit in `backend/main.py` is intact and coherent (production restricts region/scope checks to the active Silesia region; development keeps the multi-region registry for tests).

One deploy-blocking defect and several hygiene items were found. Items are ordered: **P0 first (blocks hosted rehearsal), then P1 (correctness/hygiene), then P2 (non-blocking).**

**Local verification environment (this Windows checkout).** `backend/venv` is incomplete — it lacks `pytest` and `websockets`. The working local interpreter is the Hermes agent venv:

```
C:/Users/moham/AppData/Local/hermes/hermes-agent/venv/Scripts/python
```

It has pytest, httpx, websockets, fastapi, uvicorn, sqlalchemy. On CI, `actions/setup-python` + `requirements.txt` builds the environment, so CI is unaffected by the local venv issue. Full details in [GEMINI_HANDOFF.md](GEMINI_HANDOFF.md) § "Local environment pitfalls".

---

## P0-1. `requirements.txt` is missing the WebSocket library — DEPLOY BLOCKER

**Problem.** `backend/requirements.txt` pins:

```
uvicorn==0.41.0
```

uvicorn without `websockets` or `wsproto` installed cannot serve WebSocket upgrades. Verified in a **fresh clean venv**: `pip install -r backend/requirements.txt` → `import websockets` → `ModuleNotFoundError`. Under that environment uvicorn logs `"No supported WebSocket library detected"` and every `/ws?ticket=...` upgrade returns **404**.

**Impact.** The Docker image (`Dockerfile` installs from `requirements.txt`) and therefore the Render staging deployment would build green but have a **completely dead realtime layer** — no live chat, no trip updates, no zero-refresh coordination. The current CI workflow builds the image but never exercises a WebSocket against it, so hosted CI would pass while staging is broken.

**Fix (choose one; both verified compatible in this environment):**

Option A (preferred, minimal):

```
uvicorn[standard]==0.41.0
```

Option B (explicit pin):

```
uvicorn==0.41.0
websockets==15.0.1
```

`websockets==15.0.1` is the exact version proven working here with uvicorn 0.41.0 under the full 32/32 browser suite with WS frame assertions.

**Also required — a WebSocket regression guard** (pick either, both valid):

1. Backend pytest: a test that exercises a WebSocket handshake through `starlette.testclient`'s WebSocketTestSession (TestClient supports `client.websocket_connect(...)`), driving `/ws` with a valid ws-ticket and asserting the connection is accepted rather than 404/rejected.
2. CI-only (stronger): after `docker build`, run the image and assert a real WS upgrade against it (see P0-2). If TestClient WS proves flaky on this stack, the CI smoke test alone satisfies the guard.

**Acceptance criteria:**
- Fresh `pip install -r backend/requirements.txt` in a clean venv has importable `websockets`.
- CI (or backend tests) fails if the served artifact cannot complete a WS upgrade.
- Existing 108/108 backend + 32/32 browser suites still pass after the change.

---

## P0-2. CI never tests the artifact it ships — add a smoke test against the built Docker image

**Problem.** The last CI step is `docker build --file Dockerfile --tag cartmate-staging-ci .` — build only. Nothing verifies the container actually serves the app, the React bundle, or a WebSocket.

**Fix.** Extend `.github/workflows/ci.yml` after the build step. Sketch (adjust env to what `config.py` requires for staging startup; the deployed-mode guard fails closed on missing config, so boot the image with the minimal staging set minus secrets — see `render.yaml` lines 17–41 and `staging/RENDER.md`):

```yaml
      - name: Smoke-test the built image (REST + WS)
        run: |
          set -euo pipefail
          docker run -d --name cartmate-smoke -p 127.0.0.1:8901:10000 \
            -e PORT=10000 \
            -e CARTMATE_ENV=staging \
            -e CARTMATE_DEPLOYMENT=1 \
            -e SOS_WEBHOOK_SECRET=ci-smoke-secret-not-for-prod \
            -e CARTMATE_DATABASE_PATH=/tmp/cartmate-smoke.db \
            -e OTP_PROVIDER=console \
            cartmate-staging-ci
          trap 'docker rm -f cartmate-smoke >/dev/null 2>&1 || true' EXIT
          for i in $(seq 1 30); do
            if curl --fail --silent --output /dev/null http://127.0.0.1:8901/api/health; then break; fi
            sleep 1
          done
          curl --fail --silent --output /dev/null http://127.0.0.1:8901/api/health
```

Then the WS assertion: from a small Python script using the `websockets` library (available in the CI Python env after the backend steps), obtain a ws-ticket via the API (authenticated request), connect to `ws://127.0.0.1:8901/ws?ticket=...`, and assert the connection stays open; fail the step on 404/upgrade rejection or timeout. Keep it minimal: health-check + one authenticated WS upgrade. If the staging boot guard blocks startup with a minimal env, boot with the full minimal set from `render.yaml` (all non-secret keys) — do NOT add real credentials to CI.

**Acceptance criteria:** CI fails if the image serves REST but rejects WS (today's exact latent failure mode), or fails the health endpoint. The step must fail closed on timeout.

---

## P0-3. `conftest.py`/`database.py` reload asymmetry — the `host_checked_in` trap

**Problem.** The autouse fixture `test_environment_reset` in `backend/conftest.py` resets `trip_makro_01` fields: `host_accepted`, `companion_accepted`, `status`, `pin_attempts_left`, `rendezvous_verified`, `sos_triggered` — but **not** `host_checked_in`. The `database.py` non-production reload block (around line 741) resets `pin_attempts_left`, `rendezvous_verified`, `status` for `trip_makro_01` — but again **not** `host_checked_in`.

The preserved live `backend/cartmate.db` row has `host_checked_in=false` persisted. When the suite runs against that file, `test_security_baseline.py::test_pin_verification_rate_limiting` fails (`assert 400 == 429`) — the five "failed" attempts all hit the host-check-in precondition 400 instead of decrementing the PIN budget.

**This is not a code regression** — 108/108 pass on a fresh DB. But it is a trap: anyone who runs the suite against the live DB hits a misleading failure and may "fix" working code.

**Fix (small, safe):**
1. `backend/conftest.py` `test_environment_reset`: add `trip.host_checked_in = True` (matching the seed value).
2. `backend/database.py` reload block: in the `if not is_production():` branch for `trip_makro_01`, add `tdata["host_checked_in"] = True` (matching the seed).
3. Optional: add a regression assertion (e.g. extend `test_security_baseline.py`) that the fixture restores the seed state (`host_checked_in=True`, `pin_attempts_left=5`, `rendezvous_verified=False`, status SCHEDULED) after a test that flips them.

**Acceptance criteria:** `python -m pytest test_security_baseline.py -p no:cacheprovider -q` passes both (a) against a fresh disposable DB and (b) against the preserved live `backend/cartmate.db` file. Both modes green.

**Do NOT** delete or reset `backend/cartmate.db` — LAUNCH_READINESS.md instructs preserving it.

---

## P1-1. Local verification interpreter documentation

**Problem.** `backend/venv` is incomplete (no pytest/websockets). Prior evidence runs used the Hermes agent venv. A future contributor or agent could burn hours on missing-module errors, or worse: run uvicorn from `backend/venv`, get a dead realtime layer, and misattribute it to application code.

**Fix.** Add a short "Local verification on this machine" section to `HANDOFF.md` (repo contributor doc):
- Use `C:/Users/moham/AppData/Local/hermes/hermes-agent/venv/Scripts/python` for local runs on this checkout.
- Always set `CARTMATE_DATABASE_PATH` to a fresh temp file for test/e2e runs (cross-link `qa/README.md` as the authoritative run book).
- Verify ports 8000/5280 are free and the responding pid is yours before browser suites (stale-server hazard, documented in `qa/README.md`).

**Acceptance criteria:** the section exists in `HANDOFF.md`; verification commands in `cartmate_engineering_handoff_codex.md` §4 cross-reference it.

---

## P1-2. Stale verification counts in `cartmate_engineering_handoff_codex.md` §4

**Problem.** §4 comments cite 102/102 and 24/24 while the header says 108/108, 32/32 + 4/4. Confusing for the next executor.

**Fix.** Refresh the numbers in §4 to the current verified matrix (108/108 backend, 32/32 development browser, 4/4 no-demo, 2/2 DR drill) and point to `qa/README.md` for the authoritative run commands.

**Acceptance criteria:** no stale test counts in §4; commands either current or explicitly marked historical.

---

## P2-1. `main.py` size — plan the split, do not refactor yet

**Problem.** `backend/main.py` is 2,758 lines. The founder's convention (narrow-module org, split >~2k lines by concern) calls for a split. It works, it's tested — but it is the file every contributor fears.

**Fix.** DO NOT refactor now (pilot critical path first: age gate → hosted rehearsal → first users). Instead, add a short architecture note (`docs/ARCHITECTURE.md` or a section in `HANDOFF.md`) with a planned split-by-concern outline (auth/OTP, trips/handshake, moderation, chat/WS, region/policy) to execute post-pilot. This creates the map without destabilizing the pilot path.

**P2-2. Session-storage hardening**

Already tracked as an open item in LAUNCH_READINESS.md Sprint 1 ("Review browser `localStorage` bearer-session exposure, session lifetime/rotation, token-at-rest design, CSP/CSRF"). No new action in this ticket beyond keeping it open. Not pilot-blocking for an invited, known adult cohort with OTP-proven phones; hardening before scale.

**P2-3. Ops scratch dirs**

`ops/cartmate_dr_test__c0yq3jx` and `ops/cartmate_dr_test_sxijfo0a` are leftover drill artifacts. Remove them and confirm `ops/test_disaster_recovery.py` still passes 2/2 afterward. Cosmetic; same commit as the P0/P1 work.

---

## Order of operations & regression gate

1. P0-1 + P0-2 (requirements + CI smoke) — one commit: `fix(deps): add websockets dependency + image smoke test`
2. P0-3 (fixture/reload symmetry) — separate commit: `fix(tests): reset host_checked_in in fixture and reload block`
3. P1-1 + P1-2 — one commit: `docs: contributor verification runbook + refresh stale counts`
4. P2-3 cleanup — one commit: `chore: remove ops drill artifacts`

After EACH commit, run the full local gate before moving on:

```bash
export PY=C:/Users/moham/AppData/Local/hermes/hermes-agent/venv/Scripts/python
# backend (fresh disposable DB is mandatory)
cd S:/APPs/cartmate/backend
CARTMATE_DATABASE_PATH="$LOCALAPPDATA/Temp/cm_gate.db" $PY -m pytest -p no:cacheprovider -q   # expect 108/108
# frontend
cd S:/APPs/cartmate/frontend && npm run build && npm run lint
# browser suites (see qa/README.md; fresh ports, disposable DB, CARTMATE_MODERATOR_USER_IDS=usr_zuzanna, OTP_PROVIDER=console, SOS_PROVIDER=disabled)
cd S:/APPs/cartmate/qa && CARTMATE_BASE_URL=http://127.0.0.1:5280 CARTMATE_E2E_ISOLATED=1 npm test   # expect 32/32
cd S:/APPs/cartmate/qa && npm run test:no-demo                                                      # expect 4/4
```

Do not use `backend/venv` as the local interpreter. Do not run the suite against the live `backend/cartmate.db`. Confirm ports 8000/5280 are free and owned by your processes before browser suites.

---

## What this ticket does NOT authorize

- No age-gate implementation (waits on founder/counsel choosing an assurance method — separate ticket once picked).
- No changes to safety boundaries, moderation policy, region scope, or user-facing copy.
- No new features, streaks, Jev expansion, or nationwide surface work.
- No relaxing of LAUNCH_READINESS.md gates. Passing these fixes makes the **hosted rehearsal** executable; it does not make CartMate launch-ready or user-invitable.

---

## Evidence appendix — how each item was verified on 2026-09-29

- **P0-1:** clean-venv `pip install -r backend/requirements.txt` → `import websockets` → ModuleNotFoundError; same venv boots uvicorn → `WARNING: No supported WebSocket library detected` → `/ws?ticket=...` returns 404. `websockets==15.0.1` + uvicorn 0.41.0 proven working: full 32/32 browser suite passed with WS frame assertions under that exact library set.
- **P0-2:** `.github/workflows/ci.yml` final step is `docker build` with no run/assert step. The WS-dead image would pass current CI.
- **P0-3:** reproduced twice (full suite and isolated file run) against live `cartmate.db`: `test_pin_verification_rate_limiting` fails with `assert 400 == 429`; fresh-DB run passes 108/108. DB row inspected: `host_checked_in: false`. conftest.py fixture and database.py reload block read and confirmed missing the field.
- **Baseline re-verification (post-cutoff tree):** 108/108 backend (fresh disposable DB, Hermes venv interpreter), lint+build clean, 32/32 browser (fresh ports, verified pids), 4/4 no-demo — confirming the prior session's work landed intact.