"""商業規則。路由（main.py）只負責收發 HTTP，規則都寫在這裡。"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from app.db import write_tx
from app.errors import ApiError
from app.money import format_cents, parse_amount


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


# ---- 錢包 --------------------------------------------------------------------

def wallet_view(row: sqlite3.Row) -> dict:
    return {"wallet_id": row["wallet_id"], "owner": row["owner"], "currency": row["currency"],
            "balance": format_cents(row["balance"]), "created_at": row["created_at"]}


def get_wallet_row(conn: sqlite3.Connection, wallet_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM wallets WHERE wallet_id = ?", (wallet_id,)).fetchone()
    if row is None:
        raise ApiError(404, "WALLET_NOT_FOUND", f"wallet {wallet_id} does not exist")
    return row


def create_wallet(conn: sqlite3.Connection, owner: str) -> dict:
    owner = owner.strip()
    if not 1 <= len(owner) <= 50:
        raise ApiError(400, "INVALID_OWNER", "owner must be 1-50 characters")
    wallet_id = new_id("w")
    with write_tx(conn):
        conn.execute("INSERT INTO wallets (wallet_id, owner, created_at) VALUES (?, ?, ?)",
                     (wallet_id, owner, now()))
    return wallet_view(get_wallet_row(conn, wallet_id))


# ---- 餘額變動：所有加錢、扣錢都必須走這一個函式 -----------------------------

def apply_entry(conn: sqlite3.Connection, wallet_id: str, amount: int,
                entry_type: str, ref_id: str | None) -> int:
    """在「已經開好的寫入交易」裡改餘額並記一筆 ledger。回傳變動後餘額（分）。

    集中在一個地方，是為了保證：錢包餘額 永遠等於 ledger 加總。
    """
    balance = get_wallet_row(conn, wallet_id)["balance"] + amount
    if balance < 0:
        raise ApiError(409, "INSUFFICIENT_BALANCE", "wallet balance is not enough")
    conn.execute("UPDATE wallets SET balance = ? WHERE wallet_id = ?", (balance, wallet_id))
    conn.execute("INSERT INTO ledger (wallet_id, type, amount, balance_after, ref_id, created_at)"
                 " VALUES (?, ?, ?, ?, ?, ?)", (wallet_id, entry_type, amount, balance, ref_id, now()))
    return balance


def top_up(conn: sqlite3.Connection, wallet_id: str, raw_amount: object) -> dict:
    cents = parse_amount(raw_amount)
    topup_id = new_id("t")
    with write_tx(conn):
        balance = apply_entry(conn, wallet_id, cents, "TOPUP", topup_id)
    return {"topup_id": topup_id, "wallet_id": wallet_id,
            "amount": format_cents(cents), "balance": format_cents(balance)}
