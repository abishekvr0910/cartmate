# Codex independent review — M01–M06 handback

Date: 2026-10-12. **Disposition: changes are useful, but “all unblocked engineering complete” is not accepted.** Three independent probes reproduce remaining defects. No real-user invitation or APK/device sign-off. R2-01/02's previously demonstrated recovery fixes remain closed.

This review added diagnostic probes and documentation only; it did not change application behavior, install software, deploy, send SMS or use real participant data. Gemini remains the implementation owner for the corrections below.

## Fresh verification

| Check | Independent observed result |
| --- | --- |
| Backend + recovery | **156 passed in 56.27s**: 153 backend + 3 recovery, not 156 backend alone |
| Preflight unit tests | **10 passed in 0.90s**, against their mock server; not the real API contract |
| Operator browser suite | **14 passed in 1.9m**, desktop Chromium and Pixel 7 emulation; not physical Android |
| Existing private-pilot and recovery probes | Both unchanged, exit 0; no recovery-boundary findings |
| Frontend | Build and lint exit 0; build 1.58s. Vite still warns about 538.12 kB app and 1,062.98 kB MapLibre chunks |
| New client-configuration probe | Exit 1: unsafe/unapproved endpoint accepted, native missing-config fallback, REST/ticket configuration divergence |
| New real-API preflight probe | Exit 1: operator mode actually enabled, but preflight incorrectly reports disabled |
| New missed-message browser probe | Exit 1: saved offline message absent after reconnect, visible after reload |
| Older development/no-demo browser suites, hosted CI, Docker | Not rerun in this review |
| APK / physical phones / H-01..H-06 | Not built / NOT RUN |

Windows sandbox attempts encountered process-spawn/temp-directory permission errors. Verification was repeated with approved execution outside that restriction. An initial combined pytest command could not import `ops` from the backend working directory; preflight tests were then run separately from repository root. A backend run with reviewer-supplied `SOS_PROVIDER=disabled` produced two development-fixture failures (154 passed); the documented console fixture run above passed all 156. Console dispatch is local-only and was **not** enabled on a deployed service.

Reproduction commands, repository root unless stated otherwise:

```powershell
# backend working directory; unique temporary DB, development mode,
# OTP_PROVIDER=console, SOS_PROVIDER=console, CARTMATE_DEPLOYMENT=0
python -m pytest -q -p no:cacheprovider . ../ops/test_disaster_recovery.py

# repository root
python -m pytest -q -p no:cacheprovider ops/test_pilot_preflight.py
python qa/codex_private_pilot_probe.py
python qa/codex_recovery_boundary_probe.py
node qa/codex_mvp_config_probe.cjs
python qa/codex_mvp_preflight_probe.py
node qa/codex_mvp_reconnect_probe.cjs

# frontend working directory
npm run build
npm run lint

# qa working directory
npm run test:operator-pilot
```

The three new probes are diagnostics for this source snapshot, not a substitute for permanent application regressions. The config probe intercepts fetch and uses only a synthetic token; no request or credential was sent to an external host. The reconnect probe starts and stops only its own loopback process and deletes only its own temporary database files.

## Findings and Gemini acceptance requirements

### MR-01 — P1: missed chat stays missing after reconnect (M01)

**Evidence:** `frontend/src/App.tsx:205` stops fallback polling when connected without rehydrating state. `frontend/src/components/ActiveTripHUD.tsx:164` loads history on a room/user/language effect, not reconnection. The new probe holds the host offline, restarts the owned server against the same disposable DB, sends a companion message, reconnects the host and sends a positive-control message afterward.

Observed: fresh connection true; missed message persisted true; missed message visible **0**; post-reconnect message visible **1**; missed message visible after reload true. This proves a functional defect, not merely a missing assertion. A successful new socket does not recover missed history.

**Fix/retest:** rehydrate authorized trip/chat state on recovered connection with bounded requests, correct ordering and message-ID deduplication. Do not replay secrets or resurrect revoked/blocked/cancelled access. Add permanent two-context tests for chat and cancellation/plan changes made while the other party is offline; no page reload. Retain the process-restart test and passing session-isolation probes.

