"""IOS-006：伺服器拒絕的金額，和 Android 的 APP-006、網頁的 WEB-006 是同一組行為。"""
import pytest

from testdata.factories import funded_wallet
from testdata.messages import ERROR_TEXT

pytestmark = pytest.mark.ios


@pytest.mark.business
@pytest.mark.case_id("IOS-006")
def test_payment_above_the_balance_is_refused(app, api, db):
    wallet = funded_wallet(api, "20.00")

    confirm = app.open_wallet(wallet).go_pay().continue_with("50")
    confirm.confirm()

    confirm.expect_text("error-message", ERROR_TEXT["INSUFFICIENT_BALANCE"])
    assert db.count("payments", "wallet_id = ?", wallet) == 0
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 2000
    # 被拒絕後可以回去改金額，原本輸入的還在
    pay = confirm.change_amount()
    pay.expect_text("amount-input", "50")
