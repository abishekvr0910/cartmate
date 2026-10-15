# Codex independent retest — MR-01–MR-06

**Historical review:** superseded by [Codex retest 2, 2026-10-13](CODEX_MVP_COMPLETION_RETEST_2.md). Original native leaks and bounded assertion/runbook gaps are now accepted as fixed; use the new report for MR2-01/02 follow-ups. Preserve this report as the original reproduction evidence.

Date: 2026-10-12. **Disposition: substantial fixes verified; MR-02 remains a P1 blocker, MR-05 acceptance and some runbook/documentation work remain partial.** No real-user invitation, APK or human/device sign-off. This supersedes the implementation handback's all-remediated claim, not the earlier verified recovery protections.

## Fresh execution evidence

| Check | Independently observed |
| --- | --- |
| Backend + disaster recovery | **157 passed in 34.70s** (154 backend, including 12 review cases, plus 3 recovery cases) |
| Operator preflight | **12 passed in 1.36s** from repository root |
| Operator Playwright | **16 passed in 1.4m**; Chromium desktop and Pixel 7 emulation |
| Existing five diagnostic probes | All exit 0; original private/recovery probe hashes unchanged |
| Frontend | Build/lint exit 0; build 662ms. Vite still warns about 539.14 kB app and 1,062.98 kB MapLibre chunks |
| New destination-policy probe | **Exit 1**, reproduces remaining MR-02 failures |
| Older development/no-demo suites, hosted CI/Docker, APK, physical/network/human checks | NOT RUN in this retest |

Tests used fresh disposable SQLite state and approved execution outside the Windows sandbox. Backend fixtures used development console OTP/SOS (no external dispatch); browser harnesses used staging with SOS disabled. No application behavior was changed by Codex. Only this review, its new intercepted-fetch diagnostic, and handoff summaries were edited.

Commands: from `backend/`, with a unique `CARTMATE_DATABASE_PATH`, `CARTMATE_ENV=development`, `CARTMATE_DEPLOYMENT=0`, `OTP_PROVIDER=console`, `SOS_PROVIDER=console`: `python -m pytest -q -p no:cacheprovider . ../ops/test_disaster_recovery.py`. From root: `python -m pytest -q -p no:cacheprovider ops/test_pilot_preflight.py`; run the five existing `qa/codex_*` probes listed in the previous review. From `frontend/`: `npm run build` and `npm run lint`. From `qa/`: `npm run test:operator-pilot`.

## What can close

- **MR-01's reproduced missed-chat defect:** closed. The independent owned-server restart probe now observes the persisted missed message exactly once without reload, with subsequent live messaging still working. Keep testing offline cancellation/plan changes as distinct cases rather than treating chat as proof of every state transition.
- **MR-03's real-health contract mismatch:** closed. Real API now returns the operator flag; the unchanged probe reports `contract_error=null` and correctly retains the absent-moderator readiness blocker. This does not mean the pilot is ready. Preflight tests and the five existing probes are now selected in CI; hosted execution remains unobserved.
- **MR-04's omitted settings:** explicit origins, disabled Jev and 24-hour session setting are present. The new regression verifies CORS headers and configured values, not a physical WebView or authenticated WSS journey. Remaining runbook corrections are listed below.
- **MR-05 improvements:** genuine offline form submission/draft retention, completion-count idempotency, named activation controls, wraparound, recovery alert and process-exit waiting are present and their suite passes. Several labels still exceed their assertions.
- **MR-06 Java requirement:** generated project and installed Capacitor Android code specify Java 21. Native scaffold exists; no APK. The handoff's attribution to “Gradle 8.11.1” is inaccurate: wrapper is **8.14.3**, Android Gradle Plugin **8.13.0**, and Java 21 is specified by the source-compatibility settings. Java/javac/ADB/global Gradle still not found on PATH; no installations performed.

## MR-02 — still P1: a hostname blacklist is not an approved-origin policy

Sources: `frontend/src/api.ts:44–80`, `frontend/src/api.ts:161–185`, `frontend/src/realtime/socket.ts:32–72`.

`validateApprovedBackendOrigin()` accepts syntactically matching HTTPS hosts, except names containing the literal word **`unapproved`** or ending in `.invalid`. There is no approved-origin comparison. The former probe used `https://unapproved.example`, so it passes while other unapproved hosts remain accepted. This is a property missing from implementation/testing, not an allegation about the implementer's intent.

Run:

```powershell
node qa/codex_mr02_destination_probe.cjs
```

It evaluates the actual TypeScript API and socket modules with intercepted fetch, synthetic credentials and reserved example hosts. **No network requests or real credentials leave the process.** Observations:

| Scenario | Actual result |
| --- | --- |
| Native stored `https://outside.example` | Both user request and WS-ticket request attach the synthetic bearer |
| Native stored `https://ordinary-review.example` | Same acceptance and bearer attachment |
| Missing native config | REST withholds bearer, but WS-ticket fetch attaches it to the `.invalid` placeholder |
| Browser with `VITE_WS_URL=wss://outside.example/ws` | Same-origin ticket acquisition followed by a URL carrying that ticket to the unrelated host |

The `.invalid` placeholder is not demonstrated external exfiltration; it shows missing configuration does not stop the credential-bearing ticket attempt. The host-override findings require bad configuration or control of local storage/build settings; no unauthenticated remote ability to change those settings was established.

