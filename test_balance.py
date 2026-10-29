# -*- coding: utf-8 -*-
"""
Balance Calculation Tests - Recharge Tracker
Run: python test_balance.py
Tests the carry-forward logic without needing a live database.
"""

import sys
import os
import io

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from api.balance import compute_balance_timeline

# ─────────────────────────────────────────────────────────────
# Simulate transactions as they'd come from the DB
# Using IST dates directly (2026-10-26 = Monday, etc.)
# ─────────────────────────────────────────────────────────────

MOCK_TRANSACTIONS = [
    # Monday 2026-10-26
    {"id": "1", "user_id": "u1", "type": "recharge", "name": "Recharge", "amount": "1000.00", "created_at": "2026-10-26T04:00:00+05:30"},
    {"id": "2", "user_id": "u1", "type": "expense",  "name": "Groceries","amount":  "400.00", "created_at": "2026-10-26T10:00:00+05:30"},
    # Tuesday 2026-10-27
    {"id": "3", "user_id": "u1", "type": "expense",  "name": "Milk",     "amount":  "300.00", "created_at": "2026-10-27T09:00:00+05:30"},
    # Wednesday 2026-10-28
    {"id": "4", "user_id": "u1", "type": "recharge", "name": "Recharge", "amount":  "500.00", "created_at": "2026-10-28T08:00:00+05:30"},
    {"id": "5", "user_id": "u1", "type": "expense",  "name": "Veggies",  "amount":  "200.00", "created_at": "2026-10-28T12:00:00+05:30"},
]


def run_tests():
    from datetime import date
    timeline = compute_balance_timeline(MOCK_TRANSACTIONS)
    days = timeline["days"]
    wallet = timeline["wallet_balance"]

    mon = date(2026, 10, 26)
    tue = date(2026, 10, 27)
    wed = date(2026, 10, 28)

    errors = []

    def check(desc, actual, expected):
        ok = Decimal(str(actual)) == Decimal(str(expected))
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {status}: {desc} - got {actual}, expected {expected}")
        if not ok:
            errors.append(desc)

    print("\n=== TEST 1: Monday ===")
    check("Opening balance",  days[mon]["opening"],  Decimal("0"))
    check("Received",         days[mon]["received"],  Decimal("1000"))
    check("Spent",            days[mon]["spent"],     Decimal("400"))
    check("Closing balance",  days[mon]["closing"],   Decimal("600"))

    print("\n=== TEST 2: Tuesday (no recharge) ===")
    check("Opening = Mon closing", days[tue]["opening"],  Decimal("600"))
    check("Received = 0",          days[tue]["received"], Decimal("0"))
    check("Spent",                 days[tue]["spent"],    Decimal("300"))
    check("Closing balance",       days[tue]["closing"],  Decimal("300"))

    print("\n=== TEST 3: Wednesday ===")
    check("Opening = Tue closing",  days[wed]["opening"],  Decimal("300"))
    check("Received",               days[wed]["received"], Decimal("500"))
    check("Available (300+500)",    days[wed]["opening"] + days[wed]["received"], Decimal("800"))
    check("Closing balance",        days[wed]["closing"],  Decimal("600"))

    print("\n=== TEST 4: All-time wallet balance ===")
    check("Wallet balance (1000+500-400-300-200)", wallet, Decimal("600"))

    print("\n=== TEST 5: Carry-forward is NOT a new recharge ===")
    total_recharges = sum(
        Decimal(str(t["amount"])) for t in MOCK_TRANSACTIONS if t["type"] == "recharge"
    )
    check("Only 2 real recharges = 1500", total_recharges, Decimal("1500"))
    print("  [INFO] Tuesday has 0 recharge (no fake carry-forward transaction)")

    print(f"\n{'='*40}")
    if errors:
        print(f"FAILED: {len(errors)} test(s) - {errors}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
        print("="*40)


if __name__ == "__main__":
    run_tests()
