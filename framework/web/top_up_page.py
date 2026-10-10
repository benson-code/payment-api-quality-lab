"""儲值：一步完成。儲值沒有 Idempotency-Key，所以沒有回應時不提供重試（K-07）。"""
from __future__ import annotations

from framework.web.base import WebPage
from framework.web.receipt_page import ReceiptPage


class TopUpPage(WebPage):
    def open(self, wallet_id: str) -> TopUpPage:
        self.goto(f"/w/{wallet_id}/topup")
        return self.wait()

    def wait(self) -> TopUpPage:
        self.tid("amount-input").wait_for()
        return self

    def submit(self, amount: str) -> None:
        """輸入金額並送出，不等結果：成功、被拒、沒有回應由呼叫的人決定要等哪個。"""
        self.tid("amount-input").fill(amount)
        self.tid("submit").click()

    def top_up(self, amount: str) -> ReceiptPage:
        self.submit(amount)
        return ReceiptPage(self.page, self.app_url).wait()

    def error(self) -> str:
        return self.text("error-message")
