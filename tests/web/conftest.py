"""網頁 UI 測試的 fixture：瀏覽器、兩種手機、失敗時留下截圖和 trace。

    pip install -r requirements-web.txt && python -m playwright install chromium
    (cd web && npm ci && npm run build)        # API 只在 web/dist 存在時才提供 /app
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

# 每個案例都在兩種手機設定上跑（web/SPEC.md §7）。都用 Chromium：iPhone 只模擬螢幕、觸控和
# User-Agent，不是真的 Safari。
PHONES = {"pixel7": "Pixel 7", "iphone14": "iPhone 14"}

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
def browser(playwright):
    b = playwright.chromium.launch()
    yield b
    b.close()


@pytest.fixture(params=list(PHONES), ids=list(PHONES))
def phone(request) -> str:
    return PHONES[request.param]


@pytest.fixture
def page(playwright, browser, phone, request):
    """每個測試一個全新的 context（cookie、storage 都不共用）。

    結束時檢查頁面沒有未處理的 JavaScript 例外：畫面看起來對，程式也可能已經壞了。
    """
    device = dict(playwright.devices[phone])
    device.pop("default_browser_type", None)        # iPhone 的預設是 webkit，這裡一律用 Chromium
    context = browser.new_context(**device, timezone_id=TIMEZONE)
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
