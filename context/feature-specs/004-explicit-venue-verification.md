# 004 — Explicit venue verification and a moderator venue screen

Status: **Design accepted by the founder, revision 2, not yet implemented** (2026-11-15). Feature 16 of [the friends pilot hardening scope](../../docs/scope/claude-hardening.md). Revision 2 folds in two independent reviews of revision 1; the changes are listed under "What changed in revision 2". The seven founder decisions at the end were **accepted by the founder on 2026-11-15, each as recommended**.

## Problem (observed in code at `ba030ce` plus the uncommitted feature 14 and 17 work)

1. **Creating a place verifies it.** `storage.create_third_place` writes `verified_at or now_str`, so `POST /api/pods/places` stamps "checked in person" at the moment of creation. Nobody has to have been there.
2. **No record of who or when.** `third_places` has one nullable `verified_at` column. There is no visit record, no actor and no way to tell a real visit from a default.
3. **A closed venue cannot be taken out of use.** `third_places.is_active` exists and `trg_pods_validate_insert` honours it, but no route or screen sets it, and nothing reports the pods already scheduled there. No moderator route cancels a pod either; `POST /api/pods/sweep` only cancels pods past their quorum deadline.
4. **No screen for places.** The frontend only reads places (`fetchThirdPlaces` in `frontend/src/api.ts`, which has no caller). Adding a place is a moderator-only API call; verifying one of the nine seeded places needs raw SQL.
5. **No screen for scheduling a pod.** `frontend/src/api.ts` has no call to `POST /api/pods`. Pods can be joined, left and chatted in from the app, but only created through the API.
6. **API and database disagree on validation.** `ThirdPlaceCreateRequest` accepts any `kind` and a 3-character `meeting_point`; the table requires one of seven kinds and 10–280 characters. A mismatch surfaces as a generic HTTP 400 "Nie udało się utworzyć miejsca."
7. **Two different answers to "is this user a moderator".** `require_moderator` accepts the import-time `MODERATOR_USER_IDS` and the current `CARTMATE_MODERATOR_USER_IDS`; `GET /api/moderation/access`, which the profile screen uses to show moderator buttons, checks only the first. A moderator can be allowed by the server and still not see the button.
8. **An empty venue list is invisible.** `/api/ready` does not look at venues, and the pod feed shows its "Sprawdzone Third Places" pill whether or not any exists.

## Design

### Data: migration 0017 (forward only; applied migrations are not rewritten)

All timestamps are canonical UTC and carry the same format check the rest of the schema uses, so text comparison and `MAX()` order them correctly:
`CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', col) IS col)`.

```sql
-- One row per moderator attestation of an in-person visit.
CREATE TABLE third_place_visits (
    id                       INTEGER PRIMARY KEY,
    third_place_id           INTEGER NOT NULL REFERENCES third_places(id) ON DELETE RESTRICT,
    moderator_user_id        TEXT    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    visited_at               TEXT    NOT NULL CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', visited_at) IS visited_at),
    recorded_at              TEXT    NOT NULL CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', recorded_at) IS recorded_at),
    was_there_in_person      INTEGER NOT NULL CHECK (was_there_in_person = 1),
    meeting_point_is_public  INTEGER NOT NULL CHECK (meeting_point_is_public = 1),
    notes                    TEXT    CHECK (notes IS NULL OR length(notes) <= 500),
    -- Withdrawal is only for a visit that was entered wrongly. A venue that has closed is closed, below.
    withdrawn_at             TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', withdrawn_at) IS withdrawn_at),
    withdrawn_by_user_id     TEXT    REFERENCES users(id) ON DELETE RESTRICT,
    withdrawn_reason         TEXT    CHECK (withdrawn_reason IS NULL OR length(withdrawn_reason) BETWEEN 5 AND 300),
    CHECK (visited_at <= recorded_at),
    CHECK ((withdrawn_at IS NULL) = (withdrawn_by_user_id IS NULL)),
    CHECK ((withdrawn_at IS NULL) = (withdrawn_reason IS NULL))
) STRICT;

-- One row per closure of a venue. A venue is closed while it has a row with reopened_at IS NULL.
CREATE TABLE third_place_closures (
    id                    INTEGER PRIMARY KEY,
    third_place_id        INTEGER NOT NULL REFERENCES third_places(id) ON DELETE RESTRICT,
    closed_by_user_id     TEXT    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    closed_at             TEXT    NOT NULL CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', closed_at) IS closed_at),
    reason                TEXT    NOT NULL CHECK (length(reason) BETWEEN 5 AND 300),
    reopened_at           TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', reopened_at) IS reopened_at),
    reopened_by_user_id   TEXT    REFERENCES users(id) ON DELETE RESTRICT,
    CHECK ((reopened_at IS NULL) = (reopened_by_user_id IS NULL))
) STRICT;

-- Verification that existed before visits were recorded. Kept for audit only; it grants nothing.
CREATE TABLE third_place_legacy_verifications (
    third_place_id        INTEGER NOT NULL REFERENCES third_places(id) ON DELETE RESTRICT,
    previous_verified_at  TEXT    NOT NULL,
    cleared_at            TEXT    NOT NULL,
    source                TEXT    NOT NULL CHECK (source = 'before_0017_no_visit_record'),
    PRIMARY KEY (third_place_id, previous_verified_at)
) STRICT, WITHOUT ROWID;
```

