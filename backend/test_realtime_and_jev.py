import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from main import app
import main
import database
from jev_service import jev_service
from models import ActivityCategory

client = TestClient(app)

ZUZANNA_TOKEN = "token_zuzanna"
JAKUB_TOKEN = "token_jakub"
AUTH_HEADER_ZUZANNA = {"Authorization": f"Bearer {ZUZANNA_TOKEN}"}
AUTH_HEADER_JAKUB = {"Authorization": f"Bearer {JAKUB_TOKEN}"}


# --- Phase 3: WebSocket Real-Time Tests ---

def test_websocket_unauthorized_missing_token():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()


def test_websocket_unauthorized_invalid_token():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws?token=fraudulent_token") as websocket:
            websocket.receive_json()


def test_websocket_authenticated_connection():
    with client.websocket_connect(f"/ws?token={ZUZANNA_TOKEN}") as websocket:
        welcome = websocket.receive_json()
        assert welcome["type"] == "connection.ready"
        assert welcome["payload"]["user_id"] == "usr_zuzanna"
        assert "city:katowice" in welcome["payload"]["subscribed_scopes"]


def test_websocket_heartbeat_ping_pong():
    with client.websocket_connect(f"/ws?token={ZUZANNA_TOKEN}") as websocket:
        _ = websocket.receive_json()  # Consume welcome
        websocket.send_json({"action": "ping"})
        response = websocket.receive_json()
        assert response["type"] == "pong"
        assert "time" in response


def test_websocket_scope_subscription():
    with client.websocket_connect(f"/ws?token={ZUZANNA_TOKEN}") as websocket:
        _ = websocket.receive_json()  # Consume welcome

        # 1. Authorized scope subscription (city) succeeds
        websocket.send_json({"action": "subscribe", "scope": "city:katowice"})
        conf = websocket.receive_json()
        assert conf["type"] == "subscription.confirmed"
        assert conf["scope"] == "city:katowice"

        # 2. Unauthorized scope subscription (another user's private scope) is rejected
        websocket.send_json({"action": "subscribe", "scope": "user:usr_jakub"})
        err = websocket.receive_json()
        assert err["type"] == "error"
        assert "Brak uprawnień" in err["message"]

        # 3. Unsubscribing succeeds
        websocket.send_json({"action": "unsubscribe", "scope": "city:katowice"})
        unconf = websocket.receive_json()
        assert unconf["type"] == "unsubscription.confirmed"
        assert unconf["scope"] == "city:katowice"


def test_websocket_unauthorized_chat_rejected():
    with client.websocket_connect(f"/ws?token={JAKUB_TOKEN}") as websocket:
        _ = websocket.receive_json()  # Consume welcome
        # Jakub is NOT in room_out_cafe_nero_01 (only Ania, Ola, Zuzanna)
        websocket.send_json({
            "action": "chat_message",
            "room_id": "room_out_cafe_nero_01",
            "text": "Włamanie na czat",
        })
        err = websocket.receive_json()
        assert err["type"] == "error"
        assert "Brak uprawnień" in err["message"]


def test_chat_message_reaches_other_participant_without_reload():
    room_id = "chat_trip_makro_01"
    message = f"live-coordination-{uuid.uuid4().hex}"

    with client.websocket_connect(f"/ws?token={ZUZANNA_TOKEN}") as companion_socket:
        assert companion_socket.receive_json()["type"] == "connection.ready"
        companion_socket.send_json({"action": "subscribe", "scope": f"chat:{room_id}"})
        confirmed = companion_socket.receive_json()
        assert confirmed == {"type": "subscription.confirmed", "scope": f"chat:{room_id}"}

        response = client.post(
            f"/api/chat/rooms/{room_id}/messages",
            headers=AUTH_HEADER_JAKUB,
            json={"text": message},
        )
        assert response.status_code == 200

        delivered = companion_socket.receive_json()
        assert delivered["type"] == "chat.message"
        assert delivered["scope"] == f"chat:{room_id}"
        assert delivered["payload"]["id"] == response.json()["id"]
        assert delivered["payload"]["text"] == message


