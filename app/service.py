"""商業規則。路由（main.py）只負責收發 HTTP，規則都寫在這裡。"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone

from app import bugs
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
    if bugs.on("race"):
        time.sleep(0.05)                  # bug: 讀完餘額後拖一下才寫回，別的請求讀到的是舊餘額
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


# ---- 冪等 ----------------------------------------------------------------------

def request_hash(body: dict) -> str:
    """請求內容的指紋：同一把 key 配上不同內容，指紋就不同。"""
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def check_idempotency(conn: sqlite3.Connection, scope: str, key: str, body: dict) -> tuple[int, dict] | None:
    """在寫入交易裡呼叫。這把 key 用過就回 (狀態碼, 當初的回應)；沒用過回 None。"""
    if bugs.on("no_idempotency"):
        return None                       # bug: 每次都當成新請求
    row = conn.execute("SELECT * FROM idempotency_keys WHERE scope = ? AND idem_key = ?",
                       (scope, key)).fetchone()
    if row is None:
        return None
    if row["request_hash"] != request_hash(body):
        raise ApiError(422, "IDEMPOTENCY_KEY_REUSED",
                       "this Idempotency-Key was already used with a different request")
    return row["status_code"], json.loads(row["response"])


def require_key(key: str | None) -> str:
    if not key or len(key) > 64:
        raise ApiError(400, "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key header (1-64 chars) is required")
    return key


def require_wallet_id(raw: object) -> str:
    if not isinstance(raw, str) or not raw:
        raise ApiError(400, "INVALID_REQUEST", "wallet_id must be a non-empty string")
    return raw


def save_idempotency(conn: sqlite3.Connection, scope: str, key: str, body: dict,
                     status_code: int, response: dict) -> None:
    if bugs.on("no_idempotency"):
        return
    conn.execute("INSERT INTO idempotency_keys VALUES (?, ?, ?, ?, ?, ?)",
                 (scope, key, request_hash(body), status_code, json.dumps(response), now()))


# ---- 付款 ----------------------------------------------------------------------

MAX_SINGLE_PAYMENT = 5_000_000          # 單筆上限 50,000.00（分）


def payment_view(row: sqlite3.Row, balance_after: int | None = None) -> dict:
    view = {"payment_id": row["payment_id"], "wallet_id": row["wallet_id"],
            "amount": format_cents(row["amount"]), "refunded": format_cents(row["refunded"]),
            "created_at": row["created_at"]}
    if balance_after is not None:
        view["balance_after"] = format_cents(balance_after)
    return view


def pay(conn: sqlite3.Connection, key: str | None, body: dict) -> tuple[int, dict, bool]:
    """回傳 (狀態碼, 回應, 是否為重送)。

    查 key、扣款、記住 key 三件事在同一個交易裡：
    - 兩個相同 key 的請求同時到，第二個會等第一個 COMMIT 後才查 key，看到「用過了」
    - 扣款失敗（例如餘額不足）整個 ROLLBACK，key 不會被記住，客人儲值後可以用同一把 key 再試
    """
    key = require_key(key)
    wallet_id = require_wallet_id(body.get("wallet_id"))
    cents = parse_amount(body.get("amount"))
    if cents > MAX_SINGLE_PAYMENT:
        raise ApiError(422, "LIMIT_EXCEEDED", "single payment limit is 50000.00")
    with write_tx(conn):
        seen = check_idempotency(conn, "payment", key, body)
        if seen:
            return seen[0], seen[1], True
        payment_id = new_id("p")
        balance = apply_entry(conn, wallet_id, -cents, "PAYMENT", payment_id)
        conn.execute("INSERT INTO payments (payment_id, wallet_id, amount, created_at) VALUES (?, ?, ?, ?)",
                     (payment_id, wallet_id, cents, now()))
        row = conn.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,)).fetchone()
        response = payment_view(row, balance)
        save_idempotency(conn, "payment", key, body, 201, response)
    return 201, response, False


def get_payment(conn: sqlite3.Connection, payment_id: str) -> dict:
    row = conn.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,)).fetchone()
    if row is None:
        raise ApiError(404, "PAYMENT_NOT_FOUND", f"payment {payment_id} does not exist")
    view = payment_view(row)
    view["refunds"] = [{"refund_id": r["refund_id"], "amount": format_cents(r["amount"]),
                        "created_at": r["created_at"]}
                       for r in conn.execute("SELECT * FROM refunds WHERE payment_id = ? ORDER BY rowid",
                                             (payment_id,))]
    return view


# ---- 退款 ----------------------------------------------------------------------

def refund(conn: sqlite3.Connection, key: str | None, payment_id: str, body: dict) -> tuple[int, dict, bool]:
    """退款：可以分很多次，但累計不能超過原付款。冪等的做法跟付款一樣。"""
    key = require_key(key)
    cents = parse_amount(body.get("amount"))
    fingerprint = {"payment_id": payment_id, "amount": body.get("amount")}
    with write_tx(conn):
        seen = check_idempotency(conn, "refund", key, fingerprint)
        if seen:
            return seen[0], seen[1], True
        payment = conn.execute("SELECT * FROM payments WHERE payment_id = ?", (payment_id,)).fetchone()
        if payment is None:
            raise ApiError(404, "PAYMENT_NOT_FOUND", f"payment {payment_id} does not exist")
        # 「已退累計」在鎖住的交易裡讀：同時來的另一筆退款，要等這筆做完才讀得到
        refundable = payment["amount"] - payment["refunded"]
        if bugs.on("refund_overflow"):
            refundable = payment["amount"]          # bug: 忘了扣掉已退的部分
        if cents > refundable:
            raise ApiError(409, "REFUND_EXCEEDS_PAYMENT",
                           f"only {format_cents(refundable)} of this payment can still be refunded")
        refund_id, created_at = new_id("r"), now()
        conn.execute("INSERT INTO refunds (refund_id, payment_id, amount, created_at) VALUES (?, ?, ?, ?)",
                     (refund_id, payment_id, cents, created_at))
        conn.execute("UPDATE payments SET refunded = refunded + ? WHERE payment_id = ?", (cents, payment_id))
        balance = apply_entry(conn, payment["wallet_id"], cents, "REFUND", refund_id)
        response = {"refund_id": refund_id, "payment_id": payment_id, "amount": format_cents(cents),
                    "payment_refunded": format_cents(payment["refunded"] + cents),
                    "payment_refundable": format_cents(refundable - cents),
                    "balance_after": format_cents(balance), "created_at": created_at}
        save_idempotency(conn, "refund", key, fingerprint, 201, response)
    return 201, response, False


# ---- 交易紀錄 ------------------------------------------------------------------

def transactions(conn: sqlite3.Connection, wallet_id: str) -> dict:
    get_wallet_row(conn, wallet_id)                    # 錢包不存在就 404
    rows = conn.execute("SELECT * FROM ledger WHERE wallet_id = ? ORDER BY entry_id", (wallet_id,))
    return {"wallet_id": wallet_id,
            "transactions": [{"entry_id": r["entry_id"], "type": r["type"],
                              "amount": format_cents(r["amount"]),
                              "balance_after": format_cents(r["balance_after"]),
                              "ref_id": r["ref_id"], "created_at": r["created_at"]} for r in rows]}


# ---- 轉帳 ----------------------------------------------------------------------

def transfer(conn: sqlite3.Connection, key: str | None, body: dict) -> tuple[int, dict, bool]:
    """錢包之間轉帳：扣款和入帳在同一個交易裡，要嘛都成功，要嘛都沒發生。"""
    key = require_key(key)
    from_id = require_wallet_id(body.get("from_wallet_id"))
    to_id = require_wallet_id(body.get("to_wallet_id"))
    cents = parse_amount(body.get("amount"))
    if from_id == to_id:
        raise ApiError(422, "SAME_WALLET", "cannot transfer to the same wallet")
    if cents > MAX_SINGLE_PAYMENT:
        raise ApiError(422, "LIMIT_EXCEEDED", "single transfer limit is 50000.00")
    transfer_id, created_at = new_id("x"), now()

    if bugs.on("transfer_not_atomic"):
        # bug: 扣款先自己提交，入帳另開交易；入帳失敗時扣掉的錢不會回來
        with write_tx(conn):
            seen = check_idempotency(conn, "transfer", key, body)
            if seen:
                return seen[0], seen[1], True
            from_balance = apply_entry(conn, from_id, -cents, "TRANSFER_OUT", transfer_id)
        with write_tx(conn):
            apply_entry(conn, to_id, cents, "TRANSFER_IN", transfer_id)
            conn.execute("INSERT INTO transfers VALUES (?, ?, ?, ?, ?)", (transfer_id, from_id, to_id, cents, created_at))
            response = transfer_view(transfer_id, from_id, to_id, cents, from_balance, created_at)
            save_idempotency(conn, "transfer", key, body, 201, response)
        return 201, response, False

    with write_tx(conn):
        seen = check_idempotency(conn, "transfer", key, body)
        if seen:
            return seen[0], seen[1], True
        get_wallet_row(conn, to_id)                       # 收款錢包先確認存在
        from_balance = apply_entry(conn, from_id, -cents, "TRANSFER_OUT", transfer_id)
        apply_entry(conn, to_id, cents, "TRANSFER_IN", transfer_id)
        conn.execute("INSERT INTO transfers VALUES (?, ?, ?, ?, ?)", (transfer_id, from_id, to_id, cents, created_at))
        response = transfer_view(transfer_id, from_id, to_id, cents, from_balance, created_at)
        save_idempotency(conn, "transfer", key, body, 201, response)
    return 201, response, False


def transfer_view(transfer_id: str, from_id: str, to_id: str, cents: int, from_balance: int, created_at: str) -> dict:
    return {"transfer_id": transfer_id, "from_wallet_id": from_id, "to_wallet_id": to_id,
            "amount": format_cents(cents), "from_balance_after": format_cents(from_balance),
            "created_at": created_at}
