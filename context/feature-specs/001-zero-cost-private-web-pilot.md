# 001 — Zero-cost private website pilot

**2026-10-14 scope update:** The founder approved one paid EC2 staging host, superseding this spec's local/Tailscale hosting assumptions only. The adult, authorization, backup, accessibility and H-01–H-06 gates remain. A small across-tab trip-chat cue was implemented and documented in [the product-pattern review](../../PRODUCT_PATTERN_REVIEW_2026-10-14.md); it does not alter server membership or read receipts. The older MR3/APK status immediately below is historical.

**Current independent verification (2026-10-13):** [Codex verification](../../qa/CODEX_MR2_VERIFICATION.md) closes the original MR2-01/02 failures in the tested runtime, preserving prior recovery/reconnect/native/journey fixes. 158 backend/DR, 12 preflight, 16 operator browser cases, eight existing probes and build/lint pass; fresh offline dependency install + RT-17 passes. One **MR3-01 P3** parser-unavailable fallback cleanup remains, without a demonstrated supported-browser exploit.

Status: **Local automated journeys pass; Slice D human/private-network/off-host gates remain incomplete.** H-01–H-06 are NOT RUN. Gemini owns the small fallback cleanup and focused regression. Android preparation is separately authorized in feature 002, but no APK or real-user invitation is approved. Older MR/R2 reports are historical evidence, not current instructions to redo closed work.

## Goal and value

Let two consenting adults in Silesia open the real CartMate website on their own phones during a supervised, time-limited test without paying for an SMS gateway or cloud host. Preserve truthful authentication, 18+ admission, private discovery, usable chat/meeting flow and durable local data. A GitHub link or static frontend preview is not this feature.

## Decisions and limits

- Use the existing React/FastAPI/SQLite application. Proposed network delivery is a **private HTTPS tailnet** to a loopback-bound app on the founder's computer; confirm acceptability with the founder and test the actual network before calling it operational. Do not silently substitute a public tunnel. The free Tailscale Personal/Serve plan is a candidate, not an installed dependency: [Personal plan](https://tailscale.com/pricing), [Serve](https://tailscale.com/docs/features/tailscale-serve).
- Build a **new staging-only operator-admission provenance** for this tiny pilot, independent of SMS. Operator-issued activation secrets are delivered in person only after a human checks the intended adult. Keep `phone_verified_at` null unless a real SMS OTP succeeds. Never reuse development console OTP, seeded tokens or `1234` in a shared service. Do not say the operator code proves ownership of a phone number.
- The human 18+ check still must use a live, approved procedure; the existing manual attestation may be adapted to a separately admitted account, but self-approval remains forbidden, audit/expiry/revocation remain enforced and production continues to deny live use. No ID numbers, images, birth dates or card copies are stored. The operator's own admission requires another trusted adult.
- SOS remains direct `tel:112` only; no SMS to 112 or contacts. Existing invite, block, report, region, trip and group authorization invariants remain in force.
- This feature does not authorize paid accounts, public URLs, broad signups, automated payments or national live outings. Android test packaging is separately approved as the next milestone in [feature 002](002-private-android-test-apk.md), without relaxing this feature's safety/human gates.

## Slice A — inventory and threat model (no behavior change)

Read and map the gates in `backend/config.py`, `backend/main.py`, `backend/auth_providers.py`, `backend/storage.py`, `backend/database.py`, `backend/models.py`, `frontend/src/components/AuthModal.tsx`, `frontend/src/App.tsx`, `frontend/src/api.ts`, and the current staging tests. Document where SMS is currently required for registration, login, live posting, WebSockets, operator age attestation and `/api/ready`. Propose the smallest separate account-provenance contract; explain the threat model for stolen activation codes, local host compromise, tailnet membership, leaked bearer tokens and absent operator coverage. Do not begin coding if a missing founder choice would materially change the trust boundary.

## Slice B — durable, bounded operator admission

Within staging and behind a new explicit feature flag, add an operator-owned CLI or moderator action to issue a cryptographically random, short-lived, single-use activation secret for a specifically approved participant. Store only a safe verifier and minimal issue/redeem/revoke audit, transactionally. An untrusted browser must not issue secrets or nominate itself as operator. Redemption creates or activates a real account and a normal revocable session; repeated, expired, wrong, uninvited, suspended or blocked attempts fail closed with rate limits. Tie the activation to the intended account and require an operator to verify the person's presence and informed consent out of band. Do not synthesize a `+48` number, fake email verification or SMS provenance.

Add a distinct `operator_in_person` (or equivalently explicit) account-assurance marker with timestamps and expiry; do not overload `phone_verified_at`. The server may accept this marker **only** for the private staging pilot when invite and network policy are enabled. Production's existing phone/age policy must not be relaxed. Review all current `phone_verified_at` checks rather than bypassing one endpoint at a time. Permit the existing witnessed age-check challenge only after this admission and keep moderator self-approval impossible. `GET /api/ready` must state the actual operator mode and stay 503 until the real moderator/adult, persistence and safety prerequisites are met.

## Slice C — truthful React flow and private server

Give invited people a clearly labeled activation/login path and an honest age-pending state; do not display SMS countdowns when no SMS is sent. Keep the current localization model, focus, narrow-screen and screen-reader behavior. Prefer serving the production build and API from the existing same-origin FastAPI server on loopback. Create a reviewed Windows operator runbook/script for a persistent SQLite path on the founder's computer, explicit `CARTMATE_ENV=staging`, no demo tokens, one process/worker, `SOS_PROVIDER=disabled`, limited session TTL and exact private HTTPS origin. Do not store secrets in source or unencrypted command histories. Follow the current official private sharing instructions rather than hardcoding assumed Tailscale CLI syntax. Confirm that the friend must join the private network and that the host computer must remain on.

## Slice D — verification and stop/go evidence

Add backend tests for feature-off, production hard-off, code entropy/expiry/single-use, concurrent redemption, rate limits, no false `phone_verified_at`, session revocation, owner/object checks, adult self-approval denial, age expiry/revocation, restart hydration, block/report behavior and `/api/ready`. Add browser tests on desktop and mobile for both adults and honest pending/denial states. Re-run the full existing suites on disposable databases and frontend build/lint. Test on two actual phones over private HTTPS, including `/api`, `wss` ticket/origin, check-in/chat/cancellation, disconnect/reconnect and host restart. Record exact results without secrets. An ordinary browser reaching the local app by a public path or a nonmember reaching the tailnet URL is a stop condition.

Use `ops/cartmate_backup.py` to make a verified online snapshot, copy it to a founder-approved **off-device, protected** location, and rehearse an offline restore of the full app state. If there is no such location, mark recovery open; a backup on the same computer is not off-device recovery. Arrange an independent security/accessibility review and observed human usability session before sending the real link. Record operator hours and emergency escalation; do not claim 24/7 monitoring. If any gate cannot be met, leave live social access closed and offer only a clearly marked UI preview.

## Required outputs

For each slice: affected files, test/rehearsal commands and outcomes, security/privacy diff review, updated `context/progress-tracker.md`, `GEMINI_HANDOFF.md`, `LAUNCH_READINESS.md`, `README.md`, and unresolved founder inputs. Never claim completion based solely on code compilation or local automated tests.
