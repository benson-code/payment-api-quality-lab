"""WEB-011：每個畫面在兩種手機上都不能左右捲動、沒有被卡片裁掉的內容，按鈕和連結至少
44 x 44 px（L-01、L-02），操作之後出現的訊息要在看得到的地方（L-04）。"""
import pytest
from playwright.sync_api import expect

from framework.web.history_page import HistoryPage
from framework.web.home_page import HomePage
from framework.web.pay_page import PayPage
from framework.web.payment_detail_page import PaymentDetailPage
from framework.web.start_page import StartPage
from framework.web.top_up_page import TopUpPage
from testdata.factories import funded_wallet

pytestmark = pytest.mark.web


@pytest.mark.case_id("WEB-011")
def test_every_screen_fits_the_phone(page, app_url, api):
    wallet = funded_wallet(api, "12345.60")             # 有千分位的長金額
    payment_id = api.pay(wallet, "30.00").json()["payment_id"]
    api.refund(payment_id, "5.00")

    screens = {
        "start": lambda: StartPage(page, app_url).open(),
        "home": lambda: HomePage(page, app_url).open(wallet),
        "history": lambda: HistoryPage(page, app_url).open(wallet),
        "top up": lambda: TopUpPage(page, app_url).open(wallet),
        "pay": lambda: PayPage(page, app_url).open(wallet),
        "confirm": lambda: PayPage(page, app_url).open(wallet).continue_with("10"),
        "receipt": lambda: PayPage(page, app_url).open(wallet).pay("10"),
        "payment detail": lambda: PaymentDetailPage(page, app_url).open(wallet, payment_id),
    }
    problems = problems_on(screens)
    assert not problems, problems


@pytest.mark.case_id("WEB-011")
def test_the_largest_amounts_and_a_long_name_fit(page, app_url, api):
    """API 允許的最大金額（整數 12 位）和 50 個字的名稱。QA 時發現：餘額 999,999,999,999.99
    被卡片裁掉，只看得到 999,999,999,999；頁面沒有變寬，所以原本的檢查抓不到。"""
    wallet = funded_wallet(api, "999999999999.99", owner="Alexandria Montgomery-Fitzgerald Wellington Smith")
    payment_id = api.pay(wallet, "0.01").json()["payment_id"]

    screens = {
        "home": lambda: HomePage(page, app_url).open(wallet),
        "history": lambda: HistoryPage(page, app_url).open(wallet),
        "confirm": lambda: PayPage(page, app_url).open(wallet).continue_with("0.01"),
        "receipt": lambda: PayPage(page, app_url).open(wallet).pay("0.01"),
        "payment detail": lambda: PaymentDetailPage(page, app_url).open(wallet, payment_id),
    }
    on_phone = problems_on(screens)
    page.set_viewport_size({"width": 360, "height": 640})
    on_small = problems_on(screens)
    assert not on_phone and not on_small, {"phone": on_phone, "360x640": on_small}


def problems_on(screens) -> dict:
    problems = {}
    for name, show in screens.items():
        found = show().layout_problems()
        if any(found.values()):
            problems[name] = found
    return problems


@pytest.mark.case_id("WEB-011")
def test_a_message_after_an_action_is_in_view(page, app_url):
    """開始畫面的錯誤訊息原本在兩張卡片下面：在 360 x 640 的手機上完全在畫面外，按了按鈕像是沒反應。

    Playwright 的 to_have_text 不管元素在不在畫面內，所以原本的測試抓不到；是 Android App 的
    Appium 測試（UiAutomator 只看得到畫面上的元素）先發現的。
    """
    start = StartPage(page, app_url)
    page.set_viewport_size({"width": 360, "height": 640})
    for button, field, value in (("create-wallet", None, None), ("open-wallet", "wallet-id-input", "w_nope")):
        start.open()
        if field:
            start.tid(field).fill(value)
        start.tid(button).click()
        expect(start.tid("error-message")).to_be_in_viewport()

