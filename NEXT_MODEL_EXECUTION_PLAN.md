# CartMate — completion plan for the next implementation model

> **ARCHIVED BACKLOG, 2026-10-01:** This document remains useful as defect history but is not the current Gemini task list. E00/E01 and test counts below predate later fixes, while the founder has since rejected paid SMS/Render for the two-person friend test. Read `GEMINI_HANDOFF.md`, `context/progress-tracker.md` and feature spec 001 first. Do not start E00 or turn on the paid Blueprint from this file alone.

> **2026-09-30 follow-up:** E03 has a local first slice: votes do not auto-join group chat; explicit join/leave and a six-member cap exist; group-message reports have sender-bound evidence; vote/formation and roster changes commit transactionally before in-memory publication. E07 has spot/group dialog keyboard and 320px browser checks. E09 has a disposable real-schema restore drill and WSS Origin/frame/idle checks. Current local evidence: backend 127/127, browser 40/40 development + 4/4 no-demo, recovery 3/3, frontend build/lint. This does **not** close E03–E09 or hosted/independent gates. E03 still needs closure/expiry, robust race/retry semantics and pagination; E04 still needs browser-session hardening. `LAUNCH_READINESS.md` remains the release board.

> **Current status, 2026-09-30:** E00/E01 safety follow-up and the provider-independent E02 age gate have advanced since this plan was written. Backend **122/122**, development browser **36/36**, no-demo browser **4/4**, frontend build/lint passed locally. The two F06 skip-guarded tests now run under deployed-style route guards; persisted legacy Warsaw hotspot/outing and active-socket block regressions were added. Source runtime trusts **no age provider** and deployed live access remains closed. E00 has permanent blocked-Profile/session/vote browser coverage but still needs buddies/follow-up/every-report-option acceptance; E01 still needs independent authorization/recovery review; E02 still needs founder U03 and a real provider contract. E03–E09 and hosted/operator gates remain open. Read this banner and `LAUNCH_READINESS.md` before the historical findings below; do not repeat the older 108/116 test-count claims as current evidence.

**Reviewed: 2026-09-29. Requested outcome: finish the web MVP's repository work, leaving an explicit list of founder configuration and external approval tasks.**

This turn reviewed code, ran verification, reproduced defects, and wrote this plan. It did not implement the fixes below. All work packages remain open. [LAUNCH_READINESS.md](LAUNCH_READINESS.md) remains the release board; [PRODUCT_NARRATIVE_AND_ROLLOUT.md](PRODUCT_NARRATIVE_AND_ROLLOUT.md) defines the approved product. The older remediation ticket in `CODEX_FIX_HANDOFF.md` covered a narrower set of fixes and does not close this review's findings.

## 1. What we are completing

Ship a responsive Polish-first web app for **18+ adults in an invite-only Katowice/GZM pilot**, plus a Poland-wide information page. The first meeting happens at a public venue, with clear time, duration, cost terms, mutual acceptance, chat, cancellation, reporting, blocking, and optional mutual follow-up. Retain the existing React/Vite/FastAPI/SQLite architecture. Keep the deployed service on one worker and one instance while its live state and WebSocket subscriptions are process-local.

Software completion means the independent work below is implemented, tested, documented, and ready for operator configuration. It does not mean real-user recruitment is approved. Age-provider integration cannot be declared complete until the founder selects the method and its actual contract is tested. Build the provider-independent admission controls now and deny live access while that integration is unavailable.

The approved pilot uses direct `tel:112` guidance. SMS SOS stays disabled. Identity verification, women-only eligibility, native-store releases, automated BLIK payments, a national interest list, public streaks, and nationwide live meetups are outside this completion milestone unless separately approved. Ordinary cost splitting remains a record of participants' claimed purchases; CartMate does not transfer money.

## 2. Current code and evidence

| Area | Present implementation | Completion need |
| --- | --- | --- |
| Account/admission | SMSAPI/Twilio adapters, durable six-digit OTP challenges and abuse budgets, one-use invites, session expiry/revocation | Age assurance, complete session protection, account lifecycle, consistent admission across every transport |
| Two-person outings | Discovery, join requests, host acceptance, versioned plans, PIN meeting check, cancellation, ledger, reviews, buddies | Fix contract/privacy defects; finish pre-match management, clear scheduling, completion history, and recovery after disconnection |
| Groups | Hotspot voting, threshold-based outing creation, group chat | Blocking/admission parity, explicit group commitment and leaving, atomic persistence, correct client vote state |
| Safety | Reports, moderator allowlist/queue, suspension/ban, blocking, direct-112 SOS fallback | Fix report choices and blocked-user UI; add operator notices, appeal/status handling, pause control, and accountable human procedures |
| Frontend | React 19/TypeScript/Vite; feed/deck/map; PL/EN/UK/RU strings; several accessible dialogs | Consistent API types, simpler primary journey, remaining dialog/focus work, complete translations, responsive/performance checks |
| Data | SQLite WAL, migrations, durable records, online backup/offline restore tools | Data export/erasure/retention, fuller transaction coverage, real-schema recovery and encrypted offsite operations |
| Deployment | Render/Docker blueprint, same-origin API/React/WSS, CI workflow, local QA harnesses | Private Git/host access, hosted CI/image evidence, real SMS, durable-volume and restore/rollback rehearsal |
| AI | Bounded Jev classification/screening and deterministic baseline | Audit privacy fix, accurate timing, bounded background work and usage limits; optional capability, not an admission dependency |

