# Codex independent retest 2 — bounded MR remediation handback

**Historical findings:** [Latest Codex verification](CODEX_MR2_VERIFICATION.md) closes the original MR2-01/02 failures in the tested runtime and records a separate P3 parser-unavailable fallback cleanup. Preserve the reproductions below as historical evidence, not open assignments.

Date: **2026-10-13**. Review-only: application, workflow and existing tests/probes were not modified. New diagnostic probes and review/handoff documentation were added.

## Disposition

**The previously reproduced native destination leaks are closed.** The corrected privacy sentinel, real join retry, admitted empty feed and runbook changes are present and their suites pass independently. Preserve the verified recovery and missed-chat fixes.

**Not an all-clear:** one repeatable CI prerequisite defect (P1) and one narrower web URL-validator defect (P2) remain. Neither is evidence of a new native-origin leak. No APK, hosted CI result, real phone/network result, accessibility certification or live invitation is approved by this review.

## Fresh independent evidence

| Check | Observed result |
| --- | --- |
| Backend + disaster recovery | **158 passed in 45.09s** (155 backend, including the 13 review cases, plus 3 recovery cases) |
| Preflight unit/integration tests | **12 passed in 1.31s** |
| Operator-pilot browser journeys | **16 passed in 1.8m**, 8 desktop Chromium + 8 Pixel 7 emulation |
| Six existing diagnostic probes | All exit 0; original private/recovery probe hashes preserved |
| Frontend | Build and lint exit 0; build 751ms. Existing chunk warnings: app 539.56 kB, MapLibre 1,062.98 kB |
| New CI prerequisite probe | **Exit 1**: real RT-17 fails without frontend dependencies, passes against installed local dependencies |
| New origin matrix probe | **Exit 1**: 24/25 checks pass; slash-backslash web destination incorrectly receives an auth header |
| Older development/no-demo browser suites, hosted CI/Docker, APK, H-01–H-06 | **NOT RUN in this retest** |

The first backend invocation used `JEV_MODE=disabled` and produced **156 passed / 2 failed** because two legacy audit tests require shadow mode. The final full rerun used `JEV_MODE=shadow` with `TYPESAFE_JEV_API_KEY` removed, another new disposable database, and no external AI requests. This configuration mismatch is recorded, not counted as a new application regression. The actual private pilot and operator browser harness keep Jev disabled.

### Reproduction

From `backend/`, use a new GUID-named temporary directory for `CARTMATE_DATABASE_PATH`; set `CARTMATE_ENV=development`, `CARTMATE_DEPLOYMENT=0`, `OTP_PROVIDER=console`, `SOS_PROVIDER=console`, `JEV_MODE=shadow`, remove `TYPESAFE_JEV_API_KEY`, and set `PYTHONUTF8=1`:

```powershell
python -m pytest -q -p no:cacheprovider . ../ops/test_disaster_recovery.py
```

The backend suite now needs **Node and installed `frontend/node_modules/typescript` before pytest**, because RT-17 executes the actual TypeScript modules. That prerequisite is the CI finding below, not a reason to skip RT-17.

From repository root:

```powershell
python -m pytest -q -p no:cacheprovider ops/test_pilot_preflight.py
python qa/codex_mvp_preflight_probe.py
python qa/codex_private_pilot_probe.py
python qa/codex_recovery_boundary_probe.py
node qa/codex_mr02_destination_probe.cjs
node qa/codex_mvp_config_probe.cjs
node qa/codex_mvp_reconnect_probe.cjs
python qa/codex_ci_prerequisite_probe.py
node qa/codex_origin_matrix_probe.cjs
```

Build then lint from `frontend/`. Run `npm run test:operator-pilot` from `qa/` with any inherited `CARTMATE_DATABASE_PATH` removed and `JEV_MODE=disabled`, so the harness owns fresh disposable storage. The reconnect probe owns a separate random loopback port/database. Windows subprocess/browser checks used approved execution outside the sandbox. No real SMS, paid service, public tunnel, ID collection or emergency call was made.

## MR2-01 — P1: fresh-checkout CI runs RT-17 before its prerequisites

Sources: `.github/workflows/ci.yml:33`, `:51`, `:58`; `backend/test_private_pilot_review.py:1340–1495`.

The backend pytest step comes before Node setup and frontend `npm ci`. RT-17 explicitly requires `frontend/node_modules/typescript` through a Node subprocess. Those dependencies exist on this workstation, but are not in a fresh checkout and are not installed by pip. A Node runtime preinstalled on the runner does not supply this absolute module path.

`qa/codex_ci_prerequisite_probe.py` extracts and runs the **existing RT-17 function** without importing the backend. Its installed-dependency positive control passes. The checkout-shaped temporary directory, with no frontend dependencies, fails with `MODULE_NOT_FOUND` for TypeScript. It also observes the actual workflow's incorrect step ordering. This is a local prerequisite reproduction, not a claim that a GitHub Actions run was launched.

**Gemini action:** move Node setup and frontend `npm ci` before the full backend pytest step, or place this required cross-stack test in an explicitly dependency-provisioned job without removing it from CI. Keep the regression mandatory; do not skip it when dependencies are missing. Prefer the simple step reorder in this single-job pipeline. Run a clean dependency-install rehearsal, the full suite and the probe; record hosted CI as NOT RUN until actually executed.

## MR2-02 — P2: the web helper approves a URL that resolves off-origin

Source: `frontend/src/api.ts:68`.

