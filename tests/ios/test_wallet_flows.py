"""IOS-001、003：iOS App 上的主要流程，和 Android 的 APP-001、003、網頁的 WEB-001、003 是同一組行為。
畫面對了還不算，資料庫也要對。"""
import re

import pytest

from framework.ios.base import MINUS
from testdata.factories import funded_wallet

pytestmark = pytest.mark.ios

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@pytest.mark.case_id("IOS-001")
def test_new_wallet_starts_at_zero(app, proxy, db):
    home = app.create_wallet("Alex")

    home.expect_text("owner", "Alex")
    home.expect_text("balance", "0.00")
    home.expect_shown("recent-empty")
    # 畫面上的編號是遮罩過的（D-04）：完整的編號從 App 收到的那個回應拿
    created = proxy.exchanges("/wallets")
    assert [e.status for e in created] == [201], created
    row = db.one("SELECT owner, balance FROM wallets WHERE wallet_id = ?", created[0].body["wallet_id"])
    assert (row["owner"], row["balance"]) == ("Alex", 0)


@pytest.mark.idempotency
@pytest.mark.case_id("IOS-003")
def test_payment_goes_through_confirm_to_receipt_and_home(app, api, db, proxy):
    wallet = funded_wallet(api, "100.00")

    confirm = app.open_wallet(wallet).go_pay().continue_with("30")
    confirm.expect_text("confirm-amount", "30.00")
    confirm.expect_text("confirm-balance-after", "70.00")
    assert proxy.keys("/payments") == [], "nothing may be sent before Confirm"
    assert db.count("payments", "wallet_id = ?", wallet) == 0

    receipt = confirm.confirm_and_wait()
    # K-01：按下確認時產生一把 UUID v4 的 Idempotency-Key，只送一次
    keys = proxy.keys("/payments")
    assert len(keys) == 1 and UUID4.match(keys[0] or ""), keys
    receipt.expect_text("result-amount", "30.00")
    receipt.expect_text("result-balance", "70.00")

    # 還沒有交易紀錄畫面（第一階段）：回到首頁看餘額和最近活動的第一列
    home = receipt.done()
    home.expect_text("balance", "70.00")
    first = home.recent_rows()[0]
    assert (first.title, first.amount, first.balance) == ("Payment", f"{MINUS}30.00", "70.00")
    assert [r["amount"] for r in db.all("SELECT amount FROM payments WHERE wallet_id = ?", wallet)] == [3000]
