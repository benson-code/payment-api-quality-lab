"""兩個客戶端是不是真的一樣：同一組輸入分別交給網頁和 Android App，比較使用者看到的和伺服器做的。

    .venv/bin/python tools/parity_check.py            # 需要建置好的網頁和 debug APK、裝置、Appium

SPEC.md 只寫一次規則，兩個客戶端各自實作；各自的測試證明「符合規格」，這裡證明「彼此一致」。
付款、儲值、退款各一組輸入（合法的、邊界的、API 會拒絕的），每一個都記下：

    continue   送出鈕能不能按（空白的金額不能送出，R-02）
    confirm    確認頁顯示的金額、付款後餘額（R-04）
    outcome    結果：收據上的餘額、錯誤訊息或「沒有回應」，連同文字
    server     伺服器的狀態：餘額、付款筆數、已退金額

每一個輸入都用新的錢包（透過 API 建立、儲值 100.00），兩邊從同樣的狀態開始。有任何不同就列出來，
結束碼 1。第一次跑的時候抓到 API 收下全形數字「１００」（SPEC.md §11，2.3）。

畫面文字比較前會把連續的空白壓成一個、去掉頭尾：HTML 顯示文字時本來就會這樣做（「 5 」在網頁上
看起來就是「5」），這不是兩邊行為的差別。
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from framework.wallet_api import WalletAPI  # noqa: E402

PAY = ["30", "30.00", "0", "0.00", "-1", "1e3", "10.555", "abc", " 5 ", "5.", ".5", "1,000",
       "１００", "٣٠", "00010", "0.01", "100", "100.01", "12,345.60", "", "   "]
TOP_UP = ["19.99", "0", "-1", "abc", " 5 ", "１００", "1e3", "0.001", "50000.01", "1234567.89", "", "  "]
REFUND = ["10", "0", "-1", "30.01", "10.555", "abc", "30.00", " "]

APK = ROOT / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
APPIUM_URL = "http://127.0.0.1:4723"


def shown(text: str | None) -> str | None:
    return " ".join(text.split()) if text is not None else None


# ---- 被測系統 ----------------------------------------------------------------------------

def start_api(db_path: str) -> tuple[subprocess.Popen, str]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
                            cwd=ROOT, env={**os.environ, "DB_PATH": db_path})
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if requests.get(base + "/health", timeout=1).ok:
                return proc, base
        except requests.ConnectionError:
            pass
        time.sleep(0.2)
    proc.terminate()
    raise SystemExit("the API did not start")


class Setup:
    """每個輸入一個新錢包：儲值 100.00；退款的輸入另外先付 30。"""

    def __init__(self, api: WalletAPI) -> None:
        self.api = api

    def wallet(self, paid: str | None = None) -> tuple[str, str | None]:
        wallet = self.api.create_wallet("Parity").json()["wallet_id"]
        self.api.top_up(wallet, "100.00")
        payment = self.api.pay(wallet, paid).json()["payment_id"] if paid else None
        return wallet, payment

    def server(self, wallet: str, payment: str | None = None) -> dict:
        entries = self.api.transactions(wallet).json()["transactions"]
        state = {"balance": self.api.balance(wallet), "payments": sum(e["type"] == "PAYMENT" for e in entries)}
        if payment:
            state["refunded"] = self.api.get_payment(payment).json()["refunded"]
        return state


# ---- 網頁 --------------------------------------------------------------------------------

def run_web(setup: Setup, base: str) -> dict:
    from playwright.sync_api import sync_playwright

    from framework.web.pay_page import ConfirmPage, PayPage
    from framework.web.payment_detail_page import PaymentDetailPage
    from framework.web.top_up_page import TopUpPage

    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        device = {k: v for k, v in p.devices["Pixel 7"].items() if k != "default_browser_type"}
        page = browser.new_context(**device, timezone_id="Asia/Taipei").new_page()
        app_url = base + "/app/"

        def outcome(screen, *hooks) -> str:
            page.wait_for_selector(",".join(f'[data-testid="{h}"]' for h in hooks), timeout=10_000)
            hook = next(h for h in hooks if screen.tid(h).count())
            return f"{hook}: {shown(screen.text(hook))}"

        for amount in PAY:
            wallet, _ = setup.wallet()
            pay = PayPage(page, app_url).open(wallet)
            pay.tid("balance").wait_for()
            pay.tid("amount-input").fill(amount)
            r = {"continue": pay.tid("submit").is_enabled()}
            if r["continue"]:
                pay.tid("submit").click()
                confirm = ConfirmPage(page, app_url).wait()
                r["confirm"] = shown(confirm.amount())
                r["after"] = confirm.balance_after() if confirm.tid("confirm-balance-after").count() else None
                confirm.confirm()
                r["outcome"] = outcome(confirm, "result-balance", "error-message", "no-answer")
            r["server"] = setup.server(wallet)
            results[("pay", amount)] = r

        for amount in TOP_UP:
            wallet, _ = setup.wallet()
            top_up = TopUpPage(page, app_url).open(wallet)
            top_up.tid("amount-input").fill(amount)
            r = {"continue": top_up.tid("submit").is_enabled()}
            if r["continue"]:
                top_up.tid("submit").click()
                r["outcome"] = outcome(top_up, "result-balance", "error-message", "no-answer")
            r["server"] = setup.server(wallet)
            results[("top up", amount)] = r

        for amount in REFUND:
            wallet, payment = setup.wallet(paid="30")
            detail = PaymentDetailPage(page, app_url).open(wallet, payment)
            detail.tid("amount-input").fill(amount)
            r = {"continue": detail.tid("submit").is_enabled()}
            if r["continue"]:
                detail.tid("submit").click()
                r["outcome"] = outcome(detail, "refund-done", "error-message", "no-answer")
                page.wait_for_timeout(500)              # 退款成功後明細會重新載入
                r["left"] = detail.refundable()
            r["server"] = setup.server(wallet, payment)
            results[("refund", amount)] = r
        browser.close()
    return results


# ---- App ---------------------------------------------------------------------------------

def run_app(setup: Setup, base: str) -> dict:
    from appium import webdriver
    from appium.options.android import UiAutomator2Options

    from framework.app.device import Device, connected_serials
    from framework.app.pay_screen import ConfirmScreen
    from framework.app.proxy import TestProxy
    from framework.app.start_screen import StartScreen

    serial = os.environ.get("ANDROID_SERIAL") or (connected_serials() + [""])[0]
    device = Device(serial)
    device.install(str(APK))
    proxy = TestProxy(base).start()
    device.reverse(proxy.port)
    options = UiAutomator2Options()
    options.udid = serial
    options.no_reset = True
    options.set_capability("appium:disableIdLocatorAutocompletion", True)
    options.set_capability("appium:disableWindowAnimation", True)
    driver = webdriver.Remote(APPIUM_URL, options=options)
    driver.update_settings({"waitForIdleTimeout": 300})
    results = {}

    def fresh(wallet: str):
        device.start_app(proxy.url)
        return StartScreen(driver).wait().open_wallet(wallet)

    def outcome(screen, *hooks) -> str:
        hook = screen.wait_for_any(*hooks)
        return f"{hook}: {shown(screen.text(hook))}"

    def enter(screen, amount: str) -> bool:
        """輸入金額，回傳送出鈕能不能按（type_into 會等輸入框顯示新的值，按鈕在同一次重組裡更新）。"""
        screen.type_into("amount-input", amount)
        return screen.is_enabled("submit")

    try:
        for amount in PAY:
            wallet, _ = setup.wallet()
            pay = fresh(wallet).go_pay()
            r = {"continue": enter(pay, amount)}
            if r["continue"]:
                pay.tap("submit")
                confirm = ConfirmScreen(driver).wait()
                r["confirm"] = shown(confirm.amount())
                r["after"] = confirm.balance_after() if confirm.is_shown("confirm-balance-after") else None
                confirm.confirm()
                r["outcome"] = outcome(confirm, "result-balance", "error-message", "no-answer")
            r["server"] = setup.server(wallet)
            results[("pay", amount)] = r

        for amount in TOP_UP:
            wallet, _ = setup.wallet()
            top_up = fresh(wallet).go_top_up()
            r = {"continue": enter(top_up, amount)}
            if r["continue"]:
                top_up.tap("submit")
                r["outcome"] = outcome(top_up, "result-balance", "error-message", "no-answer")
            r["server"] = setup.server(wallet)
            results[("top up", amount)] = r

        for amount in REFUND:
            wallet, payment = setup.wallet(paid="30")
            detail = fresh(wallet).tab_history().open_payment()
            r = {"continue": enter(detail, amount)}
            if r["continue"]:
                detail.tap("submit")
                r["outcome"] = outcome(detail, "refund-done", "error-message", "no-answer")
                time.sleep(0.5)
                r["left"] = detail.refundable()
            r["server"] = setup.server(wallet, payment)
            results[("refund", amount)] = r
    finally:
        driver.quit()
        device.remove_reverse(proxy.port)
        proxy.stop()
    return results


# ---- 比較 --------------------------------------------------------------------------------

def main() -> int:
    if not (ROOT / "web" / "dist" / "index.html").is_file():
        print("build the front end first: cd web && npm ci && npm run build")
        return 2
    if not APK.is_file():
        print("build the app first: cd android && ./gradlew assembleDebug")
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        proc, base = start_api(str(Path(tmp) / "wallet.db"))
        try:
            setup = Setup(WalletAPI(base))
            web = run_web(setup, base)
            app = run_app(setup, base)
        finally:
            proc.terminate()
            proc.wait(timeout=10)

    differences = 0
    for key, on_web in web.items():
        on_app = app[key]
        same = on_web == on_app
        differences += not same
        print(f"{'same' if same else 'DIFFERENT':9} {key[0]:6} {key[1]!r:12} {on_web}")
        if not same:
            print(f"{'':9} {'':6} {'':12} app: {on_app}")
    print(f"\n{len(web)} inputs, {differences} different")
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