def test_sos_websocket_event_uses_pin_shielded_trip_contract(monkeypatch):
    trip_id = "trip_makro_01"
    original = database.TRIPS[trip_id].model_copy(deep=True)
    alert = {
        "id": "sos_test_contract",
        "trip_id": trip_id,
        "triggered_by_id": "usr_zuzanna",
        "triggered_by_name": "Zuzanna",
        "status": "fallback_required",
        "delivery_confirmed": False,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "fallback_112_url": "tel:112",
    }

    async def fallback_only_sos(**_kwargs):
        return alert

    monkeypatch.setattr(main.sos_manager, "trigger_sos", fallback_only_sos)
    monkeypatch.setattr(main.sos_manager, "get_alert_by_trip", lambda requested_id: alert if requested_id == trip_id else None)
    try:
        trip = database.TRIPS[trip_id]
        trip.status = database.TripStatus.SCHEDULED
        trip.sos_triggered = False
        with client.websocket_connect(f"/ws?token={JAKUB_TOKEN}") as host_socket:
            assert host_socket.receive_json()["type"] == "connection.ready"
            host_socket.send_json({"action": "subscribe", "scope": f"trip:{trip_id}"})
            assert host_socket.receive_json() == {"type": "subscription.confirmed", "scope": f"trip:{trip_id}"}

            response = client.post(
                f"/api/trips/{trip_id}/sos",
                headers=AUTH_HEADER_ZUZANNA,
                json={"user_confirmed": True},
            )
            assert response.status_code == 200, response.text
            delivered = host_socket.receive_json()
            assert delivered["type"] == "trip.sos_triggered"
            payload = delivered["payload"]
            assert payload["id"] == trip_id
            assert payload["status"] == "emergency_sos"
            assert payload["sos_triggered"] is True
            assert payload["sos_alert"]["status"] == "fallback_required"
            assert payload["host_pin"] is None
            assert "rendezvous_pin" not in payload
    finally:
        database.TRIPS[trip_id] = original
        database.save_trip(original)


def test_websocket_ticket_is_one_use_and_logout_closes_active_socket():
    session_token = f"cmt_test_{uuid.uuid4().hex}"
    main.persist_active_session(session_token, "usr_zuzanna")
    headers = {"Authorization": f"Bearer {session_token}"}
    issued = client.post("/api/auth/ws-ticket", headers=headers)
    assert issued.status_code == 200
    assert issued.headers["cache-control"] == "no-store"
    ticket = issued.json()["ticket"]
    assert session_token not in ticket

    with client.websocket_connect(f"/ws?ticket={ticket}") as socket:
        assert socket.receive_json()["type"] == "connection.ready"
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/ws?ticket={ticket}") as replay:
                replay.receive_json()
        assert client.post("/api/auth/logout", headers=headers).status_code == 200
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()


