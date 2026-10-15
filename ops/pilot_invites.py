"""Issue or revoke closed-pilot invites against an explicitly named SQLite DB.

Codes are shown once to the operator. Do not paste them into logs, tickets, or
partner spreadsheets. Revocation only applies before redemption; suspend or ban
an admitted account through moderation if access must later be removed.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

def main() -> int:
    parser = argparse.ArgumentParser(description="Manage CartMate closed-pilot invites")
    parser.add_argument("--db", required=True, type=Path, help="Existing absolute CartMate SQLite database path")
    action = parser.add_subparsers(dest="action", required=True)
    issue = action.add_parser("issue", help="Issue one new single-use invite")
    issue.add_argument("--hours", type=int, default=168, help="Expiry in hours (1–720; default 168)")
    revoke = action.add_parser("revoke", help="Revoke an unredeemed invite")
    revoke.add_argument("--code", required=True)
    issue_act = action.add_parser("issue-activation", help="Issue one new single-use operator activation token")
    issue_act.add_argument("--for", dest="intended_for", required=True, help="Intended participant name or identifier")
    issue_act.add_argument("--hours", type=int, default=24, help="Expiry in hours (1–168; default 24)")
    issue_rec = action.add_parser("issue-recovery", help="Issue one new single-use operator recovery token bound to a user")
    issue_rec.add_argument("--user-id", required=True, help="Existing admitted user ID (usr_...)")
    issue_rec.add_argument("--for", dest="intended_for", default="", help="Intended participant name (optional)")
    issue_rec.add_argument("--hours", type=int, default=24, help="Expiry in hours (1–168; default 24)")
    revoke_act = action.add_parser("revoke-activation", help="Revoke an unconsumed operator activation token")
    revoke_act.add_argument("--token", required=True, help="Activation token (CMACT-... or CMREC-...) or its hash")
    args = parser.parse_args()

    db_path = args.db
    if not db_path.is_absolute() or not db_path.is_file():
        parser.error("--db must name an existing absolute SQLite database file")
    if args.action in {"issue", "issue-activation", "issue-recovery"} and not 1 <= args.hours <= 720:
        parser.error("--hours must be between 1 and 720")

    # storage.py initializes its module-level store on import. Point it at the
    # explicit target first so this CLI never creates/updates a default DB.
    os.environ["CARTMATE_DATABASE_PATH"] = str(db_path.resolve())
    from storage import storage as db_storage

    if args.action == "issue":
        expires_at = datetime.now(timezone.utc) + timedelta(hours=args.hours)
        code = db_storage.issue_pilot_invite(expires_at.isoformat())
        print("Store this code privately; it will not be shown again:")
        print(code)
        print(f"Expires: {expires_at.isoformat()}")
        return 0

    if args.action == "revoke":
        try:
            revoked = db_storage.revoke_pilot_invite(args.code)
        except ValueError:
            parser.error("Invalid invite code format")
        print("Unredeemed invite revoked." if revoked else "Invite not found, already redeemed, or already revoked.")
        return 0 if revoked else 1

    if args.action == "issue-activation":
        expires_at = datetime.now(timezone.utc) + timedelta(hours=args.hours)
        token = db_storage.issue_operator_activation(
            expires_at.isoformat(),
            intended_for=args.intended_for,
            operator_id="operator_cli",
        )
        print("Store this activation token privately; it will not be shown again:")
        print(token)
        print(f"Intended for: {args.intended_for}")
        print(f"Expires: {expires_at.isoformat()}")
        return 0

    if args.action == "issue-recovery":
        expires_at = datetime.now(timezone.utc) + timedelta(hours=args.hours)
        try:
            token = db_storage.issue_operator_recovery(
                target_user_id=args.user_id,
                expires_at=expires_at.isoformat(),
                operator_id="operator_cli",
                intended_for=args.intended_for,
            )
        except ValueError as err:
            parser.error(str(err))
        print("Store this recovery token privately; it will not be shown again:")
        print(token)
        print(f"Bound to user: {args.user_id}")
        print(f"Expires: {expires_at.isoformat()}")
        return 0

    if args.action == "revoke-activation":
        try:
            revoked = db_storage.revoke_operator_activation(args.token)
        except ValueError:
            parser.error("Invalid activation token or hash format")
        print("Unconsumed activation token revoked." if revoked else "Token not found, already consumed, or already revoked.")
        return 0 if revoked else 1


if __name__ == "__main__":
    raise SystemExit(main())
