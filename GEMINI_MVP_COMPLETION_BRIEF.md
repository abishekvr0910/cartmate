# CartMate — Gemini completion brief for the private Android pilot

**Current handback authority:** [Codex MR retest](qa/CODEX_MVP_COMPLETION_RETEST.md). The reproduced chat/preflight defects close; MR-02 remains a P1 destination-policy failure, with bounded MR-05 and runbook/documentation corrections. Follow that narrowed assignment; previous all-complete claims are not independent approval. No APK or human/device acceptance.

Date: 2026-10-12. **Status: independent retest completed; M01/M03/M04/M05 remain partial.** Follow [MR-01–MR-06](qa/CODEX_MVP_COMPLETION_REVIEW.md) before claiming completion. Fresh existing suites pass, but three new probes reproduce engineering defects. Hardware/network/human checks remain NOT RUN. The inventory below records the original planning snapshot; native scaffold and CI additions now exist, but are not full acceptance.

## Objective and boundaries

Finish the engineering necessary for an installable, connected Android test build of the existing CartMate app, then hand back for independent Codex verification. Android first, iPhone later. Target is the private, supervised two-adult Silesia test, not Facebook feature parity, national launch or a public app-store release.

Read `AGENTS.md` and its required context, [feature 001](context/feature-specs/001-zero-cost-private-web-pilot.md), [feature 002](context/feature-specs/002-private-android-test-apk.md), and the **latest section** of [Codex retest](qa/CODEX_PRIVATE_PILOT_RETEST.md). This brief organizes those requirements and newly inspected CI/operations gaps; it does not erase safety gates or authorize external publication.

Gemini is the single writer for the implementation/harness/CI work below. Codex reviews the completed handback. Do not run overlapping writers in the shared checkout. Preserve user changes and `CODEX_WORK_DIRECTORY.md`. Never use `backend/cartmate.db` or `ops/pilot_live.db` for automation. No paid services, public tunnels, real SMS, automatic emergency calls, ID uploads, scraped users or employer/dormitory rosters. No new AI-driven safety decisions or engagement mechanics.

## What the gap check actually established

The previous independent run passed **153 backend + 3 recovery tests, 10 operator browser cases, both unchanged diagnostic probes, frontend build and lint**. That is dated evidence, not a new run for this planning task. Current inspected hashes for `backend/main.py` and `qa/tests/operator-pilot.spec.ts` still match that snapshot. R2-01/02's demonstrated recovery defects are closed; retain their regressions, do not reopen them without new evidence.

| Area | Existing work to preserve | Remaining gap / evidence |
| --- | --- | --- |
| Reliability | Real chat, mutual plans, PIN, ledger, both-role cancellation and recovery checks | R2-03: page reload substituted for offline/owned-server restart; successful completion/private follow-up not covered by the operator browser suite |
| Android | Capacitor CLI/core/config | No Android platform dependency/native project found; Java/ADB not on PATH in this check; no verified APK or handset run. REST and ticket acquisition still use relative `/api`. |
| Continuous verification | Backend, recovery, development/no-demo browsers and container smoke in CI | `.github/workflows/ci.yml` never runs `test:operator-pilot`; `qa/playwright.config.ts:11` excludes its spec from default tests. Thus the new journey is not covered by the existing CI steps. |
| Private operation | Windows pilot runbook, readiness endpoint, backup/restore scripts | `staging/preflight.py:49` insists on SMSAPI/Twilio, incompatible with the approved no-SMS operator mode. Windows runbook sets `CARTMATE_DEPLOYMENT=0` without explicitly setting exact CORS origin, Jev disabled or bounded session TTL. |
| User experience | Error handling, empty-feed create-outing action, focus hook, cancellation UI | Need meaningful keyboard/phone checks and native/network failure feedback. `qa/USABILITY_REHEARSAL.md` explicitly says prepared, not conducted. No basis for claiming users find it easy yet. |
| Community and demand | `PILOT_PLAYBOOK.md` and a prepared human experiment | No observed recruitment/attendance/repeat-use evidence. Playbook still contains historical paid SMS/Render instructions and wrong current admission wording. Code cannot manufacture willing nearby participants. |

