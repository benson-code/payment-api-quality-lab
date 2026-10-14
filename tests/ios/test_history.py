"""IOS-010：交易紀錄的每一筆都要和資料庫的 ledger 一致：順序、類型、金額、變動後餘額（和 APP-010、WEB-010
同一組行為）。

App 的列沒有網頁的 data-entry-id、data-type（SPEC.md §7），所以靠順序對照，類型看標題文字。
"""
import pytest

from framework.ios.base import MINUS
from framework.ios.history_screen import HistoryRow
from testdata.factories import funded_wallet
from testdata.messages import ENTRY_TITLE

pytestmark = pytest.mark.ios


def money(cents: int) -> str:
    """預期值自己從整數分算出來，不呼叫 App 的格式化程式：12345 -> "123.45"。"""
    return f"{abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def signed(cents: int) -> str:
    return ("+" if cents >= 0 else MINUS) + money(cents)


def expected_rows(db, wallet) -> list[HistoryRow]:
    ledger = db.all("SELECT type, amount, balance_after FROM ledger WHERE wallet_id = ? ORDER BY entry_id DESC", wallet)
    return [HistoryRow(ENTRY_TITLE[e["type"]], signed(e["amount"]), money(e["balance_after"])) for e in ledger]


@pytest.mark.db
@pytest.mark.case_id("IOS-010")
def test_history_matches_the_ledger(app, api, db):
    wallet = funded_wallet(api, "100.00")
    payment_id = api.pay(wallet, "30.00").json()["payment_id"]
    api.refund(payment_id, "5.00")
    api.top_up(wallet, "1234.50")

    rows = app.open_wallet(wallet).tab_history().rows()

    assert rows == expected_rows(db, wallet)
    assert len(rows) == 4


@pytest.mark.db
@pytest.mark.case_id("IOS-010")
def test_a_history_longer_than_the_screen_is_read_in_order(app, api, db):
    """一個畫面放不下的紀錄：畫面外的列也要讀到，順序和筆數都不能錯。"""
    wallet = funded_wallet(api, "1.00")
    for i in range(2, 13):
        api.top_up(wallet, f"{i}.00")

    rows = app.open_wallet(wallet).tab_history().rows()

    assert rows == expected_rows(db, wallet)
    assert len(rows) == 12
