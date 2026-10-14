"""收據：儲值或付款成功之後的畫面。"""
from __future__ import annotations

from framework.ios.base import IosScreen


class ReceiptScreen(IosScreen):
    def wait(self) -> ReceiptScreen:
        self.wait_for("result")
        return self

    def amount(self) -> str:
        return self.text("result-amount")

    def balance(self) -> str:
        return self.text("result-balance")

    def payment_id(self) -> str:
        return self.text("result-payment-id")

    def done(self):
        from framework.ios.home_screen import HomeScreen
        self.tap("done")
        return HomeScreen(self.driver).wait()

    def view_payment(self):
        """付款收據才有：打開這筆付款的明細。"""
        from framework.ios.payment_detail_screen import PaymentDetailScreen
        self.tap("view-payment")
        return PaymentDetailScreen(self.driver).wait()
