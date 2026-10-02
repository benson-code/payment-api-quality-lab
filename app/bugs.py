"""故意埋 bug 的開關：用來證明測試真的抓得到錯。

    BUGS=race,refund_overflow .venv/bin/uvicorn app.main:app

正常執行時一個都不開。每個開關模擬一種真實會發生的支付 bug：

    no_idempotency   不檢查 Idempotency-Key            → 重送就重複扣款
    race             扣款沒有鎖、讀完餘額才慢慢寫回    → 併發時超扣、餘額對不上 ledger
    refund_overflow  只檢查單筆退款，不看已退累計      → 分次退款可以退超過原付款
    negative_amount  金額允許負數                      → 付負數等於幫自己加錢
    float_math       用浮點數算金額                    → "19.99" 變成 1998 分，少一分錢
    transfer_not_atomic  轉帳先扣款、另開交易才入帳      → 收款錢包不存在時，錢扣了卻沒進任何地方
"""
from __future__ import annotations

import os

KNOWN = {"no_idempotency", "race", "refund_overflow", "negative_amount", "float_math",
         "transfer_not_atomic"}

ACTIVE = frozenset(b for b in os.environ.get("BUGS", "").split(",") if b)
if ACTIVE - KNOWN:
    # 拼錯字要直接啟動失敗，不然「測試沒紅」可能只是開關根本沒打開
    raise SystemExit(f"unknown BUGS: {sorted(ACTIVE - KNOWN)}; choose from {sorted(KNOWN)}")


def on(name: str) -> bool:
    return name in ACTIVE
