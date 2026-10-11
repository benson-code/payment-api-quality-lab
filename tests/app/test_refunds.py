"""APP-009：在 App 上部分退款，累計超退要被擋下來，而且原因要講清楚（和 WEB-009 同一組行為）。"""
import pytest

from testdata.factories import funded_wallet
from testdata.messages import ERROR_TEXT

pytestmark = [pytest.mark.app, pytest.mark.refund]


@pytest.mark.case_id("APP-009")
def test_partial_refund_then_the_cumulative_limit(app, api, db):
    """付 30、退 10 之後只剩 20 可退。只檢查「單筆不超過原付款」的話，25 會被放行（埋 bug：refund_overflow）。"""
    wallet = funded_wallet(api, "100.00")
    payment_id = api.pay(wallet, "30.00").json()["payment_id"]
    # App 沒有網址：從交易紀錄打開這筆付款
    detail = app.open_wallet(wallet).tab_history().open_payment()
    detail.expect_text("payment-refundable", "30.00")

    detail.submit_refund("10")
    detail.expect_shown("refund-done")
    detail.expect_text("payment-refunded", "10.00")
    detail.expect_text("payment-refundable", "20.00")

    detail.submit_refund("25")
    detail.expect_text("error-message", ERROR_TEXT["REFUND_EXCEEDS_PAYMENT"])
    detail.expect_text("payment-refunded", "10.00")

    refunded = db.one("SELECT COALESCE(SUM(amount), 0) AS s FROM refunds WHERE payment_id = ?", payment_id)["s"]
    assert refunded == 1000
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 8000
