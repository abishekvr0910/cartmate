import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Set
from fastapi import WebSocket

logger = logging.getLogger("cartmate.realtime")


class WebSocketManager:
    """
    Manages authenticated WebSocket connections, scope subscriptions,
    heartbeats, and real-time event broadcasting for CartMate.
    """

    def __init__(self):
        # socket -> user_id
        self._socket_to_user: Dict[WebSocket, str] = {}
        # socket -> authenticated session, for immediate logout/revocation.
        self._socket_to_session: Dict[WebSocket, str] = {}
        # user_id -> set of sockets
        self._user_to_sockets: Dict[str, Set[WebSocket]] = {}
        # scope -> set of sockets (e.g., "city:warszawa", "outing:out_1", "trip:trp_1")
        self._scope_subscribers: Dict[str, Set[WebSocket]] = {}
        # socket -> set of scopes
        self._socket_scopes: Dict[WebSocket, Set[str]] = {}
        self._sequence: int = 0
        self._lock = asyncio.Lock()
        self._session_validator: Optional[Callable[[str], bool]] = None

    def set_session_validator(self, validator: Callable[[str], bool]) -> None:
        """Set a callback to check if a session token is currently valid and unrevoked."""
        self._session_validator = validator

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        session_token: str,
        initial_scopes: Optional[List[str]] = None,
    ) -> None:
        await websocket.accept()
        async with self._lock:
            self._socket_to_user[websocket] = user_id
            self._socket_to_session[websocket] = session_token
            if user_id not in self._user_to_sockets:
                self._user_to_sockets[user_id] = set()
            self._user_to_sockets[user_id].add(websocket)
            self._socket_scopes[websocket] = set()

            scopes = initial_scopes or ["city:warszawa", f"user:{user_id}"]
            for scope in scopes:
                self._subscribe_locked(websocket, scope)

        # Send welcome envelope to client
        await self.send_personal_message(
            websocket,
            {
                "version": 1,
                "id": f"evt_{uuid.uuid4().hex[:8]}",
                "sequence": 0,
                "type": "connection.ready",
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "scope": f"user:{user_id}",
                "payload": {
                    "user_id": user_id,
                    "subscribed_scopes": list(self._socket_scopes.get(websocket, set())),
                    "message": "CartMate Realtime Connection Established",
                },
            },
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            user_id = self._socket_to_user.pop(websocket, None)
            self._socket_to_session.pop(websocket, None)
            if user_id and user_id in self._user_to_sockets:
                self._user_to_sockets[user_id].discard(websocket)
                if not self._user_to_sockets[user_id]:
                    del self._user_to_sockets[user_id]

            scopes = self._socket_scopes.pop(websocket, set())
            for scope in scopes:
                if scope in self._scope_subscribers:
                    self._scope_subscribers[scope].discard(websocket)
                    if not self._scope_subscribers[scope]:
                        del self._scope_subscribers[scope]

    async def close_session(self, session_token: str) -> None:
        async with self._lock:
            sockets = [socket for socket, token in self._socket_to_session.items() if token == session_token]
        for socket in sockets:
            try:
                await socket.close(code=1008, reason="Session revoked")
            except Exception:
                pass
            await self.disconnect(socket)

    async def close_user(self, user_id: str) -> None:
        async with self._lock:
            sockets = list(self._user_to_sockets.get(user_id, set()))
        for socket in sockets:
            try:
                await socket.close(code=1008, reason="Account access revoked")
            except Exception:
                pass
            await self.disconnect(socket)

    async def close_user_except_session(self, user_id: str, except_session: Optional[str] = None) -> None:
        """Close all sockets for a user except those matching a newly established session."""
        async with self._lock:
            sockets = [
                socket for socket in self._user_to_sockets.get(user_id, set())
                if except_session is None or self._socket_to_session.get(socket) != except_session
            ]
        for socket in sockets:
            try:
                await socket.close(code=1008, reason="Session revoked")
            except Exception:
                pass
            await self.disconnect(socket)

    def _subscribe_locked(self, websocket: WebSocket, scope: str) -> None:
        if scope not in self._scope_subscribers:
            self._scope_subscribers[scope] = set()
        self._scope_subscribers[scope].add(websocket)
        if websocket in self._socket_scopes:
            self._socket_scopes[websocket].add(scope)

    async def subscribe(self, websocket: WebSocket, scope: str) -> None:
        async with self._lock:
            self._subscribe_locked(websocket, scope)

    async def unsubscribe(self, websocket: WebSocket, scope: str) -> None:
        async with self._lock:
            if scope in self._scope_subscribers:
                self._scope_subscribers[scope].discard(websocket)
                if not self._scope_subscribers[scope]:
                    del self._scope_subscribers[scope]
            if websocket in self._socket_scopes:
                self._socket_scopes[websocket].discard(scope)

    async def revoke_user_scopes(self, user_id: str, scopes: List[str]) -> None:
        """Drop newly unauthorized group subscriptions on every active device."""
        async with self._lock:
            for socket in self._user_to_sockets.get(user_id, set()):
                for scope in scopes:
                    self._socket_scopes.get(socket, set()).discard(scope)
                    subscribers = self._scope_subscribers.get(scope)
                    if subscribers:
                        subscribers.discard(socket)
                        if not subscribers:
                            del self._scope_subscribers[scope]

    async def broadcast(
        self,
        scope: str,
        event_type: str,
        payload: dict,
        exclude: Optional[WebSocket] = None,
    ) -> None:
        async with self._lock:
            self._sequence += 1
            seq = self._sequence
            target_sockets = list(self._scope_subscribers.get(scope, set()))

        envelope = {
            "version": 1,
            "id": f"evt_{uuid.uuid4().hex[:10]}",
            "sequence": seq,
            "type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "scope": scope,
            "payload": payload,
        }
        text_data = json.dumps(envelope)

        dead_sockets: List[WebSocket] = []
        for socket in target_sockets:
            if socket == exclude:
                continue
            session = self._socket_to_session.get(socket)
            if self._session_validator and session and not self._session_validator(session):
                dead_sockets.append(socket)
                try:
                    await socket.close(code=1008, reason="Session revoked")
                except Exception:
                    pass
                continue
            try:
                await socket.send_text(text_data)
            except Exception as e:
                logger.warning(f"Error sending to websocket: {e}")
                dead_sockets.append(socket)

        for dead in dead_sockets:
            await self.disconnect(dead)

    async def send_to_user(
        self,
        user_id: str,
        event_type: str,
        payload: dict,
    ) -> None:
        async with self._lock:
            self._sequence += 1
            seq = self._sequence
            target_sockets = list(self._user_to_sockets.get(user_id, set()))

        envelope = {
            "version": 1,
            "id": f"evt_{uuid.uuid4().hex[:10]}",
            "sequence": seq,
            "type": event_type,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "scope": f"user:{user_id}",
            "payload": payload,
        }
        text_data = json.dumps(envelope)

        dead_sockets: List[WebSocket] = []
        for socket in target_sockets:
            session = self._socket_to_session.get(socket)
            if self._session_validator and session and not self._session_validator(session):
                dead_sockets.append(socket)
                try:
                    await socket.close(code=1008, reason="Session revoked")
                except Exception:
                    pass
                continue
            try:
                await socket.send_text(text_data)
            except Exception as e:
                logger.warning(f"Error sending to user websocket: {e}")
                dead_sockets.append(socket)

        for dead in dead_sockets:
            await self.disconnect(dead)

    async def send_personal_message(self, websocket: WebSocket, data: dict) -> None:
        try:
            await websocket.send_text(json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")

    def get_stats(self) -> dict:
        return {
            "active_sockets": len(self._socket_to_user),
            "connected_users": len(self._user_to_sockets),
            "active_scopes": len(self._scope_subscribers),
            "total_broadcast_sequence": self._sequence,
        }


# Global singleton instance
ws_manager = WebSocketManager()
