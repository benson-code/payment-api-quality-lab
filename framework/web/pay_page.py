"""付款：輸入金額 → 確認 → 收據。確認頁有四種狀態（web/SPEC.md §6.5）。"""
from __future__ import annotations

from framework.web.base import WebPage
from framework.web.receipt_page import ReceiptPage


class PayPage(WebPage):
    """第一步：輸入金額。"""

    def open(self, wallet_id: str) -> PayPage:
        self.goto(f"/w/{wallet_id}/pay")
        return self.wait()

    def wait(self) -> PayPage:
        self.tid("amount-input").wait_for()
        return self

    def available(self) -> str:
        return self.text("balance")

    def continue_with(self, amount: str) -> ConfirmPage:
        self.tid("amount-input").fill(amount)
        self.tid("submit").click()
        return ConfirmPage(self.page, self.app_url).wait()

    def pay(self, amount: str) -> ReceiptPage:
        """整段流程走完，回傳收據。"""
        return self.continue_with(amount).confirm_and_wait()


class ConfirmPage(WebPage):
    """第二步：確認。按下「Confirm payment」才產生 Idempotency-Key（K-01）。"""

    def wait(self) -> ConfirmPage:
        self.tid("confirm-amount").wait_for()
        return self

    def amount(self) -> str:
        return self.text("confirm-amount")

    def balance_after(self) -> str:
        return self.text("confirm-balance-after")

    def confirm(self) -> None:
        """按下確認，不等結果。"""
        self.tid("confirm-pay").click()

    def confirm_and_wait(self) -> ReceiptPage:
        self.confirm()
        return ReceiptPage(self.page, self.app_url).wait()

    def error(self) -> str:
        return self.text("error-message")

    def change_amount(self) -> PayPage:
        self.tid("change-amount").click()
        return PayPage(self.page, self.app_url).wait()
