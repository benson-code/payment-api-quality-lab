"""交易紀錄（History 分頁）：最新的在最上面，依日期分組。"""
from __future__ import annotations

from framework.ios.base import IosScreen
from framework.ios.home_screen import EntryRow, entry_rows

HistoryRow = EntryRow           # 和 framework/app/history_screen.py 同名


class HistoryScreen(IosScreen):
    """App 的列沒有網頁的 data-type、data-entry-id：藏在列裡的機器可讀文字會被 VoiceOver 念出來
    （SPEC.md §7）。所以和資料庫對照時靠順序和標題。"""

    def wait(self) -> HistoryScreen:
        self.wait_for_any("history-item", "empty", "error-message")
        return self

    def rows(self) -> list[HistoryRow]:
        """所有的列，由上而下，包括捲動區域外的。"""
        return entry_rows(self, "history-item")

    def open_payment(self, index: int = 0):
        """打開第 index 個付款（只有付款列可以點開，D-05）。畫面外的列，XCUITest 點之前會自己捲過去。"""
        from framework.ios.payment_detail_screen import PaymentDetailScreen
        self.wait_for("open-payment")
        self._all("open-payment")[index].click()
        return PaymentDetailScreen(self.driver).wait()

    def tab_home(self):
        from framework.ios.home_screen import HomeScreen
        self.tap("tab-home")
        return HomeScreen(self.driver).wait()
