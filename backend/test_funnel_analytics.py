"""Unit and integration tests for the Pilot Funnel Analytics Telemetry (Migration 0015)."""
import os
import sqlite3
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

import main
from main import app
from storage import DurableStorage


@pytest.fixture
def clean_storage(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_funnel.db")
    monkeypatch.setenv("CARTMATE_DATABASE_PATH", db_file)
    monkeypatch.setenv("CARTMATE_MODERATOR_USER_IDS", "usr_zuzanna")
    monkeypatch.setattr(main, "MODERATOR_USER_IDS", frozenset({"usr_zuzanna"}))
    store = DurableStorage(db_file)
    monkeypatch.setattr(main, "storage", store)
    return store


@pytest.fixture
def client(clean_storage):
    return TestClient(app)


def test_migration_0015_creates_strict_analytics_events_table(clean_storage):
    conn = sqlite3.connect(clean_storage.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analytics_events';")
    assert cursor.fetchone() is not None

    # Check STRICT schema: inserting invalid JSON or invalid timestamp violates constraints
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO analytics_events (user_id, event_name, properties_json, created_at) VALUES ('usr_1', 'test', 'invalid-json', ?);",
            (now_iso,),
        )
    conn.close()


def test_record_analytics_event_and_funnel_metrics(clean_storage):
    # 1. Record signups
    clean_storage.record_analytics_event("signup", "usr_zuzanna", {"city": "Katowice"})
    clean_storage.record_analytics_event("signup", "usr_jakub", {"city": "Katowice"})
    clean_storage.record_analytics_event("signup", "usr_ania", {"city": "Gliwice"})

    # 2. Record pod feed views
    clean_storage.record_analytics_event("pod_feed_viewed", "usr_zuzanna", {"city": "Katowice"})
    clean_storage.record_analytics_event("pod_feed_viewed", "usr_jakub", {"city": "Katowice"})

    # 3. Record pod joins
    clean_storage.record_analytics_event("pod_joined", "usr_zuzanna", {"pod_id": 1, "is_host": True})
    clean_storage.record_analytics_event("pod_joined", "usr_jakub", {"pod_id": 1, "is_host": False})

    # 4. Record quorum reached
    clean_storage.record_analytics_event("pod_quorum_reached", "usr_zuzanna", {"pod_id": 1})
    clean_storage.record_analytics_event("pod_quorum_reached", "usr_jakub", {"pod_id": 1})

    # 5. Record attendance (arrival)
    clean_storage.record_analytics_event("pod_attended", "usr_zuzanna", {"pod_id": 1})

    # 6. Record repeat pod join for Zuzanna
    clean_storage.record_analytics_event("pod_joined", "usr_zuzanna", {"pod_id": 2, "is_host": True})

    # 7. Record voice loop events
    clean_storage.record_analytics_event("voice_lobby_viewed", "usr_ania")
    clean_storage.record_analytics_event("voice_queue_entered", "usr_ania")
    clean_storage.record_analytics_event("voice_call_connected", "usr_ania", {"call_id": "c1"})
    clean_storage.record_analytics_event("voice_call_rated", "usr_ania", {"call_id": "c1", "rating": "respectful"})

    funnel = clean_storage.get_funnel_metrics()

    # Assert pod funnel metrics
    pod_f = funnel["pod_funnel"]
    assert pod_f["signups"] == 3
    assert pod_f["first_pod_view"] == 2
    assert pod_f["pod_join"] == 2
    assert pod_f["quorum_reached"] == 2
    assert pod_f["attend"] == 1
    assert pod_f["repeat"] == 1
    assert pod_f["join_conversion_rate"] == 1.0
    assert pod_f["quorum_conversion_rate"] == 1.0
    assert pod_f["repeat_rate"] == 0.5

    # Assert voice funnel metrics
    voice_f = funnel["voice_funnel"]
    assert voice_f["lobby_viewed"] == 1
    assert voice_f["queue_entered"] == 1
    assert voice_f["call_connected"] == 1
    assert voice_f["call_rated"] == 1
    assert voice_f["connect_rate"] == 1.0
    assert voice_f["rating_rate"] == 1.0


def test_analytics_api_endpoints_and_moderator_gating(client):
    headers_zuzanna = {"Authorization": "Bearer token_zuzanna"}
    headers_jakub = {"Authorization": "Bearer token_jakub"}

    # 1. Post client event (unauthenticated and authenticated)
    res_anon = client.post(
        "/api/analytics/events",
        json={"event": "landing_viewed", "properties": {"referrer": "direct"}},
    )
    assert res_anon.status_code == 200
    assert res_anon.json()["status"] == "recorded"

    res_auth = client.post(
        "/api/analytics/events",
        headers=headers_zuzanna,
        json={"event": "pod_feed_viewed", "properties": {"city": "Katowice"}},
    )
    assert res_auth.status_code == 200
    assert res_auth.json()["status"] == "recorded"

    # 2. Non-moderator (Jakub) is denied access to GET /api/analytics/funnel
    res_denied = client.get("/api/analytics/funnel", headers=headers_jakub)
    assert res_denied.status_code == 403

    # 3. Moderator (Zuzanna) receives aggregated funnel metrics
    res_mod = client.get("/api/analytics/funnel", headers=headers_zuzanna)
    assert res_mod.status_code == 200
    data = res_mod.json()
    assert "pod_funnel" in data
    assert "voice_funnel" in data
    assert data["total_events"] >= 2


def test_automatic_server_side_pod_funnel_emission(client, clean_storage):
    headers_zuzanna = {"Authorization": "Bearer token_zuzanna"}
    headers_jakub = {"Authorization": "Bearer token_jakub"}
    headers_ania = {"Authorization": "Bearer token_ania"}

    # Seed users into SQLite to satisfy foreign keys for pods/members
    conn = sqlite3.connect(clean_storage.db_path)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email, phone, data_json, created_at, updated_at) VALUES ('usr_zuzanna', 'z@ex.pl', '+481', '{}', ?, ?);",
        (now_str, now_str),
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email, phone, data_json, created_at, updated_at) VALUES ('usr_jakub', 'j@ex.pl', '+482', '{}', ?, ?);",
        (now_str, now_str),
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email, phone, data_json, created_at, updated_at) VALUES ('usr_ania', 'a@ex.pl', '+483', '{}', ?, ?);",
        (now_str, now_str),
    )
    conn.commit()
    conn.close()

    # 1. Create third place as moderator
    place_id = clean_storage.create_third_place(
        slug="katowice-park-test",
        name="Park Kościuszki Test",
        kind="park",
        city="Katowice",
        meeting_point="Wejście główne",
        latitude=50.25,
        longitude=19.01,
        is_indoor=0,
        template_codes=["park_walk"],
    )

    now_dt = datetime.now(timezone.utc)
    from datetime import timedelta
    starts = (now_dt + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ends = (now_dt + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    deadline = (now_dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Zuzanna creates pod -> emits pod_created & pod_joined
    create_res = client.post(
        "/api/pods",
        headers=headers_zuzanna,
        json={
            "template_code": "park_walk",
            "third_place_id": place_id,
            "starts_at": starts,
            "ends_at": ends,
            "quorum_deadline_at": deadline,
            "language_code": "pl",
            "spend_expectation": "no_expected_spend",
            "title": "Spacer telemetryczny",
        },
    )
    assert create_res.status_code == 200
    pod_id = create_res.json()["id"]

    # 3. Jakub joins -> emits pod_joined (confirmed = 2)
    join_res1 = client.post(f"/api/pods/{pod_id}/join", headers=headers_jakub)
    assert join_res1.status_code == 200

    # 4. Ania joins -> reaches quorum (3/5) -> emits pod_joined & pod_quorum_reached
    join_res2 = client.post(f"/api/pods/{pod_id}/join", headers=headers_ania)
    assert join_res2.status_code == 200
    assert join_res2.json()["status"] == "quorum"

    # 5. Zuzanna marks arrived -> emits pod_attended
    arrive_res = client.post(f"/api/pods/{pod_id}/arrived", headers=headers_zuzanna)
    assert arrive_res.status_code == 200
    assert arrive_res.json()["status"] == "arrived"

    # Assert recorded analytics events in database
    conn = sqlite3.connect(clean_storage.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT event_name, user_id FROM analytics_events ORDER BY id ASC;")
    events = cursor.fetchall()
    conn.close()

    event_names = [e[0] for e in events]
    assert "pod_created" in event_names
    assert "pod_joined" in event_names
    assert "pod_quorum_reached" in event_names
    assert "pod_attended" in event_names

    # Check funnel metrics
    funnel = clean_storage.get_funnel_metrics()["pod_funnel"]
    assert funnel["pod_join"] >= 3
    assert funnel["quorum_reached"] >= 1
    assert funnel["attend"] >= 1

