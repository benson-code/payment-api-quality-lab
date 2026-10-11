"""WEB-004～006：金額精度、不合法的金額、餘額不足。

金額對不對由 API 決定（R-02），網頁只負責把結果講清楚，而且被拒絕時一分錢都不能動。
"""
import pytest
from playwright.sync_api import expect

from framework.web.pay_page import PayPage
from framework.web.top_up_page import TopUpPage
from testdata.factories import funded_wallet
from testdata.messages import ERROR_TEXT

pytestmark = pytest.mark.web


@pytest.mark.precision
@pytest.mark.case_id("WEB-004")
def test_top_up_19_99_keeps_every_cent(page, app_url, api, db):
    """19.99 用浮點數乘 100 是 1998.9999…，取整數就少一分（埋 bug：float_math）。"""
    wallet = funded_wallet(api, "0.00")

    receipt = TopUpPage(page, app_url).open(wallet).top_up("19.99")

    expect(receipt.tid("result-amount")).to_have_text("19.99")
    expect(receipt.tid("result-balance")).to_have_text("19.99")
    assert db.balance_cents(wallet) == 1999


@pytest.mark.validation
@pytest.mark.parametrize("amount", [
    pytest.param("-1", id="negative", marks=pytest.mark.negative),   # 埋 bug：negative_amount
    pytest.param("1e3", id="scientific"),
    pytest.param("10.555", id="three-decimals"),
    # 前後有空白：API 不接受，所以確認頁也不能把它顯示成 5.00、算出付款後餘額（QA 時發現兩端都會）
    pytest.param(" 5 ", id="spaces"),
])
@pytest.mark.case_id("WEB-005")
def test_invalid_amount_is_refused_and_nothing_moves(page, app_url, api, db, amount):
    wallet = funded_wallet(api, "100.00")

    confirm = PayPage(page, app_url).open(wallet).continue_with(amount)
    # R-04：不是 API 會接受的寫法，就照輸入顯示，不算付款後餘額
    expect(confirm.tid("confirm-balance-after")).to_have_count(0)
    confirm.confirm()

    expect(confirm.tid("error-message")).to_have_text(ERROR_TEXT["INVALID_AMOUNT"])
    assert db.count("payments", "wallet_id = ?", wallet) == 0
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 10000


@pytest.mark.business
@pytest.mark.case_id("WEB-006")
def test_payment_above_the_balance_is_refused(page, app_url, api, db):
    wallet = funded_wallet(api, "20.00")

    confirm = PayPage(page, app_url).open(wallet).continue_with("50")
    confirm.confirm()

    expect(confirm.tid("error-message")).to_have_text(ERROR_TEXT["INSUFFICIENT_BALANCE"])
    assert db.count("payments", "wallet_id = ?", wallet) == 0
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 2000
    # 被拒絕後可以回去改金額，原本輸入的還在
    pay = confirm.change_amount()
    expect(pay.tid("amount-input")).to_have_value("50")
