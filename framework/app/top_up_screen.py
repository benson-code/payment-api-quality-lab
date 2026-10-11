"""儲值：一步完成。儲值沒有 Idempotency-Key，所以沒有回應時不提供重試（K-07）。"""
from __future__ import annotations

from framework.app.base import AppScreen
from framework.app.receipt_screen import ReceiptScreen


class TopUpScreen(AppScreen):
    def wait(self) -> TopUpScreen:
        self.wait_for("amount-input")
        return self

    def submit(self, amount: str) -> None:
        """輸入金額並送出，不等結果：成功、被拒、沒有回應由呼叫的人決定要等哪個。"""
        self.type_into("amount-input", amount)
        self.tap("submit")

    def top_up(self, amount: str) -> ReceiptScreen:
        self.submit(amount)
        return ReceiptScreen(self.driver).wait()

    def error(self) -> str:
        return self.text("error-message")
