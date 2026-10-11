"""證明測試真的抓得到 bug：每打開一個埋 bug 開關，指定的測試就必須失敗。

    .venv/bin/python tools/fault_check.py              # 全部開關各跑一次（API + 網頁，網頁跑得起來的話）
    .venv/bin/python tools/fault_check.py race         # 只跑一個
    .venv/bin/python tools/fault_check.py --api-only   # 只看 API 測試（CI 的 fault-check 工作）
    .venv/bin/python tools/fault_check.py --web-only   # 只看網頁測試（CI 的 web 工作）
    .venv/bin/python tools/fault_check.py --app        # 再加上 Android App 的案例（要裝置）
    .venv/bin/python tools/fault_check.py --app-only   # 只看 App 的案例

只看「整套有沒有紅」不夠：可能是別的測試剛好壞掉。所以每個開關都列出
「應該被哪些測試抓到」，少一個就算失敗。

網頁案例（tests/web）也列在裡面，兩種手機各算一個。不帶參數時，網頁測試跑不起來的環境（沒裝
Playwright、前端沒建置）整個略過 tests/web 並印出原因：不然「Build it first」的失敗會被當成抓到
bug。--web-only 則一定要跑得起來，跑不起來直接失敗。
只存在於網頁裡的規則（WEB-007、012、013、014）伺服器開關弄不壞，由 web_mutation_check.py 證明。

App 案例（tests/app）兩種螢幕設定各算一個。App 測試要裝置，所以和 pytest 一樣要加 --app 才檢查；
加了卻跑不起來（沒裝 Appium 客戶端、沒建 APK、沒有裝置或 Appium 伺服器）直接失敗。每個開關只跑
指定給它的 App 案例（--target_case_ids）：整套 App 測試要幾分鐘，六個開關各跑一次太久，而這裡要
確認的只是「指定的案例有沒有失敗」。
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXPECTED = {
    "no_idempotency": ["test_same_key_twice_charges_once", "test_parallel_retries_with_one_key_charge_once",
                       "test_refund_retry_refunds_once", "test_transfer_retry_moves_money_once"],
    "race": ["test_parallel_payments_never_overdraw", "test_invariant_holds[balance_equals_ledger]"],
    "refund_overflow": ["test_partial_refunds_cannot_add_up_past_the_payment",
                        "test_parallel_refunds_never_exceed_the_payment"],
    "negative_amount": ["test_amount_formats[VAL-P08]", "test_amount_formats[VAL-T08]"],
    "float_math": ["test_float_unsafe_values_round_trip[19.99]"],
    "transfer_not_atomic": ["test_transfer_to_a_missing_wallet_takes_nothing",
                            "test_invariant_holds[no_orphan_transfer_entries]"],
}

PHONES = ("pixel7", "iphone14")
WEB_EXPECTED = {           # SPEC.md §8；{phone} 會換成每一種手機
    "no_idempotency": ["test_lost_response_then_retry_charges_once[{phone}]"],                     # WEB-008
    "refund_overflow": ["test_partial_refund_then_the_cumulative_limit[{phone}]"],                 # WEB-009
    "negative_amount": ["test_invalid_amount_is_refused_and_nothing_moves[{phone}-negative]"],     # WEB-005
    "float_math": ["test_top_up_19_99_keeps_every_cent[{phone}]"],                                 # WEB-004
}


DISPLAYS = ("360x640", "411x914")
APP_EXPECTED = {           # SPEC.md §8：（案例編號, 測試名稱）；{display} 會換成每一種螢幕設定
    "no_idempotency": [("APP-008", "test_lost_response_then_retry_charges_once[{display}]"),
                       ("APP-015", "test_process_death_with_the_outcome_unknown[{display}]")],
    "refund_overflow": [("APP-009", "test_partial_refund_then_the_cumulative_limit[{display}]")],
    "negative_amount": [("APP-005", "test_invalid_amount_is_refused_and_nothing_moves[{display}-negative]")],
    "float_math": [("APP-004", "test_top_up_19_99_keeps_every_cent[{display}]")],
}
APK = ROOT / "android" / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
APPIUM_URL = "http://127.0.0.1:4723"


def web_unavailable() -> str | None:
    """網頁測試跑不起來的原因；跑得起來回傳 None。"""
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError as e:
        return f"Playwright cannot be imported ({e}); pip install -r requirements-web.txt"
    if not (ROOT / "web" / "dist" / "index.html").is_file():
        return "the front end is not built (cd web && npm ci && npm run build)"
    return None


def app_unavailable() -> str | None:
    """App 測試跑不起來的原因；跑得起來回傳 None。"""
    try:
        import appium  # noqa: F401
    except ImportError as e:
        return f"the Appium client cannot be imported ({e}); pip install -r requirements-app.txt"
    if not APK.is_file():
        return "the debug app is not built (cd android && ./gradlew assembleDebug)"
    devices = [line.split()[0] for line in subprocess.run(["adb", "devices"], capture_output=True, text=True)
               .stdout.splitlines()[1:] if line.endswith("\tdevice")]
    if not os.environ.get("ANDROID_SERIAL") and len(devices) != 1:
        return f"adb sees {devices or 'no device'}; choose one with ANDROID_SERIAL"
    try:
        urllib.request.urlopen(APPIUM_URL + "/status", timeout=5)
    except OSError as e:
        return f"no Appium server at {APPIUM_URL} ({e})"
    return None


def expected_for(bug: str, api: bool, web: bool, app: bool) -> list[str]:
    names = list(EXPECTED[bug]) if api else []
    if web:
        names += [t.format(phone=p) for t in WEB_EXPECTED.get(bug, []) for p in PHONES]
    if app:
        names += [t.format(display=d) for _, t in APP_EXPECTED.get(bug, []) for d in DISPLAYS]
    return names


def failed_tests(bug: str, api: bool, web: bool, app: bool) -> set[str]:
    failed = set()
    if api or web:
        if api and web:
            scope = []
        elif web:
            scope = ["tests/web"]
        else:
            scope = ["--ignore=tests/web"]
        failed |= run_pytest(bug, scope)
    if app and APP_EXPECTED.get(bug):
        ids = ",".join(case for case, _ in APP_EXPECTED[bug])
        failed |= run_pytest(bug, ["tests/app", "--app", f"--target_case_ids={ids}"])
    return failed


def run_pytest(bug: str, scope: list[str]) -> set[str]:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                              f"--junitxml={report}", *scope],
                             cwd=ROOT, env={**os.environ, "BUGS": bug},
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if not report.is_file():
            # pytest 沒寫出報告（例如收集階段就失敗）：不能當成「沒有測試失敗」
            tail = "\n".join(run.stdout.splitlines()[-15:])
            raise SystemExit(f"pytest wrote no report for BUGS={bug} (exit code {run.returncode}):\n{tail}")
        failed = set()
        for case in ET.parse(report).iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                failed.add(case.get("name"))
        return failed


def main(args: list[str]) -> int:
    api_only, web_only, app_only = "--api-only" in args, "--web-only" in args, "--app-only" in args
    with_app = "--app" in args
    bugs = [a for a in args if not a.startswith("--")]
    unknown = [a for a in bugs if a not in EXPECTED] + \
        [a for a in args if a.startswith("--") and a not in ("--api-only", "--web-only", "--app-only", "--app")]
    if api_only + web_only + app_only > 1 or (with_app and (api_only or web_only or app_only)) or unknown:
        print("usage: fault_check.py [--api-only | --web-only | --app-only | --app] [bug ...]; "
              f"bugs: {', '.join(EXPECTED)}")
        return 2

    api = not (web_only or app_only)
    if api_only or app_only:
        web = False
        print(f"web cases: not part of this run ({'--api-only' if api_only else '--app-only'})")
    else:
        reason = web_unavailable()
        web = reason is None
        if web_only and not web:
            print(f"--web-only, but the web tests cannot run: {reason}")
            return 2
        print("web cases: checked" if web else f"web cases: NOT checked: {reason}")
    app = with_app or app_only
    if app:
        reason = app_unavailable()
        if reason:
            print(f"{'--app-only' if app_only else '--app'}, but the app tests cannot run: {reason}")
            return 2
        print("app cases: checked")
    else:
        print("app cases: not part of this run (add --app; they need a device)")
    selected = bugs or list(EXPECTED)
    for only, table, what in ((web_only, WEB_EXPECTED, "web"), (app_only, APP_EXPECTED, "app")):
        if only:
            # 沒有對應案例的開關（race、transfer_not_atomic）不用跑
            selected = [b for b in selected if table.get(b)]
            if not selected:
                print(f"no {what} case is assigned to {', '.join(bugs)}")
                return 2

    missed = 0
    for bug in selected:
        failed = failed_tests(bug, api, web, app)
        not_caught = [t for t in expected_for(bug, api, web, app) if t not in failed]
        status = "CAUGHT" if not not_caught else "MISSED"
        missed += bool(not_caught)
        print(f"{bug:<20} {status}  ({len(failed)} tests failed)")
        for t in not_caught:
            print(f"    expected to fail but passed: {t}")
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