**Upgrade step, in this order.** (1) Copy every non-null `third_places.verified_at` into `third_place_legacy_verifications`. (2) Set those `verified_at` values to `NULL`. (3) Create the triggers. The earlier timestamp is preserved; its authority to host pods is withdrawn. Migration 0016 already cleared the nine seeded placeholders, whose single value (`2026-11-10T00:00:00Z`) is recorded in that migration's text.

**Derived verification.** `third_places.verified_at` becomes a derived value, enforced with the same pattern as `confirmed_count` in `trg_pods_guard_update`:

```sql
-- The only value verified_at may hold: the latest visit that is not withdrawn
-- and that happened after the venue's most recent closure, if it has one.
CREATE TRIGGER trg_third_places_verified_is_derived
BEFORE UPDATE OF verified_at ON third_places
BEGIN
    SELECT RAISE(ABORT, 'verified_at_is_derived')
     WHERE NEW.verified_at IS NOT (
        SELECT MAX(v.visited_at) FROM third_place_visits v
         WHERE v.third_place_id = NEW.id AND v.withdrawn_at IS NULL
           AND v.visited_at > COALESCE(
               (SELECT MAX(c.closed_at) FROM third_place_closures c WHERE c.third_place_id = NEW.id), ''));
END;
```

Because the guard compares against the same sub-query the visit triggers write, their own updates pass it. After-insert and after-update triggers on `third_place_visits` and `third_place_closures` recompute `verified_at` and, for closures, set `is_active` to 0 on closing and 1 on reopening. A place inserted with a non-null `verified_at` and no visit is normalised to `NULL` by an after-insert trigger, which keeps `ops/seed_third_places.py` and migration 0014 working. Visit and closure rows are immutable except for their withdrawal and reopening columns, which can be set once.

`trg_pods_validate_insert` already refuses a pod at a place that is inactive or has no `verified_at`; it is unchanged.

**Withdrawing versus closing.**

| Action | For | Effect on verification | Effect on pods |
|---|---|---|---|
| Withdraw a visit | A visit entered against the wrong place or by mistake | Falls back to the next latest valid visit, or to unverified | None; the venue itself is not in question |
| Close a venue | The place has shut, moved, become unsafe or is no longer public | The venue is inactive and unverified. Earlier visits stay on record but no longer count | No new pod can be created. Every forming or quorum pod there is listed for the moderator, who cancels each with a reason |
| Reopen a venue | The closure has ended | Still unverified until a **new** visit is recorded after the closure | Pods can be scheduled again once that visit exists |

### API