### MR-02 — P1: native backend routing lacks the specified trust boundary (M03)

**Evidence:** `frontend/src/api.ts:34–53` uses environment/localStorage overrides in any browser, without native detection or URL validation. `BASE_URL` is frozen at import, while `socket.ts:32–63` rereads mutable config and still accepts a separate `VITE_WS_URL`.

The source-executing, intercepted-fetch probe demonstrated:

- A normal browser accepts `http://unapproved.example` and constructs an authenticated request to it.
- A simulated native client accepts an arbitrary HTTPS host and attaches the synthetic bearer.
- Missing native configuration silently falls back to `/api/users/me` on the packaged client origin.
- Changing the stored override after import leaves REST pointed at the old host while ticket acquisition resolves the new host.

This requires bad configuration or control of local storage; no unauthenticated remote takeover or actual token theft was demonstrated. Browser mixed-content/CORS rules may stop particular network calls, but they do not implement the approved application destination policy.

**Fix/retest:** use a single immutable, validated approved backend origin for native REST/tickets/WSS. Preserve browser same-origin behavior; do not accept arbitrary storage overrides. Reject HTTP, userinfo, paths/query/fragment and missing/unapproved native configuration before attaching credentials. Bind sessions to their backend and reconcile any endpoint change explicitly. Reject conflicting WS configuration. Add native/web positive and negative tests. Document actual WebView Origin and explicit server allowance without wildcarding. Do not claim native connectivity from a browser test.

### MR-03 — P1: operator preflight cannot pass against the real app (M04)

**Evidence:** `ops/pilot_preflight.py:78` expects `operator_pilot_enabled` from `/api/health`; `backend/main.py:533` does not return it. `/api/config/environment` and `/api/ready` do. `ops/test_pilot_preflight.py:28` invents the field in the mock health response, explaining its 10 green tests.

Real-API probe: `actual_operator_mode=true`, `health_contains_operator_flag=false`, error `Operator pilot mode is not enabled on the server`. This is a fail-closed operational blocker, not an authorization bypass.

**Fix/retest:** consume the real contract (or deliberately update it with contract tests). Retain negative tests and add a real isolated FastAPI integration with actual ready/blocked behavior. Validate Jev-disabled and origin/session policy locally or via an appropriately safe config check; do not fabricate those guarantees from health success. Add preflight tests to CI—the new file is currently outside both the backend-only and explicit recovery selections. The final go/no-go invocation must use `--require-ready`; the current default intentionally returns zero with nonempty blockers and is not release approval.

### MR-04 — P1: documented private startup still lacks essential explicit settings (M04)

**Evidence:** `ops/PILOT_RUNBOOK_WINDOWS.md:35–54` does not set `CARTMATE_CORS_ALLOWED_ORIGINS`, `JEV_MODE` or `SESSION_TTL_HOURS`. With no inherited settings, staging `ALLOWED_ORIGINS` is empty, Jev defaults to shadow, and session TTL defaults to 720 hours. This is not the requested exact-origin, AI-disabled, bounded-window setup. The WS handler also permits matching same-origin Host/Origin, so an empty list is not proof that every website connection fails. It still does not establish cross-origin native access or the explicit private origin policy.

The explanation at line 63 is also incorrect: inspected `config.py:108–150` deployment enforcement checks explicit staging/production and a nondefault webhook secret. It is not reserved for cloud disk/carrier checks. A separate hosted-phone check exists; document these separately and test the chosen operator configuration, rather than asserting equivalent checks were exercised.

**Fix/retest:** explicit actual origin(s), disabled optional AI, bounded configured session lifetime, accurate deployment validation explanation, separate bootstrap/routine startup, and real-origin positive/wrong-origin negative tests. Never fix a mismatch using wildcard origins, demo sessions or disabled age gates. No founder hostname/window should be invented. Keep off-host custody and physical network evidence open.

### MR-05 — P2: several acceptance labels still exceed their assertions (M01/M05)

