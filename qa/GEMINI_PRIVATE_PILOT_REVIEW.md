# Gemini implementation brief / Codex independent review

Date: 2026-10-12. Scope: feature 001, private two-adult Silesia website pilot only.
Status: **assigned for implementation; not a passing test report or launch approval**.

## Outcome and ownership

Gemini implements the missing regression tests and narrowly fixes demonstrated defects. Codex then independently inspects the diff, reruns it against fresh state, and challenges the authorization and recovery boundaries. This is a second-agent engineering review, not an external security certification or WCAG conformance certification.

- Gemini is the single writer of application/test/runbook changes for this assignment. Coordinate before editing shared files or CI. Keep an existing failing test and explain the fix; do not weaken it to obtain green results.
- Codex owns this acceptance brief and subsequent red-team findings. Do not mark Codex sign-off complete yourself. Propose acceptance changes explicitly rather than silently editing this brief.
- Founder/authorized humans own real age checks, Tailscale account/device access, staffed hours, off-device backup custody, and final invitation approval. A script cannot supply those facts.
- No paid services, public tunnels/Funnel, real SMS, ID uploads, actual payments, public signups, production bypasses or live-database resets. Do not dial 112 during testing.

Read `AGENTS.md` and its context/spec files before editing. Keep the existing React/FastAPI/SQLite stack and Playwright tooling. This brief defines Slice D verification and corrections; it does not replace unresolved requirements in `LAUNCH_READINESS.md`.

## Evidence baseline — do not overclaim

Codex independently ran **142 backend tests, all passing**, on a disposable database on 2026-10-12. This includes 13 operator-admission tests. The 3 recovery tests and frontend/browser counts in other handoffs are prior/reported evidence, not new runs performed for this brief.

`backend/test_operator_admission_pilot.py::test_full_no_sms_outing_join_chat_flow` exercises REST via TestClient. It makes both participants moderators, records synthetic adult attestations, publishes/joins/accepts an outing and reads REST chat history. It does **not** exercise real browser activation, WSS delivery, physical age checks, the full meeting lifecycle or actual phones.

### Confirmed correction to do first — RT-00

The current runbook sends `method = "physical_id"`. The actual `PilotAdultAttestationRequest` in `backend/main.py` accepts only `"mdowod_qr"` or `"physical_identity_document"`.

Codex validated the actual request class in isolation, without importing the app or touching its database:

```text
physical_id: REJECTED (literal_error)
physical_identity_document: ACCEPTED
mdowod_qr: ACCEPTED
```

Fix the documentation to use **`physical_identity_document`**, including its example request. Do not rename the established API to match erroneous documentation. Add a regression that validates the documented method against the actual schema and performs a synthetic physical-document attestation through the real endpoint. Invalid method stays rejected. A real `mdowod_qr` entry requires the live official QR verification, not just viewing the app. Do not describe all passports as plastic cards.

## Deliverables and isolation

Suggested new files (reuse an equivalent existing fixture when appropriate):

- `backend/test_private_pilot_review.py`: adversarial contracts, fresh-process/revocation checks and failures identified below.
- `qa/tests/operator-pilot.spec.ts`: new-account, ordinary-participant browser journey.
- `qa/playwright.operator-pilot.config.ts` and, only if necessary, `qa/operator_pilot_harness.py`: isolated built-bundle staging harness; document the exact run command in `qa/README.md`.
- `qa/PRIVATE_PILOT_REVIEW_RESULTS.md`: sanitized ID-by-ID results, commands, limitations and handback.
- Corrections to `ops/PILOT_RUNBOOK_WINDOWS.md` and the active context/handoff/evidence documents.

The names above are proposed outputs, **not files or scripts already implemented by this brief**. Ensure the new staging spec is excluded from the default development-only suite, which otherwise collects new specs automatically. Retain the existing no-demo suite. Do not reuse `qa/staging_harness.py`'s captured SMS/`qa-local` age grant as proof of operator admission.

Each run must use a unique disposable database and dedicated loopback port. Refuse existing/foreign servers and refuse real pilot database paths. Set configuration before importing backend modules. Never use `backend/cartmate.db` or `ops/pilot_live.db` for automated tests. Stop only processes created by your harness and validate paths before cleanup. Do not print raw codes, bearer tokens or document details; local traces may contain them and must remain private/ignored.

Use separate browser contexts for host H, companion C, unrelated participant X and trusted operator O (plus backup operator B for the bootstrap scenario). These are synthetic roles, not a demand for five human testers. H/C/X must not be moderators in the normal journey. Provision operator accounts and token issuance through isolated setup/CLI; use the real admission and attestation endpoints thereafter. Prefer real moderator UI for browser checks. Never set adult flags, fake SMS timestamps or demo tokens to get past the boundary under test. Synthetic witness attestations test software only, not real-world age assurance.

