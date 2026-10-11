"""產生測試資料的工廠：每個測試拿到自己的新錢包、新 key，測試之間互不影響。"""
from __future__ import annotations

from framework.wallet_api import WalletAPI


def funded_wallet(api: WalletAPI, amount: str = "100.00", owner: str = "test-user") -> str:
    """透過 API 建錢包並儲值，回傳 wallet_id。"""
    r = api.create_wallet(owner)
    assert r.status_code == 201, r.text
    wallet_id = r.json()["wallet_id"]
    if amount != "0.00":
        r = api.top_up(wallet_id, amount)
        assert r.status_code == 201, r.text
    return wallet_id


def paid(api: WalletAPI, amount: str = "100.00") -> tuple[str, str]:
    """建一個剛好付完款的錢包（餘額 0），回傳 (wallet_id, payment_id)。"""
    wallet_id = funded_wallet(api, amount)
    r = api.pay(wallet_id, amount)
    assert r.status_code == 201, r.text
    return wallet_id, r.json()["payment_id"]