Additional nuance: `App.tsx:205` stops fallback polling on reconnect; the chat history effect in `ActiveTripHUD.tsx` is keyed to room/user/language, not connection recovery. This is a **target for a missed-event regression**, not a newly proven runtime defect. `OpenNeighborhoodMap.tsx:41` already dynamically imports MapLibre after tile activation. Do not claim lazy map loading is missing or redo it solely because its emitted chunk is large.

## Execute in this order

### M01 — Finish the bounded reliability and security acceptance cases

Priority: required before live-use sign-off. Primary files: `qa/tests/operator-pilot.spec.ts`, `qa/operator_pilot_harness.py` or a separate isolated restart fixture, `backend/test_private_pilot_review.py`; narrowly change application code only when a test demonstrates the defect.

1. Replace `assert disconnected or True` with a real required close assertion and keep code-1008 and positive controls. Add the restored revoked-session WS-ticket denial missing from the claimed RT-11 result; distinguish HTTP ticket denial from socket close codes.
2. Add actual network interruption with two ordinary-member browser contexts. While one is offline, change the trip/chat from the other; reconnect **without reloading the page**. Assert fresh authorized state, missed message recovery without duplicates, and no resurrection of cancelled/revoked access.
3. Stop only the harness-owned server process, keep the browsers open, restart against the **same disposable database**, verify a fresh WS ticket and scope resubscription, then exchange another message. Persist the fixture across that owned restart; do not create a new DB or reset safety state to get green results.
4. Test failed/offline sends: retain the draft, show failure/pending accurately, never show successful delivery before acknowledgment. Test the lost-response/retry boundary; reconcile state rather than blindly resubmitting a potentially committed action.
5. Complete a separate successful outing through the UI and test private follow-up/mutual opt-in, including duplicate completion requests not double-counting the result. Retain separate host and companion cancellation paths.
6. If reconnect misses state, repair the smallest hydration/subscription behavior necessary. Scope refresh to the current authenticated user and authorized room; clear private state on denied access. Do not add broad polling as a substitute for demonstrated WS delivery.

Acceptance: explicit fail-closed assertions, no optional `isVisible()` branches, actual frames plus other-device DOM updates, bounded waits, no duplicate side effects and no helper routes in the shipped app. Both independent probes remain unchanged and pass. Record each remaining RT subcase separately; a passing reload test stays useful but is not a restart test.

### M02 — Make these checks part of repeatable CI

Priority: required before freezing the test candidate. Primary file: `.github/workflows/ci.yml` plus relevant QA config/docs.

- Add an explicit operator-pilot browser step after the built frontend and browser dependencies exist; retain the other suites and isolated ports/databases.
- Run both independent probes as distinct steps that fail on nonzero exit. Preserve backend/recovery and container checks; do not rename an unauthorized WS handshake as successful authenticated messaging.
- Give owned subprocesses bounded startup/shutdown and cleanup even on failed assertions. Do not swallow errors or turn failed tests into optional jobs.
- Keep screenshots/traces containing synthetic tokens private and short-lived; do not upload real session state or databases as ordinary artifacts.
- Document matching local verification commands. A configured workflow is not a hosted green run: GitHub login/remote/first push remain separate, optional founder-authorized operations. Never request a token in chat.

Acceptance: new suite is explicitly selected, unexpected failures stop the workflow, existing suites remain selected, and local commands run reproducibly. Label hosted execution NOT RUN until it actually runs.

### M03 — Build the private Android APK

Priority: next deliverable; toolchain preparation can proceed while M01 is being completed by the same writer. Follow [feature 002](context/feature-specs/002-private-android-test-apk.md); do not invent another mobile stack.

