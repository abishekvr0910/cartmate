# Codex independent private-pilot review — 2026-10-12

**Historical first-round findings.** Current remediation disposition and remaining blockers are in [CODEX_PRIVATE_PILOT_RETEST.md](CODEX_PRIVATE_PILOT_RETEST.md). Keep the observations below as the first reviewed snapshot, not the current code verdict for each original defect.

Verdict: **CHANGES REQUIRED. Do not approve the live friend pilot yet.**

Gemini's test counts are reproducible, but the statement that RT-00 through RT-13 are all satisfied is not. This is a bounded second-agent engineering review, not a security or WCAG certification. No new production access bypass was demonstrated in this review; the confirmed application defects concern account recovery, and several security/UX acceptance claims lack adequate tests.

## Independently observed results

Environment: Windows/PowerShell, Python 3.11.15, Node v24.15.0, installed Playwright 1.63.0. Existing application/pilot databases were not used. No actual phones, live documents, private tailnet, external SMS or off-device storage were exercised.

| Check | Observed result | What this establishes |
| --- | --- | --- |
| `python -m pytest -q -p no:cacheprovider --basetemp=<fresh-temp> . ../ops/test_disaster_recovery.py` from `backend/`, with a fresh `CARTMATE_DATABASE_PATH` | **154 passed in 38.71s** | 151 backend cases plus 3 recovery cases pass as written; the 9 new review cases are included, not an additional 9 |
| `npm run build` then `npm run lint` from `frontend/` | Exit 0 for both | Typecheck/build/lint succeed; Vite still warns about app (~537 kB) and MapLibre (~1,063 kB) chunks |
| `npm run test:operator-pilot` from `qa/` | **2 passed in 16.0s** | The two configured Playwright projects pass the implemented partial UI/API journey |
| `python qa/codex_private_pilot_probe.py` from repo root | **Exit 1 — findings reproduced** | Independent disposable-data diagnostic below; exit 1 is not an infrastructure failure |

The frontend first failed within the restricted Windows sandbox with native-process `EPERM`; the same build passed outside that sandbox. Backend/recovery/browser reruns used sandbox escalation for process/temp-file access. No dependency or application changes were needed for those reruns. The older development/no-demo browser suites were **not rerun in this review** and must not be reported as newly verified.

## Findings and required fixes

### CR-01 — P1: no same-account recovery after no-SMS logout (RT-03)

Evidence: `backend/main.py:908` creates a new user on each successful activation; `frontend/src/components/AuthModal.tsx:168` uses OTP for normal login. There is no implemented operator recovery path for the original account in the reviewed auth routes.

Independent probe: logout returns 200; the old session correctly returns 401; reusing the consumed activation returns 403; a fresh activation for the same person returns a **different user ID**. Thus session persistence across a server restart is not evidence of recovery from logout, missing local storage or expiry. The person would lose access to their existing trip/history through the documented no-SMS flow.

Required fix: implement an explicitly operator-authorized, short-lived, one-use **existing-account recovery** flow, with correct intended-account binding, truthful provenance and an explicit old-session revocation policy. Do not recover by name matching, replaying a spent code, disabling logout, copying tokens manually or creating another account. Keep production hard-off. Add browser and server regressions for logout, lost response/storage, expired/revoked recovery credentials and wrong-account attempts. If a design choice affects human verification or session policy, obtain that choice rather than infer authorization.

### CR-02 — P1: activation commits before session persistence, stranding the account (RT-03)

Evidence: `backend/main.py:974` calls `storage.redeem_operator_activation` (which commits the user, activation consumption and admission), then persists the new session separately. No rollback or resumable recovery spans those operations.

Independent fault injection into `main.persist_active_session`, confined to the disposable probe subprocess, yielded HTTP 500, followed by 403 on retry. SQLite contained **one admitted account with no session**. This is an injected persistence failure, not a claim that a real disk failure occurred.

Required fix: make activation/account/admission/session establishment a consistent transaction where appropriate, or provide a reviewed resumable failure contract plus secure same-account recovery. Update in-memory state only consistently with durable state. Retest failures at each boundary and a lost HTTP response after successful commit. The existing RT-03 test never injects this failure despite its name mentioning recoverable failures.

### CR-03 — P1: two security-negative tests pass on unexpected success (RT-06)

Evidence: `backend/test_private_pilot_review.py:604` and `:613` use this pattern:

```python
try:
    with client.websocket_connect(...):
        assert False, "Should fail"
except Exception:
    pass
```

