"""付款：輸入金額 → 確認 → 收據。確認頁有四種狀態（SPEC.md §7.5）。"""
from __future__ import annotations

from framework.app.base import AppScreen
from framework.app.receipt_screen import ReceiptScreen


class PayScreen(AppScreen):
    """第一步：輸入金額。"""

    def wait(self) -> PayScreen:
        # 「可用餘額」出現表示錢包資料已經回來：確認頁的「付款後餘額」要靠它算，
        # 不等的話，「沒有付款後餘額」可能只是還沒載入
        self.wait_for("balance")
        return self

    def available(self) -> str:
        return self.text("balance")

    def amount_field(self) -> str:
        return self.text("amount-input")

    def continue_with(self, amount: str) -> ConfirmScreen:
        self.type_into("amount-input", amount)
        self.tap("submit")
        return ConfirmScreen(self.driver).wait()

    def pay(self, amount: str) -> ReceiptScreen:
        """整段流程走完，回傳收據。"""
        return self.continue_with(amount).confirm_and_wait()


class ConfirmScreen(AppScreen):
    """第二步：確認。按下「Confirm payment」才產生 Idempotency-Key（K-01）。"""

    def wait(self) -> ConfirmScreen:
        self.wait_for("confirm-amount")
        return self

    def amount(self) -> str:
        return self.text("confirm-amount")

    def balance_after(self) -> str:
        return self.text("confirm-balance-after")

    def confirm(self) -> None:
        """按下確認，不等結果。"""
        self.tap("confirm-pay")

    def confirm_and_wait(self) -> ReceiptScreen:
        self.confirm()
        return ReceiptScreen(self.driver).wait()

    def error(self) -> str:
        return self.text("error-message")

    def change_amount(self) -> PayScreen:
        self.tap("change-amount")
        return PayScreen(self.driver).wait()

    def back(self) -> PayScreen:
        """上方的返回鍵：回到輸入金額。"""
        self.tap("back")
        return PayScreen(self.driver).wait()

    def retry(self) -> None:
        """沒有回應之後的「Retry」，不等結果。"""
        self.tap("retry")