def test_expired_websocket_ticket_is_rejected(monkeypatch):
    issued = client.post("/api/auth/ws-ticket", headers=AUTH_HEADER_ZUZANNA)
    assert issued.status_code == 200
    ticket = issued.json()["ticket"]
    main.WS_TICKETS[ticket] = (
        ZUZANNA_TOKEN,
        datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws?ticket={ticket}") as socket:
            socket.receive_json()
    assert ticket not in main.WS_TICKETS


def test_staging_websocket_rejects_long_lived_token_in_url(monkeypatch):
    monkeypatch.setattr(main, "is_production", lambda: True)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws?token={ZUZANNA_TOKEN}") as socket:
            socket.receive_json()


def test_wave_at_ping_authenticated():
    # Use existing seeded ping
    res = client.post(
        "/api/pings/png_makro_01/wave",
        headers=AUTH_HEADER_ZUZANNA,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ping_id"] == "png_makro_01"
    assert data["from_user_id"] == "usr_zuzanna"
    assert "Zuzanna" in data["from_user_name"]
    assert "pomachał" in data["message"]

    duplicate = client.post("/api/pings/png_makro_01/wave", headers=AUTH_HEADER_ZUZANNA)
    assert duplicate.status_code == 429
    assert int(duplicate.headers["Retry-After"]) > 0


def test_wave_rejects_host_and_inactive_outing():
    ping = database.PINGS["png_makro_01"]
    assert client.post("/api/pings/png_makro_01/wave", headers=AUTH_HEADER_JAKUB).status_code == 400

    original_status = ping.status
    original_expiry = ping.expires_at
    try:
        ping.status = database.PingStatus.MATCHED
        assert client.post("/api/pings/png_makro_01/wave", headers=AUTH_HEADER_ZUZANNA).status_code == 409
        ping.status = database.PingStatus.ACTIVE
        ping.expires_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        assert client.post("/api/pings/png_makro_01/wave", headers=AUTH_HEADER_ZUZANNA).status_code == 409
    finally:
        ping.status = original_status
        ping.expires_at = original_expiry


def test_wave_at_nonexistent_ping():
    res = client.post(
        "/api/pings/png_nonexistent_999/wave",
        headers=AUTH_HEADER_JAKUB,
    )
    assert res.status_code == 404


# --- Phase 2 & 3: Hotspot & Chat Persistence & Threshold Tests ---

def test_hotspot_voting_and_outing_creation():
    # Create new test hotspot
    create_res = client.post(
        "/api/hotspots",
        headers=AUTH_HEADER_ZUZANNA,
        json={
            "city": "Katowice",
            "name": "Kebab Katowice 24h",
            "category": "late_night",
            "emoji": "🥙",
            "address": "Rynek 1, Katowice",
            "target_time": "00:15 (W nocy)",
            "description": "Nocne gastro ekipa",
            "cost_policy": "Każdy płaci za siebie",
        },
    )
    assert create_res.status_code == 200
    spot = create_res.json()
    spot_id = spot["id"]
    assert spot["threshold"] == 3
    assert spot["group_formed"] is False

    # Vote 1 (Zuzanna)
    v1 = client.put(f"/api/hotspots/{spot_id}/vote", headers=AUTH_HEADER_ZUZANNA)
    assert v1.status_code == 200
    assert v1.json()["votes_count"] == 1

    # Vote 2 (Jakub)
    v2 = client.put(f"/api/hotspots/{spot_id}/vote", headers=AUTH_HEADER_JAKUB)
    assert v2.status_code == 200
    assert v2.json()["votes_count"] == 2
    assert v2.json()["group_formed"] is False

    # Vote 3 (Ania) -> Threshold Reached!
    v3 = client.put(f"/api/hotspots/{spot_id}/vote", headers={"Authorization": "Bearer token_ania"})
    assert v3.status_code == 200
    res_data = v3.json()
    assert res_data["votes_count"] == 3
    assert res_data["group_formed"] is True
    assert res_data["outing_id"] is not None

    # Threshold creates only an invitation shell; voters are not auto-joined.
    outing_id = res_data["outing_id"]
    outing_res = client.get(f"/api/outings/{outing_id}", headers=AUTH_HEADER_ZUZANNA)
    assert outing_res.status_code == 403
    outsider_res = client.get(f"/api/outings/{outing_id}", headers={"Authorization": "Bearer token_marek"})
    assert outsider_res.status_code == 403
    explicit_join = client.post(f"/api/outings/{outing_id}/join", headers=AUTH_HEADER_ZUZANNA)
    assert explicit_join.status_code == 200
    outing_res = client.get(f"/api/outings/{outing_id}", headers=AUTH_HEADER_ZUZANNA)
    assert outing_res.status_code == 200
    outing = outing_res.json()
    assert outing["hotspot_name"] == "Kebab Katowice 24h"
    assert outing["participant_ids"] == ["usr_zuzanna"]

    # Verify Chat Room
    chat_room_id = outing["chat_room_id"]
    room_res = client.get(f"/api/chat/rooms/{chat_room_id}", headers=AUTH_HEADER_ZUZANNA)
    assert room_res.status_code == 200
    room = room_res.json()
    assert len(room["messages"]) >= 1  # System announcement message

    ola_headers = {"Authorization": "Bearer token_ola"}
    before_join = client.get(f"/api/chat/rooms/{chat_room_id}", headers=ola_headers)
    assert before_join.status_code == 403
    join_outing_res = client.post(f"/api/outings/{outing_id}/join", headers=ola_headers)
    assert join_outing_res.status_code == 200
    assert "usr_ola" in join_outing_res.json()["participant_ids"]
    joined_room = client.get(f"/api/chat/rooms/{chat_room_id}", headers=ola_headers)
    assert joined_room.status_code == 200
    joined_message = client.post(
        f"/api/chat/rooms/{chat_room_id}/messages",
        headers=ola_headers,
        json={"text": "I can join at 18:00."},
    )
    assert joined_message.status_code == 200

    # Send participant chat message
    assert client.post(f"/api/outings/{outing_id}/join", headers=AUTH_HEADER_JAKUB).status_code == 200
    msg_res = client.post(
        f"/api/chat/rooms/{chat_room_id}/messages",
        headers=AUTH_HEADER_JAKUB,
        json={"text": "Siema ekipa! O której dokładnie się widzimy?"},
    )
    assert msg_res.status_code == 200
    msg = msg_res.json()
    assert "Jakub" in msg["sender_name"]
    assert msg["text"] == "Siema ekipa! O której dokładnie się widzimy?"
    assert msg["sequence"] == 3


# --- Phase 4: Jev Decision & Classification Tests ---

def test_jev_intent_classification_promocja():
    res = client.post(
        "/api/ai/classify-intent",
        headers=AUTH_HEADER_ZUZANNA,
        json={"text": "Idę do Biedronki, jest promocja na masło 2+1 gratis i mleko"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "grocery"
    assert any("PromocjaWielosztuki" in tag for tag in data["intent_tags"])
    assert data["is_safe"] is True
    assert data["confidence_score"] >= 0.8


def test_jev_intent_classification_nocne_gastro():
    res = client.post(
        "/api/ai/classify-intent",
        headers=AUTH_HEADER_ZUZANNA,
        json={"text": "Ktoś chętny na burger i frytki? Nocne gastro faza"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "late_night"
    assert any("NocneGastro" in tag for tag in data["intent_tags"])


def test_jev_intent_classification_zgrzewka():
    res = client.post(
        "/api/ai/classify-intent",
        headers=AUTH_HEADER_ZUZANNA,
        json={"text": "Ciężkie torby i zgrzewka wody mineralnej do wniesienia"},
    )
    assert res.status_code == 200
    data = res.json()
    assert any("DźwiganieZgrzewek" in tag for tag in data["intent_tags"])


def test_jev_content_safety_clean():
    res = client.post(
        "/api/ai/screen-content",
        headers=AUTH_HEADER_ZUZANNA,
        json={"text": "Szukam kogoś na wspólne zakupy spożywcze w Lidlu."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_safe"] is True
    assert data["safety_score"] > 0.9
    assert data["action_recommended"] == "allow"
    assert len(data["flagged_reasons"]) == 0


def test_jev_content_safety_unsafe_rejection():
    res = client.post(
        "/api/ai/screen-content",
        headers=AUTH_HEADER_ZUZANNA,
        json={"text": "Szukam sponsora na randki i seks za zakupy."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_safe"] is False
    assert data["safety_score"] < 0.5
    assert data["action_recommended"] == "block"
    assert len(data["flagged_reasons"]) > 0


def test_jev_suggest_rendezvous():
    res = client.post(
        "/api/ai/suggest-rendezvous",
        headers=AUTH_HEADER_ZUZANNA,
        json={
            "destination_name": "Biedronka ul. Grzybowska 4",
            "category": "grocery",
        },
    )
    assert res.status_code == 200
    suggestions = res.json()
    assert len(suggestions) >= 2
    assert any("Punkt Obsługi Klienta" in s["title"] for s in suggestions)
    assert all(s["safety_rating"] == "Do potwierdzenia przez uczestników" for s in suggestions)
    assert all("Wysoki" not in s["safety_rating"] for s in suggestions)
    for destination, category in (
        ("Silesia City Center", ActivityCategory.FASHION),
        ("Kafej", ActivityCategory.FOOD),
        ("Urząd Katowice", ActivityCategory.QUICK),
        ("Biblioteka Śląska", ActivityCategory.STUDY),
    ):
        hints = jev_service.suggest_rendezvous(destination, category)
        assert hints
        assert all(hint.safety_rating == "Do potwierdzenia przez uczestników" for hint in hints)
