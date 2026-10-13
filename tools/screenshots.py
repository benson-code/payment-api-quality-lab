"""README 用的截圖：同一組畫面，網頁、Android App、iOS App 各拍一張，放在 docs/screenshots/。

    .venv/bin/python tools/screenshots.py              # 網頁和 Android App（App 要裝置、Appium、debug APK）
    .venv/bin/python tools/screenshots.py --web-only
    .venv/bin/python tools/screenshots.py --ios        # 再加上 iOS App（macOS、開著的模擬器、建置好的 App）
    .venv/bin/python tools/screenshots.py --ios-only

兩邊用同樣的示範資料（tools/demo.py 的劇本）、同樣的 360 x 640 尺寸、同樣的時區，所以並排時看得出
兩個客戶端是同一套畫面。畫面改了就重跑，截圖不會和程式脫節。iOS 是例外：模擬器的螢幕沒辦法改成
360 x 640，用開著的那台（iPhone 的長螢幕），縮成和其他截圖一樣寬；時區用啟動時的 TZ 環境變數固定。
iOS App 還沒有交易紀錄和付款明細，只拍 home、confirm、no-answer、replayed。

    home            首頁：餘額、三個動作、最近三筆
    history         交易紀錄
    payment         付款明細：退過一部分、還能退多少、退款紀錄
    confirm         付款的確認頁
    no-answer       伺服器扣了款、回應卻遺失：「沒有回應，重試是安全的」
    replayed        重試之後的收據：「這筆付款之前已經完成，沒有再扣一次」
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from demo import seed  # noqa: E402
from parity_check import APK, APPIUM_URL, start_api  # noqa: E402

from framework.wallet_api import WalletAPI  # noqa: E402

OUT = ROOT / "docs" / "screenshots"
IOS_APP = ROOT / "ios" / "build" / "Build" / "Products" / "Debug-iphonesimulator" / "Wallet.app"
TIMEZONE = "Asia/Taipei"
AMOUNT = "120"              # 確認頁和「沒有回應」那筆付款


def the_450_payment(api: WalletAPI, wallet: str) -> str:
    """劇本裡退過一部分的那筆付款（450.00）。"""
    return next(t["ref_id"] for t in api.transactions(wallet).json()["transactions"]
                if t["type"] == "PAYMENT" and t["amount"] == "-450.00")


def web(api: WalletAPI, base: str) -> None:
    from playwright.sync_api import sync_playwright

    from framework.web.history_page import HistoryPage
    from framework.web.home_page import HomePage
    from framework.web.network import lose_response
    from framework.web.pay_page import PayPage
    from framework.web.payment_detail_page import PaymentDetailPage
    from framework.web.receipt_page import ReceiptPage

    wallet = seed(api)
    app_url = base + "/app/"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 360, "height": 640}, device_scale_factor=2,
                                   is_mobile=True, has_touch=True, timezone_id=TIMEZONE).new_page()

        def shot(name: str) -> None:
            page.wait_for_timeout(400)
            page.screenshot(path=str(OUT / f"web-{name}.png"))
            print(f"web-{name}.png", flush=True)

        HomePage(page, app_url).open(wallet)
        shot("home")
        HistoryPage(page, app_url).open(wallet)
        shot("history")
        PaymentDetailPage(page, app_url).open(wallet, the_450_payment(api, wallet))
        shot("payment")
        confirm = PayPage(page, app_url).open(wallet).continue_with(AMOUNT)
        shot("confirm")
        with lose_response(page, "**/payments"):
            confirm.confirm()
            confirm.tid("no-answer").wait_for()
        shot("no-answer")
        confirm.retry()
        ReceiptPage(page, app_url).wait().tid("replayed").wait_for()
        shot("replayed")
        browser.close()


def app(api: WalletAPI, base: str) -> None:
    from appium import webdriver
    from appium.options.android import UiAutomator2Options

    from framework.app.device import Device, connected_serials
    from framework.app.proxy import TestProxy
    from framework.app.start_screen import StartScreen

    wallet = seed(api)
    device = Device(os.environ.get("ANDROID_SERIAL") or (connected_serials() + [""])[0])
    device.install(str(APK))
    timezone_before = device.timezone()
    device.set_timezone(TIMEZONE)
    device.set_display("720x1280", 320)              # 360 x 640 dp，和網頁的截圖一樣大
    proxy = TestProxy(base).start()
    device.reverse(proxy.port)
    options = UiAutomator2Options()
    options.udid = device.serial
    options.no_reset = True
    options.set_capability("appium:disableIdLocatorAutocompletion", True)
    options.set_capability("appium:disableWindowAnimation", True)
    driver = webdriver.Remote(APPIUM_URL, options=options)
    driver.update_settings({"waitForIdleTimeout": 300})

    def shot(name: str) -> None:
        time.sleep(0.6)
        driver.get_screenshot_as_file(str(OUT / f"app-{name}.png"))
        print(f"app-{name}.png", flush=True)

    def home():
        device.start_app(proxy.url)
        return StartScreen(driver).wait().open_wallet(wallet)

    try:
        home()
        shot("home")
        history = home().tab_history()
        shot("history")
        history.open_payment(index=1)                  # 由新到舊：30.00、450.00、1,280.50
        shot("payment")
        confirm = home().go_pay().continue_with(AMOUNT)
        shot("confirm")
        with proxy.lose_response("/payments"):
            confirm.confirm()
            confirm.wait_for("no-answer")
        shot("no-answer")
        confirm.retry()
        confirm.wait_for_receipt().wait_for("replayed")
        shot("replayed")
    finally:
        driver.quit()
        device.remove_reverse(proxy.port)
        proxy.stop()
        device.set_display(None, None)
        device.set_timezone(timezone_before or "GMT")


def ios(api: WalletAPI, base: str) -> None:
    from appium import webdriver
    from appium.options.ios import XCUITestOptions

    from framework.app.proxy import TestProxy
    from framework.ios.simulator import BUNDLE_ID, Simulator, booted
    from framework.ios.start_screen import StartScreen

    wallet = seed(api)
    running = [d["udid"] for d in booted()]
    udid = os.environ.get("IOS_UDID") or (running[0] if len(running) == 1 else None)
    if not udid:
        raise SystemExit(f"boot one simulator, or choose one with IOS_UDID (booted: {running or 'none'})")
    Simulator(udid).install(str(IOS_APP))
    proxy = TestProxy(base).start()                    # 模擬器和 Mac 共用網路：不用 adb reverse
    options = XCUITestOptions()
    options.udid = udid
    options.no_reset = True
    driver = webdriver.Remote(APPIUM_URL, options=options)

    def shot(name: str) -> None:
        time.sleep(0.6)
        path = OUT / f"ios-{name}.png"
        driver.get_screenshot_as_file(str(path))
        subprocess.run(["sips", "--resampleWidth", "720", str(path)], check=True, capture_output=True)
        print(path.name, flush=True)

    def home():
        driver.terminate_app(BUNDLE_ID)
        driver.execute_script("mobile: launchApp", {"bundleId": BUNDLE_ID, "arguments": ["-apiBaseUrl", proxy.url],
                                                    "environment": {"TZ": TIMEZONE}})
        return StartScreen(driver).wait().open_wallet(wallet)

    try:
        home().recent_rows()                           # 等最近活動載入
        shot("home")
        confirm = home().go_pay().continue_with(AMOUNT)
        shot("confirm")
        with proxy.lose_response("/payments"):
            confirm.confirm()
            confirm.wait_for("no-answer")
        shot("no-answer")
        confirm.retry()
        confirm.wait_for_receipt().wait_for("replayed")
        shot("replayed")
    finally:
        driver.quit()
        proxy.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="Screenshots of the web page and the apps for the README.")
    only = parser.add_mutually_exclusive_group()
    only.add_argument("--web-only", action="store_true")
    only.add_argument("--ios-only", action="store_true")
    parser.add_argument("--ios", action="store_true", help="also the iOS app")
    args = parser.parse_args()
    with_web = not args.ios_only
    with_android = not (args.web_only or args.ios_only)
    with_ios = args.ios or args.ios_only
    if with_web and not (ROOT / "web" / "dist" / "index.html").is_file():
        print("build the front end first: cd web && npm ci && npm run build")
        return 2
    if with_android and not APK.is_file():
        print("build the app first (cd android && ./gradlew assembleDebug), or use --web-only")
        return 2
    if with_ios and not (IOS_APP / "Info.plist").is_file():
        print("build the iOS app first (ios/README.md)")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        proc, base = start_api(str(Path(tmp) / "wallet.db"))
        try:
            api = WalletAPI(base)
            if with_web:
                web(api, base)
            if with_android:
                app(api, base)
            if with_ios:
                ios(api, base)
        finally:
            proc.terminate()
            proc.wait(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
