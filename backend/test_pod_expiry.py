"""Expired forming pods must stay cancelled after the request that noticed them ends.

`list_pods` and `join_pod` sweep expired forming pods before doing their own work. These
tests read the result back through a separate connection, because a sweep that is only
visible inside the request's own uncommitted transaction is lost when the request ends.
"""

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import storage as storage_module
from main import app
from storage import DurableStorage, get_db_connection, storage

client = TestClient(app)

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
USERS = ("usr_zuzanna", "usr_jakub", "usr_ania", "usr_marek")


@pytest.fixture
def pods_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_pod_expiry.db")
    monkeypatch.setenv("CARTMATE_DATABASE_PATH", test_db)
    monkeypatch.setenv("CARTMATE_ENV", "development")
    monkeypatch.setattr(storage, "db_path", test_db)
    storage._ensure_parent_dir()
    storage.apply_migrations()

    conn = get_db_connection(test_db)
    for index, user_id in enumerate(USERS):
        name = user_id.removeprefix("usr_").capitalize()
        conn.execute(
            "INSERT INTO users (id, email, phone, data_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, '2026-11-09T00:00:00Z', '2026-11-09T00:00:00Z')",
            (user_id, f"{name.lower()}@example.pl", f"+4850000000{index}", f'{{"name":"{name}"}}'),
        )
    conn.commit()
    conn.close()

    place_id = storage.create_third_place(
        slug="expiry-test-park",
        name="Park testowy",
        kind="park",
        city="Chorzów",
        meeting_point="Główne wejście",
        latitude=50.285,
        longitude=18.988,
        is_indoor=0,
        template_codes=["park_walk"],
    )
    return test_db, place_id


@pytest.fixture
def advance_clock(monkeypatch):
    """Moves the storage layer's clock forward without sleeping."""

    def _advance(delta: timedelta) -> None:
        class ShiftedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.now(tz) + delta

        monkeypatch.setattr(storage_module, "datetime", ShiftedDatetime)

    return _advance


def _create_pod(place_id: int, host: str, start_in_hours: int, deadline_in_hours: int, **overrides) -> int:
    now = datetime.now(timezone.utc)
    return storage.create_pod(
        template_code="park_walk",
        third_place_id=place_id,
        starts_at=(now + timedelta(hours=start_in_hours)).strftime(TIME_FORMAT),
        ends_at=(now + timedelta(hours=start_in_hours + 1)).strftime(TIME_FORMAT),
        quorum_deadline_at=(now + timedelta(hours=deadline_in_hours)).strftime(TIME_FORMAT),
        created_by_user_id=host,
        **overrides,
    )