For each ID below, record **PASS / FAIL / BLOCKED / NOT RUN**, environment and evidence. A blocked mandatory case remains open, not skipped-and-green. Independent contexts must actually inherit the intended viewport/device settings; `browser.newContext()` alone must not silently turn a mobile project into a desktop test.

## Automated acceptance cases

### RT-01 — correct private startup and role bootstrap (P1)

Run the documented startup from the repository root with `--app-dir backend`, a fresh DB and built frontend. Confirm `/`, `/api/health` and environment configuration reflect staging/operator mode. Confirm seeded identities are not presented as real neighbors; demo auth and testing/reset endpoints remain unavailable.

Issue/redeem operator codes, restart with the explicit moderator IDs, then perform distinct-account attestations. `/api/ready` must be non-ready until its documented prerequisites exist; 200 is not permission to invite users. Missing bundle/config must yield a clear failure. Demonstrate the actual bootstrap without test-only mutation of `main.MODERATOR_USER_IDS` in the running app.

Review the runbook's `CARTMATE_DEPLOYMENT=0` and absent session-TTL/origin/AI settings against feature 001: document exactly which guards are bypassed and configure a bounded pilot explicitly. Do not claim deployment validation ran when disabled. Keep optional external AI disabled for this rehearsal. Test console OTP requests are rejected in staging despite the inert provider setting.

### RT-02 — operator admission is not a production bypass (P0)

Use fresh subprocesses for staging flag ON/OFF, development/test, and production with flag ON. Only explicitly enabled staging may redeem. Check production again with persisted operator-admitted accounts/session data from staging: no live access or published outing may be obtained through this provenance. A submitted `phone_verified_at`, adult proof, moderator flag or assurance marker must never elevate the caller. Response and persisted account must retain truthful assurance, including null phone verification. Women-only/SafeHaven access must remain unavailable without the separate required identity proof.

### RT-03 — activation lifecycle and recoverable failures (P0/P1)

Verify invalid, expired, revoked, replayed and concurrently redeemed codes. Exactly one concurrent redemption may create one account/admission; the loser must not create orphan state. After a genuine process restart the consumed/revoked code must still fail. Check retry/rate limits and `Retry-After`, including forwarded-IP spoof attempts; report any restart reset of the abuse budget rather than claiming durable protection.

Inject a failure between account creation and session persistence in a disposable test. Inspect partial state and demonstrate an explicit, safe recovery path. Test lost response, logout, lost browser storage and session expiry: does the person regain the **same account** without SMS, code replay, account duplication or manually copying bearer tokens? If no recovery exists, mark it as a demonstrated pilot limitation/defect; do not invent success. Distinguish activation-code expiry from admitted-account lifetime and adult-proof expiry. Resolve the spec's bounded admission requirement explicitly, not by conflating the three.

### RT-04 — adult gate, challenge binding and emergency exit (P0)

An admitted but unverified ordinary member must be denied discovery, posting, joining, group actions, chat and WebSocket participation. Self-attestation and ordinary-member attestation must fail. Reject false/missing consent, extra document fields, wrong subject, wrong/replayed/expired challenges and unsupported methods. Valid synthetic checks for both supported methods unlock only the target member. Age expiry/revocation must deny subsequent protected actions and terminate existing live access; restart must not restore revoked proof.

Retain authorized leave/cancel/report/logout and direct-112 guidance when adult proof expires. Do not make the person unable to leave an outing. Confirm that an operator code alone never counts as adult or government-ID proof. Suspected under-18 users are not real test participants.

### RT-05 — membership, sessions and objects across transports (P0)

With H/C/X as non-moderators, X cannot read/mutate their trip, PIN, private follow-up, chat history or chat scopes by changing IDs. Ordinary participants cannot read moderation queue/audit data, ban anyone or attest age. A block must work both ways in discovery, joins, waves, trip/group contact and chat according to the approved policy, including a subscription opened before the block.

Test unused-token revocation separately from already-admitted-user removal. Exercise the actual available administrative removal route, logout, revoke-all, ban/suspend and admission/adult revocation with sockets already connected. Subsequent unauthorized reads/writes must fail; no newly generated private frame may be delivered after access removal. Idle session/age expiration must close within the documented 30-second recheck bound plus a small explicit scheduling margin. Preserve safety/exit routes where the policy allows them. Persisted revoked sessions must stay invalid after restart.

### RT-06 — real WebSocket authentication and authorization (P0)