- Locate/install compatible SDK/JDK tooling with normal environment approvals; verify actual paths and installed versions. Do not silently purchase cloud builds or claim missing tools exist.
- Add the matching Android platform, generate the native project, preserve locked compatible dependencies and a reproducible Gradle build.
- Use one validated backend configuration for REST, ticket acquisition and secure WS. Preserve website same-origin behavior. An APK must not send its requests to an assumed server on the phone's own localhost.
- Validate the actual WebView Origin and narrowly configure CORS/WS policy. Keep HTTPS/WSS, fail visibly on missing configuration, reject insecure/unapproved endpoints and never disable certificates or auth/age gates.
- Bundle only client assets; exclude DBs, operator/session secrets and signing keys. Review local credential storage honestly without calling WebView storage encrypted secure storage.
- Produce an identifiable private debug APK with checksum, package/version/minimum-OS metadata, repeat-install signing behavior and installation instructions. No Play Store submission or iOS build.

Acceptance is four separate states: **built**, **installed**, **connected synthetic journey passed**, **human pilot approved**. The first is not evidence for the other three. If tools or the private endpoint are unavailable, finish unaffected engineering and report the exact remaining input; do not produce a fake-success APK.

### M04 — Make private operation repeatable and truthful

Priority: required before two-person connected rehearsal. Reuse `ops/PILOT_RUNBOOK_WINDOWS.md`, `ops/RUNBOOK.md` and `staging/preflight.py`; add a separate operator-pilot preflight if that keeps the parked carrier-backed contract intact.

- Provide explicit, validated private-pilot configuration: staging/operator flags, actual HTTPS Origin, SOS disabled, Jev disabled, session lifetime appropriate to the staffed test window, correct bundle/database paths and one worker. Do not silently hardcode an unapproved real hostname or hours.
- Explain what `CARTMATE_DEPLOYMENT=0` disables and verify equivalent necessary pilot safety/readiness checks. Do not claim deployment validation ran when it did not, or enable console OTP dispatch to solve startup issues.
- An operator-mode preflight must check honest environment/readiness, no demo auth, no public/helper endpoints, direct-112-only policy and private origin configuration without sending OTPs or external AI input. Preserve the original carrier-backed preflight for its parked mode if reused. Add isolated positive/negative tests.
- Separate first-time bootstrap from routine startup. No automatic participant promotion to moderator, seed reset or real-database replacement. If providing a launcher, stop only the process it owns and bind loopback.
- Reuse online backup and offline restore tools with explicit absolute disposable paths for tests. Document encrypted off-device custody, backup freshness, restore/revocation reconciliation and incident stop. Do not claim a local `.db` copy is encrypted or offsite.
- Record basic service availability, readiness and actionable failures without logging tokens, chats or identity data. No 24/7 coverage claim or new paid telemetry service.

Acceptance: a second operator can follow the exact commands on synthetic state without hidden environment assumptions; wrong config fails clearly. Actual private reachability, outsider denial and off-device restore remain human/environment evidence until observed.

### M05 — Verify usability and focused accessibility on the delivered flow

Priority: fix blocking friction before the handset rehearsal; broader styling is not a prerequisite. Reuse `useDialogFocus`, `locales.ts`, existing components and `qa/USABILITY_REHEARSAL.md`.

- Test activation, recovery and pending-age forms with named controls, Tab/Shift+Tab wraparound, associated errors, Escape and focus return. One Tab remaining inside the default modal is insufficient.
- Measure 320px reflow **after the relevant form is visible**; check larger text/zoom, keyboard-covered actions, Android back behavior and background/foreground recovery on the actual test build. Keep physical TalkBack findings distinct from browser emulation.
- Make disconnection/reconnecting/failed-send state understandable; preserve drafts. Reuse existing status hooks and error state rather than adding a second network client or simulated delivery indicators.
- Test the existing empty feed and create-outing action. If a filter hides all outings, make filter reset understandable; never add fabricated nearby people or fake popularity. Preserve clear activity/time/duration/cost details before acceptance.
- Keep tested Polish copy understandable, preserve the PL/EN/UK/RU locale structure, translate changed messages appropriately and disclose existing untranslated paths instead of claiming full localization.
- Update the usability script for operator activation/recovery rather than requiring expired SMS OTP in the no-SMS session. Observe understanding of “pending,” cost splitting, cancellation and emergency limits without coaching.

