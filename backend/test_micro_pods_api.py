import os
import pytest
from fastapi.testclient import TestClient
from main import app
from storage import DurableStorage, get_db_connection

client = TestClient(app)

@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_api_pods.db")
    monkeypatch.setenv("CARTMATE_DATABASE_PATH", test_db)
    monkeypatch.setenv("CARTMATE_ENV", "development")
    monkeypatch.setenv("CARTMATE_MODERATOR_USER_IDS", "usr_zuzanna")
    from storage import storage
    old_db_path = storage.db_path
    storage.db_path = test_db
    storage._ensure_parent_dir()
    storage.apply_migrations()
    
    # Insert demo test users in users table
    conn = get_db_connection(test_db)
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_zuzanna', 'zuzanna@example.pl', '+48601234567', '{"name":"Zuzanna"}', '2026-11-09T00:00:00Z', '2026-11-09T00:00:00Z')
    """)
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_jakub', 'jakub@example.pl', '+48502876543', '{"name":"Jakub"}', '2026-11-09T00:00:00Z', '2026-11-09T00:00:00Z')
    """)
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_ania', 'ania@example.pl', '+48791432109', '{"name":"Ania"}', '2026-11-09T00:00:00Z', '2026-11-09T00:00:00Z')
    """)
    conn.execute("""
        INSERT INTO users (id, email, phone, data_json, created_at, updated_at)
        VALUES ('usr_marek', 'marek@example.pl', '+48500111222', '{"name":"Marek"}', '2026-11-09T00:00:00Z', '2026-11-09T00:00:00Z')
    """)
    conn.commit()
    conn.close()
    
    yield test_db
    
    storage.db_path = old_db_path

def test_templates_endpoint(clean_db):
    res = client.get("/api/pods/templates")
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) == 4
    codes = [t["code"] for t in templates]
    assert "study_sprint" in codes
    assert "park_walk" in codes
    assert "board_games" in codes
    assert "language_exchange" in codes

def test_third_places_and_pod_lifecycle(clean_db):
    headers_zuzanna = {"Authorization": "Bearer token_zuzanna"}
    headers_jakub = {"Authorization": "Bearer token_jakub"}
    headers_ania = {"Authorization": "Bearer token_ania"}

    # 1. Create a verified Third Place
    res = client.post(
        "/api/pods/places",
        headers=headers_zuzanna,
        json={
            "slug": "silesia-park-loop",
            "name": "Park Śląski - Krąg Taneczny",
            "kind": "park",
            "city": "Chorzów",
            "meeting_point": "Główne wejście przy Kręgu Tanecznym",
            "latitude": 50.285,
            "longitude": 18.988,
            "is_indoor": 0,
            "template_codes": ["park_walk", "board_games"]
        }
    )
    assert res.status_code == 200
    place_id = res.json()["id"]

    # 2. Get Third Places
    res = client.get("/api/pods/places?city=Chorzów")
    assert res.status_code == 200
    places = res.json()
    assert len(places) == 1
    assert places[0]["name"] == "Park Śląski - Krąg Taneczny"
    assert "park_walk" in places[0]["allowed_templates"]

    # 3. Create a Micro-Pod in future
    from datetime import datetime, timezone, timedelta
    now_dt = datetime.now(timezone.utc)
    starts = (now_dt + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ends = (now_dt + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    deadline = (now_dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    res = client.post(
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
            "title": "Popołudniowy spacer po Parku Śląskim"
        }
    )
    assert res.status_code == 200
    pod = res.json()
    pod_id = pod["id"]
    assert pod["status"] == "forming"
    assert pod["confirmed_count"] == 1
    assert pod["spots_left"] == 4
    assert len(pod["members"]) == 1
    assert pod["members"][0]["user_id"] == "usr_zuzanna"

    # 4. Check Feed
    res = client.get("/api/pods/feed?city=Chorzów")
    assert res.status_code == 200
    feed = res.json()
    assert len(feed) == 1
    assert feed[0]["id"] == pod_id
    assert feed[0]["place_name"] == "Park Śląski - Krąg Taneczny"

    # 5. Try sending message before quorum -> 403 Forbidden!
    res = client.post(
        f"/api/pods/{pod_id}/messages",
        headers=headers_zuzanna,
        json={"text": "Cześć, czekam na resztę!"}
    )
    assert res.status_code == 403
    assert "chat_locked_until_quorum" in res.json()["detail"]

    # 6. User 2 (Jakub) joins
    res = client.post(f"/api/pods/{pod_id}/join", headers=headers_jakub)
    assert res.status_code == 200
    pod = res.json()
    assert pod["status"] == "forming"
    assert pod["confirmed_count"] == 2
    assert pod["spots_left"] == 3

    # 7. User 3 (Ania) joins -> Quorum reached!
    res = client.post(f"/api/pods/{pod_id}/join", headers=headers_ania)
    assert res.status_code == 200
    pod = res.json()
    assert pod["status"] == "quorum"
    assert pod["confirmed_count"] == 3
    assert pod["spots_left"] == 2

    # 8. Chat now works!
    res = client.post(
        f"/api/pods/{pod_id}/messages",
        headers=headers_zuzanna,
        json={"text": "Super, mamy quorum! Widzimy się przy kręgu tanecznym."}
    )
    assert res.status_code == 200
    msg = res.json()
    assert msg["body"] == "Super, mamy quorum! Widzimy się przy kręgu tanecznym."
    assert msg["sender_name"] == "Zuzanna"

    # 9. Read messages
    res = client.get(f"/api/pods/{pod_id}/messages", headers=headers_jakub)
    assert res.status_code == 200
    messages = res.json()
    assert len(messages) == 1
    assert messages[0]["body"] == "Super, mamy quorum! Widzimy się przy kręgu tanecznym."

    # 10. User 3 leaves -> Drops below quorum -> Chat relocks!
    res = client.post(f"/api/pods/{pod_id}/leave", headers=headers_ania)
    assert res.status_code == 200
    pod = res.json()
    assert pod["status"] == "forming"
    assert pod["confirmed_count"] == 2

    res = client.post(
        f"/api/pods/{pod_id}/messages",
        headers=headers_zuzanna,
        json={"text": "Ktoś jeszcze dołączy?"}
    )
    assert res.status_code == 403
    assert "chat_locked_until_quorum" in res.json()["detail"]

def test_blocked_user_cannot_join_pod(clean_db):
    headers_zuzanna = {"Authorization": "Bearer token_zuzanna"}
    headers_marek = {"Authorization": "Bearer token_marek"}

    # Insert block between Zuzanna and Marek in user_blocks
    conn = get_db_connection(clean_db)
    conn.execute("INSERT INTO user_blocks (blocker_id, blocked_id, created_at) VALUES ('usr_zuzanna', 'usr_marek', '2026-11-09T00:00:00Z')")
    conn.commit()
    conn.close()

    # Create place and pod with Zuzanna
    res = client.post(
        "/api/pods/places",
        headers=headers_zuzanna,
        json={
            "slug": "kawiarnia-mariacka",
            "name": "Kawiarnia Mariacka",
            "kind": "cafe",
            "city": "Katowice",
            "meeting_point": "Stolik przy oknie na Mariackiej",
            "latitude": 50.258,
            "longitude": 19.025,
            "is_indoor": 1,
            "template_codes": ["language_exchange"]
        }
    )
    place_id = res.json()["id"]

    from datetime import datetime, timezone, timedelta
    now_dt = datetime.now(timezone.utc)
    starts = (now_dt + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ends = (now_dt + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    deadline = (now_dt + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    res = client.post(
        "/api/pods",
        headers=headers_zuzanna,
        json={
            "template_code": "language_exchange",
            "third_place_id": place_id,
            "starts_at": starts,
            "ends_at": ends,
            "quorum_deadline_at": deadline,
            "language_code": "pl",
            "exchange_language_code": "en",
            "spend_expectation": "no_expected_spend",
            "title": "PL/EN Language Coffee"
        }
    )
    pod_id = res.json()["id"]

    # Feed should hide this pod from Marek
    res = client.get("/api/pods/feed?city=Katowice", headers=headers_marek)
    assert res.status_code == 200
    feed = res.json()
    assert all(p["id"] != pod_id for p in feed)

    # Marek tries to join directly -> 409 Conflict
    res = client.post(f"/api/pods/{pod_id}/join", headers=headers_marek)
    assert res.status_code == 409
    assert "BLOCKED_MEMBER_IN_POD" in res.json()["detail"]