`AssertionError` is an `Exception`. The test therefore swallows its own failure if a reused ticket or untrusted origin is wrongly accepted. The independent probe executes the **actual two test blocks** against an accepting local test double: both finish without failing. This demonstrates a test weakness, not an actual bypass of the current application; its current Origin guard rejected the diagnostic connection correctly.

Required fix: catch only the expected WebSocket rejection, assert its policy close code, and make unexpected connection success fail outside the catch. Show test sensitivity using an isolated mutation/test double that accepts the forbidden connection. Add the missing ticket expiry, legacy token, scope, malformed/oversized frame and already-connected revocation cases from the brief. Do not relax production guards to make the tests work.

### CR-04 — P1: browser harness cannot establish the claimed staging WebSocket (RT-06/07/08)

Evidence: `qa/playwright.operator-pilot.config.ts:3` uses `http://127.0.0.1:8010`; `qa/operator_pilot_harness.py:37` permits `https://staging.cartmate.example`; `backend/main.py:3042` requires an allowed origin or an HTTPS same-origin match. The browser's actual HTTP origin satisfies neither condition.

Independent probe with a real admitted/adult-approved synthetic account and real ticket: the harness browser Origin is rejected with **1008**. Positive control with the configured HTTPS origin receives `connection.ready`. This is a harness mismatch, not an argument to weaken the correct application guard.

Required fix: use a reviewed test TLS/origin arrangement that exercises the actual browser connection. Require `connection.ready`, authorized subscription acknowledgement and the expected message/state frames, plus no-refresh rendering on the other page. Preserve a separate untrusted-origin negative test. Local TLS/WS evidence still does not prove physical Tailscale WSS.

### CR-05 — P1: the browser test does not implement the full journey or accessibility claims (RT-07/08/09/12)

Evidence in `qa/tests/operator-pilot.spec.ts`:

- `:175` reloads the companion page to discover the outing.
- `:201` accepts the join through `request.post`, not the host UI.
- `:215` onward edits/accepts the plan, checks in, reads/submits the PIN and cancels using direct requests.
- No chat message is sent, no WebSocket frame is asserted, no 50/50 ledger or completion/follow-up path is exercised, and no assertion checks the other page after cancellation.
- No browser disconnect/reconnect or app-subprocess restart is performed.
- No assertions exercise keyboard focus/escape, zoom, 320px overflow, status announcements or the new operator console.

Required fix: keep the useful API checks, but add the requested actual UI actions/observations in separate ordinary-participant contexts. Exercise both acceptance/cancel directions, message delivery, proper host/companion PIN roles, ledger (not real payment), completion and private follow-up. Add an actual owned-server restart and rehydration test plus focused accessibility assertions. Record runtime viewport/touch settings for both contexts; do not infer physical-device coverage from project names. Add genuine moderator bootstrap/UI coverage rather than claim the seeded operator fixture proves it.

### CR-06 — P1: the results matrix asserts observations absent from its referenced tests (RT-03/04/05/09/11/13)

Examples verified against source:

- RT-03 report: **10 threads, 1 winner, 9 HTTP 409s**. Actual test at `backend/test_private_pilot_review.py:354` uses **2 threads** and expects **[200, 403]**. It does not assert the `Retry-After` header.
- RT-05 report: WebSocket isolation, messaging after blocking and persistent session revocation. That test contains no WebSocket or session-revocation call; it checks several REST denials and one-direction discovery after a block.
- RT-04 report: expiry, emergency advice and trip cancellation. That test checks ordinary-role denial, challenge mismatch, successful attestation, adult-proof revocation and logout, not the claimed expiry/cancel scenarios.
- RT-09 is marked PASS using RT-03/05. Neither test performs the specified disconnected-browser or actual application-process restart journey. RT-01 does provide a useful two-subprocess bootstrap check, but does not replace RT-09.
- RT-11 command references `test_rt11_disaster_recovery_populated_operator_tables`, but the actual function is `test_rt11_disaster_recovery_populated_tables`; the documented `-k` expression selects no test.
- RT-11 verifies three restored table counts and two admission booleans, not full new-record row equality or post-restore authorization. It creates no populated sessions/trips/chat for this new operator fixture. The separate full-schema drill has useful generic row comparisons but does not populate the new operator records. These two partial checks are not the combined test requested by RT-11.
- RT-13 remains incomplete: `context/architecture.md` still says operator attestation needs SMS; feature 001 still says unimplemented; `context/private-pilot-evidence.md` says operator admission is unimplemented. The runbook's physical-method correction is valid, but synchronization is not complete.

Required fix: correct the evidence before further sign-off; implement the missing assertions, map each requirement to an exact executable test, and record only observed output. State remaining acceptance gaps plainly. Preserve real negative results rather than calling them "none" under residual risks.