### Verification reproduced during this review

- Backend: **108 passed in 9.96s**, using a fresh disposable SQLite database and the documented Hermes Python interpreter.
- Frontend: lint passed; `tsc -b && vite build` passed. Main JS: **513.58 kB / 142.93 kB gzip**. Separately loaded MapLibre JS: **1,062.98 kB / 285.60 kB gzip**. Vite warns about chunk size. These sizes are not a measured rendering or network-performance score.
- Existing browser suite: **32 passed in 42.2s**, Desktop Chromium and Pixel 7 emulation, served from the production bundle on an isolated development backend.
- No-demo browser suite: **4 passed in 15.3s**, production bundle with a disposable staging-style backend and capture-only OTP adapter; no carrier SMS sent.
- Sample backup/restore drill: **2 passed in 0.19s**. This exercises a sample schema, not every CartMate table or offsite storage.
- Additional review probes reproduced the defects below. These were isolated synthetic checks, not additions to the permanent test suite. Existing green tests do not cover these failures.

The first sandboxed backend run hit Windows temporary-directory permissions; the first sandboxed Vite run hit child-process restrictions. Reruns outside that restriction passed. The successful backend run used the suite's normal `JEV_MODE=shadow` with no external key. No source fix was needed for those environment failures. No hosted CI, container execution, Render deployment, real provider, fresh coverage percentage, full screen-reader audit, or real-device Safari run is claimed here.

### Confirmed defects to fix first

| ID / priority | Evidence in the current code | Reproduction / impact | Work |
| --- | --- | --- | --- |
| F01 / P0 | `backend/models.py:UserPrivateSchema`, `main.py:require_user`, `launch_readiness_check` | No age-proof record or live-service age guard. `/api/ready` describes SMS-only eligibility and has no age blocker. This fails the approved admission policy. | E02 |
| F02 / P0 | `jev_service.py:classify_ping_intent`, `_record_shadow_audit`; `main.py:get_shadow_audit` | Classifier summary copies `text[:60]`; the audit stores the whole baseline decision. A synthetic email submitted by one account was returned to another ordinary account through `/api/ai/shadow-audit` (200). Redacting only `input_snippet` does not prevent this. | E01 |
| F03 / P0 | `models.py:TripResponseSchema`, `to_trip_response`; `main.py:submit_trip_follow_up` | After one participant submitted `would_meet_again: false` and private feedback, the other participant's trip GET contained that participant's full follow-up. The double-opt-in choice is not private. | E01 |
| F04 / P0 | `main.py:vote_for_hotspot`, `join_outing`, `get_chat_room`, `websocket_endpoint` | With one voter blocking another, the third vote still auto-created a group containing both. Blocking on explicit group join and message send does not cover automatic formation, rosters, history, or existing subscriptions. | E01, E03 |
| F05 / P0 | `frontend/src/types.ts`, `api.ts`, `ProfileView.tsx`, `ActiveTripHUD.tsx`; backend response schemas | Backend block lists return `{user, blocked_at}`, while Profile expects `blocked_name` and `blocked_user_id`. After blocking, opening Profile reproduced `Cannot read properties of undefined (reading 'trim')` in `UserAvatar`. UI report category `safety_risk` reproduced HTTP 422. Several other report options also differ from the backend enum. | E00 |
| F06 / P0 | `main.py:ping_in_live_region`, `require_live_record`, `list_live_pings`, join/trip/chat routes | Region helper functions exist, but `require_live_record` has no callers. An inserted legacy Warsaw ping was listed (200) and joined (200) in staging mode. A Warsaw trip's chat subscription was denied, but `chat_message` over the same authenticated WebSocket still wrote to that room. | E01, E02 |
| F07 / P1 | `main.py:get_all_demo_users`, `list_live_pings`; `App.tsx:loadInitialData` | A suspended synthetic account remained in `/api/users/all`. The directory has no region/member visibility filter or pagination, and production App fetches it even though its profile-switch consumer is development-only. Ping listing does not recheck the host's current account/admission state. | E01, E02 |
| F08 / P1 | `types.ts:ShoppingBuddySchema`, `TripFollowUpResponse`, `SessionInfoSchema`; `api.ts:submitTripFollowUp` | Frontend expects flat buddy fields instead of `buddy_user`, `mutual_buddy_formed` instead of `is_mutual_buddy`, `token_preview` instead of `token_masked`, and sends `vibe_tags` instead of backend `positive_tags`. Profile labels revoke-all as “other devices,” but the API revokes the current session too. Confirmed by contract comparison; not all screens were separately reproduced. | E00, E04 |
| F09 / P1 | `SpotVotingWidget.tsx` vote initialization | Client infers a vote from `voter_avatars.includes(currentUser.avatar)` despite receiving `user_voted`. New accounts share an empty avatar string, so another user's vote can look like the caller's vote. | E00, E03 |
| F10 / P1 | `CreatePingModal.tsx:handleSubmit`, `jev_service.py:suggest_rendezvous` | Custom addresses receive the account city's centre coordinates. Venue heuristics assert CCTV, lighting and “high” safety from a name/category without supporting venue evidence. Public-destination precision is not proof of a person's location or a safe entrance. | E05, E08 |

