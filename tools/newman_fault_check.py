"""證明 Postman collection 也抓得到 bug：每打開一個埋 bug 開關，指定的案例就必須失敗。

    python tools/newman_fault_check.py                 # 全部開關各跑一次
    python tools/newman_fault_check.py float_math      # 只跑一個

做法跟 tools/fault_check.py 一樣，只是跑的是 postman/run-newman.sh，
從 Newman 的 JSON 報告讀出失敗的案例編號（測試名稱開頭的 PM-xx、AMT-xx）。
需要 newman 和 newman-reporter-htmlextra 在 PATH 上。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# race 不在這裡：Postman 一次只送一個請求，造不出併發，這個 bug 交給 pytest 的 test_concurrency.py
EXPECTED = {
    "no_idempotency": ["PM-09", "PM-10", "PM-11"],
    "refund_overflow": ["PM-15"],
    "negative_amount": ["AMT-05", "AMT-06"],
    "float_math": ["AMT-03", "AMT-04"],
    "transfer_not_atomic": ["PM-25"],
}


def failed_cases(bug: str) -> set[str]:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([str(ROOT / "postman" / "run-newman.sh")], cwd=ROOT,
                       env={**os.environ, "BUGS": bug, "NEWMAN_OUT": tmp},
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        failed = set()
        for report in ("main.json", "amounts.json"):
            for f in json.loads((Path(tmp) / report).read_text())["run"]["failures"]:
                failed.add(f["error"]["test"].split()[0])
        return failed


def main(bugs: list[str]) -> int:
    missed = 0
    for bug in bugs:
        failed = failed_cases(bug)
        not_caught = [c for c in EXPECTED[bug] if c not in failed]
        status = "CAUGHT" if not not_caught else "MISSED"
        missed += bool(not_caught)
        print(f"{bug:<20} {status}  (failed: {', '.join(sorted(failed))})")
        for c in not_caught:
            print(f"    expected to fail but passed: {c}")
    return 1 if missed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or list(EXPECTED)))
