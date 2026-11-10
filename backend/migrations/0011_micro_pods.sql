-- =============================================================================
-- CartMate migration 0011: Micro-Pods anchored in Third Places
-- =============================================================================
-- Applies on top of schema version 10. Purely additive: new tables, triggers,
-- one view, indexes, and a seed of the four core activity templates. No legacy
-- table (users, 1-on-1 outings/trips, hotspots, chat, blocks, reports) is
-- altered or dropped, so the old flow keeps working until the client switches.
--
-- Apply ONLY through m0011_micro_pods.upgrade(): it runs every statement in one
-- BEGIN IMMEDIATE transaction, checks foreign keys, bumps PRAGMA user_version
-- 10 -> 11 and commits; any failure rolls cartmate.db back to version 10.
--
-- Conventions
--   * Timestamps are canonical UTC text 'YYYY-MM-DDTHH:MM:SSZ' (CHECK-enforced),
--     so text order == time order. "Today" in Europe/Warsaw is computed in the
--     API and passed in as a UTC range.
--   * Money is integer minor units (grosze) + ISO-4217 currency, never floats.
--   * Domain errors are RAISE(ABORT, '<code>') -> sqlite3.IntegrityError where
--     str(exc) == '<code>' and exc.sqlite_errorname == 'SQLITE_CONSTRAINT_TRIGGER'.
--     The API maps these codes to 409/403 responses.
--
-- Pod lifecycle. forming <-> quorum is automatic and atomic with every
-- join/leave; cancelled and completed are terminal and set by the app.
--
--      join/leave            app sweep after ends_at
--   forming <------> quorum ------------------------> completed
--      |               |
--      +------+--------+  app: quorum deadline missed, operator, weather...
--             v
--         cancelled
--
-- Invariants enforced here (each one has a test):
--   I1  3 <= min_participants <= max_participants <= 5. A pod is never a 1-on-1
--       and never a crowd.
--   I2  confirmed_count always equals the number of confirmed members and never
--       exceeds max_participants, even under concurrent joins.
--   I3  A live pod's status agrees with its count: 'quorum' iff count >= min.
--   I4  Members can post only while the pod is at quorum. There is never an open
--       chat with fewer than 3 confirmed people, so chat can't turn into a 1-on-1.
--   I5  cancelled/completed are terminal; only a pod at quorum can complete.
--   I6  The terms people joined under (what, where, when, language, size, spend)
--       cannot change. To change them, cancel the pod and create a new one.
--   I7  'no_expected_spend' pods carry no amount; 'pay_own_way' pods must state
--       a maximum; any stated amount is 1-100 PLN.
--   I8  Cohort pods are joinable only by active cohort members; revoking a
--       membership removes the user from that cohort's live pods.
--   I9  A member removed by an operator can never rejoin that pod.
--   I10 Pods only happen at active, operator-verified third places that offer
--       the activity template.
--   I11 Anti-fragmentation: no second pod for the same slot (place, activity,
--       start, language pair, cohort) while a live one there still has seats.
--   I12 Voucher redemption respects cohort, revocation, expiry, max_redemptions.
--   I13 Chat messages are evidence for moderation: content is immutable; only
--       moderation_status and deleted_at may change.
--
-- Binding assumptions about the existing schema (checked by upgrade()):
--   * users(id) is an INTEGER PRIMARY KEY.
--   * FKs to users are ON DELETE RESTRICT: account deletion must anonymise the
--     user row (keeps the safety audit trail) instead of hard-deleting it.
--   * Blocks are enforced in storage.join_pod() against the existing block
--     table (not visible to this migration).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Activity templates: the structured formats that give a pod its focal point
-- -----------------------------------------------------------------------------
CREATE TABLE activity_templates (
    code                       TEXT    PRIMARY KEY
                                       CHECK (length(code) BETWEEN 3 AND 32 AND code NOT GLOB '*[^a-z_]*'),
    name                       TEXT    NOT NULL CHECK (length(name) BETWEEN 3 AND 60),  -- internal label; UI localises by code
    default_duration_min       INTEGER NOT NULL CHECK (default_duration_min BETWEEN 15 AND 240),
    structure                  TEXT    NOT NULL                                      -- JSON array of {"phase", "minutes"}
                                       CHECK (json_valid(structure) AND json_type(structure) = 'array'),
    default_min_participants   INTEGER NOT NULL DEFAULT 3 CHECK (default_min_participants BETWEEN 3 AND 5),
    default_max_participants   INTEGER NOT NULL DEFAULT 5 CHECK (default_max_participants BETWEEN 3 AND 5),
    default_spend_expectation  TEXT    NOT NULL
                                       CHECK (default_spend_expectation IN ('no_expected_spend', 'optional_spend', 'pay_own_way')),
    sort_order                 INTEGER NOT NULL DEFAULT 0,
    is_active                  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at                 TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                                       CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS created_at),
    CHECK (default_min_participants <= default_max_participants)
) STRICT;

