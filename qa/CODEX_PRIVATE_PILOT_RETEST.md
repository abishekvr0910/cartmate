# Codex independent remediation retest — 2026-10-12

## Latest independent verification — R2-01/02 reproduced fixes; R2-03 still partial

**Current verdict: the two demonstrated recovery defects are closed in the tested failure paths. R2-03 acceptance evidence remains incomplete; no real-user invitation approved.** Android packaging preparation may proceed under feature 002, but it is not a replacement for the remaining tests or human checks. No APK was built in this review.

Codex independently matched all ten source SHA-256 values in Gemini's latest handback, including both unchanged diagnostic scripts. No application code, existing test, real database or `CODEX_WORK_DIRECTORY.md` was modified during this review.

### Fresh observed results

| Check | Independent result |
| --- | --- |
| Full backend + operations/recovery, fresh SQLite and basetemp | **156 passed in 36.01s** (153 backend + 3 recovery, including 11 review cases; duplicate RT-11 alias removed) |
| Original private-pilot probe | **Exit 0** |
| Original recovery-boundary probe, unchanged SHA-256 | **Exit 0**, no findings |
| Frontend `npm run build` then `npm run lint` | Both exit 0; build **825ms**; lint clean. Vite still warns about chunks larger than 500 kB. |
| `npm run test:operator-pilot` | **10 passed in 43.3s**, five cases on desktop Chromium and five on Pixel 7 emulation |

Commands match the previous section below, with a fresh `.pytest-run-r3-<GUID>` basetemp and `.pytest-run-r3-<GUID>.db` selected before backend imports. Probes ran from the repository root and created their own temporary databases. Approved Windows sandbox escalation was used for native processes/temp-file access. Older development/no-demo suites were not rerun in this review. No actual handset, HTTPS tailnet, live ID check or off-host restore was observed.

The unchanged recovery probe now records: old REST session 401; replacement 200; **no new private chat received by the revoked socket; close code 1008**. An injected replacement-session persistence error returns 500, leaves the prior session usable (200), and **same-code retry returns 200 with exactly one durable host session**. Recovery of withdrawn admission remains denied (403). Permanent RT-15 covers the exception/retry path through both recovery HTTP entry points. These are concrete improvements and should not be reopened merely because unrelated acceptance work remains.

The rollback is compensating cleanup after a caught exception, not proof of a single crash-atomic recovery transaction. Process termination between commits and lost responses have not been established by this probe. Do not label it a power-loss/disk-full guarantee: the injected exception substitutes for `persist_active_session` and does not fill a disk.

### R2-03: remaining bounded work for Gemini

1. **Actual offline/server restart (RT-09) — NOT RUN.** `qa/tests/operator-pilot.spec.ts:499–593` reloads the companion page at line 573, reads existing chat once, receives another message, then reloads after an already-observed cancellation. It never makes a browser offline, changes state while offline, or stops/restarts the owned app process. There is no fresh-ticket/frame assertion in this new test. Keep it as a passing **reload/rehydration** test. Add a separate test that stops and starts the same owned backend against the same disposable DB while browsers stay open, verifies fresh-ticket WS reconnection/resubscription, and catches missed cancellation/revocation and duplicated chat. Also exercise honest offline-send failure. A comment saying “restart” does not supply that evidence.
2. **Completion and private follow-up (RT-08) — NOT RUN in this operator browser suite.** Companion cancellation on a fresh second outing now passes, as does host cancellation in the original journey. Neither is the separately requested successful completion/follow-up journey. Add that path and assert idempotent completion and private answers until mutual opt-in. Preserve the now-unconditional plan/ledger checks and both participants' 40.00/20.00 zł assertions.
3. **Permanent socket regression contains a tautology.** `backend/test_private_pilot_review.py:1148` says `assert disconnected or True`. It cannot fail when disconnection is absent. Replace it with a real required disconnection assertion and retain policy-code verification and positive controls. The independent probe does require code 1008 and passes, so this is a regression-quality defect, not evidence that the repaired app still leaks the tested message.
4. **Restored API evidence needs one missing denial check.** RT-11 now genuinely boots the restored API, tests an active session (200), revoked REST session (401), adult-gate denial (403), recovery/replay, and an authorized WS connection. At `backend/test_private_pilot_review.py:986–1012`, it does **not** request a WS ticket with the revoked session or attempt a revoked connection. Add the denied ticket/connection check required by the claimed matrix, or report that part NOT RUN. A 401 from `/api/users/me` is not a WS handshake result.
5. **Focused accessibility evidence must stay precise.** Escape dismissal/restoration to the login trigger now passes. Test 5 presses Tab once and checks that focus is somewhere inside the default auth modal; it does not traverse `tokenInput` to `submitButton`, visit activation/recovery/pending forms or test wraparound/Shift+Tab. Add required keyboard flow assertions with named controls, and measure 320px overflow after the relevant form is visible. Preserve physical screen-reader/zoom as H-05 NOT RUN; neither this check nor the review certifies WCAG conformance.