Use real sockets with the application's ticket mechanism, not just REST chat. Verify missing/invalid/reused/expired tickets, deployed legacy `?token=` rejection, untrusted Origin denial, correct configured/same-origin success, and unauthorized `user:`, `trip:`, `chat:` and `outing:` subscriptions. Validate Host/Origin behavior with the intended proxy configuration, not a blanket origin bypass. Check oversize/malformed frames cannot crash the service or grant access. Keep tickets/tokens out of saved URLs/logs/traces supplied for review.

A loopback harness may use a narrowly scoped test HTTPS origin or test TLS; disclose how it differs from Tailscale. Never suppress application authorization, install global certificate-ignore behavior, or describe a local `ws://` run as physical `wss://` evidence.

### RT-07 — built React journey with ordinary members (P1)

On desktop and mobile-emulated projects, activate H/C through the UI with fresh codes. Verify an understandable age-pending screen without fake SMS success, a usable challenge/operator verification flow, and transition into the application after approval. H publishes a Silesia outing; C sees it and requests to join; H accepts. Pending is not accepted, and neither membership nor money transfers are invented. Repeat relevant out-of-region attempts directly against the API to establish server enforcement.

Capture actual trip/chat frames and require the other page to render updates **without reload or substituting REST polling for the WebSocket assertion**. Distinguish normal hydration reads from event proof. No `force: true`, removed overlays, silently optional assertions, fake data routes or demo-token injection to complete the journey. Add stable accessible locators where needed.

### RT-08 — mutual plan, rendezvous, ledger, completion/cancel (P1)

Assert both participants see the same activity/time/duration/cost terms. Check-in/PIN cannot proceed before the required mutual agreement. Host and companion have their actual distinct PIN permissions: only the authorized host fetches/displays the secret; the companion enters the verbally shared PIN. Do not write that both participants independently fetch/verify it. Wrong PIN attempts and lockout must remain enforced across reload/restart.

Verify zero-refresh acceptance, check-in, chat and agreed 50/50 ledger changes on both pages. Ledger math is not a payment or BLIK transfer. Use separate fresh trips for completion/follow-up and cancellation; duplicate requests must not double-count completion or charges. Cancel from either role and ensure both interfaces clear the active trip. Completion/follow-up must not reveal the other person's private answer before mutual opt-in. Test a failed request produces honest, recoverable UI.

### RT-09 — disconnected browsers and true process restart (P1)

Interrupt a browser connection, make an authorized change on the other, reconnect and verify current state without duplicated messages. Show failure/pending rather than false delivery during offline sends. Stop the actual app subprocess, restart against the same disposable DB, and check accounts, sessions, admissions, terms, PIN budget, messages, blocks and reports. Clearing Python dictionaries is not a cold-process test.

Ensure a restarted socket obtains a fresh ticket and resubscribes safely. A cancellation or revocation during disconnection must not reappear as an active trip after reconnect. Check browser refresh, tab close/reopen and mobile background/foreground separately. Document any deliberate pending-challenge invalidation; do not silently disable its expiry.

### RT-10 — no accidental data/service exposure (P0)

Check public DTOs, REST errors, WebSocket frames and captured server logs for synthetic phone/email/emergency-contact markers, raw activation codes, session tokens and PIN leakage outside the authorized PIN route. Inspect payloads, not only DOM text. Verify `/_qa/*`, reset and proof-grant endpoints are absent from the actual shipped app; adding QA helpers to `backend/main.py` is prohibited. Verify SOS remains direct-112-only and no external SMS/AI dispatch occurs in this configuration. Never actually call emergency services in tests.

### RT-11 — recovery has populated new tables (P1)

Extend the local recovery drill using the real schema with **nonempty** operator activations (unused, consumed, revoked), admissions, adult attestations, sessions/revocations, trips/messages, blocks and reports. Back up while the source process is operating, restore to a separate offline disposable target, and check both row fidelity and authorization after booting the restored app. An empty new table is not coverage of its records.

Checksum/manifest failure must leave the target unchanged. Verify the documented rollback/safety behavior and that the tool refuses an unsafe live restore. Use explicit validated paths and never replace the pilot database. A local drill does not count as off-device recovery. An older snapshot may predate a ban/revocation: require an explicit reconciliation/reverification procedure before reopening, and never imply backup alone preserves later security changes or guarantees zero data loss.

### RT-12 — phone usability and focused accessibility (P1)

Use the current accessibility checks plus the new activation/pending/operator flows: labels, errors, visible focus, keyboard traversal, modal containment/Escape/restoration, status announcements, 320px reflow, zoom, readable wrapping, safe-area controls and no keyboard-covered primary action. Preserve PL/EN/UK/RU language behavior; disclose untranslated copy rather than calling it fully localized. Automated checks cannot certify WCAG 2.2. Record manual screen-reader/zoom checks separately; do not substitute mobile emulation for physical-phone evidence.