The web branch returns true immediately for any string beginning `/` but not `//`. That accepts a string beginning **slash then backslash**, such as the JS literal `'/\\different-review.example/api'`. The browser-compatible `URL` parser resolves it to `https://different-review.example/api`, not a path on the CartMate origin. `getAuthHeaders(candidate)` nevertheless returns an Authorization header.

The new `qa/codex_origin_matrix_probe.cjs` verifies this using the real transpiled source, a realistic `window.location`, synthetic token and intercepted fetch only. The other 24 checks pass: approved native origin and full paths, ignored stored override, other hosts/ports/suffixes/HTTP/userinfo denial, invalid/missing native configuration, cross-origin session clearing, web relative/absolute same-origin positives, ordinary off-origin denial, and conflicting WS settings rejected before a ticket fetch.

**Scope/impact:** current application call sites use fixed `/api` paths or the immutable approved base; this review did **not** find an attacker-controlled call site that supplies this candidate. Therefore this is a latent exported-helper validation defect, **not demonstrated end-to-end token exfiltration or a renewed native P1**.

**Gemini action:** parse every web candidate with `new URL(candidate, window.location.origin)` and compare the parsed origin to the current origin; do not use the leading-slash shortcut. Preserve relative-path and absolute-same-origin positive controls. Reject malformed/userinfo targets consistently. Add slash-backslash/control-character cases to permanent coverage and keep the new probe passing; do not blacklist only its sample hostname.

## Confirmed closures and limits

- **MR-02 original failures closed:** trusted native origin comes from build settings, not local storage. API and WS-ticket requests share approval; missing native config withholds bearer and rejects ticket acquisition. Conflicting web WS host is rejected before acquiring a ticket. Normal approved native REST/WSS works in source-level tests, not yet a physical WebView.
- **MR-01/R2 recovery protections stay closed:** the independent reconnect probe finds the missed message exactly once without reload and receives later live chat. Recovery probe confirms revoked socket close 1008, no private message to the old socket, preserved original account and same-code retry after injected persistence failure.
- **MR-03 stays closed:** real API health/preflight contract works and honestly reports absent moderator readiness as a blocker; an exit-0 contract probe is not a ready pilot.
- **MR-05 bounded assertion fixes accepted:** the host saves real private tag `Punktualność` and a unique note; owner REST contains them, companion REST/frames do not; companion REST omits the host's follow-up entry. Lost-response test now performs UI retry, checks the same request ID and displays pending copy. The admitted empty-feed test explicitly mocks `[]` and checks copy/create action. Stop/restart cleanup no longer swallows the exit-wait timeout and startup is inside `try/finally`.
- **Do not overstate coverage:** the browser WS privacy assertion searches tag/note values; it does not separately assert absence of every `would_meet_again` key. The keyboard/reflow checks cover selected dialogs and a 320px viewport, not all views, 400% zoom, VoiceOver/TalkBack or WCAG 2.2 conformance. Strengthen these as follow-up coverage without claiming a demonstrated server privacy leak.
- **Runbook corrections accepted:** bootstrap redeems trusted operator accounts before configuring moderator IDs/restarting/attesting; final preflight uses `--require-ready`; deployment phone-allowlist condition is accurately described. Do not grant a friend moderator powers unless they are an explicitly trusted backup operator.
- **Android remains scaffold-only:** inspected source specifies Gradle 8.14.3, AGP 8.13.0 and Java 21. `java`, `javac`, `adb`, `gradle`, `tailscale` were not found on PATH in this retest. This is not an exhaustive machine inventory. No native build/install or real HTTPS endpoint was verified.

## Preservation and source identity

Existing database start/end SHA-256: `C16993E46A0B2FF06F8893A28BAACF2D1067AA534DFCCDF974A8CDBDF6DD2D29`. It matches this handback and remained unchanged during the review. Its earlier differing hashes remain unexplained; it is not certified as a clean pilot seed. No contents were inspected. `ops/pilot_live.db` remains absent.

Repository-wide `git diff --check` reports pre-existing trailing whitespace in `PILOT_PLAYBOOK.md` (lines 84/86/88); this unrelated file was not edited. No staging, commit, push, deployment or cleanup of user files was performed.

`CODEX_WORK_DIRECTORY.md` remained untracked and untouched: `D65F80341F67F69B2F3BA879315767075CC1B3FADE7FC6DB8A02BBB8A919059C`.

```text
frontend/src/api.ts                    F625A525979A9850F26EBDBEC1362D0FFD1ED96221223F88ED542AF413C61A04
frontend/src/realtime/socket.ts        F230AA8FA5D0143B03F5B5522415FFEF1DE9F981DCFB68FB1BA830DAD5E127BD
backend/main.py                        7A3C3D1795EEAE8C59602E01C583EB9EBF9B37B44E726F33636346561DF7B1C6
backend/test_private_pilot_review.py   87A0FE1ECF6474CDDB6751DB406BFAFBC0B4B18F2F34BADC0EF417121E5C8FE8
qa/tests/operator-pilot.spec.ts        80CE5E50BFD3799C2242B549828FBAC4CE9905560FDE99EEEB11189B2234A736
.github/workflows/ci.yml               0F9A14E8E19B8A843B45B576EA6457DF9BD7CC6CD99F4F3CC6740C715745A524
```

## Next handback

Gemini owns the two bounded fixes above and their permanent regressions. No broad rewrite, new service or reopening of verified recovery/native issues is needed. Return exact commands/results and the clean-install evidence. H-01–H-06 remain **NOT RUN**: physical phones/private HTTPS, witnessed adult checks, real meetup/PIN/cancellation rehearsal, protected off-host backup/restore, assistive-technology/zoom testing, and staffed-window/founder go/no-go. An APK or green suite does not replace these gates.
