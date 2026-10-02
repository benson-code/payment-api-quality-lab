"""G. 資料庫驗證：每條 SQL 都在找「不該存在的資料」，查到任何一列就是 bug。"""
import shutil
import sqlite3

import pytest

from framework.db import INVARIANTS, Database
from testdata.factories import funded_wallet, paid

pytestmark = pytest.mark.db


@pytest.fixture
def busy_ledger(api):
    """先製造各種交易：付款、部分退款、全額退款、轉帳、失敗的請求。"""
    w1, p1 = paid(api, "100.00")
    api.refund(p1, "40.00")
    api.refund(p1, "60.00")
    api.refund(p1, "0.01")                     # 應該被擋
    w2 = funded_wallet(api, "50.00")
    api.pay(w2, "50.01")                       # 應該被擋
    api.transfer(w2, w1, "20.00")
    api.transfer(w2, "w_missing", "1.00")      # 應該被擋


@pytest.mark.case_id("DB-001")
@pytest.mark.parametrize("name", list(INVARIANTS))
def test_invariant_holds(busy_ledger, db, name):
    assert db.violations(name) == [], f"{name} 查到不該存在的資料"


@pytest.mark.case_id("DB-005")
def test_every_invariant_can_actually_fail(api, db, tmp_path):
    """一條永遠查不到東西的 SQL，可能是資料真的對，也可能是 SQL 寫錯。

    把資料庫複製一份，故意弄髒，確認每一條都抓得到。
    """
    w, p = paid(api, "100.00")
    a, b = funded_wallet(api, "10.00"), funded_wallet(api, "0.00")
    api.transfer(a, b, "5.00")
    copy = tmp_path / "dirty.db"
    with sqlite3.connect(copy) as dst:
        db.conn.backup(dst)
    dirty = Database(str(copy))
    c = dirty.conn
    c.execute("UPDATE wallets SET balance = balance + 1 WHERE wallet_id = ?", (w,))          # 餘額 ≠ ledger
    c.execute("UPDATE wallets SET balance = -5 WHERE wallet_id = ?", (b,))                  # 負餘額
    c.execute("INSERT INTO refunds VALUES ('r_dirty', ?, 99999, 'now')", (p,))              # 超退、累計欄位對不上
    c.execute("DELETE FROM ledger WHERE ref_id = ? AND type = 'PAYMENT'", (p,))             # 付款沒有 ledger
    c.execute("DELETE FROM ledger WHERE wallet_id = ? AND type = 'TRANSFER_IN'", (b,))      # 轉帳只剩一半
    c.execute("INSERT INTO ledger (wallet_id, type, amount, balance_after, ref_id, created_at)"
              " VALUES (?, 'TRANSFER_OUT', -1, 0, 'x_ghost', 'now')", (a,))                 # 落單的轉帳 ledger
    try:
        for name in INVARIANTS:
            assert dirty.violations(name), f"{name} 沒抓到故意弄髒的資料"
    finally:
        dirty.close()