The synthetic staging probes used a clean database, real staging guards, generated sessions, and single-use invites; users/legacy records were inserted directly for the test. They did not use real credentials, contact anyone, or alter `backend/cartmate.db`. The browser defect probe used seeded accounts only on the disposable local server. The review server was stopped after testing.

### Other inspected gaps to include in completion

- Session bearer values remain in browser `localStorage` and SQLite; configured lifetime defaults to 720 hours. Request-time expiry exists, but outbound WebSocket delivery does not revalidate a silent subscriber's expiry. Cookie, CSRF, security-header and session-storage changes need one coherent design.
- WebSocket recovery remembers scopes but does not fetch a fresh snapshot after reconnect. Heartbeats send pings without a pong deadline. App's fallback starts on `disconnected`, but an initial ticket failure can move directly into `reconnecting`. A late authenticated fetch can also repopulate state after logout without an account-generation guard.
- Join creation does not send a host event; expiration/matching/withdrawal does not have a complete discovery invalidation path. `max_active_pings_per_user` is configured but unused. The UI keeps only one active trip although the backend can admit multiple.
- Hotspot formation/join, chat append, moderation, completion and buddy writes do not all share the atomic commit pattern already implemented for host acceptance. In several paths memory is changed before persistence succeeds. Whole chat histories and many collections are loaded without paging.
- Public profiles and embedded snapshots need review for stale reputation, suspension and identity labels. `coarse_coordinates` is imported but not used by main; documentation must describe actual public venue coordinates, not claim automatic coordinate coarsening is applied everywhere.
- No account export/deletion, configurable retention process, durable incident pause, or moderation appeal workflow appears in the reviewed routes. Moderation decision notes also double as `suspension_reason`; separate private evidence/notes from explanations shown to the affected user.
- LiveRadar and SpotVoting dialogs declare ARIA roles but do not use the focus hook used by Auth/Create/Trip. PL-only or PL/EN branches remain alongside the four-language selector. Profile hides failed safety-data fetches as empty lists.
- Jev shadow calls are awaited in the request path; recorded latency is computed before the remote call. Public AI endpoints have no separate call budget. The Render blueprint already keeps Jev disabled, which is the appropriate default during these fixes.

## 3. Execution rules

One implementation writer owns this checkout. It currently has no `.git`; preserve it and the existing local database. Once the founder provides a repository, work in an isolated branch/worktree, review the initial import for secrets and generated files, and record commit IDs with evidence. Do not treat previous actors' claims as a substitute for running the affected checks.

Implement small, reviewable slices. Add meaningful regression tests for the failures above before fixing them. Update tests when an explicitly approved contract changes; preserve equivalent success and denial coverage. Do not make failing journeys optional or lower the release gate to recover a green suite.

Put new admission, session and privacy logic in narrow modules. Extract existing code only when the change needs it and the boundary has tests. A whole-app rewrite, new database stack, or complete `main.py` refactor is not on the critical path.

## 4. Ordered implementation backlog

### E00 — Repair frontend/API contracts and broken safety flows

**Start now. No founder dependency.** Files: `backend/models.py`, `frontend/src/types.ts`, `api.ts`, `ProfileView.tsx`, `ActiveTripHUD.tsx`, `SpotVotingWidget.tsx`, affected tests.

