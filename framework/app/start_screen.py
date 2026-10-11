"""開始畫面：建立錢包，或用錢包編號打開。"""
from __future__ import annotations

from framework.app.base import AppScreen
from framework.app.home_screen import HomeScreen


class StartScreen(AppScreen):
    def wait(self) -> StartScreen:
        self.wait_for("create-wallet")
        return self

    def create_wallet(self, owner: str) -> HomeScreen:
        self.type_into("owner-input", owner)
        self.tap("create-wallet")
        return HomeScreen(self.driver).wait()

    def open_wallet(self, wallet_id: str) -> HomeScreen:
        """App 沒有網址可以直接打開某個錢包：測試用 API 準備好錢包，再從這裡打開。"""
        self.type_into("wallet-id-input", wallet_id)
        self.tap("open-wallet")
        return HomeScreen(self.driver).wait()

    def error(self) -> str:
        return self.text("error-message")
