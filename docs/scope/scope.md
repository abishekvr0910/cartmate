# Scope: CartMate

CartMate brings adults together in real life through structured micro pods of three to five people anchored at verified public third places, alongside quick ten minute remote voice calls from home to cut loneliness with no social awkwardness.

**Build approach:** Tracer Bullet (thin end to end thread connecting database triggers, REST endpoints, real time websockets, and a clean mobile feed).
**Workflow:** Beta (verify every acceptance criterion, then run automated tests). The project default level of rigor. Any feature can carry its own tag to do more or less.

_These are recommendations to keep your build orderly, not requirements. Skip anything that does not fit: if you already know how to build a feature, use `/develop` and skip `/architect`. You decide when a feature is done._

## At a glance

| # | Feature | Phase | Status |
|---|---------|-------|--------|
| 1 | Micro pod database schema | Foundation | done |
| 2 | Micro pod backend storage methods | Foundation | done |
| 3 | Micro pod REST and websocket API | Core Loop | done |
| 4 | Mobile first micro pod feed UI | Core Loop | done |
| 5 | Quorum gated group chat UI | Core Loop | done |
| 6 | Ten minute remote voice calls | Phase 2 | done |
| 7 | Voice and pod safety, auth, and block sync | Hardening | done |
| 8 | Voice signaling resilience, quotas, and abuse controls | Hardening | done |
| 9 | Navigation safety route, native origin guard, and accessible live UI | Hardening | done |
| 10 | Continuous integration recovery and regression suite | Hardening | done |
| 11 | Strict voice table rebuild migration and production TURN startup guard | Audit Closure | done |
| 12 | Full four language localization across pod, voice, and safety views | Audit Closure | done |
| 13 | End to end pod and voice browser journeys and root pytest isolation | Audit Closure | done |

## Foundations

### 1. Micro pod database schema · done
Additive schema migration eleven with strict constraints, activity templates, third places, and automated quorum triggers.
**Done when:** database strictly enforces three to five seat limits, locks chat until quorum is reached, and passes all migration tests.
- [x] Design it (spec): `/architect micro pod database schema`
- [x] Build it: `/develop micro pod database schema`
   - [x] STRICT tables for activity templates, third places, cohorts, pods, members, and messages
   - [x] Automated triggers for quorum calculation and chat lock enforcement
   - [x] Compatibility with string user identifiers and schema migrations table
- [x] Verify it: `/check verify micro pod database schema`
- [x] Test it: `/test micro pod database schema`
Spec 0011 · code in `backend/migrations/0011_micro_pods.sql`

### 2. Micro pod backend storage methods · done
Storage methods in backend storage for managing pods, members, messages, and deadline cancellations.
**Done when:** callers can create pods, list nearby pods with seat tallies, join or leave with mutual block checks, post messages when at quorum, and sweep expired pods.
- [x] Design it (spec): `/architect micro pod backend storage methods`
- [x] Build it: `/develop micro pod backend storage methods`
   - [x] Implement query for active pods with seat counts and venue details
   - [x] Implement join and leave methods enforcing capacity and user blocks
   - [x] Implement quorum gated message retrieval and insertion
   - [x] Implement automatic deadline cancellation sweep
- [x] Verify it: `/check verify micro pod backend storage methods`
- [x] Test it: `/test micro pod backend storage methods`
code in `backend/storage.py`

## Core Loop

### 3. Micro pod REST and websocket API · done
FastAPI endpoints and websocket event handlers for browsing the feed, joining pods, and sending real time messages.
**Done when:** authenticated users can fetch the feed, join or leave a pod, receive live membership updates, and chat over websocket when quorum is reached.
- [x] Design it (spec): `/architect micro pod REST and websocket API`
- [x] Build it: `/develop micro pod REST and websocket API`
   - [x] REST endpoints for feed, templates, places, join, leave, messages, sweep
   - [x] Scope authorization for pod websocket rooms and pod chat broadcasts
- [x] Verify it: `/check verify micro pod REST and websocket API`
- [x] Test it: `/test micro pod REST and websocket API`
code in `backend/main.py` and `backend/test_micro_pods_api.py`

### 4. Mobile first micro pod feed UI · done
Single unified feed component in the frontend displaying scheduled pods with seat indicators and clear activity templates.
**Done when:** users see an uncluttered list of available pods with seat counts, venue info, meeting points, and one tap join buttons.
- [x] Design it (spec): `/architect mobile first micro pod feed UI`
- [x] Build it: `/develop mobile first micro pod feed UI`
   - [x] Clean card layout showing template duration, city, address, meeting point, and spend
   - [x] Live progress bar for seat occupancy and spots left
   - [x] One tap join and leave controls
