"""付款明細與退款。App 沒有網址：從交易紀錄、首頁的最近活動或付款收據打開。"""
from __future__ import annotations

from framework.ios.base import IosScreen


class PaymentDetailScreen(IosScreen):
    def wait(self) -> PaymentDetailScreen:
        self.wait_for("payment-amount")
        return self

    def refunded(self) -> str:
        return self.text("payment-refunded")

    def refundable(self) -> str:
        return self.text("payment-refundable")

    def submit_refund(self, amount: str) -> None:
        """輸入退款金額並送出，不等結果。"""
        self.type_into("amount-input", amount)
        self.tap("submit")

    def retry(self) -> None:
        self.tap("retry")

    def error(self) -> str:
        return self.text("error-message")

    def back(self):
        """返回鍵：不管從哪裡打開，都回到交易紀錄（SPEC.md §4）。"""
        from framework.ios.history_screen import HistoryScreen
        self.tap("back")
        return HistoryScreen(self.driver).wait()
