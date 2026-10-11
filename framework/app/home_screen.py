"""首頁（Home 分頁）：餘額、三個動作、最近三筆。

畫面上的錢包編號是遮罩過的（D-04），完整的編號 App 不會顯示：測試從建立錢包的 API 回應拿
（用 API 準備的錢包本來就知道；在 App 裡建立的，從測試代理伺服器的紀錄拿）。
"""
from __future__ import annotations

from framework.app.base import AppScreen


class HomeScreen(AppScreen):
    def wait(self) -> HomeScreen:
        self.wait_for("balance")
        return self

    def balance(self) -> str:
        return self.text("balance")

    def owner(self) -> str:
        return self.text("owner")

    def go_top_up(self):
        from framework.app.top_up_screen import TopUpScreen
        self.tap("go-topup")
        return TopUpScreen(self.driver).wait()

    def go_pay(self):
        from framework.app.pay_screen import PayScreen
        self.tap("go-pay")
        return PayScreen(self.driver).wait()

    def go_history(self):
        from framework.app.history_screen import HistoryScreen
        self.tap("go-history")
        return HistoryScreen(self.driver).wait()