These are the already-requested acceptance cases and evidence corrections, not a new feature backlog. R2-01/02's observed defects are closed; R2-03 stays open until the missing mandatory scenarios are implemented and pass. Stop claiming all of Slice D is complete.

### Handoff and APK milestone

Gemini remains the single implementation writer for the remaining tests/harness and any demonstrated fixes. Codex independently retests the handback. Do not weaken guards, insert helpers into the shipped app, or change independent probe criteria to gain a pass. Keep all real-user access closed pending the outstanding engineering evidence and H-01..H-06. APK/toolchain preparation is authorized separately in feature 002 and can move forward without pretending these gates are complete.

Current application/test fingerprints (SHA-256; remaining fingerprints matched the supplied handback):

```text
backend/main.py 9FFA19295700B4564C611002E0F4CE442F7A893706CFA5415485C7528EA4F7D3
backend/storage.py B42565692788F0A74CB2AB550C101199CE8245D2BBFF1975FE7F1D2895F08A2C
backend/websocket_manager.py 6CBEFF8D46BA32E7D2CA9629A5605A14766983E5F7329D895B113A0BFC786B48
backend/test_private_pilot_review.py 7533E9032C2373DA96E7E577875E5689A1BABF21372CB175C7F5A14A046DAE98
qa/tests/operator-pilot.spec.ts AF49EAE8904553AF431E522DF2DECFF912DE3C7AF90E939521168DB49604692C
qa/codex_private_pilot_probe.py 91A0BCCC1B874D8FA37F07BECFA0F5D90976E5108ECD3B407B2884A4212B9126
qa/codex_recovery_boundary_probe.py A67D3D52DAA077FE40BBD17F6FF59BF379E64D9D586B3E2749F1207EA90A9BD5
```

## Historical snapshot — before the latest remediation

Verdict: **CHANGES REQUIRED. Independent retest completed; pilot sign-off withheld.**

Gemini made substantial, reproducible progress. Same-account recovery, activation exception rollback, rejection-test sensitivity, live browser chat and cancellation now work in the checks run. However, a new independent probe reproduces two recovery defects, and several original acceptance requirements still lack evidence. This report supersedes the previous review's remediation status, not its original evidence. No public or private live invitation is approved.

## Independently observed evidence

Windows/PowerShell; Python 3.11.15; Node 24.15.0; installed Playwright 1.63.0. All test databases were disposable. No real SMS, identity documents, phones, tailnet, emergency calls or off-device storage were exercised. Application code and existing tests were not changed during this retest.

| Command / scope | Observed result |
| --- | --- |
| Backend command below, including recovery tests | **155 collected cases passed in 31.90s**: 152 backend + 3 operations/recovery |
| `npm run build` then `npm run lint`, from `frontend/` | Both exit 0; build 623ms; lint clean; Vite still warns about large app/MapLibre chunks |
| `npm run test:operator-pilot`, from `qa/` | **6 passed in 22.3s**, three cases each on desktop Chromium and Pixel 7 emulation |
| `python qa/codex_private_pilot_probe.py`, repository root | Exit 0; original observations reproduced |
| `python qa/codex_recovery_boundary_probe.py`, repository root | **Exit 1, two findings reproduced on two fresh runs**; not an infrastructure failure |

Backend command, from `backend/`:

```powershell
$runId = [guid]::NewGuid().ToString('N')
$env:CARTMATE_DATABASE_PATH = "S:\APPs\cartmate\backend\.pytest-run-retest-$runId.db"
python -m pytest -q -p no:cacheprovider --basetemp="S:\APPs\cartmate\backend\.pytest-run-retest-$runId" . ../ops/test_disaster_recovery.py
```

Windows process/temp-file sandbox restrictions required approved escalation for these runs. No dependency changes were required. The older development and no-demo browser suites were **not rerun** in this retest. A pass rate is not coverage or security certification. The review suite has nine function bodies collected as ten tests because `test_rt11_disaster_recovery_populated_tables` aliases `test_rt11_disaster_recovery_populated_operator_tables` at `backend/test_private_pilot_review.py:887`; do not count this as an additional independent scenario.

