import asyncio
import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from storage import get_db_connection

logger = logging.getLogger("cartmate.voice")

MAX_CALL_DURATION_SECONDS = 600       # 10 minutes hard cap
QUEUE_TIMEOUT_SECONDS = 60           # 60 seconds matching timeout
CALL_COOLDOWN_SECONDS = 600          # 10 minutes cooldown between calls
DAILY_CALL_LIMIT = 3                 # 3 calls per 24 hours
DEFAULT_DEV_TURN_SECRET = "cartmate_ephemeral_turn_secret_dev"
DEFAULT_DISCONNECT_GRACE_SECONDS = 12.0


def is_voice_window_open() -> bool:
    """Returns True if the voice call window is open (18:00 - 23:00 Warsaw time in production)."""
    enforce = os.getenv("CARTMATE_VOICE_WINDOW_ENFORCED", "").lower() in ("1", "true") or os.getenv("CARTMATE_ENV") == "production"
    if not enforce:
        return True
    try:
        from zoneinfo import ZoneInfo
        warsaw_hour = datetime.now(ZoneInfo("Europe/Warsaw")).hour
        return 18 <= warsaw_hour < 23
    except Exception:
        return True

@dataclass
class QueueEntry:
    user_id: str
    topic: str
    joined_at: float
    websocket: any
    timeout_task: Optional[asyncio.Task] = None