INSERT INTO activity_templates (code, name, default_duration_min, structure, default_spend_expectation, sort_order) VALUES
    ('study_sprint',      'Study / Co-work Sprint',  60,
     '[{"phase":"focus","minutes":45},{"phase":"coffee_break","minutes":15}]',
     'no_expected_spend', 10),
    ('park_walk',         'Park Walk & Talk',        45,
     '[{"phase":"walk_and_talk","minutes":45}]',
     'no_expected_spend', 20),
    ('board_games',       'Board Games / Cards',     90,
     '[{"phase":"intros_and_setup","minutes":10},{"phase":"play","minutes":70},{"phase":"wrap_up","minutes":10}]',
     'no_expected_spend', 30),
    ('language_exchange', 'Language Exchange Table', 60,
     '[{"phase":"intros","minutes":5},{"phase":"language_a","minutes":25},{"phase":"language_b","minutes":25},{"phase":"wrap_up","minutes":5}]',
     'optional_spend',    40);


-- -----------------------------------------------------------------------------
-- 2. Cohorts and voucher codes: invite-only partner communities for the pilot
-- -----------------------------------------------------------------------------
CREATE TABLE cohorts (
    id                     INTEGER PRIMARY KEY,
    slug                   TEXT    NOT NULL UNIQUE
                                   CHECK (length(slug) BETWEEN 3 AND 48 AND slug NOT GLOB '*[^a-z0-9-]*'),
    name                   TEXT    NOT NULL CHECK (length(name) BETWEEN 2 AND 120),
    kind                   TEXT    NOT NULL CHECK (kind IN ('university', 'coworking', 'employer', 'community', 'other')),
    -- 1 = the partner has agreed in writing that everyone it issues codes to is 18+.
    -- Only such cohorts may admit users without the in-person ID check.
    attests_adult          INTEGER NOT NULL DEFAULT 0 CHECK (attests_adult IN (0, 1)),
    adult_attestation_ref  TEXT    CHECK (adult_attestation_ref IS NULL OR length(adult_attestation_ref) BETWEEN 3 AND 200),
    archived_at            TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', archived_at) IS archived_at),
    created_at             TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                                   CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS created_at),
    CHECK (attests_adult = 0 OR adult_attestation_ref IS NOT NULL)
) STRICT;

CREATE TABLE cohort_vouchers (
    id                INTEGER PRIMARY KEY,
    cohort_id         INTEGER NOT NULL REFERENCES cohorts(id) ON DELETE RESTRICT,
    -- HMAC-SHA256(server_secret, normalised_code) as 64 lowercase hex chars.
    -- Codes are bearer secrets: the plaintext is never stored.
    code_hash         TEXT    NOT NULL UNIQUE
                              CHECK (length(code_hash) = 64 AND code_hash NOT GLOB '*[^0-9a-f]*'),
    code_hint         TEXT    CHECK (code_hint IS NULL OR length(code_hint) BETWEEN 1 AND 4),
    max_redemptions   INTEGER NOT NULL CHECK (max_redemptions BETWEEN 1 AND 5000),
    redemption_count  INTEGER NOT NULL DEFAULT 0,                               -- derived, see triggers
    expires_at        TEXT    NOT NULL CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', expires_at) IS expires_at),
    revoked_at        TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', revoked_at) IS revoked_at),
    note              TEXT    CHECK (note IS NULL OR length(note) <= 200),
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                              CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS created_at),
    CHECK (redemption_count BETWEEN 0 AND max_redemptions),
    CHECK (expires_at > created_at)
) STRICT;

CREATE TABLE cohort_memberships (
    id              INTEGER PRIMARY KEY,
    cohort_id       INTEGER NOT NULL REFERENCES cohorts(id) ON DELETE RESTRICT,
    user_id         TEXT    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    voucher_id      INTEGER REFERENCES cohort_vouchers(id) ON DELETE RESTRICT,   -- NULL = added by an operator
    joined_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                            CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', joined_at) IS joined_at),
    revoked_at      TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', revoked_at) IS revoked_at),
    revoked_reason  TEXT    CHECK (revoked_reason IS NULL OR length(revoked_reason) BETWEEN 3 AND 200),
    UNIQUE (cohort_id, user_id),
    CHECK ((revoked_at IS NULL) = (revoked_reason IS NULL))
) STRICT;

CREATE INDEX idx_cohort_memberships_user    ON cohort_memberships (user_id) WHERE revoked_at IS NULL;
CREATE INDEX idx_cohort_memberships_voucher ON cohort_memberships (voucher_id) WHERE voucher_id IS NOT NULL;