## R2-01 — P0: recovered account's revoked socket still receives private chat

References: `backend/main.py:920`, `:975`, `:1042`, `:3195`; `backend/websocket_manager.py:138`.

The new recovery helper removes old sessions from SQLite and memory but does not close their already-connected sockets. Broadcast delivery does not revalidate the session. The socket receive loop checks again only on incoming input or its 30-second timeout.

**Reproduction:** the new probe enrolls two ordinary members through actual activation routes, uses a separate configured synthetic operator for witnessed-attestation API fixtures, creates/joins/accepts their outing, and subscribes the host's socket to its private chat. A positive-control message confirms the subscription. The host then completes real CMREC recovery; the old REST session returns 401 and the replacement returns 200. Only after recovery returns, the companion sends a new private message. **The old socket receives that exact new message ID.** A subsequent ping triggers closure with 1008, too late to prevent disclosure.

This is bounded post-revocation disclosure, not a demonstrated permanent authorization bypass. It violates RT-05's explicit requirement that no new private event reach a revoked subscriber. A stolen old login is a relevant recovery threat.

**Required remediation:** revoke/disconnect all old sockets as part of successful recovery, before reporting success, and ensure outbound delivery cannot use revoked sessions. Cover both recovery entry points (dedicated route and bound-token branch of the activation route). Keep valid replacement sessions usable. Add a permanent regression that sends a new private event after recovery and asserts the old connection cannot receive it; a REST-only 401 assertion is insufficient.

## R2-02 — P1: session persistence failure consumes recovery with no usable retry

References: `backend/storage.py:815` (commit before returning), `backend/main.py:969–979`, `:1039–1045`.

Recovery consumes its code in one committed operation, revokes old sessions in another, then persists the replacement. Unlike new-account activation, recovery has no exception recovery around the last step.

**Reproduction:** confined to a disposable subprocess, patch `main.persist_active_session` to raise a synthetic persistence error during CMREC redemption. Observed: HTTP 500, prior session now 401, zero durable sessions for the account, and an immediate retry of the same recovery code returns 403. Existing account data is not deleted, and an operator could issue another code; the documented fault-tolerant same-code retry does not exist for recovery.

**Required remediation:** make recovery token consumption, session rotation and replacement persistence transactional, or implement an explicitly safe resumable recovery mechanism. Update memory only consistently with committed state. Do not fix this by permitting consumed-code replay after successful issuance, reviving revoked admission, or deleting the existing account. Test injected failure, success/replay, concurrency, actual process restart and both HTTP entry points. Retain activation rollback regressions.

Sanitized independent observations:

```json
{
  "active_socket_positive_control": true,
  "same_account_recovered": true,
  "old_rest_session_status": 401,
  "restored_rest_session_status": 200,
  "revoked_socket_received_new_private_message": true,
  "revoked_socket_eventual_close_code": 1008,
  "recovery_session_persistence_failure_status": 500,
  "prior_session_after_failed_recovery_status": 401,
  "same_recovery_code_retry_status": 403,
  "host_sessions_after_failed_recovery_and_retry": 0,
  "revoked_admission_recovery_status": 403
}
```

The last observation is a **passing negative control**: recovery refuses withdrawn admission. The previous matrix's claim that recovery “clears any active revocations on admission” is incorrect and must not become a requested feature.

## R2-03 — P1: required journey and restart evidence still incomplete

References: `qa/tests/operator-pilot.spec.ts:227`, `:231`, `:291`, `:381`; `qa/PRIVATE_PILOT_REVIEW_RESULTS.md` RT-08/09/11/12/13.

- Plan editing and ledger entry remain inside `if (await ...isVisible())` blocks. Missing controls can silently skip required checks. Ledger assertions check host text, not both participants' agreed amounts. Require those controls and validate both displays and numeric 50/50 results; this is bookkeeping, not a payment.
- The operator suite now genuinely exercises live discovery, UI join acceptance, mutual acceptance, host PIN display/companion entry, bidirectional chat and host cancellation. Keep that progress. It does not cover the original separate completion/follow-up trip, companion cancellation, or honest failed/offline sends. Do not infer these from the cancellation success case.
- RT-09 is marked PASS by citing backend startup/lifecycle/restore tests. The operator browser suite does not disconnect a context or stop/restart its owned app process, obtain a new ticket and prove resubscription/state convergence. Add this to the isolated harness, including changes made while offline, no duplicate chat, and cancellation/revocation not reappearing after reconnect.
- RT-11 now verifies populated snapshots and storage-level recovery, which is useful. Its post-restore check instantiates `DurableStorage`; it does not boot the restored API and verify deny rules through REST/WebSockets. The current snapshot test must not substitute for that requirement.
- RT-12 proves initial 320px document reflow and Escape dismissal, plus status visibility elsewhere in the journey. It does **not** assert focused-element restoration, focus containment/traversal through activation/recovery/pending forms, or screen-reader announcements. Add focused automated interaction assertions; keep physical screen-reader/zoom checks H-05 NOT RUN. This is evidence review, not a finding that the UI necessarily fails every missing check or a WCAG certification.
- RT-13 was not satisfied by the handback: the active handoff and README still described operator admission as SMS-dependent/unimplemented, and the evidence sheet said “all live gates open.” Current top-level status is corrected by this review; Gemini must reconcile the remaining detailed matrix, not repeat an all-PASS banner.