- Use the backend schema as the source of truth for reports, block lists, buddies, follow-up and session data. Generate API types from OpenAPI or keep explicit, tested boundary adapters; remove unchecked casts that claim a different JSON shape. Distinguish public profiles from private `User` data.
- Fix every report option, actual buddy recognition, follow-up tags, block display/unblock IDs, and the session page. Make revoke-all say and do “all devices,” including clearing the current UI/session on success. A future “other devices” command would need a distinct server contract.
- Read only `user_voted` for votes. Provide safe avatar fallback and a recoverable React error boundary, while still correcting the schema mismatch that caused the crash.
- Display load failures for blocked users, buddies and sessions instead of presenting false empty states.

**Done when:** real API-backed browser tests block → open Profile → unblock; submit every report category; complete an outing and form a mutual buddy; display real session fields and revoke all. Unknown/rejected data produces a useful error, not a blank screen. Contract generation/validation runs in CI.

### E01 — Close the reproduced privacy, blocking and geography defects

**Start now; run alongside E00 only in separate ownership boundaries.** Files: backend DTO builders, Jev audit, main discovery/group/chat routes, WebSocket manager, regression tests.

- Build audit entries from an allowlist of safe structured fields. Do not retain free-text model/baseline summaries or provider response blobs. Restrict audit details to an explicit operator role; ordinary members get no other user's audit. Test nested data and failures, not just the input field.
- Project follow-up responses for the caller: show their own choice and a mutual result only after both opt in. Never return the other person's unilateral choice, tags or feedback in REST or shared events. Keep raw moderation/review evidence private as well.
- Apply eligibility, region, block and current-account checks consistently to discovery, reads, writes, formation, join/accept, active trip, history and socket actions. Keep authorized reporting/cancellation/support access available when live participation is denied.
- Stop publishing suspended/banned/ineligible profiles and their live listings. Remove the unused whole-user-directory fetch from the production shell; constrain or disable the directory API in deployment unless a real, bounded UI needs it.
- Treat automatic group formation as an admission operation. Blocked pairs cannot be silently joined. A new block must stop future relevant contact/events; keep only the authorized historical/evidence access defined by policy. Do not destroy incident evidence to hide a relationship.

**Done when:** each F02–F07 probe has a permanent negative regression. Include direct REST calls, initial socket scopes, later subscriptions, socket sends, existing connections, persisted legacy records and cold restart. Run with staging guards and ordinary generated sessions/invites, not only demo tokens.

### E02 — Implement the adult admission framework and enforce it everywhere

**Build now. Real provider completion depends on U03.** Files: new eligibility/provider module, schemas, migrations/storage, auth dependencies, `/api/ready`, Auth/App onboarding, staging harness.

- Store minimal age-assurance status and provenance: provider/method identifier, opaque verification reference, checked/expiry/revocation times and policy version. Final fields and retention follow the approved method. Do not accept a browser-supplied `over_18=true` as proof.
- Separate an authenticated onboarding account from a live member. Pending/denied users may access their own admission status, approved appeal/privacy/support functions and logout; they may not discover or contact members.
- Centralize live-member checks: current account status, SMS provenance, invite membership, valid approved age result, live region and operational pause. Use the same policy for REST, ticket issue, socket connection, subscription, send and outbound events.
- Provide unavailable/pending/failed/expired/revoked/approved UI states and an accessible recovery path. Invalidate existing access when evidence expires or is revoked. Keep source records private.
- While no real method is selected, configure the provider as unavailable and keep live access closed. Test success with a capture-only adapter confined to tests; never ship an executable test bypass or a production manual approval shortcut.
- Extend readiness and public capability config with accurate age availability and policy version. Add contract tests for the approved age, geographic and direct-112 policies so frontend, API and maintained docs cannot drift silently.

**Done locally when:** unknown/false/expired/revoked/forged age claims are denied across all paths, existing sessions and restart included. Provider replay/outage tests pass; a pending user can still seek help or exercise account rights. **Provider integration remains open** until an approved contract and credentials exist; authenticated callbacks/claims must then be verified against that contract.

### E03 — Finish group commitment and transactional reliability

**Depends on E01/E02 policy interfaces.** Files: hotspots/outings/chat services, storage migrations, `SpotVotingWidget`, tests.

- A vote expresses interest. Give users a clear, explicit step to join a formed group and see its agreed time/place/cost terms. Add leaving, cancellation and group closure behavior, member limits, and reporting from a group context.
- Check blocks, age/admission, active account status and region at every transition, including threshold creation and existing members. Refresh rosters and socket access immediately after changes. Define history access on leaving without permitting new contact.
- Commit related hotspot/vote/outing/room membership changes together. Add database constraints and transaction checks for retries/races; update memory and emit events only after commit.
- Extend the same commit discipline to chat sequence/idempotency, moderation decisions, completion counters and mutual-buddy creation. Give retried messages and ledger submissions a client operation ID so a network retry cannot duplicate them.
- Bound message/frame sizes, per-user connections, send concurrency and collection reads. Add paging for chat/history; keep a deterministic recovery snapshot for reconnect.

