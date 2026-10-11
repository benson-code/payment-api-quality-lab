"""付款明細與退款。App 只能從交易紀錄打開付款（沒有網址），所以由 HistoryScreen.open_payment() 進來。"""
from __future__ import annotations

from framework.app.base import AppScreen


class PaymentDetailScreen(AppScreen):
    def wait(self) -> PaymentDetailScreen:
        self.wait_for("payment-amount")
        return self

    def refunded(self) -> str:
        return self.text("payment-refunded")

    def refundable(self) -> str:
        return self.text("payment-refundable")

    def submit_refund(self, amount: str) -> None:
        """輸入退款金額並送出，不等結果。退款表單在小螢幕上可能在畫面下方，find() 會捲過去。"""
        self.type_into("amount-input", amount)
        self.tap("submit")

    def retry(self) -> None:
        self.tap("retry")

    def error(self) -> str:
        return self.text("error-message")