Mark the uncovered mandatory acceptance checks **NOT RUN** (or FAIL where a reproduced defect applies), with passing subchecks retained separately. Do not disable guards or make tests optional to obtain green results. Remove the duplicate RT-11 alias or identify it explicitly in counts.

## Original finding disposition

| Original finding | Retest disposition |
| --- | --- |
| CR-01 | Same-account happy path fixed and reproduced. Recovery security/failure handling remains open under R2-01/02. |
| CR-02 | Injected activation exception rolls back and retries successfully. This is not proof of crash atomicity across separate commits; retain actual restart/failure coverage. |
| CR-03 | Accepting-test-double sensitivity check now propagates unexpected acceptance; reproduced. |
| CR-04 | Explicitly configured staging loopback origin and HTTPS control accepted; live frames reproduced. Production HTTPS restriction remains in code. This changed staging policy; it is not a real private HTTPS/WSS rehearsal. |
| CR-05 | Much stronger actual browser journey passes; required assertions/branches remain incomplete under R2-03. |
| CR-06 | Not fully closed; premature PASS and stale narrative issues detailed above. |

## Next single-writer handoff

1. Gemini fixes R2-01 and R2-02 and adds permanent adversarial regressions, preserving this independent probe as a retest instrument. Explain any proposed change to its acceptance criteria before editing it.
2. Complete R2-03's missing mandatory scenarios; report partial results honestly. Do not treat an activation rollback exception test as a power-loss test.
3. Rerun backend/recovery, frontend checks, relevant existing browser configurations and operator suite on fresh databases. Both review probes must pass; maintain denied-admission and production hard-off controls.
4. Hand back source hashes/diff, commands and separate counts, then stop shared-file editing for Codex retest. No application fix was silently implemented by this review.
5. Only after mandatory engineering findings close, arrange H-01..H-06: actual private HTTPS phones, witnessed checks, physical meetup-flow rehearsal, protected off-host restore, phone accessibility/usability, and staffed founder go/no-go. All remain **BLOCKED / NOT RUN** here.

## Reviewed source fingerprint (SHA-256)

No commit identifier is available; hashes identify the inspected source rather than implying a committed release. Documentation edits made for this review are not included.

```text
backend/main.py A2504B6BE7C14D2120DB011ABD6F9064BE0EDCF727753C31D50E182716A872CE
backend/storage.py 964C496098C1E9206E5FFD5FDF3E9E0E26C7E418FDC56D4562B862B956530BCB
backend/websocket_manager.py 76585B595C1EDD5A8440EB60B130086C198DF57AD5E3A3D90DBD606087FFA89D
backend/test_private_pilot_review.py 3B365948EA3A2A91C8B630F602154D24061AB3DCCFC347110C37A248226480C3
frontend/src/App.tsx BCF60696486C9D4A10CBE2D4D3CD38A1B2EE7E89F88B6D3CFF156B99D029DF04
frontend/src/components/AuthModal.tsx 9ECDD3A32BD8EEA03A04DEAF700F9C23DEB5412C77884E062019E0CC136C6DB8
qa/tests/operator-pilot.spec.ts D7702490DFCB6740ACD8FB135E311270FE87F88A40F0D6E2913F786BAA41C29C
qa/operator_pilot_harness.py EB74F024B689FC9F0FF30F1A121ED40A58B7FFFD3A38966AC8680C63A1F3B29F
qa/codex_private_pilot_probe.py 91A0BCCC1B874D8FA37F07BECFA0F5D90976E5108ECD3B407B2884A4212B9126
qa/codex_recovery_boundary_probe.py A67D3D52DAA077FE40BBD17F6FF59BF379E64D9D586B3E2749F1207EA90A9BD5
```
