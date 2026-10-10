"""收據：儲值或付款成功之後的畫面。"""
from __future__ import annotations

from framework.web.base import WebPage


class ReceiptPage(WebPage):
    def wait(self) -> ReceiptPage:
        self.tid("result").wait_for()
        return self

    def amount(self) -> str:
        return self.text("result-amount")

    def balance(self) -> str:
        return self.text("result-balance")

    def done(self):
        from framework.web.home_page import HomePage
        self.tid("done").click()
        home = HomePage(self.page, self.app_url)
        home.tid("balance").wait_for()
        return home