**Done when:** three-user browser coverage includes explicit joining, leaving, blocked members, suspension, repeated votes, duplicate requests and a forced database-write failure. Restore/restart gives the same authorized membership and no duplicate room, message, purchase or buddy count. Keep the group surface unavailable in deployment until its gate passes; hiding only its frontend is insufficient.

### E04 — Harden browser sessions and realtime recovery

**Build now; coordinate the auth contract with E02.** Files: auth/session module, storage migration, `api.ts`, `realtime/socket.ts`, App state, server middleware.

- For the approved same-origin web deployment, migrate to an opaque `HttpOnly`, `Secure`, host-scoped session cookie with a reviewed `SameSite` policy. Implement CSRF and Origin checks for state-changing requests, including login/logout, and WebSocket Origin/ticket checks. Document local-test behavior. Do not silently keep a second weaker bearer path in deployed web mode.
- Store a digest of the random session credential, not its reusable value, in persistent storage. Define rotation, idle/absolute expiry and reauthentication for account-sensitive actions. Use separate session IDs for display/revocation. Migrate or revoke old sessions deliberately.
- Ensure expiry, suspension, admission revocation and logout close existing sockets even when the client sends no frames. Clean up failed/closed sockets and scope state in all exits; cap slow-client sends.
- On reconnect/foreground, fetch authorized trip, chat and feed snapshots. Stop retrying permanently denied sessions. Add a heartbeat deadline, clear subscriptions/account state on identity changes, and ignore responses from earlier account/load generations.
- Add appropriate cache and security headers, with CSP tested against React and the opt-in map's actual image/style/worker sources. Logout may clear local sensitive state offline, but must explain when server revocation was not confirmed.

**Done when:** cross-origin mutation attempts fail; JS cannot read the web session credential; stolen database rows do not contain reusable sessions; old/expired credentials and sockets fail; switching accounts/offline-reconnect/logout never restores another account's UI. Session protections follow [OWASP session-management guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html); cookies still require CSRF protection and do not eliminate XSS.

### E05 — Complete the ordinary outing journey

**Depends on E00 and shared admission policy.** Files: ping/trip services and schemas, Create/LiveRadar/ActiveTrip/Profile, API, tests.

- Collect an actual meeting date/time with a timezone-aware server value, duration, cost rule and meaningful budget before commitment. Clearly distinguish listing expiry from meeting time. Preserve plan versions and invalidate acceptance after changes.
- Use a server-owned public-venue catalogue for the pilot, with provenance and approximate/exact coordinate labels. A custom location must be verified or honestly shown as unlocated; never place an arbitrary address at a city centre. Approved venues/time windows are U07. Remove unverified “24h,” CCTV and safety-rating claims unless supported by current venue evidence.
- Let a host withdraw an unmatched listing and decline a request; let an applicant withdraw and see pending/declined/expired outcomes. Enforce active-listing limits and an explicit policy for multiple simultaneous trips so no accepted plan becomes inaccessible in the one-trip UI.
- Notify the right participant about requests/decisions. Invalidate discovery when a ping is matched/withdrawn/expired, and route nearby updates consistently across the active region, not only the host's profile city.
- Keep completed/cancelled outing history accessible for reporting, optional follow-up and ledger review. Persist recoverable form/input state only where appropriate; show pending/retry/success accurately. Complete optional feedback after the server confirms completion without losing the ability to retry it.
- Add basic profile editing for the fields the app actually uses, with validation and clear self-declared labels. Sensitive phone changes require a separately secured proof flow; no unverified identity badges.

**Done when:** two fresh users can complete the whole journey, including refusal/withdrawal, schedule changes, cancellation before and during a meetup, optional review/follow-up, and later reporting. Test conflicting plans, stale version acceptance, duplicate submissions, midnight/timezone cases and loss of network after a successful write.

### E06 — Add account rights and usable human safety operations

**Build mechanics now. Published policies and operational setup depend on U04/U05.** Files: new privacy/moderation services, migrations, Profile/Safety/Moderator screens, runbooks.

- Implement authenticated account export and erasure requests with identity confirmation, a clear result/status and bounded jobs. Separate the user's own data from other participants' private information and moderator evidence.
- Implement configurable retention and approved legal-hold handling, covering database JSON snapshots, chat, invitations, OTP/session leftovers, reports, logs and backups. Dry-run deletion jobs and test repeat execution. Do not silently invent retention periods or delete safety evidence awaiting a reviewed decision.
- Provide a report receipt and status, safe decision explanations, an appeal/contact path, and separate private moderator notes. Add the necessary group-message/evidence context without exposing other cases to members. A suspended account must retain the limited support/rights path.
- Add moderator queue alerts through a configured provider plus an operational fallback. Expose alert failures to the operator. Require a real human to review; no AI ban/age/eligibility decisions.
- Add a durable, auditable control to pause invitations and new live interactions during an incident. Keep help, reporting, privacy requests and direct-112 guidance reachable. Scope reopen permissions explicitly.