### RT-13 — runbook and evidence agree (P1)

Rehearse the corrected commands against synthetic data, including startup, moderator bootstrap, attestation methods, shutdown and local restore. Cross-check documentation against OpenAPI/schema, not a copied handoff. Keep the corrected `tailscale serve --https=443 http://127.0.0.1:8000`; use Serve, never Funnel. Review the real certificate, origin and access policy in the human rehearsal.

Synchronize `GEMINI_HANDOFF.md`, `context/architecture.md`, `context/progress-tracker.md`, feature 001, `context/private-pilot-evidence.md`, `LAUNCH_READINESS.md` and relevant README sections. Currently some still describe operator admission as unimplemented/SMS-only. Replace ambiguous "all live gates open" with "mandatory release evidence remains incomplete" where that is the truth. Keep historical counts clearly dated; do not label a pass rate as code coverage.

## Human/network evidence — cannot be signed off by Gemini alone

Keep these rows BLOCKED or NOT RUN until actually observed. Arrange a supervised rehearsal with synthetic outings first; that is not authorization for an unsupervised real meetup.

| ID | Required observation | Evidence, without personal data |
| --- | --- | --- |
| H-01 | Two physical phones open the built site over trusted private HTTPS; authorized `/api` and `wss` work; a nonmember cannot reach it; the app listens only on loopback | OS/browser versions, time, access-test outcomes and redacted configuration; never a claim based only on Serve being configured |
| H-02 | Named trusted operator/backup consent to their powers and conduct actual separate age/account checks | Procedure/method and completion result; identities kept privately; no ID images, numbers, birth dates or QR captures |
| H-03 | Both people complete RT-07/08 and disconnect/restart tasks through the UI | Device observations, measured update delays, confusion/errors and fixes; test ledger only, no real payment |
| H-04 | Protected backup is copied off the host and successfully restored offline; old-snapshot revocation risk is addressed | Storage class/custodian, checksum outcome, restore duration and reconciliation result; never database contents |
| H-05 | Real screen-reader/zoom review and observed human usability | Tasks, findings, remaining limitations and reviewer role; do not claim universal device support/certification |
| H-06 | Staffed test window, incident stop, privacy/retention/appeal information and final founder go/no-go | Explicit decision after mandatory findings close; no assumption of 24/7 monitoring |

## Commands, reporting and handback

First run focused failing cases; then full backend pytest, frontend lint/build, both existing browser configurations, new operator browser tests and all recovery tests. Use `python -m pytest ../ops/test_disaster_recovery.py` (from `backend/`, with a disposable DB configured) to collect the full recovery suite: running that file directly only invokes its `__main__` drill, not every pytest test. Follow `qa/README.md` for the development isolation guard. Add/document a new operator command only when it exists and runs.

Report backend, recovery and browser results **separately**, including test count, failures/skips, interpreter/browser versions, exact command, date and tested revision. If there is no commit, provide a source SHA-256 manifest of the reviewed files excluding secrets/artifacts, plus the sanitized diff; do not invent a commit. Passing tests are not 100% coverage. No `.only`, skipped mandatory checks, broad catch-and-pass or retries-until-green.

Use this structure in `qa/PRIVATE_PILOT_REVIEW_RESULTS.md`:

```text
Review ID:
Status: PASS | FAIL | BLOCKED | NOT RUN
Environment / revision / role(s):
Command or human procedure:
Expected:
Observed:
Evidence location (sanitized):
Fix and regression, if any:
Residual risk / missing input:
```

For each defect include severity, file/line, shortest safe reproduction, expected versus observed behavior and the retest. P0 means unauthorized access, safety-gate bypass or sensitive-data exposure; P1 means a broken core pilot journey, unsafe recovery or unusable operator procedure. Hypotheses are not confirmed findings. P0/P1 defects block pilot approval until fixed/retested; any proposed exception needs an explicit founder decision and cannot override the agreed safety boundaries.

## Codex red-team acceptance after handback

Codex will inspect changes independently, rerun from a new DB/environment, and test variations: ordinary rather than moderator users, swapped IDs/roles, stale or revoked accounts, simultaneous requests, missing flags, state restored after restart, and events on already-open sockets. Codex will check that expected results are independent of the implementation and that the test fails if the relevant guard is removed in an isolated throwaway copy (never weaken the working/shared app).

Hand back: changed files; results matrix for RT-00 through RT-13 and H-01 through H-06; exact reproduction commands; sanitized evidence; unresolved founder inputs; and any boundaries you could not verify. Stop editing shared code during the independent review. **Codex review is pending until that handback is inspected; no live link is approved by this document.**
