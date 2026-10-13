"""首頁：餘額、動作、最近三筆。

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

    def recent_rows(self) -> list[EntryRow]:
        """最近活動的每一列，由上而下（還沒有交易紀錄畫面：第一階段只有首頁的最近三筆）。

        一次讀整個畫面結構，再從每一列裡找三個 hook：列和它的內容都在同一份結構裡，不會讀到
        一半畫面剛好重畫。"""
        self.wait_for("recent-item")
        rows = []
        for item in self.tree().iter():
            if item.get("name") != "recent-item":
                continue
            parts = {e.get("name"): e.get("label") for e in item.iter()}
            rows.append(EntryRow(parts.get("item-title"), parts.get("item-amount"), parts.get("item-balance")))
        return rows

    def go_pay(self):
        from framework.ios.pay_screen import PayScreen
        self.tap("go-pay")
        return PayScreen(self.driver).wait()