**Done when:** export contains only authorized data; deletion covers live caches and storage and cannot be undone by routine hydration; held evidence stays restricted; all retained data has an approved owner/rule. Moderator, ordinary-user and suspended-user tests cover report, appeal, pause and audit paths. A human subsequently rehearses the workflow.

### E07 — Finish the interface, accessibility and public information surface

**Depends on stabilized API contracts. Most work needs no credentials.** Files: App/navigation, shared UI components/tokens, dialogs, locales, CSS, public page, browser tests.

- Make the default screen answer “What can I do nearby?” with one main outing list and a clear create action. Keep secondary modes available only where they have a usable purpose. Make status, place, time, cost and next action consistent across cards, requests and trip screens.
- Establish shared spacing/type/color/control tokens and reusable buttons, inputs, status messages and dialogs. Use inline errors and recovery actions in place of scattered browser alerts. Keep original CartMate assets and honest empty states.
- Extend focus trapping, Escape, focus restoration, accessible names, scroll containment and background inertness to every modal, including nested dialogs. Ensure keyboard access has an equivalent to map interaction. Announce request/status/chat errors appropriately.
- Verify all offered languages in every live flow, localize server error codes at the UI boundary, and preserve language preferences. Remove corrupted text and unsupported safety/reputation claims. Initial Polish copy gets native-speaker review.
- Check 320px through desktop widths, short landscape screens, virtual keyboards, safe areas, zoom/reflow, contrast and reduced motion. Use 44px targets where practical as a design target; evaluate the actual [WCAG 2.2](https://www.w3.org/TR/WCAG22/) criteria, including exceptions, rather than treating a size rule as certification.
- Build the Poland-wide information page: what CartMate does, 18+ requirement, exact pilot area, how invitations work, safety limits, support and reviewed policy links. Provide a clear out-of-area state. Do not add a national signup/interest endpoint as an implicit extension of this task.
- Measure first load and interactions before optimizing. Split heavy app views where useful; retain the map's existing on-demand import. Test slow-network/low-end-device behavior and choose budgets based on the measured baseline. Do not suppress chunk warnings to claim a performance gain.

**Done when:** core journeys work on Chromium, Firefox and WebKit at representative sizes; every dialog passes keyboard tests; manual VoiceOver/TalkBack or equivalent assistive-technology checks and real-phone keyboard/zoom checks are recorded. The public page works without account creation and does not fetch member data. Real-device/manual checks remain explicitly open if equipment or a reviewer is unavailable.

### E08 — Make optional Jev assistance truthful, bounded and useful

**E01 audit fix is urgent; the remaining AI improvements follow the core journey.** Files: Jev service, AI endpoints, Create form, config, evaluation fixtures.

- Keep `JEV_MODE=disabled` as the deploy default until the privacy fix and evaluations pass. A missing AI key must not prevent an otherwise eligible user from using the core app.
- Move shadow comparison off the critical publish/join response path with bounded concurrency, timeouts and shutdown handling. Measure actual provider latency, failures and skipped evaluations separately from baseline time; do not label a failed call as an evaluated agreement.
- Add AI request limits and explicit provider budget controls. Minimize/redact allowed public text before sending; do not send private chats, age proof, account contacts, moderation case details or raw location history. Evaluate multilingual errors and redaction limitations before enabling it.
- Replace heuristic “safe venue” ratings with suggestions from the approved public-venue catalogue and clear uncertainty. Structured output validates shape; it does not verify a safety claim.
- Incorporate the useful idea from the earlier Ripple research as deterministic policy-consistency tests now: 18+, GZM-only live service, direct-112-only SOS, unavailable ID verification, and truthful release state must agree across canonical contracts and UI. Do not string-match historical docs or mark checks complete merely because a phrase exists.

**Done when:** gateway timeout/outage does not stall core writes; raw synthetic PII never appears in audit fields accessible to any role; budget/timeout tests pass; optional assistance can be disabled immediately. Needle-style semantic outing search and a cited policy-help assistant stay in the later experiment backlog until real users show the need. No wholesale import of the example repository or new agent framework is required.

### E09 — Package, protect and rehearse the real application

**Repository tools can be built now; external rehearsal depends on U01/U02/U04/U06.** Files: Docker, Render config, CI, ops, staging scripts, runbooks.

- Create a reproducible project environment from pinned/locked dependencies and document it; the Hermes interpreter is a temporary local convenience. Add dependency and secret scanning and review findings. Harden the container's user/file permissions while preserving the persistent volume's required access.
- Verify the shipped image serves the built frontend and API. Keep the invalid-ticket WebSocket smoke, and add positive authenticated WSS evidence in a controlled hosted rehearsal; the existing 403 check proves rejection handling, not a complete authenticated deployment journey.
- Extend recovery tests to the real schema: age provenance, sessions/revocations, invitations/budgets, blocks, reports/holds, plans, pings, group memberships, messages, ledger entries and buddies. Use a separate process and disposable data. Inject write failures, stop/restart the process, and test migrations from a previous schema.
- Add an established encrypted-backup workflow, restricted offsite upload, scheduling, retention, integrity/authenticity verification and failure alerts. Keep encryption keys separate from backups. Write an offline restore and release rollback procedure, including handling revocations/deletions made after a restored snapshot so old access is not silently resurrected.
- Add minimal redacted operational metrics and alerts for errors, OTP failures/limits, database/disk health, WebSocket disconnects and report backlog. Record availability/recovery expectations agreed with the operator. Verify log filtering on actual deployed handlers, including exceptions and provider errors.
- Document maintenance for the single-instance service. Render persistent disks constrain scaling and deployment behavior; account for downtime in the rehearsal using [Render's disk documentation](https://render.com/docs/disks). Never reuse the local seeded database as the deployed database.

**Done locally when:** CI definitions, image checks, local encrypted restore, actual-schema process-restart tests, negative auth matrix and documented operator commands pass. **Done operationally when:** hosted CI/image, real OTP/outage, HTTPS/WSS, volume persistence, encrypted offsite restore and rollback have timestamped evidence reviewed by a human. Missing credentials leave these specific checks open.

## 5. Work order and ownership for the next model

1. **First implementation pass:** E00 contract fixes, E01 privacy/block/geography fixes, then E02 admission foundation. Attach regressions and update the release board after each completed slice.
2. **Core completion:** E03 group/transaction work, E04 sessions/recovery, E05 full outing journey, E06 privacy/moderation operations. Coordinate common schemas first.
3. **Presentation and packaging:** E07 UI/public page, E08 bounded assistance, E09 release/operations. Begin independent ops scaffolding earlier where it does not conflict.
4. **Final integration:** run the expanded matrix once against the final candidate, review changes independently, and list every unsatisfied external gate with its owner. A larger passing test count is not an acceptance criterion on its own.

If another contributor is involved later, agree a file boundary before concurrent edits. A QA author can own new `qa/tests/*` files and an ops author can own new `ops/*` tools, but changes to `api.ts`, `types.ts`, main, storage, config, shared dependencies and CI have one integration owner. This plan does not start additional agents or authorize simultaneous writers in this non-Git checkout.

This is several implementation passes, not a cosmetic finish. A credible calendar estimate needs the age method and acceptance scope of group/privacy work; do not promise a launch date from the present test count. Re-estimate after E00–E02 and provider selection, using completed slices and remaining evidence.

## 6. Founder inputs: the items code cannot supply

Provide secrets only in the hosting/provider secret store. They do not belong in chat, commits, screenshots or handoff files.

| ID | Needed from founder/operator | What work it unlocks | What engineering can finish first |
| --- | --- | --- | --- |
| U01 | Private Git destination/access; Render project, billing and region; public/staging hostname and any domain/DNS control | Hosted CI/deployment and HTTPS/WSS rehearsal | Source review, CI/image setup and staging runbook |
| U02 | SMSAPI account token and approved sender, consenting approved +48 test handset, spend cap | Real SMS delivery, outage/retry and invite-redemption exercises | Capture-only contract tests, limits, failure UI and operator runner |
| U03 | Qualified approval of age-assurance method/provider, accessible appeal route, minimum returned proof and retention; then provider credentials/callback setup | Actual age verification and permission to pass adult admission | Durable states, server guard, unavailable/pending UI and test adapter; production remains closed |
| U04 | Named human safety/moderation owner, account IDs, coverage hours, escalation/support contact, notification destination and incident authority | Moderator onboarding, alert rehearsal, incident response | Role enforcement, queue/status/appeal mechanics, pause tools and runbooks |
| U05 | Controller/company identity and contact, reviewed terms/community/privacy copy, data-retention and evidence-hold rules, rights procedure | Publication of policies and execution of approved retention; legal/privacy approval | Draft data inventory, export/erasure framework, configurable jobs and consent/version records |
| U06 | Restricted offsite storage account/access, separately held encryption/recovery keys, recovery objectives, alert recipient | Scheduled offsite backups and human restore/rollback exercise | Local encrypted pipeline, full-schema drill and operator checklist |
| U07 | First microarea/cohort, current public venues and meeting windows, voluntary partner wording and consent to recruitment | Final venue catalogue and closed invitation rollout | Region constraints, invitation tools, empty/out-of-area UI and pilot measurement design |

These are not all configuration fields. U03–U05 include decisions and review by accountable people. SMS OTP does not settle the age question; provider credentials do not constitute an operating safety team. Jev credentials are optional and are not a launch dependency. Future identity verification/SMS SOS need their own decisions if those capabilities are later requested.

## 7. Completion evidence and release boundary

- [ ] E00–E09 repository work done or a precise subtask explicitly blocked by U01–U07; no known P0 finding open.
- [ ] Approved age method integrated, provider negative paths reviewed, and 18+ admission verified in the real configuration.
- [ ] Endpoint/transport authorization matrix includes outsider, blocked, suspended, unadmitted, underage/unknown-age, expired/revoked proof, out-of-region and revoked-session cases.
- [ ] Browser matrix covers report choices, populated blocks/buddies/session screens, group lifecycle, completion history, reloading/reconnecting/offline retry and private follow-up behavior.
- [ ] Frontend lint/typecheck/build, backend regressions, real-schema recovery and image checks pass on the same candidate; evidence includes environment and commit when Git exists.
- [ ] Public page and all live screens use reviewed, accurate copy; keyboard/zoom/assistive-technology evidence is recorded.
- [ ] Hosted CI, provider, persistent disk, encrypted offsite backup/restore and rollback evidence is recorded; no local-only test is relabeled as a hosted exercise.
- [ ] Privacy/legal, independent technical review and human safety/operator approval are recorded; the founder then approves a limited invitation batch.

## 8. Paste this to the next implementation model

> **Verification update 1 (2026-09-29, Hermes fact-check after the 17:56 handoff):** a prior model claimed E00/E01 complete with regressions; audit found the frontend did not compile, no regression tests existed, and F06 remained open. Hermes repaired the E00 frontend contract migration and restored the corrupted CI smoke value; `tsc -b`, `oxlint`, 108/108 backend, 32/32 dev browser and 4/4 no-demo passed on the repaired tree.

> **Verification update 2 (2026-09-29, Hermes E01 implementation):** Hermes then implemented the E01 P0 fixes with permanent regressions in `backend/test_completion_regressions.py` (8 tests): F02 audit allowlist + moderator-only endpoint, F03 broadcast follow-up removal, F04 blocked-pair exclusion from auto-formed groups, F05 report-category contract parity (frontend options now match the backend enum), F06 region enforcement on listing/join/chat REST and the WS `chat_message` bypass path, F07 suspended-user hiding in directory and discovery. Verified: **116 passed + 2 skipped** backend (F06 staging-mode regressions skip in dev fixtures and run under production semantics), frontend build/lint clean, 32/32 dev browser, 4/4 no-demo. **Still open in E01:** persisted-legacy-record + cold-restart coverage, existing-connection invalidation after a new block. **E02 remains blocked on founder U03 (age-assurance method). E03–E09 untouched.**

> **Verification update 3 (2026-09-30, Codex integration):** Closed the remaining known out-of-region hotspot/outing paths; the old F06 tests now exercise deployed-style REST and WebSocket authorization instead of skipping, and a separate subprocess test hydrates legacy Warsaw records from SQLite. Blocking now closes existing sockets and denies blocked chat/trip/outing subscriptions and chat history. Fixed vote ownership and implemented a genuine `revoke-other-sessions` API. Added provider-independent 18+ proof fields, fail-closed deployed live-access checks, a truthful pending UI, and a QA-only local proof adapter. **122/122 backend, 36/36 dev browser, 4/4 no-demo, frontend build/lint passed locally.** Founder confirmed no age method selected; source trusts no provider and `/api/ready` remains blocked. Next engineering: permanent browser coverage for populated buddies/follow-up/report options; deeper group/transaction/session/account-rights work E03–E09, independent endpoint/security/accessibility review, and hosted evidence after U01–U07. Never convert the QA proof adapter into a deployed bypass.

> Work in `S:\APPs\cartmate`. Read the 2026-09-30 update above, `PRODUCT_NARRATIVE_AND_ROLLOUT.md` and `LAUNCH_READINESS.md`. Preserve the local database, keep a single writer, and do not rewrite the stack. Next: add permanent browser acceptance for populated buddies, private follow-up and every report choice; independently audit every live route and transport after the age and block guards; then continue E03–E09. The source trusts no age provider: keep live participation closed until founder U03 selects an independently reviewed method and its real signed proof contract is integrated. Keep SMS SOS disabled. Turn each gap into a negative regression before fixing it. Update the release board with files changed, commands run and remaining evidence. Do not deploy or invite real users merely because local tests pass. Hand back a working candidate, reproducible verification and the short U01–U07 checklist.
