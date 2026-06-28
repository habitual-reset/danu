#!/usr/bin/env python3
"""Wipe a user's memory and conversations for fresh onboarding test runs."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from danu.admin.reset import reset_user_data
from danu.config import get_settings
from danu.db.base import get_session_factory


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Reset DANU user data for fresh testing")
    parser.add_argument("--user-id", default=settings.default_user_id)
    parser.add_argument("--tenant-id", default=settings.default_tenant_id)
    parser.add_argument(
        "--keep-usage",
        action="store_true",
        help="Keep usage_events for cost history",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    args = parser.parse_args()

    if not args.yes:
        print(f"This will delete all memory, conversations, and messages for user '{args.user_id}'.")
        print("Schema and code are untouched.")
        confirm = input("Type 'reset' to continue: ").strip().lower()
        if confirm != "reset":
            print("Aborted.")
            return

    session = get_session_factory()()
    try:
        counts = reset_user_data(
            session,
            tenant_id=args.tenant_id,
            user_id=args.user_id,
            keep_usage=args.keep_usage,
        )
        session.commit()
        print(f"Reset complete for user={args.user_id} tenant={args.tenant_id}")
        for table, count in counts.items():
            print(f"  {table}: {count} rows deleted")
        print()
        print("Ready for a fresh onboarding call.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()