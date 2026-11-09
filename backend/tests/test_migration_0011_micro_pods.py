"""Tests for migration 0011 (Micro-Pods anchored in Third Places).

Each test runs against a real on-disk SQLite file in WAL mode with foreign keys
ON, mirroring production. BASELINE_V10 stands in for migrations 1-10. Once the
real repository is wired in, replace it with the project's own v10 runner.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import threading
from pathlib import Path

import pytest

MIGRATION_PATH = Path(__file__).resolve().parents[1] / "migrations" / "m0011_micro_pods.py"
_spec = importlib.util.spec_from_file_location("m0011_micro_pods", MIGRATION_PATH)
m0011 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m0011)

BASELINE_V10 = """
CREATE TABLE users (
    id           INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL
);
CREATE TABLE hotspots (              -- stand-in for the legacy hotspot-voting table
    id             INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    vote_threshold INTEGER NOT NULL
);
INSERT INTO hotspots (name, vote_threshold) VALUES ('Rynek', 3), ('Dolina Trzech Stawow', 4);
PRAGMA user_version = 10;
"""

# Pods live in 2030 so they are always in the future relative to created_at.
DAY = "2030-06-01"
START = f"{DAY}T16:00:00Z"
END = f"{DAY}T16:45:00Z"
DEADLINE = f"{DAY}T13:00:00Z"
FEED_NOW = f"{DAY}T08:00:00Z"
FEED_DAY_END = "2030-06-01T22:00:00Z"  # end of the local Warsaw day, in UTC

FEED_SQL = """
SELECT pod_id, status, seats_left, needed_for_quorum, chat_open
  FROM v_pod_cards
 WHERE status IN ('forming', 'quorum')
   AND starts_at >= :now AND starts_at < :day_end
   AND seats_left > 0
   AND (status = 'quorum' OR quorum_deadline_at > :now)
   AND (cohort_id IS NULL OR cohort_id IN (SELECT cohort_id FROM cohort_memberships
                                           WHERE user_id = :viewer AND revoked_at IS NULL))
   AND latitude  BETWEEN :lat_min AND :lat_max
   AND longitude BETWEEN :lng_min AND :lng_max
 ORDER BY starts_at
 LIMIT 50
