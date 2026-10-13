"""WEB-015：每個畫面和它的訊息狀態都通過 axe-core 的 WCAG 2.2 A、AA 規則（L-03、L-05）：
輸入框和圖示按鈕有名稱、文字對比夠、ARIA 用法正確。

只有自動掃描看得到的部分：報讀器實際唸出來的順序和內容，仍然要人用 VoiceOver 或 TalkBack 聽
（SPEC.md §10）。
"""
import pytest

from framework.web.history_page import HistoryPage
from framework.web.home_page import HomePage
from framework.web.network import lose_response
from framework.web.pay_page import PayPage
from framework.web.payment_detail_page import PaymentDetailPage
from framework.web.receipt_page import ReceiptPage
from framework.web.start_page import StartPage
from framework.web.top_up_page import TopUpPage
from testdata.factories import funded_wallet

pytestmark = pytest.mark.web


@pytest.mark.case_id("WEB-015")
def test_every_screen_passes_the_accessibility_scan(page, app_url, api):
    wallet = funded_wallet(api, "100.00")
    empty = funded_wallet(api, "0.00")                     # 沒有交易：首頁和交易紀錄的空狀態
    payment_id = api.pay(wallet, "30.00").json()["payment_id"]
    api.refund(payment_id, "5.00")

    def start_error():
        start = StartPage(page, app_url).open()
        start.tid("create-wallet").click()                # 沒填名字：錯誤訊息
        start.tid("error-message").wait_for()
        return start

    def home_balance_hidden():
        home = HomePage(page, app_url).open(wallet)
        home.tid("balance-toggle").click()
        return home

    def top_up_refused():
        top_up = TopUpPage(page, app_url).open(wallet)
        top_up.submit("-1")                               # 欄位下方的錯誤（E-01）
        top_up.error()
        return top_up

    def confirm_no_answer():
        confirm = PayPage(page, app_url).open(wallet).continue_with("10")
        with lose_response(page, "**/payments"):
            confirm.confirm()
            confirm.tid("no-answer").wait_for()
        return confirm

    def receipt_replayed():
        confirm = confirm_no_answer()
        confirm.retry()
        receipt = ReceiptPage(page, app_url).wait()
        receipt.tid("replayed").wait_for()
        return receipt

    def refund_done():
        detail = PaymentDetailPage(page, app_url).open(wallet, payment_id)
        detail.submit_refund("1")
        detail.tid("refund-done").wait_for()
        return detail

    def refund_refused():
        detail = PaymentDetailPage(page, app_url).open(wallet, payment_id)
        detail.submit_refund("1000")                      # 超過可退金額（E-03）
        detail.error()
        return detail

    screens = {
        "start": lambda: StartPage(page, app_url).open(),
        "start, error": start_error,
        "home": lambda: HomePage(page, app_url).open(wallet),
        "home, balance hidden": home_balance_hidden,
        "home, no activity": lambda: HomePage(page, app_url).open(empty),
        "history": lambda: HistoryPage(page, app_url).open(wallet),
        "history, empty": lambda: HistoryPage(page, app_url).open(empty),
        "top up": lambda: TopUpPage(page, app_url).open(wallet),
        "top up, refused": top_up_refused,
        "pay": lambda: PayPage(page, app_url).open(wallet),
        "confirm": lambda: PayPage(page, app_url).open(wallet).continue_with("10"),
        "confirm, no answer": confirm_no_answer,
        "receipt": lambda: PayPage(page, app_url).open(wallet).pay("10"),
        "receipt, replayed": receipt_replayed,
        "payment detail": lambda: PaymentDetailPage(page, app_url).open(wallet, payment_id),
        "payment detail, refunded": refund_done,
        "payment detail, refused": refund_refused,
    }
    violations = {}
    for name, show in screens.items():
        found = show().accessibility_violations()
        if found:
            violations[name] = found
    assert not violations, violations


@pytest.mark.case_id("WEB-016")
def test_a_focused_element_is_never_under_a_sticky_bar(page, app_url, api):
    """用鍵盤的人要看得到焦點（L-06）。首頁在 iPhone 14 上，Tab 到最後的「Use another wallet」
    時，Chromium 把它捲到畫面最底下，正好整個藏在分頁列後面；Firefox 則完全不捲動。是追 axe 的
    target-size 回報時發現的（那一條本身是捲動位置造成的誤報，見 framework/web/base.py）。"""
    wallet = funded_wallet(api, "100.00")
    for i in range(8):                                     # 交易紀錄比畫面長，要捲動
        api.pay(wallet, f"{i + 1}.00")
    payment_id = api.pay(wallet, "10.00").json()["payment_id"]
    for _ in range(4):                                     # 退款紀錄也變長
        api.refund(payment_id, "1.00")

    screens = {
        "start": lambda: StartPage(page, app_url).open(),
        "home": lambda: HomePage(page, app_url).open(wallet),
        "history": lambda: HistoryPage(page, app_url).open(wallet),
        "top up": lambda: TopUpPage(page, app_url).open(wallet),
        "pay": lambda: PayPage(page, app_url).open(wallet),
        "confirm": lambda: PayPage(page, app_url).open(wallet).continue_with("10"),
        "payment detail": lambda: PaymentDetailPage(page, app_url).open(wallet, payment_id),
    }
    page.set_viewport_size({"width": 360, "height": 640})   # 最小的螢幕：最容易被蓋住
    hidden = {}
    for name, show in screens.items():
        found = show().hidden_focus()
        if found:
            hidden[name] = found
    assert not hidden, hidden
