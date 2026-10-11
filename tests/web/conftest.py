"""網頁 UI 測試的 fixture：三種瀏覽器設定（Chromium、WebKit、Firefox）、失敗時留下截圖和 trace。

    pip install -r requirements-web.txt && python -m playwright install chromium webkit firefox
    sudo python -m playwright install-deps webkit     # Linux 上第一次：WebKit 需要的系統函式庫
    (cd web && npm ci && npm run build)               # API 只在 web/dist 存在時才提供 /app
    pytest tests/web

API 和資料庫沿用上一層 conftest 的 server、api、db：網頁測完一樣直接查資料庫。

沒裝 Playwright 時整個目錄跳過（只跑 API 測試的環境不需要瀏覽器），pytest -ra 會印出原因。
裝了 Playwright 卻沒有建置前端，則每個網頁測試都會失敗：不能讓「什麼都沒跑」看起來像「全過」。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import requests

pytest.importorskip("playwright.sync_api", reason="web UI tests need: pip install -r requirements-web.txt")

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "reports" / "web"

# 每個案例在三種設定上各跑一次（SPEC.md §8），每種用它真正的瀏覽器引擎：Android 手機用 Chromium
# （Chrome 的引擎），iPhone 用 WebKit（Safari 的引擎），桌機用 Firefox。
# 設定名稱 → （Playwright 的裝置設定, 引擎）
PROFILES = {
    "pixel7": ("Pixel 7", "chromium"),
    "iphone14": ("iPhone 14", "webkit"),
    "desktop-firefox": ("Desktop Firefox", "firefox"),
}

# 畫面時間依裝置時區顯示（D-03），固定下來結果才穩定
TIMEZONE = "Asia/Taipei"


@pytest.fixture(scope="session")
def app_url(server) -> str:
    url = server["base_url"] + "/app/"
    r = requests.get(url, timeout=5)
    if r.status_code != 200 or 'id="root"' not in r.text:
        pytest.fail(f"{url} does not serve the front end (HTTP {r.status_code}). "
                    "Build it first: cd web && npm ci && npm run build", pytrace=False)
    return url


@pytest.fixture(scope="session")
def playwright():
    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browsers(playwright):
    """每種引擎第一次用到時才啟動，整個測試過程共用。"""
    launched = {}

    def get(engine: str):
        if engine not in launched:
            launched[engine] = getattr(playwright, engine).launch()
        return launched[engine]

    yield get
    for b in launched.values():
        b.close()


@pytest.fixture(params=list(PROFILES), ids=list(PROFILES))
def profile(request) -> tuple[str, str]:
    return PROFILES[request.param]


@pytest.fixture
def page(playwright, browsers, profile, request):
    """每個測試一個全新的 context（cookie、storage 都不共用）。

    結束時檢查頁面沒有未處理的 JavaScript 例外：畫面看起來對，程式也可能已經壞了。
    """
    device_name, engine = profile
    device = dict(playwright.devices[device_name])
    device.pop("default_browser_type", None)        # 引擎由 PROFILES 決定，不是 context 的設定
    context = browsers(engine).new_context(**device, timezone_id=TIMEZONE)
    context.tracing.start(screenshots=True, snapshots=True)
    pg = context.new_page()
    js_errors: list[str] = []
    pg.on("pageerror", lambda e: js_errors.append(str(e)))
    yield pg

    failed = getattr(request.node, "rep_call", None) is not None and request.node.rep_call.failed
    if failed:
        out = ARTIFACTS / re.sub(r"[^\w.-]+", "_", request.node.nodeid)
        out.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(out / "screen.png"), full_page=True)
        context.tracing.stop(path=str(out / "trace.zip"))     # 用 playwright show-trace 打開
    else:
        context.tracing.stop()
    context.close()
    assert not js_errors, f"uncaught JavaScript errors: {js_errors}"


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """把每個階段的結果掛在 item 上，page fixture 收尾時才知道測試有沒有失敗。"""
    rep = yield
    setattr(item, f"rep_{rep.when}", rep)
    return rep