"""


# --------------------------------------------------------------------------- fixtures

def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "cartmate.db"
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(BASELINE_V10)
    conn.close()
    return path


@pytest.fixture
def baseline(db_path: Path) -> sqlite3.Connection:
    conn = connect(db_path)
    yield conn
    conn.close()


@pytest.fixture
def db(baseline: sqlite3.Connection) -> sqlite3.Connection:
    m0011.upgrade(baseline)
    return baseline


# --------------------------------------------------------------------------- helpers

def raises(code: str):
    """Expect a trigger-raised domain error with exactly this code."""
    return pytest.raises(sqlite3.IntegrityError, match=rf"^{code}$")


def check_fails():
    return pytest.raises(sqlite3.IntegrityError, match=r"^CHECK constraint failed")


def add_user(db, name="user") -> int:
    return db.execute("INSERT INTO users (display_name) VALUES (?)", (name,)).lastrowid


def add_users(db, n: int) -> list[int]:
    return [add_user(db, f"user{i}") for i in range(n)]


def add_cohort(db, slug="uni-silesia", attests_adult=1) -> int:
    return db.execute(
        "INSERT INTO cohorts (slug, name, kind, attests_adult, adult_attestation_ref) VALUES (?, ?, 'university', ?, ?)",
        (slug, slug.title(), attests_adult, "AGR-2026-001" if attests_adult else None),
    ).lastrowid


def add_member_of_cohort(db, cohort_id, user_id, voucher_id=None) -> int:
    return db.execute(
        "INSERT INTO cohort_memberships (cohort_id, user_id, voucher_id) VALUES (?, ?, ?)",
        (cohort_id, user_id, voucher_id),
    ).lastrowid


def add_voucher(db, cohort_id, *, code_hash="a" * 64, max_redemptions=2,
                expires_at="2030-12-31T23:59:59Z", revoked_at=None) -> int:
    return db.execute(
        "INSERT INTO cohort_vouchers (cohort_id, code_hash, code_hint, max_redemptions, expires_at, revoked_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (cohort_id, code_hash, code_hash[-4:], max_redemptions, expires_at, revoked_at),
    ).lastrowid


def add_place(db, slug="silesia-park-fountain-loop", *, templates=("park_walk",), cohort_id=None,
              verified=True, active=True, lat=50.2848, lng=18.9945) -> int:
    place_id = db.execute(
        "INSERT INTO third_places (slug, name, kind, city, meeting_point, latitude, longitude, is_indoor, "
        "cohort_id, is_active, verified_at) VALUES (?, ?, 'park', 'Chorzow', ?, ?, ?, 0, ?, ?, ?)",
        (slug, slug.replace("-", " ").title(), "North side of the fountain, by the benches", lat, lng,
         cohort_id, int(active), "2026-11-01T10:00:00Z" if verified else None),
    ).lastrowid
    for code in templates:
        db.execute("INSERT INTO third_place_templates (third_place_id, template_code) VALUES (?, ?)", (place_id, code))
    return place_id


def add_pod(db, place_id, *, template="park_walk", starts=START, ends=END, deadline=DEADLINE, language="pl",
            exchange=None, cohort_id=None, creator=None, spend="no_expected_spend", spend_max=None,
            min_p=3, max_p=5, title=None) -> int:
    return db.execute(
        "INSERT INTO pods (template_code, third_place_id, cohort_id, created_by_user_id, title, language_code, "
        "exchange_language_code, starts_at, ends_at, quorum_deadline_at, min_participants, max_participants, "
        "spend_expectation, spend_max_minor) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (template, place_id, cohort_id, creator, title, language, exchange, starts, ends, deadline,
         min_p, max_p, spend, spend_max),
    ).lastrowid


def join(db, pod_id, user_id) -> None:
    db.execute("INSERT INTO pod_members (pod_id, user_id) VALUES (?, ?)", (pod_id, user_id))


def set_status(db, pod_id, user_id, status, reason=None) -> None:
    db.execute(
        "UPDATE pod_members SET status = ?, removal_reason = ? WHERE pod_id = ? AND user_id = ?",
        (status, reason, pod_id, user_id),
    )


def say(db, pod_id, user_id, body="hi all") -> None:
    db.execute("INSERT INTO pod_messages (pod_id, sender_user_id, body) VALUES (?, ?, ?)", (pod_id, user_id, body))


def pod(db, pod_id) -> sqlite3.Row:
    return db.execute("SELECT * FROM pods WHERE id = ?", (pod_id,)).fetchone()


@pytest.fixture
def walk(db):
    """A verified park anchor with one forming walk pod and six users."""
    place = add_place(db)
    pod_id = add_pod(db, place)
    return {"place": place, "pod": pod_id, "users": add_users(db, 6)}


# --------------------------------------------------------------------------- migration mechanics

def test_upgrade_moves_v10_to_v11_and_leaves_legacy_untouched(db):
    assert db.execute("PRAGMA user_version").fetchone()[0] == 11
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    legacy = db.execute("SELECT name, vote_threshold FROM hotspots ORDER BY id").fetchall()
    assert [tuple(r) for r in legacy] == [("Rynek", 3), ("Dolina Trzech Stawow", 4)]
    codes = [r[0] for r in db.execute("SELECT code FROM activity_templates ORDER BY sort_order")]
    assert codes == ["study_sprint", "park_walk", "board_games", "language_exchange"]


@pytest.mark.parametrize("version", [9, 11])
def test_upgrade_refuses_any_version_but_10(baseline, version):
    baseline.execute(f"PRAGMA user_version = {version}")
    with pytest.raises(m0011.MigrationError, match=f"found {version}"):
        m0011.upgrade(baseline)
    assert baseline.execute("SELECT 1 FROM sqlite_master WHERE name = 'pods'").fetchone() is None
    assert baseline.execute("PRAGMA user_version").fetchone()[0] == version


def test_upgrade_cannot_run_twice(db):
    with pytest.raises(m0011.MigrationError, match="found 11"):
        m0011.upgrade(db)
    assert db.execute("PRAGMA user_version").fetchone()[0] == 11


def test_upgrade_refuses_when_foreign_keys_are_off(baseline):
    baseline.execute("PRAGMA foreign_keys = OFF")
    with pytest.raises(m0011.MigrationError, match="foreign_keys"):
        m0011.upgrade(baseline)


def test_upgrade_works_with_pythons_default_transaction_mode(db_path):
    conn = sqlite3.connect(db_path)          # legacy isolation_level='' as most storage layers use it
    conn.execute("PRAGMA foreign_keys = ON")
    m0011.upgrade(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 11
    assert not conn.in_transaction
    conn.close()


def test_upgrade_refuses_inside_an_open_transaction(baseline):
    baseline.execute("BEGIN")
    with pytest.raises(m0011.MigrationError, match="open transaction"):
        m0011.upgrade(baseline)
    baseline.execute("ROLLBACK")


def test_upgrade_accepts_text_user_ids(tmp_path):
    conn = connect(tmp_path / "uuid.db")
    conn.executescript("CREATE TABLE users (id TEXT PRIMARY KEY); PRAGMA user_version = 10;")
    m0011.upgrade(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 11


def test_upgrade_refuses_name_clashes(baseline):
    baseline.execute("CREATE TABLE pods (id INTEGER PRIMARY KEY)")
    with pytest.raises(m0011.MigrationError, match="already exist: pods"):
        m0011.upgrade(baseline)


def test_upgrade_is_atomic_when_a_statement_fails(baseline, tmp_path, monkeypatch):
    broken = tmp_path / "0011_micro_pods.sql"
    broken.write_text(m0011.SQL_FILE.read_text() + "\nINSERT INTO no_such_table VALUES (1);\n")
    monkeypatch.setattr(m0011, "SQL_FILE", broken)
    with pytest.raises(sqlite3.OperationalError, match="no_such_table"):
        m0011.upgrade(baseline)
    assert baseline.execute("PRAGMA user_version").fetchone()[0] == 10
    leftovers = baseline.execute(
        "SELECT name FROM sqlite_master WHERE name NOT IN ('users', 'hotspots') AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    assert leftovers == []
    assert not baseline.in_transaction


def test_template_phases_add_up_to_their_duration(db):
    for row in db.execute("SELECT code, default_duration_min, structure FROM activity_templates"):
        phases = json.loads(row["structure"])
        assert sum(p["minutes"] for p in phases) == row["default_duration_min"], row["code"]
    sprint = json.loads(db.execute("SELECT structure FROM activity_templates WHERE code = 'study_sprint'").fetchone()[0])
    assert [(p["phase"], p["minutes"]) for p in sprint] == [("focus", 45), ("coffee_break", 15)]


# --------------------------------------------------------------------------- pod creation rules

@pytest.mark.parametrize("min_p,max_p", [(2, 5), (3, 6), (4, 3)])
def test_pods_are_always_3_to_5_people(db, min_p, max_p):
    place = add_place(db)
    with check_fails():
        add_pod(db, place, min_p=min_p, max_p=max_p)


@pytest.mark.parametrize("bad", [
    "2030-06-01 16:00:00",           # naive, no T/Z
    "2030-06-01T16:00:00+02:00",     # offset instead of UTC
    "2030-02-30T16:00:00Z",          # impossible date
    "2030-06-01T16:00:00.250Z",      # fractional seconds
    "tomorrow at four",
])
def test_timestamps_must_be_canonical_utc(db, bad):
    place = add_place(db)
    with check_fails():
        add_pod(db, place, starts=bad)


def test_duration_and_deadline_bounds(db):
    place = add_place(db)
    with check_fails():
        add_pod(db, place, ends=f"{DAY}T16:10:00Z")            # 10 minutes is too short
    with check_fails():
        add_pod(db, place, ends=f"{DAY}T20:30:00Z")            # 4.5 hours is too long
    with check_fails():
        add_pod(db, place, deadline=f"{DAY}T16:30:00Z")        # deadline after start
    with check_fails():
        add_pod(db, place, starts="2020-01-01T10:00:00Z", ends="2020-01-01T10:45:00Z",
                deadline="2020-01-01T09:00:00Z")               # in the past


def test_spend_terms_are_explicit(db):
    place = add_place(db, templates=("park_walk", "board_games"))
    with check_fails():
        add_pod(db, place, spend="no_expected_spend", spend_max=1500)  # free pods carry no amount
    with check_fails():
        add_pod(db, place, spend="pay_own_way")                        # paid pods must state a max
    with check_fails():
        add_pod(db, place, spend="pay_own_way", spend_max=25000)       # 250 PLN is above the cap
    with check_fails():
        add_pod(db, place, spend="host_pays")
    add_pod(db, place, template="board_games", spend="pay_own_way", spend_max=1500)
    add_pod(db, place, spend="no_expected_spend")


def test_pods_need_a_verified_active_place_that_offers_the_template(db):
    unverified = add_place(db, "unverified-spot", verified=False)
    inactive = add_place(db, "closed-spot", active=False)
    walk_only = add_place(db, "walk-only-loop")
    with raises("place_unavailable"):
        add_pod(db, unverified)
    with raises("place_unavailable"):
        add_pod(db, inactive)
    with raises("template_not_offered_at_place"):
        add_pod(db, walk_only, template="board_games", ends=f"{DAY}T17:30:00Z")
    db.execute("UPDATE activity_templates SET is_active = 0 WHERE code = 'park_walk'")
    with raises("template_unavailable"):
        add_pod(db, walk_only)


def test_cohort_venues_and_creators(db):
    cohort = add_cohort(db)
    other = add_cohort(db, "tech-hub")
    campus = add_place(db, "campus-library-floor", cohort_id=cohort)
    outsider, insider = add_users(db, 2)
    add_member_of_cohort(db, cohort, insider)
    with raises("place_restricted_to_other_cohort"):
        add_pod(db, campus)                                    # public pod at a cohort-only venue
    with raises("place_restricted_to_other_cohort"):
        add_pod(db, campus, cohort_id=other)
    with raises("creator_not_in_cohort"):
        add_pod(db, campus, cohort_id=cohort, creator=outsider)
    add_pod(db, campus, cohort_id=cohort, creator=insider)
    db.execute("UPDATE cohorts SET archived_at = '2026-11-02T10:00:00Z' WHERE id = ?", (other,))
    public_place = add_place(db, "public-loop")
    with raises("cohort_archived"):
        add_pod(db, public_place, cohort_id=other)


def test_new_pods_start_forming_and_empty(db):
    place = add_place(db)
    with raises("pod_must_start_forming_and_empty"):
        db.execute(
            "INSERT INTO pods (template_code, third_place_id, language_code, starts_at, ends_at, quorum_deadline_at, "
            "spend_expectation, status, confirmed_count, quorum_reached_at) "
            "VALUES ('park_walk', ?, 'pl', ?, ?, ?, 'no_expected_spend', 'quorum', 3, ?)",
            (place, START, END, DEADLINE, DEADLINE),
        )


def test_no_second_pod_for_a_slot_while_the_first_has_seats(db, walk):
    place, first = walk["place"], walk["pod"]
    with raises("duplicate_slot_join_existing_pod"):
        add_pod(db, place)
    add_pod(db, place, language="en")                          # different spoken language is a different pod
    add_pod(db, place, starts=f"{DAY}T17:00:00Z", ends=f"{DAY}T17:45:00Z")  # different start time
    for user in walk["users"][:5]:
        join(db, first, user)
    assert pod(db, first)["confirmed_count"] == 5
    add_pod(db, place)                                         # first pod is full, so a new one may form


def test_language_exchange_pairs_match_in_either_order(db):
    cafe = add_place(db, "main-square-cafe-table", templates=("language_exchange",))
    add_pod(db, cafe, template="language_exchange", language="pl", exchange="en", ends=f"{DAY}T17:00:00Z")
    with raises("duplicate_slot_join_existing_pod"):
        add_pod(db, cafe, template="language_exchange", language="en", exchange="pl", ends=f"{DAY}T17:00:00Z")
    add_pod(db, cafe, template="language_exchange", language="pl", exchange="uk", ends=f"{DAY}T17:00:00Z")
    with check_fails():
        add_pod(db, cafe, template="language_exchange", language="pl", exchange="pl",
                starts=f"{DAY}T18:00:00Z", ends=f"{DAY}T19:00:00Z")


def test_terms_people_joined_under_cannot_change(db, walk):
    p = walk["pod"]
    for column, value in [("starts_at", f"{DAY}T18:00:00Z"), ("third_place_id", walk["place"] + 1),
                          ("spend_expectation", "pay_own_way"), ("max_participants", 4),
                          ("language_code", "en"), ("template_code", "board_games")]:
        with raises("pod_terms_immutable"):
            db.execute(f"UPDATE pods SET {column} = ? WHERE id = ?", (value, p))
    db.execute("UPDATE pods SET title = 'Evening loop', quorum_deadline_at = ? WHERE id = ?", (f"{DAY}T15:00:00Z", p))
    assert pod(db, p)["title"] == "Evening loop"


# --------------------------------------------------------------------------- seats, quorum and chat

def test_third_confirmation_reaches_quorum_and_opens_chat(db, walk):
    p, (a, b, c, *_) = walk["pod"], walk["users"]
    join(db, p, a)
    join(db, p, b)
    card = db.execute("SELECT * FROM v_pod_cards WHERE pod_id = ?", (p,)).fetchone()
    assert (card["status"], card["confirmed_count"], card["needed_for_quorum"], card["chat_open"]) == ("forming", 2, 1, 0)
    with raises("chat_locked_until_quorum"):
        say(db, p, a)
    join(db, p, c)
    card = db.execute("SELECT * FROM v_pod_cards WHERE pod_id = ?", (p,)).fetchone()
    assert (card["status"], card["seats_left"], card["needed_for_quorum"], card["chat_open"]) == ("quorum", 2, 0, 1)
    assert pod(db, p)["quorum_reached_at"] is not None
    say(db, p, a, "Hi both! I'll be by the benches in a green jacket.")


def test_pods_never_overbook(db, walk):
    p, users = walk["pod"], walk["users"]
    for user in users[:5]:
        join(db, p, user)
    with raises("pod_full"):
        join(db, p, users[5])
    assert pod(db, p)["confirmed_count"] == 5
    set_status(db, p, users[0], "left")
    join(db, p, users[5])                                      # the freed seat goes to someone else
    with raises("pod_full"):
        set_status(db, p, users[0], "confirmed")               # rejoining can't overbook either
    assert pod(db, p)["confirmed_count"] == 5


def test_dropping_below_three_relocks_chat_until_someone_rejoins(db, walk):
    p, (a, b, c, *_) = walk["pod"], walk["users"]
    for user in (a, b, c):
        join(db, p, user)
    first_quorum = pod(db, p)["quorum_reached_at"]
    set_status(db, p, c, "left")                               # blame-free leave
    row = pod(db, p)
    assert (row["status"], row["confirmed_count"], row["quorum_reached_at"]) == ("forming", 2, first_quorum)
    with raises("chat_locked_until_quorum"):
        say(db, p, a, "just us two now?")                      # never a 1-on-1 chat
    set_status(db, p, c, "confirmed")                          # changed their mind
    assert pod(db, p)["status"] == "quorum"
    say(db, p, a, "welcome back")


def test_a_user_holds_at_most_one_seat_per_pod(db, walk):
    join(db, walk["pod"], walk["users"][0])
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        join(db, walk["pod"], walk["users"][0])


def test_removed_members_cannot_rejoin(db, walk):
    p, a = walk["pod"], walk["users"][0]
    join(db, p, a)
    with check_fails():
        set_status(db, p, a, "removed")                        # a removal must say why
    set_status(db, p, a, "removed", "safety")
    with raises("membership_removed_is_final"):
        set_status(db, p, a, "confirmed")
    with raises("membership_identity_immutable"):
        db.execute("UPDATE pod_members SET pod_id = pod_id + 1 WHERE user_id = ?", (a,))


def test_seat_count_and_status_cannot_be_forged(db, walk):
    p = walk["pod"]
    join(db, p, walk["users"][0])
    with raises("confirmed_count_is_derived"):
        db.execute("UPDATE pods SET confirmed_count = 3, status = 'quorum', quorum_reached_at = ? WHERE id = ?",
                   (DEADLINE, p))
    with check_fails():
        db.execute("UPDATE pods SET status = 'quorum', quorum_reached_at = ? WHERE id = ?", (DEADLINE, p))


def test_cancelled_and_completed_are_terminal(db, walk):
    place, p, users = walk["place"], walk["pod"], walk["users"]
    with check_fails():
        db.execute("UPDATE pods SET status = 'cancelled' WHERE id = ?", (p,))    # needs time + reason
    with raises("pod_cannot_complete_without_quorum"):
        db.execute("UPDATE pods SET status = 'completed', completed_at = ? WHERE id = ?", (END, p))
    db.execute("UPDATE pods SET status = 'cancelled', cancelled_at = ?, cancel_reason = 'quorum_not_reached' "
               "WHERE id = ?", (DEADLINE, p))
    with raises("pod_not_joinable"):
        join(db, p, users[0])
    with raises("pod_is_terminal"):
        db.execute("UPDATE pods SET status = 'forming', cancelled_at = NULL, cancel_reason = NULL WHERE id = ?", (p,))

    done = add_pod(db, place, starts=f"{DAY}T18:00:00Z", ends=f"{DAY}T18:45:00Z")
    for user in users[:3]:
        join(db, done, user)
    db.execute("UPDATE pods SET status = 'completed', completed_at = ? WHERE id = ?", (f"{DAY}T19:00:00Z", done))
    with raises("chat_closed"):
        say(db, done, users[0], "thanks all!")
    with raises("pod_is_terminal"):
        set_status(db, done, users[0], "left")
    db.execute("INSERT INTO pod_messages (pod_id, kind, body) VALUES (?, 'system', 'Pod completed')", (done,))


def test_leaving_is_never_blocked_by_the_anti_fragmentation_rule(db, walk):
    place, first, users = walk["place"], walk["pod"], walk["users"]
    for user in users[:5]:
        join(db, first, user)
    second = add_pod(db, place)                                # allowed: first pod is full
    for user in users[:3]:
        set_status(db, first, user, "left")
    assert (pod(db, first)["status"], pod(db, second)["status"]) == ("forming", "forming")


def test_chat_membership_and_evidence_rules(db, walk):
    p, (a, b, c, outsider, *_) = walk["pod"], walk["users"]
    db.execute("INSERT INTO pod_messages (pod_id, kind, body) VALUES (?, 'system', 'Waiting for 3 people')", (p,))
    for user in (a, b, c):
        join(db, p, user)
    with raises("not_a_pod_member"):
        say(db, p, outsider)
    say(db, p, a, "See you at the fountain")
    msg = db.execute("SELECT id FROM pod_messages WHERE sender_user_id = ?", (a,)).fetchone()[0]
    with raises("message_immutable"):
        db.execute("UPDATE pod_messages SET body = 'edited' WHERE id = ?", (msg,))
    db.execute("UPDATE pod_messages SET moderation_status = 'flagged' WHERE id = ?", (msg,))
    db.execute("UPDATE pod_messages SET deleted_at = ? WHERE id = ?", (DEADLINE, msg))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO pod_messages (pod_id, sender_user_id, kind, body) VALUES (?, ?, 'system', 'x')", (p, a))


# --------------------------------------------------------------------------- cohorts and vouchers

def test_cohort_pods_are_members_only(db):
    cohort = add_cohort(db)
    place = add_place(db)
    p = add_pod(db, place, cohort_id=cohort)
    member, outsider = add_users(db, 2)
    add_member_of_cohort(db, cohort, member)
    join(db, p, member)
    with raises("not_in_pod_cohort"):
        join(db, p, outsider)
    set_status(db, p, member, "left")
    db.execute("UPDATE cohort_memberships SET revoked_at = ?, revoked_reason = 'partner request' WHERE user_id = ?",
               (DEADLINE, member))
    with raises("not_in_pod_cohort"):
        set_status(db, p, member, "confirmed")                 # no rejoining after access is revoked


def test_revoking_cohort_access_removes_user_from_live_pods(db):
    cohort = add_cohort(db)
    place = add_place(db)
    p = add_pod(db, place, cohort_id=cohort)
    users = add_users(db, 3)
    for user in users:
        add_member_of_cohort(db, cohort, user)
        join(db, p, user)
    assert pod(db, p)["status"] == "quorum"
    db.execute("UPDATE cohort_memberships SET revoked_at = ?, revoked_reason = 'left the university' "
               "WHERE cohort_id = ? AND user_id = ?", (DEADLINE, cohort, users[2]))
    member = db.execute("SELECT status, removal_reason FROM pod_members WHERE pod_id = ? AND user_id = ?",
                        (p, users[2])).fetchone()
    assert tuple(member) == ("removed", "cohort_revoked")
    assert (pod(db, p)["status"], pod(db, p)["confirmed_count"]) == ("forming", 2)
    with raises("chat_locked_until_quorum"):
        say(db, p, users[0])


def test_voucher_redemption_rules(db):
    cohort = add_cohort(db)
    other = add_cohort(db, "tech-hub")
    users = add_users(db, 6)
    voucher = add_voucher(db, cohort, max_redemptions=2)
    add_member_of_cohort(db, cohort, users[0], voucher)
    add_member_of_cohort(db, cohort, users[1], voucher)
    assert db.execute("SELECT redemption_count FROM cohort_vouchers WHERE id = ?", (voucher,)).fetchone()[0] == 2
    with raises("voucher_exhausted"):
        add_member_of_cohort(db, cohort, users[2], voucher)
    with raises("voucher_wrong_cohort"):
        add_member_of_cohort(db, other, users[2], voucher)
    revoked = add_voucher(db, cohort, code_hash="b" * 64, revoked_at="2026-11-05T10:00:00Z")
    with raises("voucher_revoked"):
        add_member_of_cohort(db, cohort, users[3], revoked)
    expired = db.execute(
        "INSERT INTO cohort_vouchers (cohort_id, code_hash, max_redemptions, expires_at, created_at) "
        "VALUES (?, ?, 5, '2026-01-31T00:00:00Z', '2026-01-01T00:00:00Z')", (cohort, "c" * 64)).lastrowid
    with raises("voucher_expired"):
        add_member_of_cohort(db, cohort, users[4], expired)
    with raises("redemption_count_is_derived"):
        db.execute("UPDATE cohort_vouchers SET redemption_count = 0 WHERE id = ?", (voucher,))
    with raises("membership_identity_immutable"):
        db.execute("UPDATE cohort_memberships SET voucher_id = NULL WHERE user_id = ?", (users[0],))
    db.execute("UPDATE cohorts SET archived_at = '2026-11-06T10:00:00Z' WHERE id = ?", (other,))
    with raises("cohort_archived"):
        add_member_of_cohort(db, other, users[5])


def test_cohort_and_voucher_hygiene(db):
    with check_fails():
        db.execute("INSERT INTO cohorts (slug, name, kind, attests_adult) VALUES ('uni', 'Uni', 'university', 1)")
    cohort = add_cohort(db)
    with check_fails():
        add_voucher(db, cohort, code_hash="WELCOME-2026")      # plaintext codes are rejected
    user = add_user(db)
    with raises("membership_must_start_active"):
        db.execute("INSERT INTO cohort_memberships (cohort_id, user_id, revoked_at, revoked_reason) "
                   "VALUES (?, ?, ?, 'x-test')", (cohort, user, DEADLINE))


# --------------------------------------------------------------------------- concurrency and feed

def test_concurrent_joins_for_the_last_seats_never_overbook(db, db_path):
    place = add_place(db)
    p = add_pod(db, place)
    users = add_users(db, 12)
    barrier = threading.Barrier(len(users))
    outcomes: list[str] = []

    def try_join(user_id: int) -> None:
        conn = connect(db_path)
        try:
            barrier.wait()
            conn.execute("BEGIN IMMEDIATE")
            try:
                join(conn, p, user_id)
                conn.execute("COMMIT")
                outcomes.append("joined")
            except sqlite3.IntegrityError as exc:
                conn.execute("ROLLBACK")
                outcomes.append(str(exc))
        finally:
            conn.close()

    threads = [threading.Thread(target=try_join, args=(u,)) for u in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert outcomes.count("joined") == 5
    assert set(outcomes) == {"joined", "pod_full"}
    assert (pod(db, p)["confirmed_count"], pod(db, p)["status"]) == (5, "quorum")


def test_feed_shows_only_joinable_pods_for_the_viewer(db):
    cohort, other_cohort = add_cohort(db), add_cohort(db, "tech-hub")
    viewer = add_user(db, "viewer")
    add_member_of_cohort(db, cohort, viewer)
    place = add_place(db, templates=("park_walk", "board_games"))
    far = add_place(db, "far-away-loop", lat=52.2297, lng=21.0122)     # Warsaw
    users = add_users(db, 5)

    def slot(hour: int, deadline_hour: int | None = None) -> dict:
        deadline_hour = hour - 1 if deadline_hour is None else deadline_hour
        return {"starts": f"{DAY}T{hour:02d}:00:00Z", "ends": f"{DAY}T{hour:02d}:45:00Z",
                "deadline": f"{DAY}T{deadline_hour:02d}:00:00Z"}

    open_public = add_pod(db, place, **slot(10))
    full = add_pod(db, place, **slot(11))
    for user in users:
        join(db, full, user)
    cancelled = add_pod(db, place, **slot(12))
    db.execute("UPDATE pods SET status = 'cancelled', cancelled_at = ?, cancel_reason = 'weather' WHERE id = ?",
               (FEED_NOW, cancelled))
    mine = add_pod(db, place, cohort_id=cohort, **slot(13))
    add_pod(db, place, cohort_id=other_cohort, **slot(14))             # not the viewer's cohort
    add_pod(db, place, **slot(15, deadline_hour=7))                    # forming, past its quorum deadline
    add_pod(db, far, **slot(16))                                       # outside the bounding box
    add_pod(db, place, starts="2030-06-02T10:00:00Z", ends="2030-06-02T10:45:00Z",
            deadline="2030-06-02T08:00:00Z")                           # tomorrow

    params = {"now": FEED_NOW, "day_end": FEED_DAY_END, "viewer": viewer,
              "lat_min": 50.20, "lat_max": 50.35, "lng_min": 18.90, "lng_max": 19.10}
    rows = db.execute(FEED_SQL, params).fetchall()
    assert [r["pod_id"] for r in rows] == [open_public, mine]
    assert all(r["needed_for_quorum"] == 3 and r["chat_open"] == 0 for r in rows)

    plan = " ".join(r["detail"] for r in db.execute("EXPLAIN QUERY PLAN " + FEED_SQL, params))
    assert "idx_pods_feed" in plan