| Route | Who | Behaviour |
|---|---|---|
| `POST /api/pods/places` | moderator | Creates the place **unverified**. Validation matches the table: `kind` is one of the seven allowed values, `meeting_point` is 10–280 characters. The slug is generated on the server (below). Returns `verified_at: null`. |
| `GET /api/moderation/places` | moderator | All places, each with status (unverified, verified, closed), latest valid visit (time and moderator name), and its forming and quorum pods. |
| `POST /api/moderation/places/{place_id}/visits` | moderator | Records a visit. Body: `visited_at`, `was_there_in_person: true`, `meeting_point_is_public: true`, optional `notes`. The actor is always the signed-in moderator, never a field in the body. Refuses a visit time in the future or older than the allowed age (decision 2), an unknown or closed place, and either confirmation not literally `true`. Rate limited. |
| `POST /api/moderation/places/{place_id}/visits/{visit_id}/withdraw` | moderator | Withdraws a mistaken visit with a reason. |
| `POST /api/moderation/places/{place_id}/close` | moderator | Closes the venue with a reason. Returns the forming and quorum pods there, which the screen then shows as needing action. |
| `POST /api/moderation/places/{place_id}/reopen` | moderator | Reopens a closed venue. It stays unverified until a new visit. |
| `POST /api/moderation/pods/{pod_id}/cancel` | moderator | Cancels a forming or quorum pod with one of the existing reasons `venue_unavailable`, `weather`, `safety`, `operator`, and broadcasts the cancellation to its members. |
| `GET /api/pods/places` | signed-in user | Unchanged: verified, active places only. |
| `POST /api/pods` | signed-in admitted user | **Permission unchanged** (decision 7). The request is still refused for an unverified or closed place by the database trigger. A duplicate slot returns HTTP 409 with a message that names the existing pod, instead of today's generic 400. |
| `GET /api/moderation/access` | signed-in user | Uses the same check as `require_moderator`, through one shared `is_moderator(user_id)` function, so the button and the server always agree. |

**Slug generation.** Lowercase the name and city, transliterate Polish letters (`ą→a ć→c ę→e ł→l ń→n ó→o ś→s ź→z ż→z`), replace every other run of characters outside `a-z0-9` with one hyphen, trim hyphens, cut to 64 characters, and require at least 3. On a collision append `-2`, `-3`, and so on. A moderator never types a slug, and a slug problem is never reported as a bare 400.

### Screens (all text in Polish, English, Ukrainian and Russian)

Entry point: a "Miejsca spotkań" button beside the existing moderation button in `ProfileView`, under the same `canModerate` condition. It opens a new `VenueConsole.tsx`; `ModeratorConsole.tsx` is not touched.

1. **Venue list.** One row per place: name, city, kind, meeting point and a status: "Niezweryfikowane", "Sprawdzone osobiście: date · moderator name", or "Zamknięte: date · reason". Row actions depend on status: record a visit, withdraw a visit, close, reopen, schedule a pod. A closed venue with live pods shows them under a "Wymaga działania" heading with a cancel button each. When no place is verified, a banner says pods cannot be scheduled yet.
2. **Add a place.** Name, kind (seven choices), city (the launch-boundary cities), optional district and address, meeting point with a 10–280 character counter, indoor or outdoor, the activities offered there, optional accessibility notes. Coordinates come from a "Użyj mojej lokalizacji" button with manual latitude and longitude fields as the fallback; the location is used once for the venue's coordinates and is not stored against the moderator. The form states that adding a place does not mark it as checked.
3. **Record a visit.** Shows the place and its meeting point. The moderator enters when they were there (default now, never in the future) and ticks two required boxes: "Byłem/Byłam tam osobiście w podanym czasie" and "Punkt spotkania istnieje i jest ogólnodostępny". The confirm button names the moderator: "Potwierdzam wizytę jako Zuzanna".
4. **Schedule a pod.** This screen is for moderators; it does not change who may call `POST /api/pods` (decision 7). Fields:
   - Activity: only the templates offered at that place.
   - Date and start time, entered and shown as **Warsaw time** with that label, and converted to UTC before sending.
   - Duration: 15 minutes to 4 hours, defaulting to the template's duration.
   - "Potwierdzenie do": the quorum deadline. Defaults to two hours before the start. It must be later than now and no later than the start; the form enforces both before sending.
   - Language, and an optional exchange language for the language-exchange template.
   - Cost: no expected spend (default), optional spend, or pay your own way with a required maximum.
   - A duplicate slot shows the existing pod with a "join it instead" link.
5. **Pod feed empty state, for everyone.** When no verified place exists in the viewer's city, the feed says so instead of showing an empty grid.

### Readiness and deployment

- `/api/ready` stays an infrastructure and configuration check, so bootstrap and liveness are unaffected by an empty venue list.
- `ops/pilot_preflight.py` gains a check, on by default, that fails the go/no-go when the deployment has no verified, active place, and prints the count when it has.
- **Before migration 0017 runs on any database that is not disposable**, an operator runs a read-only report against a copy of it: how many places are verified, which of them would be cleared, and which have live pods. The deployment step reads that report; it does not assume the database is empty. The report ships as `ops/venue_verification_report.py` with a test.

