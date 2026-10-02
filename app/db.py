"""SQLite：建表、開連線、寫入用的交易。

所有金額欄位都是 INTEGER（單位：分）。
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS wallets (
    wallet_id   TEXT PRIMARY KEY,
    owner       TEXT NOT NULL,
    currency    TEXT NOT NULL DEFAULT 'TWD',
    balance     INTEGER NOT NULL DEFAULT 0,       -- 分
    created_at  TEXT NOT NULL
);

-- 每一筆餘額變動都記一筆：儲值為正、付款為負。錢包餘額必須等於這裡的加總。
CREATE TABLE IF NOT EXISTS ledger (
    entry_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id      TEXT NOT NULL REFERENCES wallets(wallet_id),
    type           TEXT NOT NULL,                  -- TOPUP / PAYMENT / REFUND / TRANSFER_OUT / TRANSFER_IN
    amount         INTEGER NOT NULL,               -- 分，有正負
    balance_after  INTEGER NOT NULL,               -- 分
    ref_id         TEXT,                           -- 對應的付款、退款或轉帳編號
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id   TEXT PRIMARY KEY,
    wallet_id    TEXT NOT NULL REFERENCES wallets(wallet_id),
    amount       INTEGER NOT NULL,                 -- 分
    refunded     INTEGER NOT NULL DEFAULT 0,       -- 已退款累計（分）
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_id    TEXT PRIMARY KEY,
    payment_id   TEXT NOT NULL REFERENCES payments(payment_id),
    amount       INTEGER NOT NULL,                 -- 分
    created_at   TEXT NOT NULL
);

-- 用過的 Idempotency-Key：同一把 key 再來，就回當初的結果，不再做一次
CREATE TABLE IF NOT EXISTS idempotency_keys (
    scope         TEXT NOT NULL,                   -- 哪一支 API：payment / refund
    idem_key      TEXT NOT NULL,
    request_hash  TEXT NOT NULL,                   -- 當初請求內容的指紋
    status_code   INTEGER NOT NULL,
    response      TEXT NOT NULL,                   -- 當初回應的 JSON
    created_at    TEXT NOT NULL,
    PRIMARY KEY (scope, idem_key)
);
"""


def connect(db_path: str) -> sqlite3.Connection:
    # 每個請求自己開一條連線；isolation_level=None 代表交易由我們自己用 BEGIN 控制。
    # FastAPI 可能在不同執行緒開、關同一條連線，所以關掉 check_same_thread；
    # 一條連線只服務一個請求，不會被兩個執行緒同時使用。
    conn = sqlite3.connect(db_path, isolation_level=None, timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")         # 讀寫可以同時進行
    conn.executescript(SCHEMA)
    conn.close()


@contextmanager
def write_tx(conn: sqlite3.Connection):
    """寫入用的交易。

    BEGIN IMMEDIATE 一開始就拿到寫入鎖：兩個請求同時要扣同一個錢包時，
    第二個會等第一個做完，才讀到正確的餘額。中途出錯就整個 ROLLBACK。
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
