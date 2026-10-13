"""IOS-005、006：API 不接受的金額、餘額不足，和 Android 的 APP-005、006、網頁的 WEB-005、006 是同一組行為。"""
import pytest

from testdata.factories import funded_wallet
from testdata.messages import ERROR_TEXT

pytestmark = pytest.mark.ios


@pytest.mark.validation
@pytest.mark.parametrize("amount", [
    pytest.param("10.555", id="three-decimals"),
    # API 的整數最多 12 位，13 位以上照輸入顯示（R-04，三端同一個規則）
    pytest.param("1000000000000", id="13-digits"),
    pytest.param("99999999999999999999", id="20-digits"),
])
@pytest.mark.case_id("IOS-005")
def test_invalid_amount_is_refused_and_nothing_moves(app, api, db, amount):
    """只有數字和小數點：iOS 的小數鍵盤沒有負號、e 和空白，APP-005 的另外三個輸入打不出來。"""
    wallet = funded_wallet(api, "100.00")

    confirm = app.open_wallet(wallet).go_pay().continue_with(amount)
    confirm.expect_text("confirm-amount", amount)
    confirm.expect_absent("confirm-balance-after")
    confirm.confirm()

    confirm.expect_text("error-message", ERROR_TEXT["INVALID_AMOUNT"])
    assert db.count("payments", "wallet_id = ?", wallet) == 0
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 10000


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
