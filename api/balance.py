from decimal import Decimal
from datetime import date, datetime, timedelta
import pytz
from dateutil import parser as dateutil_parser

IST = pytz.timezone("Asia/Kolkata")


def utc_to_ist_date(utc_str: str) -> date:
    """
    Convert a UTC ISO string to an IST date.
    Uses dateutil.parser to handle any number of fractional seconds
    (Supabase can return 5, 6 or other digit counts).
    """
    dt = dateutil_parser.parse(utc_str)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(IST).date()


def compute_balance_timeline(transactions: list) -> dict:
    """
    Given a flat list of transaction dicts (sorted by created_at ASC),
    compute per-day opening/closing balances and an all-time wallet balance.

    Returns:
        {
          "wallet_balance": Decimal,
          "days": {
            date: {
              "opening": Decimal,
              "closing": Decimal,
              "received": Decimal,
              "spent": Decimal,
              "txns": [...]
            }
          }
        }
    """
    # Group by IST date
    from collections import defaultdict
    daily: dict = defaultdict(lambda: {
        "received": Decimal("0"),
        "spent": Decimal("0"),
        "txns": []
    })

    for txn in transactions:
        d = utc_to_ist_date(txn["created_at"])
        amt = Decimal(str(txn["amount"]))
        if txn["type"] == "recharge":
            daily[d]["received"] += amt
        else:
            daily[d]["spent"] += amt
        daily[d]["txns"].append(txn)

    # Walk dates in chronological order
    if not daily:
        return {"wallet_balance": Decimal("0"), "days": {}}

    sorted_dates = sorted(daily.keys())
    running_balance = Decimal("0")
    result = {}

    for d in sorted_dates:
        opening = running_balance
        received = daily[d]["received"]
        spent = daily[d]["spent"]
        closing = opening + received - spent
        result[d] = {
            "opening": opening,
            "received": received,
            "spent": spent,
            "closing": closing,
            "txns": sorted(daily[d]["txns"], key=lambda t: t["created_at"]),
        }
        running_balance = closing

    return {"wallet_balance": running_balance, "days": result}


def get_week_bounds(week_start_date: date) -> tuple[date, date]:
    """Return (monday, sunday) for the week containing week_start_date."""
    monday = week_start_date - timedelta(days=week_start_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def compute_weekly_report(days: dict, week_start: date) -> dict:
    monday, sunday = get_week_bounds(week_start)

    # Opening balance = closing of the day before monday (or 0)
    pre_dates = [d for d in days if d < monday]
    if pre_dates:
        opening = days[max(pre_dates)]["closing"]
    else:
        opening = Decimal("0")

    week_received = Decimal("0")
    week_spent = Decimal("0")
    d = monday
    while d <= sunday:
        if d in days:
            week_received += days[d]["received"]
            week_spent += days[d]["spent"]
        d += timedelta(days=1)

    total_available = opening + week_received
    closing = total_available - week_spent

    return {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "opening_balance": opening,
        "total_received": week_received,
        "total_available": total_available,
        "total_spent": week_spent,
        "closing_balance": closing,
    }


def compute_monthly_report(days: dict, year: int, month: int) -> dict:
    from calendar import monthrange
    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])

    # Opening balance = closing of day before month_start (or 0)
    pre_dates = [d for d in days if d < month_start]
    if pre_dates:
        opening = days[max(pre_dates)]["closing"]
    else:
        opening = Decimal("0")

    month_received = Decimal("0")
    month_spent = Decimal("0")
    d = month_start
    while d <= month_end:
        if d in days:
            month_received += days[d]["received"]
            month_spent += days[d]["spent"]
        d += timedelta(days=1)

    total_available = opening + month_received
    closing = total_available - month_spent

    import calendar
    return {
        "year": year,
        "month": month,
        "month_label": f"{calendar.month_name[month]} {year}",
        "opening_balance": opening,
        "total_received": month_received,
        "total_available": total_available,
        "total_spent": month_spent,
        "closing_balance": closing,
    }
