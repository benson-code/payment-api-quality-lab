"""控制網頁和 API 之間的網路，製造「處理中」「回應遺失」「完全沒送到」這幾種情況。

全部用 Playwright 的 page.route 在瀏覽器這一側攔截，API 本身不用改。三種情況要分清楚：

    hold           請求先停在瀏覽器，release() 才送出：用來看「處理中」的畫面、測連點
    lose_response  請求送到伺服器、伺服器也處理完了，但回應在半路丟掉：畫面看到的是沒有回應，
                   錢其實已經扣了。這是重送必須用同一把 key 的原因（WEB-008）
    block          請求根本沒送到伺服器：畫面一樣是沒有回應，但什麼都沒發生

只攔 POST：GET /payments/{id} 這類讀取不受影響。
"""
from __future__ import annotations

from contextlib import contextmanager

from playwright.sync_api import Page, Route


class Held:
    """被 hold 住、還沒送出的請求。"""

    def __init__(self) -> None:
        self.routes: list[Route] = []

    def release(self) -> None:
        for route in self.routes:
            route.continue_()
        self.routes.clear()


@contextmanager
def hold(page: Page, url: str):
    held = Held()

    def handler(route: Route) -> None:
        if route.request.method != "POST":
            route.continue_()
            return
        held.routes.append(route)       # 不回應，請求就一直停著

    page.route(url, handler)
    try:
        yield held
    finally:
        held.release()
        page.unroute(url, handler)


@contextmanager
def lose_response(page: Page, url: str, times: int = 1):
    """前 times 個 POST 送到伺服器、等它處理完，再把回應丟掉。"""
    left = [times]

    def handler(route: Route) -> None:
        if route.request.method != "POST" or left[0] == 0:
            route.continue_()
            return
        left[0] -= 1
        route.fetch()                   # 真的送到伺服器，並等它回應
        route.abort("connectionreset")  # 但瀏覽器只看到連線被切斷

    page.route(url, handler)
    try:
        yield
    finally:
        page.unroute(url, handler)


@contextmanager
def block(page: Page, url: str):
    """POST 完全送不出去（伺服器什麼都沒收到）。"""

    def handler(route: Route) -> None:
        if route.request.method != "POST":
            route.continue_()
            return
        route.abort("connectionreset")

    page.route(url, handler)
    try:
        yield
    finally:
        page.unroute(url, handler)


class SentKeys:
    """記下每個 POST 帶的 Idempotency-Key（沒帶就記 None），依送出順序。"""

    def __init__(self, page: Page, path_suffix: str) -> None:
        self.keys: list[str | None] = []
        page.on("request", lambda r: self.keys.append(r.headers.get("idempotency-key"))
                if r.method == "POST" and r.url.endswith(path_suffix) else None)

    def __len__(self) -> int:
        return len(self.keys)

    def __getitem__(self, i: int) -> str | None:
        return self.keys[i]