- [x] Verify it: `/check verify mobile first micro pod feed UI`
- [x] Test it: `/test mobile first micro pod feed UI`
code in `frontend/src/components/PodFeed.tsx` and `frontend/src/components/BottomNav.tsx`

### 5. Quorum gated group chat UI · done
Mobile chat interface opening automatically once three people confirm their attendance.
**Done when:** chat displays a locked banner while forming, unlocks immediately upon quorum, and supports live message updates.
- [x] Design it (spec): `/architect quorum gated group chat UI`
- [x] Build it: `/develop quorum gated group chat UI`
   - [x] Slide in chat drawer for active pod members
   - [x] Displays locked state if below quorum, unlocks when quorum is reached
   - [x] Message input and delivery with sender badge and time
- [x] Verify it: `/check verify quorum gated group chat UI`
- [x] Test it: `/test quorum gated group chat UI`
code in `frontend/src/components/PodFeed.tsx`

## Phase 2: Remote Voice Connections

### 6. Ten minute remote voice calls · done
Spontaneous peer to peer voice calls with automatic countdown timer and zero physical meeting pressure.
**Done when:** two matched users can connect over WebRTC audio for a ten minute conversation with an on screen prompt and clean auto disconnect.
- [x] Design it (spec): `/architect ten minute remote voice calls`
- [x] Build it: `/develop ten minute remote voice calls`
   - [x] STRICT SQLite migration twelve for voice call sessions and post call ratings
   - [x] VoiceCallManager engine with 60s queue timeout, mutual block checks, authoritative 600s timer, and ephemeral TURN credentials
   - [x] Authenticated WebSocket and REST endpoints for status, matching, signaling, rating, and hangup
   - [x] Frontend VoiceCallHUD component with WebRTC audio, glowing activity wave, 10:00 countdown, one tap end and block, and post call rating drawer
- [x] Verify it: `/check verify ten minute remote voice calls`
- [x] Test it: `/test ten minute remote voice calls`
code in `backend/migrations/0012_voice_calls.sql`, `backend/voice_manager.py`, `backend/main.py`, `backend/test_voice_calls.py`, `frontend/src/components/VoiceCallHUD.tsx`

## Phase 3: Pilot Safety Hardening and CI Recovery

### 7. Voice and pod safety, auth, and block sync · done · GA
Align voice hangup and disconnect reasons with database check constraints, unify bidirectional user blocking across memory, persistent storage, active voice calls, and shared pods, enforce eighteen plus pilot age admission, and lock down pod roster and moderator place routes.
**Done when:** one tap end and block and peer socket drops save cleanly without constraint errors, blocking separates both users across pods, voice, and core feeds by withdrawing the blocker as left rather than kicking existing pod members, unverified or unauthenticated callers are rejected on pod and voice discovery and chat while leave, hangup, and rate stay open even after seven day attestation expiry, only confirmed call participants can mark a call connected or hang it up, and only moderators can add verified third places or trigger pod sweeps.
- [x] Build it: `/develop voice and pod safety, auth, and block sync`
- [x] Verify it: `/check verify voice and pod safety, auth, and block sync`
- [x] Test it: `/test voice and pod safety, auth, and block sync`
- [x] Review it: `/check review voice and pod safety, auth, and block sync`
- [x] Document it: `/document`

### 8. Voice signaling resilience, quotas, and abuse controls · done · GA
Harden peer to peer audio handshake reliability during microphone permission prompts, close quota and cooldown loopholes on reported calls, enforce evening call hours and rate limits, and fail closed on default relay secrets in production.
**Done when:** early session offers and network candidates buffer safely until microphone setup finishes without listener churn or duplicate hangup requests, reported calls count toward the three call daily cap and ten minute cooldown, inappropriate call ratings escalate to the human moderation queue while honoring the explicit block checkbox, production enforces the evening call window in Warsaw time, pod and voice inputs pass region, length, rate limit, and content safety checks with sanitized errors, expired pods clear automatically without hanging test shutdowns, brief cellular drops get a twelve second grace window that never delays blocks or bans, and production readiness blocks startup if the relay secret uses a development default.
- [x] Build it: `/develop voice signaling resilience, quotas, and abuse controls`
- [x] Verify it: `/check verify voice signaling resilience, quotas, and abuse controls`
- [x] Test it: `/test voice signaling resilience, quotas, and abuse controls`
- [x] Review it: `/check review voice signaling resilience, quotas, and abuse controls`
- [x] Document it: `/document`
code in `backend/voice_manager.py`, `backend/main.py`, `frontend/src/components/VoiceCallHUD.tsx`