**Required bounded fix:**

1. Establish one trusted, build/operator-approved exact backend origin for native use. Validate with URL parsing, compare normalized origin to the approved value, reject arbitrary storage destinations, and fail visibly before any request when configuration is absent/invalid. Do not blacklist test words.
2. Use that same policy for REST **and** ticket fetches; derive WSS from it. For web, enforce the current website origin or reject a conflicting WS override before ticket acquisition. Don't send an existing session to a newly selected backend; explicitly bind/clear sessions across endpoint changes.
3. Add permanent tests using multiple independently chosen nonapproved hosts, missing config, credential-free failure, conflicting WS settings and a positive approved endpoint. Existing probes remain useful but are not the entire security specification. Do not manufacture approval for example domains just to pass.

This is the main remaining code/security blocker; Android SDK installation alone does not resolve it.

## MR-05 — remaining evidence gaps, not a demonstrated server privacy leak

1. **Wrong privacy sentinel:** `operator-pilot.spec.ts:684,719–723` clicks and searches for `Punktualność ⏰`. In `ActiveTripHUD.tsx`, that is a review badge in `selectedBadges`, not a private follow-up tag. Private `followUpVibeTags` uses `Punktualność` without the emoji; `would_meet_again` and private feedback are not checked. A leaked follow-up object can therefore escape these assertions. Populate unique private feedback/tag values, verify the caller sees them, then require their absence (and partner answers) in the other participant's REST and relevant received WS payloads. Preserve backend privacy checks; no new runtime leak was demonstrated here.
2. **Lost-response test does not retry or prove the participant's status:** lines 1168–1212 commit once, abort the response, reload, find the destination title and count one server record. Add a real retry and assert the same request ID plus an honest pending state in the participant UI. Don't equate a visible outing title with knowledge of whether joining succeeded.
3. **Empty-feed assertion is only shell visibility:** lines 1110–1113 require `main` or `#root`. Use an admitted account and a deliberately empty feed; assert explanatory copy and the create-outing action. Keep recovery keyboard/error focus checks separate from activation traversal. The accessibility skill was used to distinguish these selected assertions from unperformed screen-reader/zoom verification.
4. **Restart failure cleanup remains partial:** the new stop helper waits for exit but catches its timeout; initial `waitForHarness` is still outside `try/finally`. Do not treat a timeout as successful shutdown or let failed startup escape owned-process cleanup.

## Remaining runbook/doc corrections (MR-04/MR-06)

- The readiness command in section 2.3 still omits `--require-ready`. Use it for the final go/no-go command; bootstrap diagnostic checks may deliberately report HOLD. Do not use exit 0 with blockers as permission to invite.
- The bootstrap note says to attest before configuring moderator IDs, but the endpoint requires an authorized moderator. Correct sequence: issue/redeem the trusted operator accounts, obtain IDs, configure allowlist and restart, then perform separate witnessed attestations. Never promote an ordinary participant by default; preserve the existing full-privilege warning.
- Configuration documentation should distinguish what the deployment guard actually checks. Do not claim its staging phone allowlist check only applies to carrier-backed providers if the code's condition is simply deployed staging.
- Active documents still contain stale “native project absent,” “not implemented,” old-count and pending/complete claims. Use this retest as current authority and clearly label historical snapshots. The native project, build and installed/connected phone are different milestones.

## Database/source preservation

Before any runtime tests, the observed `backend/cartmate.db` SHA-256 was **`C3F39A589559A48686B06B40848F3F1A3708F2EEF31332B716545C867DD0D690`**; it remained identical after the retest. This differs from Gemini's supplied `748DF725...` and Codex's earlier `14EFA1B1...` snapshot. Hashes establish that the bytes differ; this review did **not** determine who/what changed them or infer corruption. Do not use that unverified existing database as a clean pilot seed. No database contents were inspected or modified. `ops/pilot_live.db` is absent. `CODEX_WORK_DIRECTORY.md` hash remains `D65F80341F67F69B2F3BA879315767075CC1B3FADE7FC6DB8A02BBB8A919059C`.

Reviewed source fingerprints:

```text
frontend/src/api.ts              585A7FD56C69BEAE99360E9FB5721FBA31C59DAF1218DFCB4563E1B8DBB30519
frontend/src/realtime/socket.ts  DD403B8D6D9416F63358FD694F0E588E02244869298B68F4B1240DBEB00B0FA1
frontend/src/App.tsx             70C239A636D63BF01AA7BF6E273CB76BA3249E5D71FEFAF5ABDE96DA00F04842
backend/main.py                  7A3C3D1795EEAE8C59602E01C583EB9EBF9B37B44E726F33636346561DF7B1C6
qa/tests/operator-pilot.spec.ts  A3FD0F7E532A0F8CE013D00E551CDFA0FEBBF4A36D6B8091B330710D4FE0AD3B
```

**Next handback:** Gemini fixes the destination policy first, closes or honestly labels the bounded assertion/runbook gaps, and returns exact results. Do not reopen the verified recovery or missed-chat fixes. H-01–H-06 stay NOT RUN; no paid service, public tunnel, actual SMS, real ID collection or invitation is authorized.
