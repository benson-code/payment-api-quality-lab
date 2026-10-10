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

    def back(self) -> PayPage:
        """上方的返回鍵：回到輸入金額。"""
        self.tid("back").click()
        return PayPage(self.page, self.app_url).wait()

    def retry(self) -> None:
        """沒有回應之後的「Retry」，不等結果。"""
        self.tid("retry").click()

    def double_tap_confirm(self) -> None:
        """同一瞬間點兩下確認。

        在同一個 JavaScript 工作裡連續觸發兩次 click：第二下發生時 React 還來不及重畫、按鈕還沒
        變成 disabled，只有程式裡的「送出中」旗標擋得住。Playwright 的 dblclick 兩下之間畫面已經
        更新，按鈕已停用，測不到這個空檔。
        """
        self.tid("confirm-pay").evaluate("b => { b.click(); b.click(); }")