def _persisted_pod(db_path: str, pod_id: int) -> dict:
    """Reads the pod through a brand-new connection, as another request or process would."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT status, cancel_reason, cancelled_at, confirmed_count FROM pods WHERE id = ?", (pod_id,)
        ).fetchone()
        return dict(row)
    finally:
        conn.close()


def _confirmed_members(db_path: str, pod_id: int) -> set:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT user_id FROM pod_members WHERE pod_id = ? AND status = 'confirmed'", (pod_id,)
        ).fetchall()
        return {row[0] for row in rows}
    finally:
        conn.close()


def test_listing_pods_persists_expired_cancellation(pods_db, advance_clock):
    db_path, place_id = pods_db
    pod_id = _create_pod(place_id, "usr_zuzanna", start_in_hours=3, deadline_in_hours=1)
    assert _persisted_pod(db_path, pod_id)["status"] == "forming"

    advance_clock(timedelta(hours=2))
    assert storage.list_pods() == []

    persisted = _persisted_pod(db_path, pod_id)
    assert persisted["status"] == "cancelled"
    assert persisted["cancel_reason"] == "quorum_not_reached"
    assert persisted["cancelled_at"] is not None
    # A restarted process (new storage object) sees the same thing.
    assert DurableStorage(db_path).get_pod(pod_id)["status"] == "cancelled"


def test_rejected_join_of_expired_pod_persists_cancellation(pods_db, advance_clock):
    db_path, place_id = pods_db
    pod_id = _create_pod(place_id, "usr_zuzanna", start_in_hours=3, deadline_in_hours=1)

    advance_clock(timedelta(hours=2))
    with pytest.raises(ValueError, match="POD_NOT_JOINABLE_CANCELLED"):
        storage.join_pod(pod_id, "usr_jakub")

    assert _persisted_pod(db_path, pod_id)["status"] == "cancelled"
    assert _confirmed_members(db_path, pod_id) == {"usr_zuzanna"}


def test_duplicate_join_keeps_sweep_of_other_expired_pod(pods_db, advance_clock):
    db_path, place_id = pods_db
    active_pod = _create_pod(place_id, "usr_zuzanna", start_in_hours=6, deadline_in_hours=5)
    expired_pod = _create_pod(place_id, "usr_jakub", start_in_hours=3, deadline_in_hours=1)

    advance_clock(timedelta(hours=2))
    # The host is already a confirmed member, so join_pod returns early without writing a membership.
    result = storage.join_pod(active_pod, "usr_zuzanna")

    assert result["status"] == "forming"
    assert _persisted_pod(db_path, expired_pod)["status"] == "cancelled"
    assert _persisted_pod(db_path, active_pod)["status"] == "forming"
    assert _confirmed_members(db_path, active_pod) == {"usr_zuzanna"}


def test_failed_join_keeps_sweep_and_writes_no_partial_membership(pods_db, advance_clock):
    db_path, place_id = pods_db
    full_pod = _create_pod(place_id, "usr_zuzanna", start_in_hours=6, deadline_in_hours=5, max_participants=3)
    storage.join_pod(full_pod, "usr_jakub")
    storage.join_pod(full_pod, "usr_ania")
    assert _persisted_pod(db_path, full_pod)["status"] == "quorum"
    expired_pod = _create_pod(place_id, "usr_marek", start_in_hours=3, deadline_in_hours=1)

    advance_clock(timedelta(hours=2))
    # The database trigger aborts the membership insert: the pod is full.
    with pytest.raises(sqlite3.IntegrityError, match="pod_full"):
        storage.join_pod(full_pod, "usr_marek")

    assert _persisted_pod(db_path, expired_pod)["status"] == "cancelled"
    full = _persisted_pod(db_path, full_pod)
    assert full["status"] == "quorum"
    assert full["confirmed_count"] == 3
    assert _confirmed_members(db_path, full_pod) == {"usr_zuzanna", "usr_jakub", "usr_ania"}


def test_expired_pod_accepts_neither_members_nor_chat(pods_db, advance_clock):
    db_path, place_id = pods_db
    pod_id = _create_pod(place_id, "usr_zuzanna", start_in_hours=3, deadline_in_hours=1)

    advance_clock(timedelta(hours=2))
    storage.list_pods()

    with pytest.raises(ValueError, match="POD_NOT_JOINABLE_CANCELLED"):
        storage.join_pod(pod_id, "usr_jakub")
    with pytest.raises(sqlite3.IntegrityError, match="chat_closed"):
        storage.send_pod_message(pod_id, "usr_zuzanna", "Czy ktoś jeszcze przyjdzie?")
    assert _confirmed_members(db_path, pod_id) == {"usr_zuzanna"}


def test_sweep_leaves_active_and_quorum_pods_alone(pods_db, advance_clock):
    db_path, place_id = pods_db
    still_forming = _create_pod(place_id, "usr_zuzanna", start_in_hours=6, deadline_in_hours=5)
    at_quorum = _create_pod(place_id, "usr_zuzanna", start_in_hours=3, deadline_in_hours=1)
    storage.join_pod(at_quorum, "usr_jakub")
    storage.join_pod(at_quorum, "usr_ania")

    advance_clock(timedelta(hours=2))
    listed_ids = {pod["id"] for pod in storage.list_pods()}

    assert listed_ids == {still_forming, at_quorum}
    assert _persisted_pod(db_path, still_forming)["status"] == "forming"
    # A pod that reached quorum before its deadline is not cancelled by the deadline passing.
    assert _persisted_pod(db_path, at_quorum)["status"] == "quorum"
    # Capacity is still enforced on the surviving pod.
    assert storage.join_pod(still_forming, "usr_marek")["confirmed_count"] == 2


def test_listing_does_not_leave_a_write_transaction_open(pods_db, monkeypatch):
    """Reading the feed must not hold the database write lock while it builds the response."""
    db_path, place_id = pods_db
    _create_pod(place_id, "usr_zuzanna", start_in_hours=3, deadline_in_hours=1)

    real_connect = storage_module.get_db_connection
    in_transaction_at_close = []

    class ConnectionProxy:
        """Records whether a transaction is still open when list_pods closes its connection."""

        def __init__(self, conn):
            self._conn = conn

        def __getattr__(self, name):
            return getattr(self._conn, name)

        def close(self):
            in_transaction_at_close.append(self._conn.in_transaction)
            self._conn.close()

    monkeypatch.setattr(
        storage_module, "get_db_connection", lambda *args, **kwargs: ConnectionProxy(real_connect(*args, **kwargs))
    )
    storage.list_pods()

    assert in_transaction_at_close == [False]


def test_feed_request_persists_cancellation_through_the_api(pods_db, advance_clock):
    db_path, place_id = pods_db
    headers = {"Authorization": "Bearer token_zuzanna"}
    pod_id = _create_pod(place_id, "usr_zuzanna", start_in_hours=3, deadline_in_hours=1)

    advance_clock(timedelta(hours=2))
    feed = client.get("/api/pods/feed", headers=headers)
    assert feed.status_code == 200
    assert feed.json() == []

    detail = client.get(f"/api/pods/{pod_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "cancelled"

    join = client.post(f"/api/pods/{pod_id}/join", headers={"Authorization": "Bearer token_jakub"})
    assert join.status_code in (400, 409)
    assert _persisted_pod(db_path, pod_id)["status"] == "cancelled"


def test_reading_one_pod_persists_expired_cancellation(pods_db, advance_clock):
    """Opening a pod directly (a refreshed deep link) must not show an expired pod as forming."""
    db_path, place_id = pods_db
    pod_id = _create_pod(place_id, "usr_zuzanna", start_in_hours=3, deadline_in_hours=1)

    advance_clock(timedelta(hours=2))
    assert storage.get_pod(pod_id)["status"] == "cancelled"
    assert _persisted_pod(db_path, pod_id)["status"] == "cancelled"

    detail = client.get(f"/api/pods/{pod_id}", headers={"Authorization": "Bearer token_zuzanna"})
    assert detail.status_code == 200
    assert detail.json()["status"] == "cancelled"