### 9. Navigation safety route, native origin guard, and accessible live UI · done · Beta
Restore the five item mobile bottom bar with direct Safety and 112 access, route all pod and voice client calls through the native destination token guard, wire live pod room socket updates, and finish keyboard focus and screen reader polish.
**Done when:** bottom navigation keeps the Safety button reachable at 320px width while pairing micro pods and ten minute voice calls in a shared social switcher, every pod and voice API helper withholds bearer tokens on unapproved native origins, open pod chat drawers stream live messages and quorum shifts over the realtime socket without browser alert popups, modals trap focus and close on Escape, countdown announcements speak only at five minutes, one minute, and thirty seconds, match chimes respect reduced motion settings, copy supports all four app languages, and heavy feature views load lazily.
- [x] Build it: `/develop navigation safety route, native origin guard, and accessible live UI`
- [x] Verify it: `/check verify navigation safety route, native origin guard, and accessible live UI`
- [x] Test it: `/test navigation safety route, native origin guard, and accessible live UI`
- [x] Review it: `/check review navigation safety route, native origin guard, and accessible live UI`
- [x] Document it: `/document`
code in `frontend/src/App.tsx`, `frontend/src/api.ts`, `frontend/src/components/PodFeed.tsx`, `frontend/src/components/VoiceCallHUD.tsx`, `frontend/src/components/SafetyHub.tsx`

### 10. Continuous integration recovery and regression suite · done · GA
Restore a green main pipeline by expanding compile checks, backup manifest tallies, native destination probes, and automated backend and browser regression tests across desktop and mobile profiles.
**Done when:** syntax compile checks include the voice manager and micro pod migration runner, backup manifests record pod and voice session counts alongside users and trips, the native destination probe verifies zero token leakage across all pod and voice helpers, isolated backend suites cover every new safety and block invariant without touching the local development database, and desktop plus mobile browser journeys pass end to end in continuous integration.
- [x] Build it: `/develop continuous integration recovery and regression suite`
- [x] Verify it: `/check verify continuous integration recovery and regression suite`
- [x] Test it: `/test continuous integration recovery and regression suite`
- [x] Review it: `/check review continuous integration recovery and regression suite`
- [x] Document it: `/document`
code in `backend/test_voice_calls.py`, `ops/cartmate_backup.py`, `ops/test_disaster_recovery.py`, `qa/codex_mr02_destination_probe.cjs`, `qa/tests/safety-and-sos.spec.ts`

## Phase 4: Final Audit Closure

### 11. Strict voice table rebuild migration and production TURN startup guard · done · GA
Add an atomic Python migration runner (`m0013_voice_calls_strict_rebuild.py`) following the `m0011_micro_pods.py` pattern to rebuild existing non strict version twelve voice tables into strict SQLite tables without losing session or rating rows, and enforce a hard ASGI lifespan startup refusal when the production environment boots with a missing or default TURN secret.
**Done when:** `m0013_voice_calls_strict_rebuild.upgrade(conn)` sets `PRAGMA foreign_keys = OFF` before `BEGIN IMMEDIATE`, creates strict replacement tables, copies all rows, drops and renames tables, recreates all four indexes, asserts exact row counts and an empty `PRAGMA foreign_key_check` on both tables, records migration thirteen, and restores `PRAGMA foreign_keys = ON` after commit; both upgrading a populated version twelve database and initializing a fresh version thirteen database pass automated tests; and entering the FastAPI `_app_lifespan` under `CARTMATE_ENV=production` with a missing or default `CARTMATE_TURN_SECRET` raises a `RuntimeError` immediately without breaking non lifespan subprocess tests.
- [x] Design it (spec): `/architect strict voice table rebuild migration and production TURN startup guard`
- [x] Build it: `/develop strict voice table rebuild migration and production TURN startup guard`
   - [x] Implement `backend/migrations/0013_voice_calls_strict_rebuild.sql` and atomic Python runner `backend/migrations/m0013_voice_calls_strict_rebuild.py` wired into `storage.py:apply_migrations()`
   - [x] Enforce `assert_production_turn_secret_configured()` inside FastAPI `_app_lifespan` in `backend/main.py`
   - [x] Test populated v12 to v13 table rebuild, fresh v13 initialization, and subprocess lifespan refusal on missing and default TURN secrets
- [x] Verify it: `/check verify strict voice table rebuild migration and production TURN startup guard`
- [x] Test it: `/test strict voice table rebuild migration and production TURN startup guard`
- [x] Review it: `/check review strict voice table rebuild migration and production TURN startup guard`
- [x] Document it: `/document`
Spec 0013 in `docs/specs/0013-final-audit-closure.md`

