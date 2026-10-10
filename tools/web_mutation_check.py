"""證明只存在於網頁裡的規則也有測試守著：故意改壞前端，對應的案例就必須失敗。

    PATH=~/.local/node20/bin:$PATH .venv/bin/python tools/web_mutation_check.py      # 全部
    PATH=~/.local/node20/bin:$PATH .venv/bin/python tools/web_mutation_check.py no_in_flight_guard

fault_check.py 用伺服器的埋 bug 開關證明測試抓得到錯，但 WEB-007、012、013、014 守的規則寫在
網頁裡：連點的「送出中」旗標、處理中的按鈕、付款嘗試的 key、儲值不提供重試。伺服器怎麼改都
弄不壞它們。所以這裡改的是網頁原始碼：每個「突變」把一小段程式換掉，另外編譯一份前端，讓 API
改掛這份（WEB_DIST 環境變數），再跑指定的案例。案例沒有失敗 = 這段程式壞了也沒人發現。

需要 Node（編譯前端）、requirements-web.txt，以及 web/node_modules（cd web && npm ci）。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

# 名稱: (檔案, 原本的程式, 改壞後的程式, 必須失敗的案例, 說明)
MUTANTS = {
    "no_in_flight_guard": (
        "src/useAttempt.js",
        "    if (inFlight.current) return;\n    inFlight.current = true;",
        "    inFlight.current = true;",
        ["WEB-007"],
        "remove the flag that ignores a second tap while a request is in flight",
    ),
    "confirm_stays_enabled": (
        "src/screens/Pay.jsx",
        'data-testid="confirm-pay" disabled={pending}',
        'data-testid="confirm-pay"',
        ["WEB-012"],
        "Confirm payment stays enabled while processing",
    ),
    "back_forgets_the_attempt": (
        "src/screens/Pay.jsx",
        "    if (state.kind !== 'unknown') attempt.reset();\n    setStep('amount');",
        "    attempt.reset();\n    setStep('amount');",
        ["WEB-013"],
        "Back from Confirm drops the pending attempt (the first two-step version did this)",
    ),
    "top_up_offers_retry": (
        "src/screens/TopUp.jsx",
        "        {state.kind === 'unknown' && (",
        "        {state.kind === 'unknown' && <button type=\"button\" data-testid=\"retry\""
        " onClick={() => attempt.submit(amount)}>Retry</button>}\n        {state.kind === 'unknown' && (",
        ["WEB-014"],
        "offer Retry after a top-up gets no answer",
    ),
}


def build(mutant: str, out: Path) -> None:
    """複製 web/（node_modules 用連結），套用突變，編譯到 out。"""
    path, before, after, _, _ = MUTANTS[mutant]
    src = out.parent / "web"
    shutil.copytree(WEB, src, ignore=shutil.ignore_patterns("node_modules", "dist"))
    (src / "node_modules").symlink_to(WEB / "node_modules")
    target = src / path
    code = target.read_text()
    # 原本的程式必須剛好出現一次：網頁改版後突變沒套上，會在這裡停下，而不是假裝驗證過
    if code.count(before) != 1:
        raise SystemExit(f"{mutant}: the code to mutate was found {code.count(before)} times in {path}; "
                         "update MUTANTS")
    target.write_text(code.replace(before, after))
    npm = shutil.which("npm") or sys.exit("npm not found: put Node on PATH")
    subprocess.run([npm, "run", "build", "--", "--outDir", str(out), "--emptyOutDir"], cwd=src,
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def run_cases(case_ids: list[str], dist: Path, report: Path) -> tuple[set[str], set[str]]:
    """回傳 (失敗的測試, 出錯的測試)。只有 failure 算抓到：error 是環境問題，不是突變被發現。"""
    subprocess.run([sys.executable, "-m", "pytest", "tests/web", "-q", "-p", "no:cacheprovider",
                    f"--target_case_ids={','.join(case_ids)}", f"--junitxml={report}"],
                   cwd=ROOT, env={**os.environ, "WEB_DIST": str(dist)},
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    failed, errored = set(), set()
    for case in ET.parse(report).iter("testcase"):
        if case.find("failure") is not None:
            failed.add(case.get("name"))
        if case.find("error") is not None:
            errored.add(case.get("name"))
    return failed, errored


def main(names: list[str]) -> int:
    survived = 0
    for name in names:
        _, _, _, case_ids, what = MUTANTS[name]
        with tempfile.TemporaryDirectory() as tmp:
            dist = Path(tmp) / "dist"
            build(name, dist)
            failed, errored = run_cases(case_ids, dist, Path(tmp) / "junit.xml")
        if errored:
            status = "ERROR"
        elif failed:
            status = "KILLED"
        else:
            status = "SURVIVED"
        survived += status != "KILLED"
        print(f"{name:<26} {status:<9} {','.join(case_ids)}: {what}")
        for t in sorted(failed):
            print(f"    failed as it should: {t}")
        for t in sorted(errored):
            print(f"    error (not a detection): {t}")
    return 1 if survived else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or list(MUTANTS)))
