"""付款明細與退款。"""
from __future__ import annotations

from framework.web.base import WebPage


class PaymentDetailPage(WebPage):
    def open(self, wallet_id: str, payment_id: str) -> PaymentDetailPage:
        self.goto(f"/w/{wallet_id}/p/{payment_id}")
        self.tid("payment-amount").wait_for()
        return self

    def refunded(self) -> str:
        return self.text("payment-refunded")

    def refundable(self) -> str:
        return self.text("payment-refundable")

    def submit_refund(self, amount: str) -> None:
        """輸入退款金額並送出，不等結果。"""
        self.tid("amount-input").fill(amount)
        self.tid("submit").click()

    def error(self) -> str:
        return self.text("error-message")
