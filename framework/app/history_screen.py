"""交易紀錄（History 分頁）：最新的在最上面，依日期分組。"""
from __future__ import annotations

from dataclasses import dataclass

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException

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
        """目前畫面上看得到的列，由上而下。被切到、少了某一行字的列不算（捲動之後會再讀到）。"""
        rows = []
        for item in self._all("history-item"):
            try:
                rows.append(HistoryRow(*(item.find_element(AppiumBy.ID, tag).text
                                         for tag in ("item-title", "item-amount", "item-balance"))))
            except NoSuchElementException:
                pass
        return rows

    def rows(self) -> list[HistoryRow]:
        """所有的列，由上而下。

        Compose 不會把畫面外的元素交給無障礙服務（UiAutomator2 的 allowInvisibleElements 也沒用），
        所以邊捲邊讀：每次捲六成畫面，前後兩次讀到的列一定有重疊，用重疊的部分接起來。每一筆的
        「變動後餘額」都和上一筆不同，連續幾列完全相同的情況不會發生；真的接不起來就直接失敗，
        不會悄悄漏掉幾列。
        """
        self.scroll_to_top()
        rows = self.rows_on_screen()
        more = True
        for _ in range(50):
            if not more:
                break
            more = self.scroll("down")
            rows = _join(rows, self.rows_on_screen())
        return rows

    def open_payment(self, index: int = 0):
        """打開畫面上第 index 個付款（只有付款列可以點開，D-05）。"""
        from framework.app.payment_detail_screen import PaymentDetailScreen
        self.wait_for("open-payment")
        self._all("open-payment")[index].click()
        return PaymentDetailScreen(self.driver).wait()


def _join(above: list[HistoryRow], below: list[HistoryRow]) -> list[HistoryRow]:
    """把捲動前後讀到的兩段接起來：找最長的「above 的結尾 = below 的開頭」。"""
    if not below:
        return above
    for k in range(min(len(above), len(below)), 0, -1):
        if above[-k:] == below[:k]:
            return above + below[k:]
    raise AssertionError(f"no overlap between two scroll positions: {above[-3:]} / {below[:3]}")
