import pytest
from fastapi.testclient import TestClient
from main import app
import database

client = TestClient(app)


def test_health_check():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_unauthenticated_protected_route():
    res = client.get("/api/users/me")
    assert res.status_code == 401
    assert "Brak autoryzacji" in res.json()["detail"]


def test_invalid_bearer_token():
    res = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalid_token_12345"},
    )
    assert res.status_code == 401
    assert "Nieprawidłowy lub wygasły token" in res.json()["detail"]


def test_authenticated_user_me():
    res = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer token_zuzanna"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "usr_zuzanna"
    assert data["name"] == "Zuzanna Wiśniewska"
    assert "email" in data  # Private DTO contains email
    assert "phone" in data


def test_public_users_pii_shielding():
    res = client.get("/api/users/all")
    assert res.status_code == 200
    users = res.json()
    assert len(users) > 0
    for u in users:
        assert "email" not in u
        assert "phone" not in u
        assert "emergency_contact" not in u
        assert "name" in u
        assert "trust_tier" in u


def test_pings_privacy():
    res = client.get("/api/pings")
    assert res.status_code == 200
    pings = res.json()
    assert len(pings) > 0
    for p in pings:
        host = p["host"]
        assert "email" not in host
        assert "phone" not in host
        assert "emergency_contact" not in host


def test_trip_rendezvous_pin_not_in_general_response():
    # Jakub is host, Zuzanna is companion of trip_makro_01
    res = client.get(
        "/api/trips/trip_makro_01",
        headers={"Authorization": "Bearer token_zuzanna"},
    )
    assert res.status_code == 200
    trip_data = res.json()
    # rendezvous_pin must NEVER be exposed in the response DTO
    assert "rendezvous_pin" not in trip_data
    # Companion should not receive host_pin
    assert trip_data.get("host_pin") is None


def test_host_can_view_pin():
    # Host (Jakub) queries /api/trips/trip_makro_01/pin
    res = client.get(
        "/api/trips/trip_makro_01/pin",
        headers={"Authorization": "Bearer token_jakub"},
    )
    assert res.status_code == 200
    assert "pin" in res.json()
    assert res.json()["pin"] == "4819"


def test_companion_cannot_view_pin_endpoint():
    # Companion (Zuzanna) queries /api/trips/trip_makro_01/pin -> 403 Forbidden
    res = client.get(
        "/api/trips/trip_makro_01/pin",
        headers={"Authorization": "Bearer token_zuzanna"},
    )
    assert res.status_code == 403
    assert "Tylko organizator" in res.json()["detail"]


def test_unauthorized_user_cannot_access_trip():
    # Ania (usr_ania) is not a participant in trip_makro_01 -> 403
    res = client.get(
        "/api/trips/trip_makro_01",
        headers={"Authorization": "Bearer token_ania"},
    )
    assert res.status_code == 403
    assert "Brak uprawnień" in res.json()["detail"]


def test_pin_verification_rate_limiting():
    # Seeded trip_makro_01 starts with 5 attempts
    trip = database.TRIPS["trip_makro_01"]
    trip.pin_attempts_left = 5
    trip.rendezvous_verified = False

    host_attempt = client.post(
        "/api/trips/trip_makro_01/verify-pin",
        headers={"Authorization": "Bearer token_jakub"},
        json={"pin": "4819"},
    )
    assert host_attempt.status_code == 403
    assert trip.pin_attempts_left == 5

    # Fail 5 times
    for i in range(5):
        res = client.post(
            "/api/trips/trip_makro_01/verify-pin",
            headers={"Authorization": "Bearer token_zuzanna"},
            json={"pin": "0000"},
        )
        assert res.status_code in [400, 429]
        if res.status_code == 400:
            assert "0000" not in res.json()["detail"]

    # 6th attempt should be blocked with 429 Too Many Requests
    blocked_res = client.post(
        "/api/trips/trip_makro_01/verify-pin",
        headers={"Authorization": "Bearer token_zuzanna"},
        json={"pin": "4819"},
    )
    assert blocked_res.status_code == 429
    assert "Przekroczono limit prób" in blocked_res.json()["detail"]


def test_safehaven_eligibility_enforced():
    # Jakub is male -> cannot toggle SafeHaven
    res = client.post(
        "/api/users/toggle-safe-haven",
        headers={"Authorization": "Bearer token_jakub"},
    )
    assert res.status_code == 403
    assert "wyłącznie dla zweryfikowanych kobiet" in res.json()["detail"]


