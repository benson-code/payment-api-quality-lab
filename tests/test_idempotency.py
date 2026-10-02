"""C. 冪等：網路逾時後重送，錢只能動一次。

斷言不只看回應，還去查交易紀錄與資料庫——API 說「沒重複扣」不算數，帳上只有一筆才算。
"""
import pytest

from framework.wallet_api import new_key
from testdata.factories import funded_wallet, paid

pytestmark = pytest.mark.idempotency


@pytest.mark.smoke
@pytest.mark.case_id("IDM-001")
def test_same_key_twice_charges_once(api, db):
    wallet = funded_wallet(api, "100.00")
    key = new_key()
    first = api.pay(wallet, "30.00", key=key)
    again = api.pay(wallet, "30.00", key=key)

    assert (first.status_code, again.status_code) == (201, 201)
    assert again.headers["Idempotent-Replayed"] == "true"
    assert again.json() == first.json()                      # 回的是同一筆付款
    assert api.balance(wallet) == "70.00"
    assert db.count("payments", "wallet_id = ?", wallet) == 1


@pytest.mark.case_id("IDM-002")
def test_same_key_five_times_charges_once(api):
    wallet = funded_wallet(api, "100.00")
    key = new_key()
    ids = {api.pay(wallet, "10.00", key=key).json()["payment_id"] for _ in range(5)}
    assert len(ids) == 1
    assert api.balance(wallet) == "90.00"


@pytest.mark.case_id("IDM-003")
def test_same_key_different_amount_is_rejected(api):
    wallet = funded_wallet(api, "100.00")
    key = new_key()
    api.pay(wallet, "30.00", key=key)
    r = api.pay(wallet, "31.00", key=key)
    assert (r.status_code, r.json()["error_code"]) == (422, "IDEMPOTENCY_KEY_REUSED")
    assert api.balance(wallet) == "70.00"


@pytest.mark.case_id("IDM-004")
def test_different_keys_are_different_purchases(api):
    """冪等不能擋掉合法的重複購買：同一個人買兩杯一樣的咖啡。"""
    wallet = funded_wallet(api, "100.00")
    a = api.pay(wallet, "30.00")
    b = api.pay(wallet, "30.00")
    assert a.json()["payment_id"] != b.json()["payment_id"]
    assert api.balance(wallet) == "40.00"


@pytest.mark.case_id("IDM-005")
def test_failed_payment_does_not_burn_the_key(api):
    """餘額不足失敗後，同一把 key 儲值後可以再用——失敗的請求不該被記住。"""
    wallet = funded_wallet(api, "10.00")
    key = new_key()
    assert api.pay(wallet, "20.00", key=key).status_code == 409
    api.top_up(wallet, "20.00")
    assert api.pay(wallet, "20.00", key=key).status_code == 201
    assert api.balance(wallet) == "10.00"


@pytest.mark.refund
@pytest.mark.case_id("REF-004")
def test_refund_retry_refunds_once(api):
    wallet, payment_id = paid(api, "100.00")
    key = new_key()
    first = api.refund(payment_id, "30.00", key=key)
    again = api.refund(payment_id, "30.00", key=key)
    assert again.json()["refund_id"] == first.json()["refund_id"]
    assert api.balance(wallet) == "30.00"
    assert len(api.get_payment(payment_id).json()["refunds"]) == 1


@pytest.mark.transfer
@pytest.mark.case_id("TRF-005")
def test_transfer_retry_moves_money_once(api):
    a, b = funded_wallet(api, "100.00"), funded_wallet(api, "0.00")
    key = new_key()
    api.transfer(a, b, "25.00", key=key)
    api.transfer(a, b, "25.00", key=key)
    assert (api.balance(a), api.balance(b)) == ("75.00", "25.00")
