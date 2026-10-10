"""首頁（Home 分頁）：餘額、三個動作、最近三筆。"""
from __future__ import annotations

import re

from framework.web.base import WebPage


class HomePage(WebPage):
    def open(self, wallet_id: str) -> HomePage:
        self.goto(f"/w/{wallet_id}")
        self.tid("balance").wait_for()
        return self

    @property
    def wallet_id(self) -> str:
        """畫面上的錢包編號是遮罩過的（D-04），完整的在網址裡。"""
        m = re.search(r"#/w/([^/]+)", self.page.url)
        assert m, f"no wallet in {self.page.url}"
        return m.group(1)

    def balance(self) -> str:
        return self.text("balance")

    def owner(self) -> str:
        return self.text("owner")

    def go_top_up(self):
        from framework.web.top_up_page import TopUpPage
        self.tid("go-topup").click()
        return TopUpPage(self.page, self.app_url).wait()

    def go_pay(self):
        from framework.web.pay_page import PayPage
        self.tid("go-pay").click()
        return PayPage(self.page, self.app_url).wait()

    def go_history(self):
        from framework.web.history_page import HistoryPage
        self.tid("go-history").click()
        return HistoryPage(self.page, self.app_url).wait()
