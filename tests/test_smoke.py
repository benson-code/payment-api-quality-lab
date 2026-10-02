"""部署後第一個跑：服務活著、主要流程走得通。這裡失敗，後面就不用跑了。"""
import pytest

from testdata.factories import funded_wallet

pytestmark = pytest.mark.smoke


@pytest.mark.case_id("SMK-001")
def test_health(api):
    r = api.health()
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.case_id("SMK-002")
def test_main_money_flow(api):
    """建錢包 → 儲值 → 付款 → 部分退款 → 轉帳，每一步看餘額。"""
    alice = funded_wallet(api, "100.00")
    bob = funded_wallet(api, "0.00")

    payment = api.pay(alice, "30.00")
    assert payment.status_code == 201
    assert api.balance(alice) == "70.00"

    refund = api.refund(payment.json()["payment_id"], "10.00")
    assert refund.status_code == 201
    assert api.balance(alice) == "80.00"

    transfer = api.transfer(alice, bob, "20.00")
    assert transfer.status_code == 201
    assert (api.balance(alice), api.balance(bob)) == ("60.00", "20.00")