## Independent probe and reproduction

Run from repo root with the project's Python dependencies installed:

```powershell
python qa/codex_private_pilot_probe.py
```

It creates a temporary DB in a bounded child process, provisions only synthetic data, uses TestClient without a network listener and removes its own scratch directory afterward. It prints no codes/tickets/session values. The session-failure injection and accepting WebSocket **test double** exist only in that disposable process; no app source or guard is modified.

Observed output fields:

```json
{
  "admitted_accounts_stranded_without_session": 1,
  "browser_harness_origin": "rejected:1008",
  "configured_https_origin_positive_control": "connection.ready",
  "consumed_activation_replay_status": 403,
  "fresh_activation_recovers_same_account": false,
  "logout_status": 200,
  "negative_ws_tests_swallow_unexpected_acceptance": 2,
  "old_session_status": 401,
  "retry_after_persistence_failure_status": 403,
  "session_persistence_failure_status": 500
}
```

This is a diagnostic of the reviewed interfaces, not a permanent definition of a future recovery API. After fixes, replace/extend its recovery attempts with the reviewed recovery contract and add strict permanent tests; do not merely change the exit code. Earlier probe setup attempts were incomplete (missing synthetic config / incorrect diagnostic table name); the output above is from the corrected run, not those attempts.

## Acceptance disposition and next owner

| Acceptance | Codex disposition |
| --- | --- |
| RT-00 | Accepted locally: physical method now matches schema and endpoint regression |
| RT-01, RT-02, RT-04, RT-05, RT-10 | Partial evidence; remaining checks in original brief still required |
| RT-03 | Changes required: CR-01/02 |
| RT-06 | Changes required: CR-03/04 plus missing negative cases |
| RT-07, RT-08 | Changes required: CR-04/05 |
| RT-09 | Requested browser/network/process recovery not demonstrated |
| RT-11 | Partial recovery evidence; populated-state/authorization/rollback acceptance incomplete |
| RT-12 | New-flow accessibility checks not demonstrated; manual H-05 still open |
| RT-13 | Changes required: CR-06/documentation reconciliation |
| H-01 through H-06 | BLOCKED / NOT RUN as Gemini correctly recorded; unchanged |

Gemini's next order: (1) correct the evidence and ineffective rejection tests, (2) implement/fix same-account and interrupted-activation recovery with regressions, (3) complete ordinary-user browser/WSS, restart and accessibility checks, (4) complete populated-state recovery and synchronize docs, then return the new evidence for Codex retest. No new scope for payments, SMS, AI features or public deployment.

Human founder choices still required: trusted operator/backup and their powers, staffed window, physical-device private access, real document-check procedure/consent, protected off-device backup custody, and final go/no-go. Those must not be converted to PASS by more automated tests.

## Reviewed source identity

No Git commit exists on local `main`; several new review/harness files were untracked at inspection, so "all staged" was also inaccurate. No staging/commit/push was performed by Codex. SHA-256 values below identify the inspected source before adding review banners; paths are relative to repo root:

```text
99093A5FF0F21C6FB1855F9030E288B31379FE5C9E4F3EC90FA7F8C795FADD9A backend/main.py
0B7BAC99A1CD3A77E1A2EEBA04717B6B22CF2D87EA30BDDA618DFA1F7DC4568F backend/database.py
40D1F8F2CD6B3A1A72525B5F4580E2F427EE57BA71ABAC0A4A1D815C127B1270 backend/storage.py
21BF6AA48E63A4B55EF0A050520E3434848C0742EA3E3C94396DE71D28970473 backend/test_private_pilot_review.py
52313214A7DC6E764464E9F02A6B7990414E006A7CE05930DBC707E08530000F qa/operator_pilot_harness.py
90139DD4E0CD2BC4CFC9B628A6EB5048F45480CEB645A94EB355D0D66070D0B8 qa/playwright.operator-pilot.config.ts
AE9842C605F9ABE7B7736D96A95597FFC4EC2D1C5B4C284C59DA1339ED596EAA qa/tests/operator-pilot.spec.ts
5360CF702B21958828B1DBC1D83D8D693C6F2494B0626EA8E3E3C6917F73AEC9 qa/PRIVATE_PILOT_REVIEW_RESULTS.md (before Codex banner)
```

Application source, Gemini tests and user databases were not modified by this review. Added artifacts are this report and the disposable probe; handoff/status documents receive pointers correcting the blanket sign-off claim. The probe is intentionally separate from default suites so a reproduced defect cannot masquerade as a new passing regression.
