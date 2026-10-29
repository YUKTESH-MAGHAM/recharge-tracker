from pydantic import BaseModel, field_validator
from typing import Optional
from decimal import Decimal
import uuid


class TransactionCreate(BaseModel):
    type: str          # "recharge" | "expense"
    name: str
    amount: Decimal

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("recharge", "expense"):
            raise ValueError("type must be 'recharge' or 'expense'")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return round(v, 2)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty")
        return v


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    type: str
    name: str
    amount: Decimal
    created_at: str


class BalanceSummary(BaseModel):
    wallet_balance: Decimal       # all-time balance
    today_received: Decimal
    today_spent: Decimal
    today_opening: Decimal
    today_closing: Decimal


class DailyLedgerEntry(BaseModel):
    date: str                     # YYYY-MM-DD in IST
    opening_balance: Decimal
    transactions: list
    total_received: Decimal
    total_spent: Decimal
    closing_balance: Decimal


class WeeklyReport(BaseModel):
    week_start: str
    week_end: str
    opening_balance: Decimal
    total_received: Decimal
    total_available: Decimal
    total_spent: Decimal
    closing_balance: Decimal


class MonthlyReport(BaseModel):
    year: int
    month: int
    month_label: str
    opening_balance: Decimal
    total_received: Decimal
    total_available: Decimal
    total_spent: Decimal
    closing_balance: Decimal
