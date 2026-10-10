"""證明測試真的抓得到 bug：每打開一個埋 bug 開關，指定的測試就必須失敗。

    .venv/bin/python tools/fault_check.py              # 全部開關各跑一次
    .venv/bin/python tools/fault_check.py race         # 只跑一個

只看「整套有沒有紅」不夠：可能是別的測試剛好壞掉。所以每個開關都列出
「應該被哪些測試抓到」，少一個就算失敗。

網頁案例（tests/web）也列在裡面，兩種手機各算一個。網頁測試跑不起來的環境（沒裝 Playwright、
前端沒建置）整個略過 tests/web 並印出原因：不然「Build it first」的失敗會被當成抓到 bug。
只存在於網頁裡的規則（WEB-007、012、013、014）伺服器開關弄不壞，由 web_mutation_check.py 證明。
"""
from __future__ import annotations

import os
import importlib.util
import subprocess
import sys
import tempfile
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
WEB_EXPECTED = {           # web/SPEC.md §7；{phone} 會換成每一種手機
    "no_idempotency": ["test_lost_response_then_retry_charges_once[{phone}]"],                     # WEB-008
    "refund_overflow": ["test_partial_refund_then_the_cumulative_limit[{phone}]"],                 # WEB-009
    "negative_amount": ["test_invalid_amount_is_refused_and_nothing_moves[{phone}-negative]"],     # WEB-005
    "float_math": ["test_top_up_19_99_keeps_every_cent[{phone}]"],                                 # WEB-004
}


def web_unavailable() -> str | None:
    """網頁測試跑不起來的原因；跑得起來回傳 None。"""
    if importlib.util.find_spec("playwright") is None:
        return "Playwright is not installed (pip install -r requirements-web.txt)"
    if not (ROOT / "web" / "dist" / "index.html").is_file():
        return "the front end is not built (cd web && npm ci && npm run build)"
    return None


def expected_for(bug: str, web: bool) -> list[str]:
    names = list(EXPECTED[bug])
    if web:
        names += [t.format(phone=p) for t in WEB_EXPECTED.get(bug, []) for p in PHONES]
    return names


def failed_tests(bug: str, web: bool) -> set[str]:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        f"--junitxml={report}", *([] if web else ["--ignore=tests/web"])],
                       cwd=ROOT, env={**os.environ, "BUGS": bug},
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        failed = set()
        for case in ET.parse(report).iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                failed.add(case.get("name"))
        return failed


def main(bugs: list[str]) -> int:
    reason = web_unavailable()
    web = reason is None
    print("web cases: checked" if web else f"web cases: NOT checked: {reason}")
    missed = 0
    for bug in bugs:
        failed = failed_tests(bug, web)
        not_caught = [t for t in expected_for(bug, web) if t not in failed]
        status = "CAUGHT" if not not_caught else "MISSED"
        missed += bool(not_caught)
        print(f"{bug:<20} {status}  ({len(failed)} tests failed)")
        for t in not_caught:
            print(f"    expected to fail but passed: {t}")
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or list(EXPECTED)))
