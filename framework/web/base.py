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
        """route 是 # 後面的路徑，例如 /w/w_xxx/pay。

        網址和目前完全相同時（例如付款的確認步驟，網址還是 /pay），瀏覽器什麼都不做，畫面會
        停在原本的步驟；這時改成重新載入，保證從這個畫面的起點開始。
        """
        url = f"{self.app_url}#{route}"
        if self.page.url == url:
            self.page.reload()
        else:
            self.page.goto(url)

    def layout_problems(self) -> dict:
        """目前畫面的版面問題（web/SPEC.md L-01、L-02）：

        horizontal_scroll  頁面比螢幕寬，要左右捲動
        small_targets      小於 44 x 44 CSS px 的按鈕或連結（觸控目標太小，手指點不準）
        """
        return self.page.evaluate("""() => ({
            horizontal_scroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
            small_targets: [...document.querySelectorAll('a, button')]
                .map(e => ({ el: e.dataset.testid || e.textContent.trim(), r: e.getBoundingClientRect() }))
                .filter(x => x.r.width < 44 || x.r.height < 44)
                .map(x => `${x.el} ${Math.round(x.r.width)}x${Math.round(x.r.height)}`),
        })""")
