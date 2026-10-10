"""開始畫面：建立錢包，或用錢包編號打開。"""
from __future__ import annotations

from framework.web.base import WebPage
from framework.web.home_page import HomePage


class StartPage(WebPage):
    def open(self) -> StartPage:
        self.goto("/")
        self.tid("create-wallet").wait_for()
        return self

    def create_wallet(self, owner: str) -> HomePage:
        self.tid("owner-input").fill(owner)
        self.tid("create-wallet").click()
        home = HomePage(self.page, self.app_url)
        home.tid("balance").wait_for()
        return home

    def error(self) -> str:
        return self.text("error-message")
