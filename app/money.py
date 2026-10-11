"""金額處理：API 用字串、資料庫用整數「分」，中間不經過浮點數。

    "100.50"  --parse_amount-->  10050  --format_cents-->  "100.50"
"""
from __future__ import annotations

import re
from decimal import Decimal

from app import bugs
from app.errors import ApiError

# 整數最多 12 位，小數最多 2 位；不接受正負號、空白、科學記號。
# 寫 [0-9] 不寫 \d：Python 的 \d 也比對全形「１００」、阿拉伯-印度數字「٣٠」等 Unicode 數字（VAL-P16/17）
AMOUNT_RE = re.compile(r"[0-9]{1,12}(\.[0-9]{1,2})?")
BUGGY_SIGNED_RE = re.compile(r"-?[0-9]{1,12}(\.[0-9]{1,2})?")        # bug: negative_amount


def parse_amount(raw: object) -> int:
    """把 API 收到的金額字串轉成「分」。不合法一律 400。"""
    pattern = BUGGY_SIGNED_RE if bugs.on("negative_amount") else AMOUNT_RE
    if not isinstance(raw, str) or not pattern.fullmatch(raw):
        raise ApiError(400, "INVALID_AMOUNT",
                       "amount must be a string like '100' or '100.50' (max 2 decimals)")
    if bugs.on("float_math"):
        cents = int(float(raw) * 100)         # bug: 19.99 * 100 = 1998.9999999999998 → 1998
    else:
        cents = int(Decimal(raw) * 100)
    if cents <= 0 and not bugs.on("negative_amount"):
        raise ApiError(400, "INVALID_AMOUNT", "amount must be greater than 0")
    return cents


def format_cents(cents: int) -> str:
    """分 → 固定兩位小數的字串。10050 → '100.50'、-5 → '-0.05'。"""
    sign = "-" if cents < 0 else ""
    return f"{sign}{abs(cents) // 100}.{abs(cents) % 100:02d}"
