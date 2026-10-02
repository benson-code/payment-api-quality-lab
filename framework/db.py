"""測試直接連 SQLite：準備資料，以及驗證 API 做完之後資料庫的狀態。

API 回 201 只代表「API 說它成功了」，帳是不是真的對，要自己查。
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

# 每一條都是「應該查不到任何資料」的查詢：查到任何一列 = 有 bug
INVARIANTS = {
    # DB-001 錢包餘額必須等於 ledger 加總
    "balance_equals_ledger": """
        SELECT w.wallet_id, w.balance, COALESCE(SUM(l.amount), 0) AS ledger_sum
        FROM wallets w LEFT JOIN ledger l ON l.wallet_id = w.wallet_id
        GROUP BY w.wallet_id, w.balance
        HAVING w.balance <> COALESCE(SUM(l.amount), 0)""",
    # DB-002 沒有任何錢包是負餘額
    "no_negative_balance": """
        SELECT wallet_id, balance FROM wallets WHERE balance < 0""",
    # DB-003 每筆付款的退款加總不超過付款金額
    "refunds_within_payment": """
        SELECT p.payment_id, p.amount, SUM(r.amount) AS refunded
        FROM payments p JOIN refunds r ON r.payment_id = p.payment_id
        GROUP BY p.payment_id, p.amount
        HAVING SUM(r.amount) > p.amount""",
    # DB-003b 付款上的「已退累計」欄位必須等於退款紀錄加總（同一件事存了兩份，要一致）
    "refunded_column_matches": """
        SELECT p.payment_id, p.refunded, COALESCE(SUM(r.amount), 0) AS actual
        FROM payments p LEFT JOIN refunds r ON r.payment_id = p.payment_id
        GROUP BY p.payment_id, p.refunded
        HAVING p.refunded <> COALESCE(SUM(r.amount), 0)""",
    # DB-004 每一筆付款在 ledger 剛好有一筆扣款
    "one_ledger_entry_per_payment": """
        SELECT p.payment_id, COUNT(l.entry_id) AS entries
        FROM payments p LEFT JOIN ledger l ON l.ref_id = p.payment_id AND l.type = 'PAYMENT'
        GROUP BY p.payment_id
        HAVING COUNT(l.entry_id) <> 1""",
    # DB-007 每一筆轉帳：轉出與轉入金額相同，兩邊都有記錄
    "transfers_balanced": """
        SELECT t.transfer_id
        FROM transfers t
        LEFT JOIN ledger o ON o.ref_id = t.transfer_id AND o.type = 'TRANSFER_OUT'
        LEFT JOIN ledger i ON i.ref_id = t.transfer_id AND i.type = 'TRANSFER_IN'
        WHERE o.amount IS NULL OR i.amount IS NULL OR o.amount <> -t.amount OR i.amount <> t.amount""",
    # DB-007b 轉帳 ledger 不能落單（扣了錢卻沒有對應的轉帳紀錄）
    "no_orphan_transfer_entries": """
        SELECT l.entry_id, l.ref_id FROM ledger l
        LEFT JOIN transfers t ON t.transfer_id = l.ref_id
        WHERE l.type IN ('TRANSFER_OUT', 'TRANSFER_IN') AND t.transfer_id IS NULL""",
}


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=10)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def one(self, sql: str, *params):
        return self.conn.execute(sql, params).fetchone()

    def all(self, sql: str, *params) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    # ---- 查詢 --------------------------------------------------------------------

    def balance_cents(self, wallet_id: str) -> int:
        return self.one("SELECT balance FROM wallets WHERE wallet_id = ?", wallet_id)["balance"]

    def ledger_sum_cents(self, wallet_id: str) -> int:
        return self.one("SELECT COALESCE(SUM(amount), 0) AS s FROM ledger WHERE wallet_id = ?",
                        wallet_id)["s"]

    def count(self, table: str, where: str = "1=1", *params) -> int:
        return self.one(f"SELECT COUNT(*) AS n FROM {table} WHERE {where}", *params)["n"]

    def violations(self, name: str) -> list[tuple]:
        return [tuple(r) for r in self.all(INVARIANTS[name])]

    # ---- 用 SQL 準備資料 ---------------------------------------------------------

    def seed_wallet(self, balance_cents: int, owner: str = "seeded") -> str:
        """直接寫資料庫建一個有錢的錢包：比打 API 儲值快，也不受單筆限額影響。

        一定同時寫一筆 ledger，否則資料本身就違反「餘額 = ledger 加總」。
        """
        wallet_id = f"w_seed{uuid.uuid4().hex[:12]}"
        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        self.conn.execute("BEGIN IMMEDIATE")
        self.conn.execute("INSERT INTO wallets (wallet_id, owner, balance, created_at) VALUES (?, ?, ?, ?)",
                          (wallet_id, owner, balance_cents, ts))
        self.conn.execute("INSERT INTO ledger (wallet_id, type, amount, balance_after, ref_id, created_at)"
                          " VALUES (?, 'TOPUP', ?, ?, 'seed', ?)", (wallet_id, balance_cents, balance_cents, ts))
        self.conn.execute("COMMIT")
        return wallet_id