Acceptance: blocking issues have concrete regressions or device retests; manual usability remains NOT RUN until real consenting people participate. Automated assertions do not certify WCAG compliance or prove the UI is popular.

### M06 — Prepare the human pilot and learn whether people want it

Priority: prepare now; execute only after engineering/human approval. Primary files: `PILOT_PLAYBOOK.md`, `qa/USABILITY_REHEARSAL.md`, `context/private-pilot-evidence.md`.

- Reconcile historical SMS/Render/website-only instructions with current operator admission and Android-first testing. Never describe operator activation as phone/identity verification. Keep the second authorized adult check for the operator and existing no-self-approval rule.
- Prepare one small, voluntary public-place/time-window rehearsal with the founder's consenting adult friend. Wider dorm/company recruitment is a later choice, not authorized by this brief. No bulk outreach, roster ingestion or contact scraping.
- Use an unfilled, minimal observation sheet: task completed unaided, point of confusion, whether an outing actually occurred, comfort/concerns, and voluntary willingness to repeat. Record counts and denominators, not invented percentages or representative market claims from two friends.
- Reuse the existing plan/privacy/safety notices, flag actual placeholders for the founder/reviewer, and explain support hours and stop conditions. Gemini cannot invent the operator's availability, a legal compliance opinion or witness an ID remotely by asserting a database flag.
- Do not add an analytics SDK, behavioral profiling, punitive streaks, addictive feed ranking or extra AI features to “create retention.” Successful real-world use is the experiment.

Acceptance: documents are ready to use and their historical instructions cannot mislead the operator. Participant outcomes remain blank until observed. Software cannot mark community traction or human approval complete.

## Performance: measured follow-up, not an extra rewrite

The last build emitted about 538 kB app JS and 1,063 kB MapLibre JS before compression; those warnings alone do not prove sluggish rendering. MapLibre already loads on demand. On the target phone, capture startup/network/render responsiveness for activation, feed and chat, then fix reproducible blocking stalls. Record device/network/conditions and before/after results. Do not remove functionality or rewrite React solely to silence a size warning. No numerical “Facebook-level performance” claim without measurements.

## Inputs only the founder/environment can supply

| Input | Needed for | Work that can continue without it |
| --- | --- | --- |
| Available Android phone; model/version when accessible | Actual install, compatibility, keyboard/TalkBack checks | Native preparation, synthetic web tests |
| Private-network enrollment and verified HTTPS backend address; host kept awake | Connected APK/phone rehearsal | Build setup, endpoint validation tests, local synthetic journeys |
| Trusted operator/backup, witnessed checks, staffed window, final go/no-go | Real admitted participation | All safe implementation and automated verification |
| Approved protected off-host backup destination and custodian | Real off-device recovery evidence | Disposable backup/restore drills and instructions |
| Consent/support/retention decisions and voluntary participants | Human usability and real pilot | Blank rehearsal materials and engineering |

Do not ask for ID photos, OTPs, API keys or passwords in chat. No paid provider, registered business, app-store account or GitHub push is a prerequisite for the local build itself. If a particular external action needs approval, name it rather than inventing credentials or assuming consent.

## Definition of done and handback

Continue through all unblocked engineering units; do not stop after writing another plan or one green suite. For each M01–M06 report **DONE / PARTIAL / BLOCKED / NOT RUN**, changed files, exact commands and evidence. Preserve all existing tests. Do not lower acceptance criteria or alter the independent probes to manufacture a pass.

Hand back:

1. Reviewed source commit or SHA-256 manifest, narrow diff and dependency/native permission changes.
2. Separate backend, recovery, development/no-demo/operator browser and probe results, with failures/skips and dates; build warnings honestly listed.
3. APK artifact and checksum **only if actually built**, install/connected-test results separately, and reproducible build instructions.
4. Updated active docs and a short operator checklist with remaining founder inputs; no conflicting all-complete banner.
5. Human H-01..H-06 evidence or explicit NOT RUN. Stop shared edits for Codex independent retest before approving live participation.

This brief was produced by repository inspection and the prior independent verification snapshot. No application implementation, installation, deployment or new test-suite run occurred while preparing it.
