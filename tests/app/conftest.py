"""Android App UI 測試的 fixture：裝置、Appium、測試代理伺服器、兩種螢幕設定、失敗時留下證據。

    pip install -r requirements-app.txt
    (cd android && ./gradlew assembleDebug)            # 測 debug 版：只有它讀啟動參數 apiBaseUrl
    appium --address 127.0.0.1 --port 4723             # 另一個終端機；需要 uiautomator2 driver
    ANDROID_SERIAL=127.0.0.1:5555 pytest tests/app --app

要裝置，所以加了 --app 才收集（tests/conftest.py）。加了 --app 卻少了東西（裝置、Appium 伺服器、
APK），每個測試都會失敗並說缺什麼：不能讓「什麼都沒跑」看起來像「全過」。

API 和資料庫沿用上一層 conftest 的 server、api、db：App 測完一樣直接查資料庫。App 不直接連
API，而是連測試代理伺服器（framework/app/proxy.py），由它轉給 API，需要時製造網路狀況。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import requests

try:
    from appium import webdriver
    from appium.options.android import UiAutomator2Options
except ImportError as e:
    # 會收集到這裡就表示要跑 App 測試：缺客戶端要講清楚，不能悄悄跳過
    raise ImportError(f"{e}. The Android app tests need: pip install -r requirements-app.txt") from e

from framework.app.device import Device, connected_serials
from framework.app.proxy import TestProxy
from framework.app.start_screen import StartScreen

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "reports" / "app"

# 每個案例在兩種螢幕設定各跑一次（SPEC.md §5）：360 x 640 dp 是常見的最小尺寸，
# 411 x 914 dp 是現在主流的長螢幕。用 wm 改同一台裝置的設定，結束後還原。
DISPLAYS = {
    "360x640": ("720x1280", 320),
    "411x914": ("1080x2400", 420),
}

# 畫面時間依裝置時區顯示（D-03），固定下來結果才穩定；和網頁測試相同
TIMEZONE = "Asia/Taipei"


def pytest_collection_modifyitems(config, items):
    """直接指定 pytest tests/app 時，pytest 不套用 tests/conftest.py 的忽略規則：沒加 --app 一樣跳過，並說原因。"""
    if config.getoption("--app"):
        return
    skip = pytest.mark.skip(reason="the Android app tests need a device: run with --app")
    for item in items:
        if Path(item.path).is_relative_to(Path(__file__).parent):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def device(request) -> Device:
    serial = request.config.getoption("--udid")
    if not serial:
        serials = connected_serials()
        if len(serials) != 1:
            pytest.fail(f"--app needs one device; adb sees {serials or 'none'}. "
                        "Choose with --udid or ANDROID_SERIAL", pytrace=False)
        serial = serials[0]
    d = Device(serial)
    if not d.is_booted():
        pytest.fail(f"device {serial} is not connected or has not finished booting", pytrace=False)
    return d


@pytest.fixture(scope="session")
def installed(request, device) -> None:
    """測試開始前安裝一次要測的 APK。"""
    apk = Path(request.config.getoption("--apk"))
    if not apk.is_file():
        pytest.fail(f"{apk} does not exist. Build it first: cd android && ./gradlew assembleDebug",
                    pytrace=False)
    device.install(str(apk))


@pytest.fixture(scope="session")
def proxy(server, device):
    """App 和 API 之間的測試代理伺服器；裝置經由 adb reverse 連到它。"""
    p = TestProxy(server["base_url"]).start()
    device.reverse(p.port)
    yield p
    device.remove_reverse(p.port)
    p.stop()


@pytest.fixture(scope="session", autouse=True)
def pinned_timezone(device):
    before = device.timezone()
    device.set_timezone(TIMEZONE)
    yield
    device.set_timezone(before or "GMT")


@pytest.fixture(scope="session", params=list(DISPLAYS), ids=list(DISPLAYS))
def display(request, device) -> str:
    """session 範圍的參數：pytest 會把同一種設定的測試排在一起，每種只切換一次。"""
    size, density = DISPLAYS[request.param]
    device.set_display(size, density)
    yield request.param
    device.set_display(None, None)


@pytest.fixture(scope="session")
def driver(request, device, installed):
    url = request.config.getoption("--appium-url")
    try:
        requests.get(url + "/status", timeout=5).raise_for_status()
    except requests.RequestException as e:
        pytest.fail(f"no Appium server at {url} ({e}). Start one: appium --address 127.0.0.1 --port 4723",
                    pytrace=False)
    options = UiAutomator2Options()
    options.udid = device.serial
    options.no_reset = True                       # 每個測試自己用 adb 重新啟動 App（device.start_app）
    options.new_command_timeout = 300
    # Compose 的 testTag 以 resource-id 呈現，但沒有「套件名:id/」前綴；不關掉自動補前綴就找不到
    options.set_capability("appium:disableIdLocatorAutocompletion", True)
    options.set_capability("appium:disableWindowAnimation", True)
    d = webdriver.Remote(url, options=options)
    # 每個動作之後 UiAutomator 預設最多等 10 秒讓畫面「靜止」；「處理中」的轉圈會讓它一直等
    d.update_settings({"waitForIdleTimeout": 300})
    yield d
    d.quit()


@pytest.fixture
def app(request, device, driver, display, proxy):
    """每個測試一個全新啟動的 App，停在開始畫面，API 位址指向測試代理伺服器。

    結束時檢查 App 沒有崩潰：畫面看起來對，程式也可能已經掛了（網頁測試檢查 JavaScript 例外，
    這裡檢查 Android 的崩潰紀錄）。失敗時留下截圖和畫面結構（UiAutomator 看到的樹）。
    """
    proxy.reset()
    device.clear_crashes()
    device.start_app(proxy.url)
    yield StartScreen(driver).wait()

    failed = getattr(request.node, "rep_call", None) is not None and request.node.rep_call.failed
    if failed:
        out = ARTIFACTS / re.sub(r"[^\w.-]+", "_", request.node.nodeid)
        out.mkdir(parents=True, exist_ok=True)
        driver.get_screenshot_as_file(str(out / "screen.png"))
        (out / "screen.xml").write_text(driver.page_source, encoding="utf-8")
    crashes = device.app_crashes()
    assert not crashes, f"the app crashed: {crashes}"


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """把每個階段的結果掛在 item 上，app fixture 收尾時才知道測試有沒有失敗。"""
    rep = yield
    setattr(item, f"rep_{rep.when}", rep)
    return rep
