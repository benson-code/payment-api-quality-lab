"""證明測試真的抓得到 bug：每打開一個埋 bug 開關，指定的測試就必須失敗。

    .venv/bin/python tools/fault_check.py              # 全部開關各跑一次
    .venv/bin/python tools/fault_check.py race         # 只跑一個

只看「整套有沒有紅」不夠：可能是別的測試剛好壞掉。所以每個開關都列出
「應該被哪些測試抓到」，少一個就算失敗。
"""
from __future__ import annotations

import os
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


def failed_tests(bug: str) -> set[str]:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        f"--junitxml={report}"],
                       cwd=ROOT, env={**os.environ, "BUGS": bug},
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        failed = set()
        for case in ET.parse(report).iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                failed.add(case.get("name"))
        return failed


def main(bugs: list[str]) -> int:
    missed = 0
    for bug in bugs:
        failed = failed_tests(bug)
        not_caught = [t for t in EXPECTED[bug] if t not in failed]
        status = "CAUGHT" if not not_caught else "MISSED"
        missed += bool(not_caught)
        print(f"{bug:<20} {status}  ({len(failed)} tests failed)")
        for t in not_caught:
            print(f"    expected to fail but passed: {t}")
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or list(EXPECTED)))
