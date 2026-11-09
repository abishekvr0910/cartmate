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

## Legend

**The decision box.** Every feature carries exactly one, the sub task whose label ends with `(spec)`. Its wording varies, so skills locate it by that `(spec)` suffix, never by an exact label. Every other box is an execution box and `/architect` never ticks one.

**Feature lifecycle**: the scope updates as a feature moves. Each row shows what it shows and who sets it.
