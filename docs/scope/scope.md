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

### 8. Voice signaling resilience, quotas, and abuse controls · done
Harden peer to peer audio handshake reliability during microphone permission prompts, close quota and cooldown loopholes on reported calls, enforce evening call hours and rate limits, and fail closed on default relay secrets in production.
**Done when:** early session offers and network candidates buffer safely until microphone setup finishes without listener churn or duplicate hangup requests, reported calls count toward the three call daily cap and ten minute cooldown, inappropriate call ratings escalate to the human moderation queue while honoring the explicit block checkbox, production enforces the evening call window in Warsaw time, pod and voice inputs pass region, length, rate limit, and content safety checks with sanitized errors, expired pods clear automatically without hanging test shutdowns, brief cellular drops get a twelve second grace window that never delays blocks or bans, and production readiness blocks startup if the relay secret uses a development default.
- [x] Build it: `/develop voice signaling resilience, quotas, and abuse controls`
- [x] Verify it: `/check verify voice signaling resilience, quotas, and abuse controls`
- [x] Test it: `/test voice signaling resilience, quotas, and abuse controls`

### 9. Navigation safety route, native origin guard, and accessible live UI · done
Restore the five item mobile bottom bar with direct Safety and 112 access, route all pod and voice client calls through the native destination token guard, wire live pod room socket updates, and finish keyboard focus and screen reader polish.
**Done when:** bottom navigation keeps the Safety button reachable at 320px width while pairing micro pods and ten minute voice calls in a shared social switcher, every pod and voice API helper withholds bearer tokens on unapproved native origins, open pod chat drawers stream live messages and quorum shifts over the realtime socket without browser alert popups, modals trap focus and close on Escape, countdown announcements speak only at five minutes, one minute, and thirty seconds, match chimes respect reduced motion settings, copy supports all four app languages, and heavy feature views load lazily.
- [x] Build it: `/develop navigation safety route, native origin guard, and accessible live UI`
- [x] Verify it: `/check verify navigation safety route, native origin guard, and accessible live UI`
- [x] Test it: `/test navigation safety route, native origin guard, and accessible live UI`

### 10. Continuous integration recovery and regression suite · done
Restore a green main pipeline by expanding compile checks, backup manifest tallies, native destination probes, and automated backend and browser regression tests across desktop and mobile profiles.
**Done when:** syntax compile checks include the voice manager and micro pod migration runner, backup manifests record pod and voice session counts alongside users and trips, the native destination probe verifies zero token leakage across all pod and voice helpers, isolated backend suites cover every new safety and block invariant without touching the local development database, and desktop plus mobile browser journeys pass end to end in continuous integration.
- [x] Build it: `/develop continuous integration recovery and regression suite`
- [x] Verify it: `/check verify continuous integration recovery and regression suite`
- [x] Test it: `/test continuous integration recovery and regression suite`

## Deferred
Out of scope for the current build pass, kept so the plan stays honest.
- **Dedicated relay host**: separate media relay infrastructure outside the single approved pilot host · needs a decision
- **Background push notifications**: prompt for browser notification permissions when joining a pod · needs a decision
- **Audio output device switcher**: speakerphone routing toggle across mobile browsers · Prototype

## Legend

**The decision box.** Every feature carries exactly one, the sub task whose label ends with `(spec)`. Its wording varies, so skills locate it by that `(spec)` suffix, never by an exact label. Every other box is an execution box and `/architect` never ticks one.

**Feature lifecycle**: the scope updates as a feature moves. Each row shows what it shows and who sets it.
