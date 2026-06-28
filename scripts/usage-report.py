#!/usr/bin/env python3
"""Print estimated usage costs from the DANU database."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from danu.config import get_settings
from danu.db.base import get_session_factory
from danu.db.repositories.usage import UsageRepository


def main() -> None:
    settings = get_settings()
    session = get_session_factory()()
    try:
        repo = UsageRepository(session)
        rows = repo.summarize_by_provider(tenant_id=settings.default_tenant_id)
        total = repo.total_estimated_cost(tenant_id=settings.default_tenant_id)

        print(f"DANU usage report (tenant={settings.default_tenant_id})")
        print(f"Database: {settings.database_url}")
        print()

        if not rows:
            print("No usage events recorded yet.")
            return

        print(f"{'Provider':<10} {'Resource':<16} {'Events':>8} {'Quantity':>12} {'Est. USD':>10}")
        print("-" * 60)
        for row in rows:
            print(
                f"{row['provider']:<10} "
                f"{row['resource_type']:<16} "
                f"{row['event_count']:>8} "
                f"{row['total_quantity']:>12.1f} "
                f"${row['estimated_cost_usd']:>9.4f}"
            )
        print("-" * 60)
        print(f"{'TOTAL':<36} ${total:>9.4f}")
        print()
        print("Note: estimates use approximate list prices; Twilio bills may lag.")
    finally:
        session.close()


if __name__ == "__main__":
    os.chdir(ROOT)
    main()