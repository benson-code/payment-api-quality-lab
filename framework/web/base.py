"""所有畫面共用：用 data-testid 找元素、讀文字。"""
from __future__ import annotations

from playwright.sync_api import Locator, Page

MINUS = "−"       # 交易紀錄的負號是 U+2212（web/SPEC.md D-02），不是減號鍵的 "-"


class WebPage:
    def __init__(self, page: Page, app_url: str) -> None:
        self.page = page
        self.app_url = app_url          # 例如 http://127.0.0.1:8400/app/

    def tid(self, test_id: str) -> Locator:
        return self.page.get_by_test_id(test_id)

    def text(self, test_id: str) -> str:
        """元素的文字（會等元素出現）。"""
        return self.tid(test_id).inner_text().strip()

    def goto(self, route: str) -> None:
        """route 是 # 後面的路徑，例如 /w/w_xxx/pay。"""
        self.page.goto(f"{self.app_url}#{route}")
