"""WEB-009：在網頁上部分退款，累計超退要被擋下來，而且原因要講清楚。"""
import pytest
from playwright.sync_api import expect

from framework.web.payment_detail_page import PaymentDetailPage
from testdata.factories import funded_wallet
from testdata.messages import ERROR_TEXT

pytestmark = [pytest.mark.web, pytest.mark.refund]


@pytest.mark.case_id("WEB-009")
def test_partial_refund_then_the_cumulative_limit(page, app_url, api, db):
    """付 30、退 10 之後只剩 20 可退。只檢查「單筆不超過原付款」的話，25 會被放行（埋 bug：refund_overflow）。"""
    wallet = funded_wallet(api, "100.00")
    payment_id = api.pay(wallet, "30.00").json()["payment_id"]
    detail = PaymentDetailPage(page, app_url).open(wallet, payment_id)

    detail.submit_refund("10")
    expect(detail.tid("refund-done")).to_be_visible()
    expect(detail.tid("payment-refunded")).to_have_text("10.00")
    expect(detail.tid("payment-refundable")).to_have_text("20.00")

    detail.submit_refund("25")
    expect(detail.tid("error-message")).to_have_text(ERROR_TEXT["REFUND_EXCEEDS_PAYMENT"])
    expect(detail.tid("payment-refunded")).to_have_text("10.00")

    refunded = db.one("SELECT COALESCE(SUM(amount), 0) AS s FROM refunds WHERE payment_id = ?", payment_id)["s"]
    assert refunded == 1000
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 8000