### 12. Full four language localization across pod, voice, and safety views · done · Beta
Eliminate all remaining hardcoded Polish strings in the micro pod feed and ten minute voice HUD, expand the safety hub from two languages (`pl` and `en`) to all four supported locales (`pl`, `en`, `uk`, `ru`), and add automated language switch assertions.
**Done when:** switching the header language selector across Polish, English, Ukrainian, and Russian updates every visible label, template title, value prop pill, venue field, seat counter, chat drawer state, in call control, block modal, quota widget, privacy rule, icebreaker prompt, rating modal option, and safety hub card with zero hardcoded Polish text or `pl` only ternary fallbacks remaining in `PodFeed.tsx`, `VoiceCallHUD.tsx`, or `SafetyHub.tsx`, verified by automated tests across all four locales.
- [x] Design it (spec): `/architect full four language localization across pod, voice, and safety views`
- [x] Build it: `/develop full four language localization across pod, voice, and safety views`
   - [x] Complete `POD_COPY` across `pl`, `en`, `uk`, and `ru` for all remaining strings in `frontend/src/components/PodFeed.tsx`
   - [x] Complete `VOICE_COPY` across `pl`, `en`, `uk`, and `ru` for all in call, lobby, icebreaker, block, and rating strings in `frontend/src/components/VoiceCallHUD.tsx`
   - [x] Replace binary `lang === 'pl'` ternaries in `frontend/src/components/SafetyHub.tsx` with a four language `SAFETY_COPY` dictionary and add automated locale switch assertions
- [x] Verify it: `/check verify full four language localization across pod, voice, and safety views`
- [x] Test it: `/test full four language localization across pod, voice, and safety views`
- [x] Review it: `/check review full four language localization across pod, voice, and safety views`
- [x] Document it: `/document`
Spec 0013 in `docs/specs/0013-final-audit-closure.md`

### 13. End to end pod and voice browser journeys and root pytest isolation · done · GA
Add a dedicated multi user Playwright test suite (`qa/tests/pods-and-voice.spec.ts`) covering real time micro pod quorum unlock, two user group chat delivery, and two user WebRTC voice matching, hangup, and post call rating, execute `codex_mr02_destination_probe.cjs` inside the automated pytest pass from the repository root, and isolate `ops/test_pilot_preflight.py` so root level `pytest` passes cleanly.
**Done when:** `qa/tests/pods-and-voice.spec.ts` uses two isolated browser contexts to verify that a third member joining a pod unlocks quorum live for both members, a chat message sent by user A renders live in user B's open drawer, and two matched callers with fake media streams connect inside an active call window, hang up, and submit a post call rating on desktop and mobile viewports; `codex_mr02_destination_probe.cjs` runs via subprocess with `cwd` at the repository root inside `pytest`; and `ops/test_pilot_preflight.py` runs its real app check in an isolated subprocess (or reloads `config` and `main`) so running `pytest` from the repository root passes every backend and ops test together.
- [x] Design it (spec): `/architect end to end pod and voice browser journeys and root pytest isolation`
- [x] Build it: `/develop end to end pod and voice browser journeys and root pytest isolation`
   - [x] Create `qa/tests/pods-and-voice.spec.ts` with two context pod quorum plus live chat delivery and two context voice match, hangup, and rating journeys
   - [x] Add a repository root subprocess test invoking `node qa/codex_mr02_destination_probe.cjs` inside `backend/test_voice_calls.py`
   - [x] Isolate `test_preflight_real_fastapi_app` in `ops/test_pilot_preflight.py` from cached `main.CARTMATE_ENV` state so root `pytest` passes
- [x] Verify it: `/check verify end to end pod and voice browser journeys and root pytest isolation` (6/6 tests proven across Desktop Chromium and Pixel 7 mobile in 16.7s; 249/249 root pytest clean)
- [x] Test it: `/test end to end pod and voice browser journeys and root pytest isolation`
- [x] Review it: `/check review end to end pod and voice browser journeys and root pytest isolation`
- [x] Document it: `/document`
Spec 0013 in `docs/specs/0013-final-audit-closure.md`

## Deferred
Out of scope for the current build pass, kept so the plan stays honest.
- **Dedicated relay host**: separate media relay infrastructure outside the single approved pilot host · needs a decision (pilot co-locates coturn on EC2 host)
- **Background push notifications**: prompt for browser notification permissions when joining a pod · needs a decision
- **Audio output device switcher**: speakerphone routing toggle across mobile browsers · done (implemented in VoiceCallHUD via setSinkId and output device toggle)

## Legend

**The decision box.** Every feature carries exactly one, the sub task whose label ends with `(spec)`. Its wording varies, so skills locate it by that `(spec)` suffix, never by an exact label. Every other box is an execution box and `/architect` never ticks one.

**Feature lifecycle**: the scope updates as a feature moves. Each row shows what it shows and who sets it.