-- -----------------------------------------------------------------------------
-- 3. Third places: fixed, operator-verified anchors with an exact meeting point
-- -----------------------------------------------------------------------------
CREATE TABLE third_places (
    id                   INTEGER PRIMARY KEY,
    slug                 TEXT    NOT NULL UNIQUE
                                 CHECK (length(slug) BETWEEN 3 AND 64 AND slug NOT GLOB '*[^a-z0-9-]*'),
    name                 TEXT    NOT NULL CHECK (length(name) BETWEEN 3 AND 120),
    kind                 TEXT    NOT NULL
                                 CHECK (kind IN ('library', 'park', 'cafe', 'coworking', 'campus', 'community_center', 'other')),
    city                 TEXT    NOT NULL CHECK (length(city) BETWEEN 2 AND 80),
    district             TEXT    CHECK (district IS NULL OR length(district) BETWEEN 2 AND 80),
    address              TEXT    CHECK (address IS NULL OR length(address) BETWEEN 5 AND 200),
    -- Where exactly people gather, e.g. "North side of the fountain, by the benches".
    meeting_point        TEXT    NOT NULL CHECK (length(meeting_point) BETWEEN 10 AND 280),
    latitude             REAL    NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude            REAL    NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    is_indoor            INTEGER NOT NULL CHECK (is_indoor IN (0, 1)),
    accessibility_notes  TEXT    CHECK (accessibility_notes IS NULL OR length(accessibility_notes) <= 500),
    cohort_id            INTEGER REFERENCES cohorts(id) ON DELETE RESTRICT,     -- NULL = public venue
    is_active            INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    verified_at          TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', verified_at) IS verified_at),  -- checked in person
    created_at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                                 CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS created_at),
    updated_at           TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                                 CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', updated_at) IS updated_at)
) STRICT;

-- Which formats an anchor supports (a fountain loop hosts walks, not board games).
CREATE TABLE third_place_templates (
    third_place_id  INTEGER NOT NULL REFERENCES third_places(id) ON DELETE CASCADE,
    template_code   TEXT    NOT NULL REFERENCES activity_templates(code) ON DELETE RESTRICT,
    PRIMARY KEY (third_place_id, template_code)
) STRICT, WITHOUT ROWID;