## Acceptance tests to write first

- **Migration and storage:** creating a place leaves it unverified; a direct `UPDATE third_places SET verified_at = …` without a visit is rejected; a timestamp with an offset or milliseconds is rejected by the table; a visit sets `verified_at` to the visit time; withdrawing the only visit clears it; withdrawing the newer of two falls back to the older; closing clears verification even with older visits and blocks pod creation; reopening does not restore it; a new visit after reopening does. Upgrade from v16 with a place verified through the old API keeps the old timestamp in the legacy table and clears its authority. Reseeding after a real visit keeps it.
- **API:** a non-moderator gets 403 on every moderator route; a future visit time, a too-old visit time and an unticked confirmation each get 422; the recorded actor is the session user even when the body names someone else; a pod at an unverified or closed place gets 400 and succeeds after a visit; a duplicate slot gets 409; `GET /api/moderation/access` and `require_moderator` agree for a moderator configured only through the environment variable; slugs for names with Polish letters and for two identical names are valid and distinct.
- **Browser:** a moderator adds a place, records a visit and schedules a pod without SQL or API tools, with labels checked in all four languages; closing a venue lists its pods and cancelling one notifies its members; a non-moderator never sees the entry point; the empty-state text appears when no place is verified.
- **Operations:** the preflight fails with zero verified places and passes with one; the report lists the places a migration would clear.

## Build order

1. Migration 0017, storage functions, the routes, the shared moderator check and their tests. **This step also updates every fixture that relies on a place being verified at creation:** `backend/test_pod_expiry.py`, `backend/test_micro_pods_api.py`, `backend/test_funnel_analytics.py`, `qa/tests/pods-and-voice.spec.ts`, and any other caller found by searching for `create_third_place` and `/api/pods/places`. They get one shared helper that records a visit.
2. `VenueConsole` (list, add, record visit, withdraw, close, reopen, cancel a pod) with four-language text and browser tests.
3. Schedule-a-pod form, pod feed empty state, the preflight check and the report script.

## Out of scope

Pod scheduling by ordinary participants from the app; photographs or documents as proof of a visit; an external map or places provider; automatic re-verification reminders; any change to age, admission or SOS policy; AI monitoring; translating server-sent Polish strings.

## Limits this design cannot remove

A visit record is a moderator's signed statement, not proof. The software can record who said they went and when; it cannot establish that they did. Feature 19 (the hosted rehearsal) still needs a person to go to the venue.

## What changed in revision 2

- Withdrawing a visit and closing a venue are separate actions. Closing removes verification regardless of older visits, blocks new pods, lists existing pods for moderator action, and requires a fresh visit after reopening. A moderator pod-cancel route is added because none exists.
- Pre-existing verification is copied to an audit table before its authority is cleared, and a read-only report must be run against the real target database before the migration. The assumption that no pilot database exists is removed.
- Every timestamp column has the canonical UTC format check, and the derived-value guard is written in the same form as `trg_pods_guard_update` so the recomputing triggers do not trip it.
- `GET /api/moderation/access` and `require_moderator` share one check.
- The schedule form lists the quorum deadline, cost, Warsaw-time entry and duplicate-slot handling; the wording makes clear that "moderator-only" describes the screen, not the API permission.
- Slug generation handles Polish letters and collisions.
- Fixing existing test fixtures is part of step 1.

## Founder decisions (all seven accepted as recommended, 2026-11-15)

| # | Question | Decision |
|---|---|---|
| 1 | At upgrade, a place that is marked verified but has no visit record: withdraw its verification? | Yes, after copying the old timestamp to the audit table and running the report on the target database. |
| 2 | How old may a visit be when it is recorded? | 30 days. |
| 3 | May the moderator who added a place also record its visit? | Yes. With two moderators a second-person rule would block the friends test. |
| 4 | Should a verification expire? | Not for the friends test. Show the visit date so staleness is visible. |
| 5 | Should an empty venue list block `/api/ready`? | No. Keep `/api/ready` for infrastructure; make the preflight go/no-go require one verified place. |
| 6 | Should recording a visit capture the phone's location as evidence? | No. It is easy to fake and adds location data to store; a signed declaration is enough at this size. |
| 7 | Should `POST /api/pods` itself become moderator-only, or stay open to any admitted user as it is today? | Leave it as it is in this slice. Only moderators get a screen for it, and changing the permission would be a separate, deliberate change with its own tests. |
