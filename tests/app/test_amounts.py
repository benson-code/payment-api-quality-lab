"""APP-004～006：金額精度、不合法的金額、餘額不足，和網頁的 WEB-004～006 是同一組行為。

金額對不對由 API 決定（R-02），App 只負責把結果講清楚，而且被拒絕時一分錢都不能動。
"""
import pytest

from testdata.factories import funded_wallet
from testdata.messages import ERROR_TEXT

pytestmark = pytest.mark.app


@pytest.mark.precision
@pytest.mark.case_id("APP-004")
def test_top_up_19_99_keeps_every_cent(app, api, db):
    """19.99 用浮點數乘 100 是 1998.9999…，取整數就少一分（埋 bug：float_math）。"""
    wallet = funded_wallet(api, "0.00")

    receipt = app.open_wallet(wallet).go_top_up().top_up("19.99")

    receipt.expect_text("result-amount", "19.99")
    receipt.expect_text("result-balance", "19.99")
    assert db.balance_cents(wallet) == 1999


@pytest.mark.validation
@pytest.mark.parametrize("amount", [
    pytest.param("-1", id="negative", marks=pytest.mark.negative),   # 埋 bug：negative_amount
    pytest.param("1e3", id="scientific"),
    pytest.param("10.555", id="three-decimals"),
    pytest.param(" 5 ", id="spaces"),     # API 不接受前後空白，確認頁也不能把它當成 5.00
])
@pytest.mark.case_id("APP-005")
def test_invalid_amount_is_refused_and_nothing_moves(app, api, db, amount):
    wallet = funded_wallet(api, "100.00")

    confirm = app.open_wallet(wallet).go_pay().continue_with(amount)
    # R-04：不是 API 會接受的寫法，就照輸入顯示，也不算付款後餘額
    confirm.expect_text("confirm-amount", amount)
    confirm.expect_absent("confirm-balance-after")
    confirm.confirm()

    confirm.expect_text("error-message", ERROR_TEXT["INVALID_AMOUNT"])
    assert db.count("payments", "wallet_id = ?", wallet) == 0
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 10000


@pytest.mark.business
@pytest.mark.case_id("APP-006")
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