def test_login_validation():
    # Invalid OTP code
    bad_res = client.post(
        "/api/auth/login",
        json={"identifier": "zuzanna.w@example.pl", "code": "wrong_code"},
    )
    assert bad_res.status_code == 401

    # Valid OTP code
    good_res = client.post(
        "/api/auth/login",
        json={"identifier": "zuzanna.w@example.pl", "code": "1234"},
    )
    assert good_res.status_code == 200
    assert good_res.json()["token"].startswith("cmt_")


def test_list_hotspots():
    res = client.get("/api/hotspots?city=Katowice")
    assert res.status_code == 200
    spots = res.json()
    assert len(spots) >= 4
    # Kafej / Strefa Kultury is already formed in seed
    nero = next(s for s in spots if s["id"] == "spot_cafe_nero")
    assert nero["group_formed"] is True
    assert nero["votes_count"] == 3


def test_hotspot_voting_and_threshold_formation():
    # Burger King starts with 2 votes (threshold 3)
    bk = database.HOTSPOTS["spot_bk_centralny"]
    bk.voter_ids = ["usr_jakub", "usr_mateusz"]
    bk.voter_avatars = [database.USERS["usr_jakub"].avatar, database.USERS["usr_mateusz"].avatar]
    bk.votes_count = 2
    bk.group_formed = False
    bk.outing_id = None

    # Zuzanna casts the 3rd vote
    res = client.put(
        "/api/hotspots/spot_bk_centralny/vote",
        headers={"Authorization": "Bearer token_zuzanna"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["votes_count"] == 3
    assert data["group_formed"] is True
    assert data["outing_id"] is not None

    outing_id = data["outing_id"]
    assert outing_id in database.OUTINGS
    outing = database.OUTINGS[outing_id]
    assert outing.hotspot_name == "Burger King Katowice Dworzec 24h"
    assert outing.participant_ids == []  # a vote is not consent to join

    # Chat room was created in same transaction
    chat_room_id = outing.chat_room_id
    assert chat_room_id in database.CHAT_ROOMS
    room = database.CHAT_ROOMS[chat_room_id]
    assert len(room.messages) >= 1  # System greeting


def test_hotspot_voting_idempotent():
    # Zuzanna votes again for Burger King -> should be idempotent
    res = client.put(
        "/api/hotspots/spot_bk_centralny/vote",
        headers={"Authorization": "Bearer token_zuzanna"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["votes_count"] == 3
    # The authenticated caller can see their own vote, but not the raw voter roster.
    assert data["user_voted"] is True
    assert "voter_ids" not in data
    assert database.HOTSPOTS["spot_bk_centralny"].voter_ids.count("usr_zuzanna") == 1


def test_chat_room_and_message_delivery():
    chat_room_id = "room_out_cafe_nero_01"
    # Send message from Zuzanna
    res = client.post(
        f"/api/chat/rooms/{chat_room_id}/messages",
        headers={"Authorization": "Bearer token_zuzanna"},
        json={"text": "Cześć dziewczyny, ja też już idę na Nowy Świat!"},
    )
    assert res.status_code == 200
    msg = res.json()
    assert msg["sender_name"] == "Zuzanna Wiśniewska"
    assert msg["text"] == "Cześć dziewczyny, ja też już idę na Nowy Świat!"

    # Fetch room messages
    room_res = client.get(
        f"/api/chat/rooms/{chat_room_id}",
        headers={"Authorization": "Bearer token_zuzanna"},
    )
    assert room_res.status_code == 200
    room_data = room_res.json()
    texts = [m["text"] for m in room_data["messages"]]
    assert "Cześć dziewczyny, ja też już idę na Nowy Świat!" in texts


def test_unauthorized_user_cannot_access_or_send_chat():
    chat_room_id = "room_out_cafe_nero_01"
    # Jakub is not a member of Kafej Strefa Kultury outing
    # 1. Reading chat room is forbidden (403)
    read_res = client.get(
        f"/api/chat/rooms/{chat_room_id}",
        headers={"Authorization": "Bearer token_jakub"},
    )
    assert read_res.status_code == 403
    assert "Brak uprawnień" in read_res.json()["detail"]

    # 2. Sending message to chat room is forbidden (403)
    send_res = client.post(
        f"/api/chat/rooms/{chat_room_id}/messages",
        headers={"Authorization": "Bearer token_jakub"},
        json={"text": "Czy mogę wpaść?"},
    )
    assert send_res.status_code == 403
    assert "Brak uprawnień" in send_res.json()["detail"]
