"""IOS-018：文字樣式保有 Figma 的行高（SPEC.md §3、§5）。

SwiftUI 沒有「行高」可設：App 在行與行之間補行距，再在文字上下各補一半（Theme.swift），和 CSS、
Compose 一樣。原本只補了行距，單行文字只有字型本身的高度（15 pt 的字 18 pt 高，不是 Body 的 22），
每一列都比網頁和 Android 矮，整個畫面擠在一起：2.11 版三端並排量測時發現。

量的是相鄰兩列的距離，不是元素的外框：SwiftUI 回報的容器外框只包住裡面的文字、不含 padding，
兩列之間的距離才是一列真正的高度。期望值由設計的數字算出來，網頁和 Android 量起來也是這兩個數。
"""
import pytest

from testdata.factories import funded_wallet

pytestmark = pytest.mark.ios

HAIRLINE = 1
# 交易紀錄的一列：上下 spacing/md 12、Body/Strong 22、間距 2、Caption 18，再加列與列之間的細線
TRANSACTION_ROW = 12 + 22 + 2 + 18 + 12 + HAIRLINE          # 67
# 收據的一列：上下 spacing/md 12、Body/Regular 22，加細線
RECEIPT_ROW = 12 + 22 + 12 + HAIRLINE                       # 47
TOLERANCE = 1                                               # pt：外框會四捨五入


def pitches(frames) -> list[float]:
    return [round(b[1] - a[1], 1) for a, b in zip(frames, frames[1:])]


@pytest.mark.case_id("IOS-018")
def test_text_styles_keep_their_line_heights(app, api):
    wallet = funded_wallet(api, "100.00")
    api.pay(wallet, "10.00")
    api.pay(wallet, "20.00")

    home = app.open_wallet(wallet)
    home.recent_rows()                                       # 等最近三筆載入
    rows = home.frames("recent-item")
    assert len(rows) == 3, rows
    home_pitches = pitches(rows)

    receipt = home.go_pay().pay("5")
    rows = receipt.frames("receipt-row")
    assert len(rows) == 4, rows                               # Status、Time、Payment ID、Balance after
    receipt_pitches = pitches(rows)

    assert all(abs(p - TRANSACTION_ROW) <= TOLERANCE for p in home_pitches) and \
        all(abs(p - RECEIPT_ROW) <= TOLERANCE for p in receipt_pitches), \
        f"transaction rows {home_pitches} pt apart, expected {TRANSACTION_ROW}; " \
        f"receipt rows {receipt_pitches} pt apart, expected {RECEIPT_ROW}"
