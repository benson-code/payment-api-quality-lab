"""WEB-010：交易紀錄的每一筆都要和資料庫的 ledger 一致：順序、類型、金額、變動後餘額。"""
import pytest

from framework.web.base import MINUS
from framework.web.history_page import HistoryPage, HistoryRow
from testdata.factories import funded_wallet

pytestmark = pytest.mark.web


def money(cents: int) -> str:
    """預期值自己從整數分算出來，不呼叫前端的格式化程式：12345 -> "123.45"。"""
    return f"{abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def signed(cents: int) -> str:
    return ("+" if cents >= 0 else MINUS) + money(cents)


@pytest.mark.db
@pytest.mark.case_id("WEB-010")
def test_history_matches_the_ledger(page, app_url, api, db):
    wallet = funded_wallet(api, "100.00")
    payment_id = api.pay(wallet, "30.00").json()["payment_id"]
    api.refund(payment_id, "5.00")
    api.top_up(wallet, "1234.50")

    rows = HistoryPage(page, app_url).open(wallet).rows()

    ledger = db.all("SELECT entry_id, type, amount, balance_after FROM ledger WHERE wallet_id = ? "
                    "ORDER BY entry_id DESC", wallet)
    assert rows == [HistoryRow(e["entry_id"], e["type"], signed(e["amount"]), money(e["balance_after"]))
                    for e in ledger]
    assert len(rows) == 4