class VoiceCallManager:
    def __init__(self, ws_manager, storage):
        self.ws = ws_manager
        self.storage = storage
        self.queue: Dict[str, QueueEntry] = {}
        self.active_calls: Dict[str, dict] = {}
        self.user_to_call: Dict[str, str] = {}
        self.call_timer_tasks: Dict[str, asyncio.Task] = {}
        self.disconnect_grace_tasks: Dict[str, asyncio.Task] = {}
        self.lock = asyncio.Lock()

    def get_ice_servers(self, user_id: str) -> List[dict]:
        """
        Returns STUN and TURN relay configurations.
        Includes Google public STUN plus RFC 5766 TURN relay servers with ephemeral credentials.
        Fails closed on TURN credentials in production if CARTMATE_TURN_SECRET uses the dev default.
        """
        turn_secret = os.getenv("CARTMATE_TURN_SECRET", DEFAULT_DEV_TURN_SECRET)
        turn_host = os.getenv("CARTMATE_TURN_HOST", "turn.cartmate.pl")
        stun_servers = [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"},
        ]
        if os.getenv("CARTMATE_ENV") == "production" and (not turn_secret or turn_secret == DEFAULT_DEV_TURN_SECRET):
            logger.warning("Production TURN secret is unconfigured or set to dev default; withholding TURN credentials.")
            return stun_servers

        # Ephemeral timestamp-based credentials (valid for 15 minutes)
        expiry = int(time.time()) + 900
        username = f"{expiry}:{user_id}"
        digest = hmac.new(turn_secret.encode("utf-8"), username.encode("utf-8"), hashlib.sha1).digest()
        credential = base64.b64encode(digest).decode("utf-8")

        return stun_servers + [
            {
                "urls": [
                    f"turn:{turn_host}:3478?transport=udp",
                    f"turn:{turn_host}:3478?transport=tcp",
                    f"turns:{turn_host}:443?transport=tcp",
                ],
                "username": username,
                "credential": credential,
            },
        ]

    def cancel_disconnect_grace(self, user_id: str) -> None:
        """Cancels any pending cellular disconnect grace timer when a user reconnects."""
        task = self.disconnect_grace_tasks.pop(user_id, None)
        if task and not task.done():
            task.cancel()

    async def handle_socket_disconnect(self, user_id: str, grace_seconds: Optional[float] = None) -> None:
        """
        Gives brief cellular/Wi-Fi handoffs a 12-second reconnection grace window before
        tearing down an active voice call. Never delays explicit hangups, blocks, or bans.
        """
        call_id = self.user_to_call.get(user_id)
        if not call_id:
            return
        if grace_seconds is None:
            try:
                grace_seconds = float(os.getenv("CARTMATE_VOICE_DISCONNECT_GRACE_SECONDS", str(DEFAULT_DISCONNECT_GRACE_SECONDS)))
            except ValueError:
                grace_seconds = DEFAULT_DISCONNECT_GRACE_SECONDS

        if grace_seconds <= 0:
            await self.terminate_call(call_id, initiator_user_id=user_id, reason="connection_failed")
            return

        self.cancel_disconnect_grace(user_id)

        async def _grace_wait():
            try:
                await asyncio.sleep(grace_seconds)
                # If the user reconnected on another socket during the grace window, keep the call alive
                if hasattr(self.ws, "_user_to_sockets") and self.ws._user_to_sockets.get(user_id):
                    return
                if self.user_to_call.get(user_id) == call_id:
                    await self.terminate_call(call_id, initiator_user_id=user_id, reason="connection_failed")
            except asyncio.CancelledError:
                pass
            finally:
                self.disconnect_grace_tasks.pop(user_id, None)

        self.disconnect_grace_tasks[user_id] = asyncio.create_task(_grace_wait())

    async def enqueue_caller(self, user_id: str, topic: str, websocket) -> Tuple[str, Optional[dict]]:
        """
        Enqueues a user for a 10-minute voice call or matches immediately with an available peer.
        Enforces daily quotas, cooldowns, single-active call invariant, and mutual block checks.
        """
        async with self.lock:
            # 0. Evening window check
            if not is_voice_window_open():
                return "WINDOW_CLOSED", None

            # 1. Already in an active call check
            if user_id in self.user_to_call:
                return "ALREADY_IN_CALL", None

            # 2. Daily limit check
            daily_count = self.storage.get_daily_voice_call_count(user_id)
            if daily_count >= DAILY_CALL_LIMIT:
                return "DAILY_LIMIT_REACHED", None

            # 3. Cooldown check
            sec_since_last = self.storage.get_seconds_since_last_voice_call(user_id)
            if sec_since_last is not None and sec_since_last < CALL_COOLDOWN_SECONDS:
                remaining = int(CALL_COOLDOWN_SECONDS - sec_since_last)
                return f"COOLDOWN_ACTIVE_{remaining}S", None

            # 4. Check for compatible waiting peer
            matched_candidate_id = None
            for candidate_id in list(self.queue.keys()):
                if candidate_id == user_id:
                    continue
                # Mutual block check
                if not self.storage.are_users_mutually_blocked(user_id, candidate_id):
                    matched_candidate_id = candidate_id
                    break

            if matched_candidate_id:
                peer_entry = self.queue.pop(matched_candidate_id)
                if peer_entry.timeout_task and not peer_entry.timeout_task.done():
                    peer_entry.timeout_task.cancel()

                call_id = f"vcall_{secrets.token_hex(8)}"
                now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                call_data = {
                    "id": call_id,
                    "user_a_id": user_id,
                    "user_b_id": matched_candidate_id,
                    "topic": topic,
                    "status": "connecting",
                    "created_at": now_str,
                    "started_at": None,
                    "created_epoch": time.time(),
                }

                # Persist in database
                self.storage.create_voice_session(call_id, user_id, matched_candidate_id, topic)

                self.active_calls[call_id] = call_data
                self.user_to_call[user_id] = call_id
                self.user_to_call[matched_candidate_id] = call_id

                # Fetch alias profiles
                user_a_profile = self._get_user_alias(user_id)
                user_b_profile = self._get_user_alias(matched_candidate_id)

                # Send WebRTC match notifications
                # User A is designated 'offerer', User B is 'answerer'
                await self.ws.send_personal_message(
                    websocket,
                    {
                        "type": "voice.call_matched",
                        "call_id": call_id,
                        "role": "offerer",
                        "topic": topic,
                        "peer": user_b_profile,
                        "ice_servers": self.get_ice_servers(user_id),
                        "max_duration_seconds": MAX_CALL_DURATION_SECONDS,
                    },
                )

                if peer_entry.websocket:
                    await self.ws.send_personal_message(
                        peer_entry.websocket,
                        {
                            "type": "voice.call_matched",
                            "call_id": call_id,
                            "role": "answerer",
                            "topic": topic,
                            "peer": user_a_profile,
                            "ice_servers": self.get_ice_servers(matched_candidate_id),
                            "max_duration_seconds": MAX_CALL_DURATION_SECONDS,
                        },
                    )

                logger.info(f"Matched voice call {call_id} between {user_id} and {matched_candidate_id}")
                return "MATCHED", call_data

            else:
                # Add to queue with 60-second automatic timeout
                entry = QueueEntry(
                    user_id=user_id,
                    topic=topic,
                    joined_at=time.time(),
                    websocket=websocket,
                )
                
                # Launch timeout watcher
                entry.timeout_task = asyncio.create_task(self._queue_timeout_watcher(user_id, QUEUE_TIMEOUT_SECONDS))
                self.queue[user_id] = entry
                return "QUEUED", None

    async def _queue_timeout_watcher(self, user_id: str, timeout_sec: int):
        """Automatically removes user from queue after 60s and notifies them politely."""
        try:
            await asyncio.sleep(timeout_sec)
            async with self.lock:
                entry = self.queue.pop(user_id, None)
                if entry and entry.websocket:
                    await self.ws.send_personal_message(
                        entry.websocket,
                        {
                            "type": "voice.queue_timeout",
                            "message": "Brak dostępnych rozmówców w tej chwili. Spróbuj ponownie za chwilę lub dołącz w wieczornym oknie połączeń.",
                        },
                    )
        except asyncio.CancelledError:
            pass

    async def dequeue_caller(self, user_id: str) -> bool:
        """Removes a user from the matchmaking queue."""
        async with self.lock:
            entry = self.queue.pop(user_id, None)
            if entry and entry.timeout_task and not entry.timeout_task.done():
                entry.timeout_task.cancel()
            return entry is not None

    def get_peer_id(self, call_id: str, user_id: str) -> Optional[str]:
        """Returns the ID of the other user in this call."""
        call = self.active_calls.get(call_id)
        if not call:
            return None
        if call["user_a_id"] == user_id:
            return call["user_b_id"]
        elif call["user_b_id"] == user_id:
            return call["user_a_id"]
        return None

    async def forward_signaling(self, call_id: str, sender_id: str, event_type: str, data: dict) -> bool:
        """Forwards WebRTC signaling messages (offer, answer, ice_candidate) directly to the peer."""
        peer_id = self.get_peer_id(call_id, sender_id)
        if not peer_id:
            logger.warning(f"Cannot forward {event_type}: call {call_id} not found or user {sender_id} not participant.")
            return False

        message = {
            "type": event_type,
            "call_id": call_id,
            "sender_id": sender_id,
            **data,
        }

        delivered = False
        try:
            if hasattr(self.ws, "_user_to_sockets"):
                sockets = list(self.ws._user_to_sockets.get(peer_id, set()))
                for s in sockets:
                    await self.ws.send_personal_message(s, message)
                    delivered = True
            elif hasattr(self.ws, "send_to_user"):
                await self.ws.send_to_user(peer_id, event_type, message)
                delivered = True
        except Exception as exc:
            logger.error(f"Error forwarding signaling {event_type} to {peer_id}: {exc}")

        return delivered

    async def handle_call_connected(self, call_id: str, user_id: str):
        """
        Invoked when WebRTC peer connection is established and media begins streaming.
        Sets status to active and arms the authoritative 600-second server countdown.
        """
        async with self.lock:
            call = self.active_calls.get(call_id)
            if not call or call["status"] == "active":
                return

            if user_id not in (call["user_a_id"], call["user_b_id"]):
                logger.warning(f"Unauthorized call_connected attempt for {call_id} by {user_id}")
                return

            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            call["status"] = "active"
            call["started_at"] = now_str
            call["started_epoch"] = time.time()

            self.storage.update_voice_session(
                call_id=call_id,
                status="active",
                started_at=now_str,
            )

            # Start authoritative 600-second timeout task
            self.call_timer_tasks[call_id] = asyncio.create_task(
                self._authoritative_call_timer(call_id, MAX_CALL_DURATION_SECONDS)
            )
            logger.info(f"Voice call {call_id} active. Authoritative timer armed for {MAX_CALL_DURATION_SECONDS}s.")

    async def _authoritative_call_timer(self, call_id: str, duration_sec: int):
        """Authoritative server-side timer that cuts call at 600 seconds."""
        try:
            # 30-second warning before cutoff
            if duration_sec > 30:
                await asyncio.sleep(duration_sec - 30)
                await self._broadcast_call_event(call_id, "voice.call_warning_30s", {
                    "call_id": call_id,
                    "seconds_remaining": 30,
                    "message": "Połączenie zakończy się za 30 sekund.",
                })
                await asyncio.sleep(30)
            else:
                await asyncio.sleep(duration_sec)

            # Hard stop
            await self.terminate_call(
                call_id=call_id,
                initiator_user_id=None,
                reason="timeout_10min",
                block_peer=False,
            )
        except asyncio.CancelledError:
            pass

    async def terminate_call(
        self,
        call_id: str,
        initiator_user_id: Optional[str],
        reason: str = "user_hangup",
        block_peer: bool = False,
    ) -> dict:
        """
        Atomically terminates an active voice call session.
        Calculates exact duration, writes session record, triggers peer blocks if requested,
        and broadcasts call_ended events to both participants.
        """
        async with self.lock:
            call = self.active_calls.pop(call_id, None)
            if not call:
                return {}

            user_a = call["user_a_id"]
            user_b = call["user_b_id"]

            if initiator_user_id and initiator_user_id not in (user_a, user_b):
                logger.warning(f"Unauthorized terminate_call attempt for {call_id} by {initiator_user_id}")
                # Restore call in active_calls so authorized participants are not disrupted
                self.active_calls[call_id] = call
                return {}

            # Cancel countdown timer and any pending disconnect grace timers
            timer_task = self.call_timer_tasks.pop(call_id, None)
            if timer_task and not timer_task.done():
                timer_task.cancel()
            self.cancel_disconnect_grace(user_a)
            self.cancel_disconnect_grace(user_b)

            self.user_to_call.pop(user_a, None)
            self.user_to_call.pop(user_b, None)

            # Calculate duration
            started_epoch = call.get("started_epoch")
            duration_seconds = int(time.time() - started_epoch) if started_epoch else 0
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Map to allowed end_reason in 0012_voice_calls.sql:
            # ('timeout_10min', 'user_hangup', 'blocked', 'connection_failed', 'cancelled')
            if block_peer or reason in ("blocked", "user_blocked"):
                clean_reason = "blocked"
                final_status = "reported"
            elif reason in ("peer_disconnected", "connection_dropped", "connection_failed"):
                clean_reason = "connection_failed"
                final_status = "dropped"
            elif reason == "timeout_10min":
                clean_reason = "timeout_10min"
                final_status = "completed"
            elif reason == "cancelled":
                clean_reason = "cancelled"
                final_status = "cancelled"
            else:
                clean_reason = "user_hangup"
                final_status = "completed"

            # 1. Update database record
            self.storage.update_voice_session(
                call_id=call_id,
                status=final_status,
                ended_at=now_str,
                duration_seconds=duration_seconds,
                end_reason=clean_reason,
            )

            # 2. Atomic block commit if requested
            if (block_peer or clean_reason == "blocked") and initiator_user_id:
                target_id = user_b if initiator_user_id == user_a else user_a
                try:
                    import database
                    database.block_user(initiator_user_id, target_id)
                    separated_pids = self.storage.separate_blocked_user_from_pods(initiator_user_id, target_id)
                    if hasattr(self.ws, "broadcast"):
                        for pid in separated_pids:
                            updated_pod = self.storage.get_pod(pid)
                            if updated_pod:
                                await self.ws.broadcast(
                                    f"pod:{pid}",
                                    "pod.member_left",
                                    {
                                        "pod_id": pid,
                                        "user_id": initiator_user_id,
                                        "confirmed_count": updated_pod["confirmed_count"],
                                        "status": updated_pod["status"],
                                    },
                                )
                    logger.info(f"Voice call {call_id}: {initiator_user_id} blocked {target_id}")
                except Exception as exc:
                    logger.error(f"Error persisting block during voice hangup: {exc}")

            # 3. Broadcast termination to both parties
            payload = {
                "type": "voice.call_ended",
                "call_id": call_id,
                "reason": clean_reason,
                "duration_seconds": duration_seconds,
                "ended_at": now_str,
            }
            await self._broadcast_call_event(call_id, "voice.call_ended", payload, user_ids=[user_a, user_b])
            return payload

    async def _broadcast_call_event(self, call_id: str, event_type: str, data: dict, user_ids: Optional[List[str]] = None):
        """Sends a WebSocket message directly to participants of this call."""
        target_ids = user_ids or []
        if not target_ids and call_id in self.active_calls:
            c = self.active_calls[call_id]
            target_ids = [c["user_a_id"], c["user_b_id"]]

        for uid in target_ids:
            try:
                if hasattr(self.ws, "_user_to_sockets"):
                    sockets = list(self.ws._user_to_sockets.get(uid, set()))
                    for s in sockets:
                        await self.ws.send_personal_message(s, data)
                elif hasattr(self.ws, "send_to_user"):
                    await self.ws.send_to_user(uid, event_type, data)
            except Exception as e:
                logger.debug(f"Could not deliver {event_type} to user {uid}: {e}")

    def _get_user_alias(self, user_id: str) -> dict:
        """Returns privacy-preserving display alias (First Name only, no contacts)."""
        try:
            import json
            conn = get_db_connection(self.storage.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT data_json FROM users WHERE id = ?;", (user_id,))
            row = cursor.fetchone()
            conn.close()
            if row and row["data_json"]:
                data = json.loads(row["data_json"])
                name = data.get("name", "Rozmówca").split()[0]  # First name only
                return {
                    "user_id": user_id,
                    "first_name": name,
                    "city": data.get("city", "Silesia"),
                }
        except Exception:
            pass
        return {"user_id": user_id, "first_name": "Rozmówca", "city": "Silesia"}
