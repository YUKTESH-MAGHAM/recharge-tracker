import os
import pytz
from decimal import Decimal
from datetime import date, datetime, timedelta
from pathlib import Path
from dateutil import parser as dateutil_parser

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from api.models import TransactionCreate, TransactionResponse, BalanceSummary
from api.auth import verify_token, security
from api.supabase_client import get_supabase_admin
from api.balance import (
    compute_balance_timeline,
    compute_weekly_report,
    compute_monthly_report,
    utc_to_ist_date,
    IST,
)

app = FastAPI(title="Recharge Tracker API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILES — icons, manifest, sw, css, js
# SPA catch-all (/) is registered LAST so /api/* routes always win
# ─────────────────────────────────────────────────────────────────────────────
_PUBLIC_DIR = Path(__file__).parent.parent / "public"

if _PUBLIC_DIR.exists():
    app.mount("/icons", StaticFiles(directory=str(_PUBLIC_DIR / "icons")), name="icons")

    @app.get("/manifest.json", include_in_schema=False)
    def serve_manifest():
        return FileResponse(str(_PUBLIC_DIR / "manifest.json"))

    @app.get("/sw.js", include_in_schema=False)
    def serve_sw():
        return FileResponse(str(_PUBLIC_DIR / "sw.js"))

    @app.get("/style.css", include_in_schema=False)
    def serve_css():
        return FileResponse(str(_PUBLIC_DIR / "style.css"))

    @app.get("/app.js", include_in_schema=False)
    def serve_appjs():
        return FileResponse(str(_PUBLIC_DIR / "app.js"))


# ─────────────────────────────────────────────────────────────────────────────
# SHARED HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_all_transactions(user_id: str) -> list:
    """Fetch every transaction for a user, ordered by created_at ASC."""
    client = get_supabase_admin()
    result = (
        client.table("transactions")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data or []


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# BALANCE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/balance")
def get_balance(user_id: str = Depends(verify_token)):
    """Return wallet balance + today's summary (IST)."""
    txns = _fetch_all_transactions(user_id)
    timeline = compute_balance_timeline(txns)
    days = timeline["days"]
    wallet_balance = timeline["wallet_balance"]

    today_ist = datetime.now(IST).date()

    if today_ist in days:
        today_data = days[today_ist]
    else:
        # No transactions today — opening equals current wallet balance
        today_data = {
            "opening":  wallet_balance,
            "received": Decimal("0"),
            "spent":    Decimal("0"),
            "closing":  wallet_balance,
        }

    return {
        "wallet_balance":  float(wallet_balance),
        "today_received":  float(today_data["received"]),
        "today_spent":     float(today_data["spent"]),
        "today_opening":   float(today_data["opening"]),
        "today_closing":   float(today_data["closing"]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTIONS — CREATE
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/transactions", status_code=201)
def create_transaction(body: TransactionCreate, user_id: str = Depends(verify_token)):
    """
    Create a new transaction.
    For expenses, checks that the wallet has enough balance.
    user_id is always taken from the verified JWT — never from the request body.
    """
    txns = _fetch_all_transactions(user_id)
    timeline = compute_balance_timeline(txns)
    wallet_balance = timeline["wallet_balance"]

    if body.type == "expense" and body.amount > wallet_balance:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient balance. Available: {wallet_balance:.2f}, Requested: {body.amount:.2f}"
        )

    client = get_supabase_admin()
    result = client.table("transactions").insert({
        "user_id": user_id,
        "type":    body.type,
        "name":    body.name,
        "amount":  float(body.amount),
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to save transaction")

    return result.data[0]


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTIONS — LIST
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/transactions")
def list_transactions(user_id: str = Depends(verify_token)):
    return _fetch_all_transactions(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTIONS — DELETE
# ─────────────────────────────────────────────────────────────────────────────

@app.delete("/api/transactions/{txn_id}", status_code=204)
def delete_transaction(txn_id: str, user_id: str = Depends(verify_token)):
    client = get_supabase_admin()
    check = (
        client.table("transactions")
        .select("id")
        .eq("id", txn_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Transaction not found")
    client.table("transactions").delete().eq("id", txn_id).execute()
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DAILY LEDGER
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/reports/daily")
def daily_ledger(user_id: str = Depends(verify_token)):
    """
    Return all days newest-first.
    Each day has transactions sorted oldest-first within the day.
    """
    txns = _fetch_all_transactions(user_id)
    timeline = compute_balance_timeline(txns)
    days = timeline["days"]

    result = []
    for d in sorted(days.keys(), reverse=True):
        day_data = days[d]
        txn_list = []
        for t in day_data["txns"]:
            dt_utc = dateutil_parser.parse(t["created_at"])
            if dt_utc.tzinfo is None:
                dt_utc = pytz.utc.localize(dt_utc)
            dt_ist = dt_utc.astimezone(IST)
            txn_list.append({
                "id":         t["id"],
                "type":       t["type"],
                "name":       t["name"],
                "amount":     float(t["amount"]),
                "time_ist":   dt_ist.strftime("%I:%M %p"),
                "created_at": t["created_at"],
            })

        result.append({
            "date":            d.isoformat(),
            "date_label":      d.strftime("%A, %d %B %Y").upper(),
            "opening_balance": float(day_data["opening"]),
            "transactions":    txn_list,
            "total_received":  float(day_data["received"]),
            "total_spent":     float(day_data["spent"]),
            "closing_balance": float(day_data["closing"]),
        })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# WEEKLY REPORT
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/reports/weekly")
def weekly_report(
    week_start: str = Query(None, description="ISO date of any day in the target week (YYYY-MM-DD)"),
    user_id: str = Depends(verify_token),
):
    txns = _fetch_all_transactions(user_id)
    timeline = compute_balance_timeline(txns)
    days = timeline["days"]

    ref_date = date.fromisoformat(week_start) if week_start else datetime.now(IST).date()
    return compute_weekly_report(days, ref_date)


# ─────────────────────────────────────────────────────────────────────────────
# MONTHLY REPORT
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/reports/monthly")
def monthly_report(
    year:  int = Query(None),
    month: int = Query(None),
    user_id: str = Depends(verify_token),
):
    txns = _fetch_all_transactions(user_id)
    timeline = compute_balance_timeline(txns)
    days = timeline["days"]

    now_ist = datetime.now(IST)
    y = year  or now_ist.year
    m = month or now_ist.month

    if not (1 <= m <= 12):
        raise HTTPException(status_code=422, detail="month must be 1-12")

    return compute_monthly_report(days, y, m)


# ─────────────────────────────────────────────────────────────────────────────
# SPA FALLBACK — MUST be last so all /api/* routes above take priority
# ─────────────────────────────────────────────────────────────────────────────

if _PUBLIC_DIR.exists():
    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str = ""):
        return FileResponse(str(_PUBLIC_DIR / "index.html"))
