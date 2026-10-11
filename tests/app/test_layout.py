"""APP-011：每個畫面在兩種螢幕設定上都放得下、沒有疊在一起或被擠扁的字、可點的東西至少 48 x 48 dp
（L-01、L-02），操作之後出現的訊息要在看得到的地方（L-04）。和 WEB-011 同一組行為。

檢查的方法在 framework/app/layout.py：從 UiAutomator 的畫面結構判斷，畫面從頭捲到尾每個位置都看。
"""
import pytest

from framework.app.home_screen import HomeScreen
from testdata.factories import funded_wallet

pytestmark = pytest.mark.app

LONG_NAME = "Alexandria Montgomery-Fitzgerald Wellington Smith"       # 50 個字，名稱的上限


def walk_every_screen(app, wallet: str, amount: str) -> dict:
    """從開始畫面走過每一個畫面，每一個都檢查版面；回傳有問題的畫面和問題。"""
    problems = {}

    def check(name, screen):
        found = screen.layout_problems()
        if found:
            problems[name] = found

    check("start", app)
    home = app.open_wallet(wallet)
    check("home", home)
    top_up = home.go_top_up()
    check("top up", top_up)
    top_up.system_back()
    pay = HomeScreen(app.driver).wait().go_pay()
    check("pay", pay)
    confirm = pay.continue_with(amount)
    check("confirm", confirm)
    receipt = confirm.confirm_and_wait()
    check("receipt", receipt)
    history = receipt.done().tab_history()
    check("history", history)
    detail = history.open_payment()
    check("payment detail", detail)
    return problems


@pytest.mark.case_id("APP-011")
def test_every_screen_fits_the_phone(app, api):
    wallet = funded_wallet(api, "12345.60")             # 有千分位的長金額
    payment_id = api.pay(wallet, "30.00").json()["payment_id"]
    api.refund(payment_id, "5.00")

    problems = walk_every_screen(app, wallet, "10")
    assert not problems, problems


@pytest.mark.case_id("APP-011")
def test_the_largest_amounts_and_a_long_name_fit(app, api):
    """API 允許的最大金額（整數 12 位）和 50 個字的名稱。QA 時發現：「From」被壓成一行一個字、
    還被名稱蓋住，餘額旁的「TWD」被擠成直排。"""
    wallet = funded_wallet(api, "999999999999.99", owner=LONG_NAME)

    problems = walk_every_screen(app, wallet, "0.01")
    assert not problems, problems


@pytest.mark.case_id("APP-011")
def test_a_message_after_an_action_is_in_view(app, api, proxy):
    """開始畫面的錯誤訊息原本在兩張卡片下面，360 x 640 的手機上完全看不到（SPEC.md 2.1）；
    退款成功的訊息會被重新載入的退款紀錄擠下去，沒有回應時「Retry」在訊息下面的畫面外（2.2）。"""
    app.tap("create-wallet")                            # 沒有名字：API 拒絕（E-07）
    app.wait_for("error-message")
    assert app.is_fully_visible("error-message"), "the Start screen's error is out of view"

    app.type_into("wallet-id-input", "w_nope")
    app.tap("open-wallet")                              # 沒有這個錢包（E-05）
    app.expect_text("error-message", "No wallet with this ID.")
    assert app.is_fully_visible("error-message"), "the open-wallet error is out of view"

    wallet = funded_wallet(api, "100.00")
    api.pay(wallet, "30.00")
    detail = app.open_wallet(wallet).tab_history().open_payment()
    detail.submit_refund("10")
    detail.wait_for("refund-done")
    assert detail.is_fully_visible("refund-done"), "the refund's success message is out of view"

    with proxy.lose_response("/refunds"):
        detail.submit_refund("5")
        detail.wait_for("no-answer")
    assert detail.is_fully_visible("no-answer"), "the refund's no-answer warning is out of view"
    assert detail.is_fully_visible("retry"), "Retry is out of view"
