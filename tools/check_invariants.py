"""對帳：對一個資料庫跑全部不變式，查到任何一列就失敗。

    python tools/check_invariants.py wallet.db

壓測後一定要跑：k6 只看得到回應快不快、狀態碼對不對，帳對不對要查資料庫。
不變式跟 tests/test_db_invariants.py 用的是同一份（framework/db.py 的 INVARIANTS），
另外多一條壓測特有的：每一筆付款都要對應一把 Idempotency-Key。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from framework.db import INVARIANTS, Database  # noqa: E402

# 付款和記住 key 在同一個交易裡：付款筆數 ≠ key 數，代表有付款沒經過冪等檢查（重送就會重複扣款）
PAYMENTS_HAVE_KEYS = """
    SELECT (SELECT COUNT(*) FROM payments) AS payments,
           (SELECT COUNT(*) FROM idempotency_keys WHERE scope = 'payment') AS payment_keys
    WHERE payments <> payment_keys"""


def main(path: str) -> int:
    if not Path(path).exists():
        print(f"no such database: {path}")
        return 1
    db = Database(path)
    try:
        print(f"wallets {db.count('wallets')}, payments {db.count('payments')}, "
              f"refunds {db.count('refunds')}, transfers {db.count('transfers')}, ledger {db.count('ledger')}")
        checks = dict(INVARIANTS)
        checks["payments_have_idempotency_keys"] = PAYMENTS_HAVE_KEYS
        broken = 0
        for name, sql in checks.items():
            rows = [tuple(r) for r in db.all(sql)]
            broken += bool(rows)
            print(f"{name:<32} {'OK' if not rows else f'BROKEN ({len(rows)} rows)'}")
            for r in rows[:5]:
                print(f"    {r}")
        return 1 if broken else 0
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(sys.argv[1]))
