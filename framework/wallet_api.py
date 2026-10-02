"""WalletAPI：每支 API 一個方法。測試案例只呼叫這裡，不管 URL 長什麼樣。

需要 Idempotency-Key 的方法，預設自動產生一把新的；
要測「重送」就自己傳同一把，要測「沒帶 key」就傳 key=NO_KEY。
"""
from __future__ import annotations

import uuid

import requests

from framework.base_client import BaseClient

NO_KEY = object()          # 代表「這次故意不帶 Idempotency-Key」


def new_key() -> str:
    return uuid.uuid4().hex


class WalletAPI(BaseClient):
    @staticmethod
    def _key_header(key) -> dict:
        if key is NO_KEY:
            return {}
        return {"Idempotency-Key": key or new_key()}

    def health(self) -> requests.Response:
        return self.request("GET", "/health")

    def create_wallet(self, owner: str = "test-user") -> requests.Response:
        return self.request("POST", "/wallets", json={"owner": owner})

    def get_wallet(self, wallet_id: str) -> requests.Response:
        return self.request("GET", f"/wallets/{wallet_id}")

    def top_up(self, wallet_id: str, amount) -> requests.Response:
        return self.request("POST", f"/wallets/{wallet_id}/topups", json={"amount": amount})

    def pay(self, wallet_id, amount, key=None) -> requests.Response:
        return self.request("POST", "/payments", json={"wallet_id": wallet_id, "amount": amount},
                            headers=self._key_header(key))

    def get_payment(self, payment_id: str) -> requests.Response:
        return self.request("GET", f"/payments/{payment_id}")

    def refund(self, payment_id: str, amount, key=None) -> requests.Response:
        return self.request("POST", f"/payments/{payment_id}/refunds", json={"amount": amount},
                            headers=self._key_header(key))

    def transfer(self, from_wallet_id, to_wallet_id, amount, key=None) -> requests.Response:
        return self.request("POST", "/transfers",
                            json={"from_wallet_id": from_wallet_id, "to_wallet_id": to_wallet_id,
                                  "amount": amount},
                            headers=self._key_header(key))

    def transactions(self, wallet_id: str) -> requests.Response:
        return self.request("GET", f"/wallets/{wallet_id}/transactions")

    # ---- 讓測試好讀的捷徑 --------------------------------------------------------

    def balance(self, wallet_id: str) -> str:
        return self.get_wallet(wallet_id).json()["balance"]
