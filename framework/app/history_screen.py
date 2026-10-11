"""交易紀錄（History 分頁）：最新的在最上面，依日期分組。"""
from __future__ import annotations

from dataclasses import dataclass

from appium.webdriver.common.appiumby import AppiumBy

from framework.app.base import AppScreen


@dataclass(frozen=True)
class HistoryRow:
    title: str          # 使用者看到的類型，例如 "Payment"、"Top-up"
    amount: str         # 畫面上的樣子，例如 "+100.00"、"−30.00"
    balance: str        # 這筆之後的餘額，例如 "70.00"


class HistoryScreen(AppScreen):
    """App 的列沒有網頁的 data-type、data-entry-id：藏在列裡的機器可讀文字會被螢幕閱讀器念出來
    （SPEC.md §7）。所以和資料庫對照時靠順序和標題。"""

    def wait(self) -> HistoryScreen:
        self.wait_for_any("history-item", "empty")
        return self

    def rows_on_screen(self) -> list[HistoryRow]:
        """目前畫面上看得到的列，由上而下。UiAutomator 只看得到畫面上的元素：一個畫面放不下的
        紀錄要捲動才讀得到（APP-010 處理）。"""
        rows = []
        for item in self._all("history-item"):
            child = lambda tag: item.find_element(AppiumBy.ID, tag).text
            rows.append(HistoryRow(child("item-title"), child("item-amount"), child("item-balance")))
        return rows
