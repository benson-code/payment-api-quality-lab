"""首頁（Home 分頁）：餘額、三個動作、最近三筆。

畫面上的錢包編號是遮罩過的（D-04），完整的編號 App 不會顯示：測試從建立錢包的 API 回應拿
（用 API 準備的錢包本來就知道；在 App 裡建立的，從測試代理伺服器的紀錄拿）。
"""
from __future__ import annotations

from dataclasses import dataclass

from framework.ios.base import IosScreen


@dataclass(frozen=True)
class EntryRow:
    title: str          # 使用者看到的類型，例如 "Payment"、"Top-up"
    amount: str         # 畫面上的樣子，例如 "+100.00"、"−30.00"
    balance: str        # 這筆之後的餘額，例如 "70.00"


class HomeScreen(IosScreen):
    def wait(self) -> HomeScreen:
        self.wait_for("balance")
        return self

    def balance(self) -> str:
        return self.text("balance")

    def owner(self) -> str:
        return self.text("owner")

    def recent_rows(self) -> list[EntryRow]:
        """最近活動的每一列，由上而下。"""
        self.wait_for("recent-item")
        return entry_rows(self, "recent-item")

    def go_top_up(self):
        from framework.ios.top_up_screen import TopUpScreen
        self.tap("go-topup")
        return TopUpScreen(self.driver).wait()

    def go_pay(self):
        from framework.ios.pay_screen import PayScreen
        self.tap("go-pay")
        return PayScreen(self.driver).wait()

    def go_history(self):
        from framework.ios.history_screen import HistoryScreen
        self.tap("go-history")
        return HistoryScreen(self.driver).wait()

    def tab_history(self):
        from framework.ios.history_screen import HistoryScreen
        self.tap("tab-history")
        return HistoryScreen(self.driver).wait()


def entry_rows(screen: IosScreen, row_tag: str) -> list[EntryRow]:
    """畫面上每一列 row_tag，由上而下（首頁的最近活動、交易紀錄）。

    一次讀整個畫面結構，再從每一列裡找三個 hook：列和它的內容都在同一份結構裡，不會讀到一半畫面
    剛好重畫。捲動區域外的列也在結構裡，所以不像 Android 版要邊捲邊讀。"""
    rows = []
    for item in screen.tree().iter():
        if item.get("name") != row_tag:
            continue
        parts = {e.get("name"): e.get("label") for e in item.iter()}
        rows.append(EntryRow(parts.get("item-title"), parts.get("item-amount"), parts.get("item-balance")))
    return rows