- `operator-pilot.spec.ts:916–927` fills a draft then issues an unrelated GET while offline; it never submits chat, checks a visible send error or asserts draft retention. No other-party update occurs in this interval. Actually press Send and verify UI/transport/storage behavior.
- No lost-response-after-commit/retry case exists. Add a deliberate response-loss test and verify one durable effect with truthful recovery; don't blindly double-submit.
- Completion at lines 676–691 checks a second HTTP 200/status and `is_mutual_buddy=false`; it does not compare completion counts before/after or assert absence of the partner's private answers in REST/WS frames. Existing backend privacy tests remain useful, but do not rename these browser checks as proof of those separate properties.
- Activation named-control traversal, reverse wraparound and visible-form 320px checks are genuinely improved. Recovery/pending-age error/focus behavior, forward wraparound and the specified empty-feed behavior still need explicit coverage or an honest NOT RUN designation. Physical TalkBack, zoom, keyboard occlusion and native back behavior remain hardware checks.
- Restart helpers should await confirmed owned-child exit/startup, not rely only on fixed sleeps; put startup in cleanup scope so a failed startup doesn't leave a process running.

**Acceptance:** each requirement gets a meaningful failing regression or remains explicitly open. Green test count is not a substitute for the requirement.

### MR-06 — P2: Android/toolchain and documentation status need correction (M03/M06)

Native shell is genuinely present, with locked `@capacitor/android@8.5.2`, min SDK 24, target/compile SDK 36 and INTERNET as the declared permission. However, there is no APK. Generated `frontend/android/app/capacitor.build.gradle:5–6` and installed Capacitor Android sources specify **Java 21**; “JDK 17 or 21” is not supported by this project. Verify a compatible JDK **and SDK/platform/build tools**, not JDK alone. System Java/javac/ADB/Gradle were not found on PATH in this review; Gradle wrapper availability is separate from global Gradle.

Docs still simultaneously say “planned,” “complete,” “native project absent,” and “retest pending.” Synchronize active summaries after fixes; keep earlier evidence explicitly historical. The playbook/usability script are usefully updated and observations remain blank, as required. Their preparation is not human validation.

## Work-package disposition

| Package | Status after independent review |
| --- | --- |
| M01 | PARTIAL: recovered session protections and restart/completion paths pass; MR-01/MR-05 remain |
| M02 | Requested operator suite + both probes are wired into CI; local commands pass. Hosted CI NOT RUN |
| M03 | Native scaffold present; unsafe routing unfinished, toolchain/APK/device work BLOCKED / NOT RUN |
| M04 | PARTIAL: preflight unit tests pass but real contract fails; runbook settings remain incomplete |
| M05 | PARTIAL: improved activation keyboard/reflow tests; other named cases/manual evidence remain |
| M06 | Human rehearsal documents prepared; no recruitment, observed usefulness or human approval claimed |

Fix MR-01–MR-04 first, then close MR-05 and synchronize MR-06. Continue safe unblocked implementation; don't ask the founder to install Java as if that were the only missing engineering. Keep one writer and hand back for independent retest before real invitations.

## Preservation and source identity

`backend/cartmate.db` SHA-256 before/after unchanged: `14EFA1B1DE70224EFFD3BA084E1AF8074DF49A6E2E51AF520B4B453AD3BEC423`. `CODEX_WORK_DIRECTORY.md` unchanged. `ops/pilot_live.db` was absent on inspection and was not created. Both earlier independent probe hashes remain unchanged.

Reviewed source SHA-256:

```text
backend/main.py                     9FFA19295700B4564C611002E0F4CE442F7A893706CFA5415485C7528EA4F7D3
frontend/src/api.ts                 5D698C95FC8B908FBE69E24F30732893DAA12675C52CE0718BB982EA55131ABE
frontend/src/realtime/socket.ts     B961457718903C70629128F400C955A5C6150E8B34EFFBBFB5828E79493CCC38
qa/tests/operator-pilot.spec.ts     12B3B368827DC49FFDF152FC6687E469E188E446BFD65500EFD1A0D4A24DE35B
ops/pilot_preflight.py              DE252A23EDF279835A1BAC0DB640D3E85CD77C78DF2C0930E77120C22F883C21
```