INSERT OR IGNORE INTO third_places (
    slug, name, kind, city, district, address, meeting_point,
    latitude, longitude, is_indoor, verified_at, created_at, updated_at
) VALUES
    ('katowice-biblioteka-slaska', 'Biblioteka Śląska - Hol Główny', 'library', 'Katowice', 'Śródmieście', 'plac Rady Europy 1, Katowice', 'Główne wejście przy recepcji na parterze', 50.2520, 19.0310, 1, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('katowice-trzy-stawy-polana', 'Dolina Trzech Stawów - Przystań', 'park', 'Katowice', 'Muchowiec', 'ul. Trzech Stawów, Katowice', 'Drewniany pomost przy wypożyczalni kajaków', 50.2395, 19.0350, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('katowice-strefa-kultury', 'Strefa Kultury - Plac KTW', 'campus', 'Katowice', 'Bogucice', 'plac Sławika i Antalla 1, Katowice', 'Schody wejściowe przed gmachem NOSPR', 50.2635, 19.0275, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('gliwice-palmiarnia-park', 'Palmiarnia Miejska - Park Chopina', 'park', 'Gliwice', 'Śródmieście', 'ul. Fredry 6, Gliwice', 'Główne wejście do Palmiarni przy fontannie', 50.2985, 18.6790, 1, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('gliwice-rynek-ratusz', 'Rynek w Gliwicach - Podcienia Ratusza', 'community_center', 'Gliwice', 'Stare Miasto', 'Rynek 1, Gliwice', 'Pod arkadami Ratusza naprzeciw fontanny Neptuna', 50.2938, 18.6654, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('gliwice-nowe-gliwice', 'Nowe Gliwice - Dziedziniec Cecha', 'coworking', 'Gliwice', 'Bojków', 'ul. Bojkowska 37, Gliwice', 'Dziedziniec główny przy cechowni (Budynek A)', 50.2780, 18.6835, 1, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('chorzow-park-slaski-rosarium', 'Park Śląski - Rosarium', 'park', 'Chorzów', 'Park Śląski', 'al. Różana, Chorzów', 'Główna pergola przy zegarze słonecznym', 50.2885, 18.9950, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('chorzow-sztygarka', 'Kompleks Sztygarka - Wieża Prezydent', 'community_center', 'Chorzów', 'Klimzowiec', 'ul. Piotra Skargi 34a, Chorzów', 'Plac pod wieżą wyciągową Szybu Prezydent', 50.3015, 18.9620, 0, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z'),
    ('chorzow-mbp-filia', 'Miejska Biblioteka Publiczna w Chorzowie', 'library', 'Chorzów', 'Centrum', 'ul. Sobieskiego 8, Chorzów', 'Strefa czytelni na I piętrze', 50.2970, 18.9540, 1, '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z', '2026-11-10T00:00:00Z');

INSERT OR IGNORE INTO third_place_templates (third_place_id, template_code)
SELECT id, 'study_sprint' FROM third_places WHERE slug = 'katowice-biblioteka-slaska'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'katowice-biblioteka-slaska'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'katowice-biblioteka-slaska'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'katowice-trzy-stawy-polana'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'katowice-trzy-stawy-polana'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'katowice-strefa-kultury'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'katowice-strefa-kultury'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'gliwice-palmiarnia-park'
UNION ALL SELECT id, 'study_sprint' FROM third_places WHERE slug = 'gliwice-palmiarnia-park'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'gliwice-palmiarnia-park'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'gliwice-rynek-ratusz'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'gliwice-rynek-ratusz'
UNION ALL SELECT id, 'study_sprint' FROM third_places WHERE slug = 'gliwice-nowe-gliwice'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'gliwice-nowe-gliwice'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'chorzow-park-slaski-rosarium'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'chorzow-park-slaski-rosarium'
UNION ALL SELECT id, 'park_walk' FROM third_places WHERE slug = 'chorzow-sztygarka'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'chorzow-sztygarka'
UNION ALL SELECT id, 'study_sprint' FROM third_places WHERE slug = 'chorzow-mbp-filia'
UNION ALL SELECT id, 'board_games' FROM third_places WHERE slug = 'chorzow-mbp-filia'
UNION ALL SELECT id, 'language_exchange' FROM third_places WHERE slug = 'chorzow-mbp-filia';


-- -----------------------------------------------------------------------------
-- 4. Pods: the primary entity. Already scheduled, 3-5 seats, quorum-gated chat
-- -----------------------------------------------------------------------------
CREATE TABLE pods (
    id                      INTEGER PRIMARY KEY,
    template_code           TEXT    NOT NULL REFERENCES activity_templates(code) ON DELETE RESTRICT,
    third_place_id          INTEGER NOT NULL REFERENCES third_places(id) ON DELETE RESTRICT,
    cohort_id               INTEGER REFERENCES cohorts(id) ON DELETE RESTRICT,   -- NULL = any admitted user
    created_by_user_id      TEXT    REFERENCES users(id) ON DELETE RESTRICT,     -- NULL = scheduled by the CartMate team
    title                   TEXT    CHECK (title IS NULL OR length(trim(title)) BETWEEN 3 AND 80),
    language_code           TEXT    NOT NULL                                     -- spoken language (ISO 639)
                                    CHECK (language_code GLOB '[a-z][a-z]' OR language_code GLOB '[a-z][a-z][a-z]'),
    exchange_language_code  TEXT    CHECK (exchange_language_code IS NULL
                                           OR exchange_language_code GLOB '[a-z][a-z]'
                                           OR exchange_language_code GLOB '[a-z][a-z][a-z]'),
    template_params         TEXT    CHECK (template_params IS NULL
                                           OR (json_valid(template_params) AND json_type(template_params) = 'object')),
    starts_at               TEXT    NOT NULL CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', starts_at) IS starts_at),
    ends_at                 TEXT    NOT NULL CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', ends_at) IS ends_at),
    -- If the pod is still 'forming' at this moment, the app cancels it (blame-free)
    -- so nobody turns up to a 1-on-1.
    quorum_deadline_at      TEXT    NOT NULL CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', quorum_deadline_at) IS quorum_deadline_at),
    min_participants        INTEGER NOT NULL DEFAULT 3 CHECK (min_participants BETWEEN 3 AND 5),
    max_participants        INTEGER NOT NULL DEFAULT 5 CHECK (max_participants BETWEEN 3 AND 5),
    confirmed_count         INTEGER NOT NULL DEFAULT 0,                          -- derived, maintained by triggers
    spend_expectation       TEXT    NOT NULL
                                    CHECK (spend_expectation IN ('no_expected_spend', 'optional_spend', 'pay_own_way')),
    spend_max_minor         INTEGER CHECK (spend_max_minor IS NULL OR spend_max_minor BETWEEN 100 AND 10000),
    spend_currency          TEXT    NOT NULL DEFAULT 'PLN' CHECK (spend_currency GLOB '[A-Z][A-Z][A-Z]'),
    status                  TEXT    NOT NULL DEFAULT 'forming'
                                    CHECK (status IN ('forming', 'quorum', 'cancelled', 'completed')),
    quorum_reached_at       TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', quorum_reached_at) IS quorum_reached_at),
    cancelled_at            TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', cancelled_at) IS cancelled_at),
    cancel_reason           TEXT    CHECK (cancel_reason IS NULL OR cancel_reason IN
                                           ('quorum_not_reached', 'quorum_lost', 'venue_unavailable', 'weather', 'safety', 'operator')),
    completed_at            TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', completed_at) IS completed_at),
    created_at              TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                                    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS created_at),
    updated_at              TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                                    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', updated_at) IS updated_at),

    CHECK (min_participants <= max_participants),                                              -- I1
    CHECK (confirmed_count BETWEEN 0 AND max_participants),                                    -- I2
    CHECK (status NOT IN ('forming', 'quorum')
           OR (status = 'quorum') = (confirmed_count >= min_participants)),                    -- I3
    CHECK (status NOT IN ('quorum', 'completed') OR quorum_reached_at IS NOT NULL),
    CHECK ((status = 'cancelled') = (cancelled_at IS NOT NULL)),
    CHECK ((status = 'cancelled') = (cancel_reason IS NOT NULL)),
    CHECK ((status = 'completed') = (completed_at IS NOT NULL)),
    CHECK (starts_at > created_at),
    CHECK (quorum_deadline_at > created_at AND quorum_deadline_at <= starts_at),
    CHECK (CAST(strftime('%s', ends_at) AS INTEGER)
           - CAST(strftime('%s', starts_at) AS INTEGER) BETWEEN 900 AND 14400),                -- 15 min .. 4 h
    CHECK (exchange_language_code IS NULL OR exchange_language_code <> language_code),
    CHECK (spend_expectation <> 'no_expected_spend' OR spend_max_minor IS NULL),               -- I7
    CHECK (spend_expectation <> 'pay_own_way' OR spend_max_minor IS NOT NULL)                  -- I7
) STRICT;

CREATE INDEX idx_pods_feed            ON pods (status, starts_at);
CREATE INDEX idx_pods_place_slot      ON pods (third_place_id, starts_at);
CREATE INDEX idx_pods_cohort          ON pods (cohort_id, starts_at) WHERE cohort_id IS NOT NULL;
CREATE INDEX idx_pods_quorum_deadline ON pods (quorum_deadline_at) WHERE status = 'forming';
CREATE INDEX idx_pods_to_complete     ON pods (ends_at) WHERE status = 'quorum';

CREATE TABLE pod_members (
    id                 INTEGER PRIMARY KEY,
    pod_id             INTEGER NOT NULL REFERENCES pods(id) ON DELETE RESTRICT,
    user_id            TEXT    NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status             TEXT    NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'left', 'removed')),
    removal_reason     TEXT    CHECK (removal_reason IS NULL OR removal_reason IN ('safety', 'blocked', 'cohort_revoked', 'operator')),
    joined_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                               CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', joined_at) IS joined_at),
    status_changed_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                               CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', status_changed_at) IS status_changed_at),
    arrived_at         TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', arrived_at) IS arrived_at),  -- optional "I'm here"
    UNIQUE (pod_id, user_id),
    CHECK ((status = 'removed') = (removal_reason IS NOT NULL))
) STRICT;

CREATE INDEX idx_pod_members_user ON pod_members (user_id, status);

CREATE TABLE pod_messages (
    id                 INTEGER PRIMARY KEY,
    pod_id             INTEGER NOT NULL REFERENCES pods(id) ON DELETE RESTRICT,
    sender_user_id     TEXT    REFERENCES users(id) ON DELETE RESTRICT,          -- NULL for system messages
    kind               TEXT    NOT NULL DEFAULT 'user' CHECK (kind IN ('user', 'system')),
    body               TEXT    NOT NULL CHECK (length(trim(body)) BETWEEN 1 AND 2000),
    -- 'flagged' = queued for human review (Jev shadow mode), still visible;
    -- 'hidden'  = hidden by an operator.
    moderation_status  TEXT    NOT NULL DEFAULT 'visible' CHECK (moderation_status IN ('visible', 'flagged', 'hidden')),
    created_at         TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                               CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', created_at) IS created_at),
    deleted_at         TEXT    CHECK (strftime('%Y-%m-%dT%H:%M:%SZ', deleted_at) IS deleted_at),
    CHECK ((kind = 'system') = (sender_user_id IS NULL))
) STRICT;

CREATE INDEX idx_pod_messages_pod ON pod_messages (pod_id, id);


-- -----------------------------------------------------------------------------
-- 5. Triggers: pods
-- -----------------------------------------------------------------------------
-- I10, I11 and creation sanity.
CREATE TRIGGER trg_pods_validate_insert
BEFORE INSERT ON pods
BEGIN
    SELECT RAISE(ABORT, 'pod_must_start_forming_and_empty')
     WHERE NEW.status <> 'forming' OR NEW.confirmed_count <> 0;
    SELECT RAISE(ABORT, 'template_unavailable')
     WHERE NOT EXISTS (SELECT 1 FROM activity_templates t
                        WHERE t.code = NEW.template_code AND t.is_active = 1);
    SELECT RAISE(ABORT, 'place_unavailable')
     WHERE NOT EXISTS (SELECT 1 FROM third_places p
                        WHERE p.id = NEW.third_place_id AND p.is_active = 1 AND p.verified_at IS NOT NULL);
    SELECT RAISE(ABORT, 'template_not_offered_at_place')
     WHERE NOT EXISTS (SELECT 1 FROM third_place_templates x
                        WHERE x.third_place_id = NEW.third_place_id AND x.template_code = NEW.template_code);
    SELECT RAISE(ABORT, 'place_restricted_to_other_cohort')
     WHERE EXISTS (SELECT 1 FROM third_places p
                    WHERE p.id = NEW.third_place_id AND p.cohort_id IS NOT NULL AND p.cohort_id IS NOT NEW.cohort_id);
    SELECT RAISE(ABORT, 'cohort_archived')
     WHERE EXISTS (SELECT 1 FROM cohorts c WHERE c.id = NEW.cohort_id AND c.archived_at IS NOT NULL);
    SELECT RAISE(ABORT, 'creator_not_in_cohort')
     WHERE NEW.cohort_id IS NOT NULL AND NEW.created_by_user_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM cohort_memberships m
                        WHERE m.cohort_id = NEW.cohort_id AND m.user_id = NEW.created_by_user_id
                          AND m.revoked_at IS NULL);
    SELECT RAISE(ABORT, 'duplicate_slot_join_existing_pod')
     WHERE EXISTS (SELECT 1 FROM pods q
                    WHERE q.third_place_id = NEW.third_place_id
                      AND q.starts_at = NEW.starts_at
                      AND q.template_code = NEW.template_code
                      AND q.cohort_id IS NEW.cohort_id
                      AND (   (q.language_code = NEW.language_code
                               AND q.exchange_language_code IS NEW.exchange_language_code)
                           OR (q.language_code = NEW.exchange_language_code
                               AND q.exchange_language_code = NEW.language_code))
                      AND q.status IN ('forming', 'quorum')
                      AND q.confirmed_count < q.max_participants);
END;

-- I2 (count is derived), I5 (transitions), I6 (immutable terms).
CREATE TRIGGER trg_pods_guard_update
BEFORE UPDATE ON pods
BEGIN
    SELECT RAISE(ABORT, 'pod_is_terminal')
     WHERE OLD.status IN ('cancelled', 'completed') AND NEW.status IS NOT OLD.status;
    SELECT RAISE(ABORT, 'pod_cannot_complete_without_quorum')
     WHERE NEW.status = 'completed' AND OLD.status = 'forming';
    SELECT RAISE(ABORT, 'pod_terms_immutable')
     WHERE NEW.template_code          IS NOT OLD.template_code
        OR NEW.third_place_id         IS NOT OLD.third_place_id
        OR NEW.cohort_id              IS NOT OLD.cohort_id
        OR NEW.created_by_user_id     IS NOT OLD.created_by_user_id
        OR NEW.language_code          IS NOT OLD.language_code
        OR NEW.exchange_language_code IS NOT OLD.exchange_language_code
        OR NEW.starts_at              IS NOT OLD.starts_at
        OR NEW.ends_at                IS NOT OLD.ends_at
        OR NEW.min_participants       IS NOT OLD.min_participants
        OR NEW.max_participants       IS NOT OLD.max_participants
        OR NEW.spend_expectation      IS NOT OLD.spend_expectation
        OR NEW.spend_max_minor        IS NOT OLD.spend_max_minor
        OR NEW.spend_currency         IS NOT OLD.spend_currency
        OR NEW.created_at             IS NOT OLD.created_at;
    SELECT RAISE(ABORT, 'confirmed_count_is_derived')
     WHERE NEW.confirmed_count IS NOT (SELECT COUNT(*) FROM pod_members m
                                        WHERE m.pod_id = NEW.id AND m.status = 'confirmed');
END;


-- -----------------------------------------------------------------------------
-- 6. Triggers: pod_members (seat counter, quorum flip, join rules)
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_pod_members_validate_insert
BEFORE INSERT ON pod_members
BEGIN
    SELECT RAISE(ABORT, 'membership_must_start_confirmed')
     WHERE NEW.status <> 'confirmed';
    SELECT RAISE(ABORT, 'pod_not_joinable')
     WHERE NOT EXISTS (SELECT 1 FROM pods p WHERE p.id = NEW.pod_id AND p.status IN ('forming', 'quorum'));
    SELECT RAISE(ABORT, 'pod_full')
     WHERE EXISTS (SELECT 1 FROM pods p WHERE p.id = NEW.pod_id AND p.confirmed_count >= p.max_participants);
    SELECT RAISE(ABORT, 'not_in_pod_cohort')
     WHERE EXISTS (SELECT 1 FROM pods p
                    WHERE p.id = NEW.pod_id AND p.cohort_id IS NOT NULL
                      AND NOT EXISTS (SELECT 1 FROM cohort_memberships m
                                       WHERE m.cohort_id = p.cohort_id AND m.user_id = NEW.user_id
                                         AND m.revoked_at IS NULL));
END;

-- I9 plus the same join rules for a rejoin (left -> confirmed).
CREATE TRIGGER trg_pod_members_guard_update
BEFORE UPDATE ON pod_members
BEGIN
    SELECT RAISE(ABORT, 'membership_identity_immutable')
     WHERE NEW.pod_id IS NOT OLD.pod_id OR NEW.user_id IS NOT OLD.user_id OR NEW.joined_at IS NOT OLD.joined_at;
    SELECT RAISE(ABORT, 'membership_removed_is_final')
     WHERE OLD.status = 'removed' AND NEW.status IS NOT OLD.status;
    SELECT RAISE(ABORT, 'pod_is_terminal')
     WHERE NEW.status IS NOT OLD.status
       AND EXISTS (SELECT 1 FROM pods p WHERE p.id = NEW.pod_id AND p.status IN ('cancelled', 'completed'));
    SELECT RAISE(ABORT, 'pod_full')
     WHERE NEW.status = 'confirmed' AND OLD.status <> 'confirmed'
       AND EXISTS (SELECT 1 FROM pods p WHERE p.id = NEW.pod_id AND p.confirmed_count >= p.max_participants);
    SELECT RAISE(ABORT, 'not_in_pod_cohort')
     WHERE NEW.status = 'confirmed' AND OLD.status <> 'confirmed'
       AND EXISTS (SELECT 1 FROM pods p
                    WHERE p.id = NEW.pod_id AND p.cohort_id IS NOT NULL
                      AND NOT EXISTS (SELECT 1 FROM cohort_memberships m
                                       WHERE m.cohort_id = p.cohort_id AND m.user_id = NEW.user_id
                                         AND m.revoked_at IS NULL));
END;

-- Recount from the source of truth and flip forming <-> quorum in ONE UPDATE,
-- so the I3 CHECK holds for every intermediate row state. quorum_reached_at
-- records the first time quorum was reached (time-to-quorum metric).
CREATE TRIGGER trg_pod_members_recount_after_insert
AFTER INSERT ON pod_members
BEGIN
    UPDATE pods
       SET confirmed_count = (SELECT COUNT(*) FROM pod_members m WHERE m.pod_id = NEW.pod_id AND m.status = 'confirmed'),
           status = CASE
               WHEN status NOT IN ('forming', 'quorum') THEN status
               WHEN (SELECT COUNT(*) FROM pod_members m WHERE m.pod_id = NEW.pod_id AND m.status = 'confirmed')
                    >= min_participants THEN 'quorum'
               ELSE 'forming' END,
           quorum_reached_at = CASE
               WHEN quorum_reached_at IS NULL AND status IN ('forming', 'quorum')
                    AND (SELECT COUNT(*) FROM pod_members m WHERE m.pod_id = NEW.pod_id AND m.status = 'confirmed')
                        >= min_participants
               THEN strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
               ELSE quorum_reached_at END,
           updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
     WHERE id = NEW.pod_id;
END;

CREATE TRIGGER trg_pod_members_recount_after_status
AFTER UPDATE OF status ON pod_members
WHEN NEW.status IS NOT OLD.status
BEGIN
    UPDATE pod_members SET status_changed_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = NEW.id;
    UPDATE pods
       SET confirmed_count = (SELECT COUNT(*) FROM pod_members m WHERE m.pod_id = NEW.pod_id AND m.status = 'confirmed'),
           status = CASE
               WHEN status NOT IN ('forming', 'quorum') THEN status
               WHEN (SELECT COUNT(*) FROM pod_members m WHERE m.pod_id = NEW.pod_id AND m.status = 'confirmed')
                    >= min_participants THEN 'quorum'
               ELSE 'forming' END,
           quorum_reached_at = CASE
               WHEN quorum_reached_at IS NULL AND status IN ('forming', 'quorum')
                    AND (SELECT COUNT(*) FROM pod_members m WHERE m.pod_id = NEW.pod_id AND m.status = 'confirmed')
                        >= min_participants
               THEN strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
               ELSE quorum_reached_at END,
           updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
     WHERE id = NEW.pod_id;
END;

CREATE TRIGGER trg_pod_members_recount_after_delete
AFTER DELETE ON pod_members
BEGIN
    UPDATE pods
       SET confirmed_count = (SELECT COUNT(*) FROM pod_members m WHERE m.pod_id = OLD.pod_id AND m.status = 'confirmed'),
           status = CASE
               WHEN status NOT IN ('forming', 'quorum') THEN status
               WHEN (SELECT COUNT(*) FROM pod_members m WHERE m.pod_id = OLD.pod_id AND m.status = 'confirmed')
                    >= min_participants THEN 'quorum'
               ELSE 'forming' END,
           updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
     WHERE id = OLD.pod_id;
END;


-- -----------------------------------------------------------------------------
-- 7. Triggers: pod_messages (I4 quorum-gated chat, I13 evidence integrity)
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_pod_messages_chat_gate
BEFORE INSERT ON pod_messages
WHEN NEW.kind = 'user'
BEGIN
    SELECT RAISE(ABORT, 'chat_closed')
     WHERE EXISTS (SELECT 1 FROM pods p WHERE p.id = NEW.pod_id AND p.status IN ('cancelled', 'completed'));
    SELECT RAISE(ABORT, 'chat_locked_until_quorum')
     WHERE NOT EXISTS (SELECT 1 FROM pods p WHERE p.id = NEW.pod_id AND p.status = 'quorum');
    SELECT RAISE(ABORT, 'not_a_pod_member')
     WHERE NOT EXISTS (SELECT 1 FROM pod_members m
                        WHERE m.pod_id = NEW.pod_id AND m.user_id = NEW.sender_user_id AND m.status = 'confirmed');
END;

CREATE TRIGGER trg_pod_messages_immutable
BEFORE UPDATE ON pod_messages
WHEN NEW.pod_id IS NOT OLD.pod_id
  OR NEW.sender_user_id IS NOT OLD.sender_user_id
  OR NEW.kind IS NOT OLD.kind
  OR NEW.body IS NOT OLD.body
  OR NEW.created_at IS NOT OLD.created_at
BEGIN
    SELECT RAISE(ABORT, 'message_immutable');
END;


-- -----------------------------------------------------------------------------
-- 8. Triggers: cohorts and vouchers (I8, I12)
-- -----------------------------------------------------------------------------
CREATE TRIGGER trg_cohort_memberships_validate_insert
BEFORE INSERT ON cohort_memberships
BEGIN
    SELECT RAISE(ABORT, 'cohort_archived')
     WHERE EXISTS (SELECT 1 FROM cohorts c WHERE c.id = NEW.cohort_id AND c.archived_at IS NOT NULL);
    SELECT RAISE(ABORT, 'membership_must_start_active')
     WHERE NEW.revoked_at IS NOT NULL;
    SELECT RAISE(ABORT, 'voucher_wrong_cohort')
     WHERE NEW.voucher_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM cohort_vouchers v WHERE v.id = NEW.voucher_id AND v.cohort_id = NEW.cohort_id);
    SELECT RAISE(ABORT, 'voucher_revoked')
     WHERE EXISTS (SELECT 1 FROM cohort_vouchers v WHERE v.id = NEW.voucher_id AND v.revoked_at IS NOT NULL);
    SELECT RAISE(ABORT, 'voucher_expired')
     WHERE EXISTS (SELECT 1 FROM cohort_vouchers v
                    WHERE v.id = NEW.voucher_id AND v.expires_at <= strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));
    SELECT RAISE(ABORT, 'voucher_exhausted')
     WHERE EXISTS (SELECT 1 FROM cohort_vouchers v
                    WHERE v.id = NEW.voucher_id AND v.redemption_count >= v.max_redemptions);
END;

CREATE TRIGGER trg_cohort_memberships_guard_update
BEFORE UPDATE ON cohort_memberships
WHEN NEW.cohort_id IS NOT OLD.cohort_id
  OR NEW.user_id IS NOT OLD.user_id
  OR NEW.voucher_id IS NOT OLD.voucher_id
  OR NEW.joined_at IS NOT OLD.joined_at
BEGIN
    SELECT RAISE(ABORT, 'membership_identity_immutable');
END;

CREATE TRIGGER trg_cohort_memberships_count_redemption
AFTER INSERT ON cohort_memberships
WHEN NEW.voucher_id IS NOT NULL
BEGIN
    UPDATE cohort_vouchers
       SET redemption_count = (SELECT COUNT(*) FROM cohort_memberships m WHERE m.voucher_id = NEW.voucher_id)
     WHERE id = NEW.voucher_id;
END;

CREATE TRIGGER trg_cohort_memberships_revoke_cascade
AFTER UPDATE OF revoked_at ON cohort_memberships
WHEN OLD.revoked_at IS NULL AND NEW.revoked_at IS NOT NULL
BEGIN
    UPDATE pod_members
       SET status = 'removed', removal_reason = 'cohort_revoked'
     WHERE user_id = NEW.user_id
       AND status = 'confirmed'
       AND pod_id IN (SELECT p.id FROM pods p
                       WHERE p.cohort_id = NEW.cohort_id AND p.status IN ('forming', 'quorum'));
END;

CREATE TRIGGER trg_cohort_vouchers_guard_update
BEFORE UPDATE ON cohort_vouchers
BEGIN
    SELECT RAISE(ABORT, 'voucher_identity_immutable')
     WHERE NEW.cohort_id IS NOT OLD.cohort_id OR NEW.code_hash IS NOT OLD.code_hash;
    SELECT RAISE(ABORT, 'redemption_count_is_derived')
     WHERE NEW.redemption_count IS NOT (SELECT COUNT(*) FROM cohort_memberships m WHERE m.voucher_id = NEW.id);
END;


-- -----------------------------------------------------------------------------
-- 9. Feed view: one row per pod with the derived slot counters the UI shows
-- -----------------------------------------------------------------------------
-- Reference feed query ("What micro-pods are happening near me today?"):
--   SELECT * FROM v_pod_cards
--    WHERE status IN ('forming', 'quorum')
--      AND starts_at >= :now AND starts_at < :local_day_end_utc
--      AND seats_left > 0
--      AND (status = 'quorum' OR quorum_deadline_at > :now)
--      AND (cohort_id IS NULL OR cohort_id IN (SELECT cohort_id FROM cohort_memberships
--                                              WHERE user_id = :viewer AND revoked_at IS NULL))
--      AND latitude  BETWEEN :lat_min AND :lat_max
--      AND longitude BETWEEN :lng_min AND :lng_max
--    ORDER BY starts_at LIMIT 50;
-- Block filtering and exact distance sorting happen in storage.py.
CREATE VIEW v_pod_cards AS
SELECT
    p.id                                             AS pod_id,
    p.status,
    p.template_code,
    t.name                                           AS template_name,
    t.structure                                      AS template_structure,
    p.title,
    p.cohort_id,
    p.language_code,
    p.exchange_language_code,
    p.starts_at,
    p.ends_at,
    p.quorum_deadline_at,
    p.min_participants,
    p.max_participants,
    p.confirmed_count,
    p.max_participants - p.confirmed_count           AS seats_left,
    max(p.min_participants - p.confirmed_count, 0)   AS needed_for_quorum,
    (p.status = 'quorum')                            AS chat_open,
    p.spend_expectation,
    p.spend_max_minor,
    p.spend_currency,
    tp.id                                            AS third_place_id,
    tp.name                                          AS place_name,
    tp.kind                                          AS place_kind,
    tp.meeting_point,
    tp.district,
    tp.city,
    tp.latitude,
    tp.longitude,
    tp.is_indoor
FROM pods p
JOIN activity_templates t ON t.code = p.template_code
JOIN third_places tp      ON tp.id  = p.third_place_id;
