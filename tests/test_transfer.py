"""TRF. 轉帳：扣款和入帳要嘛都發生，要嘛都沒發生。"""
import pytest

from testdata.factories import funded_wallet

pytestmark = pytest.mark.transfer


@pytest.mark.case_id("TRF-001")
def test_transfer_moves_the_exact_amount(api):
    a, b = funded_wallet(api, "100.00"), funded_wallet(api, "0.01")
    r = api.transfer(a, b, "30.50")
    assert r.status_code == 201
    assert r.json()["from_balance_after"] == "69.50"
    assert (api.balance(a), api.balance(b)) == ("69.50", "30.51")


@pytest.mark.case_id("TRF-002")
def test_short_balance_moves_nothing(api, db):
    a, b = funded_wallet(api, "100.00"), funded_wallet(api, "0.00")
    r = api.transfer(a, b, "100.01")
    assert (r.status_code, r.json()["error_code"]) == (409, "INSUFFICIENT_BALANCE")
    assert (api.balance(a), api.balance(b)) == ("100.00", "0.00")
    assert db.count("ledger", "wallet_id IN (?, ?) AND type LIKE 'TRANSFER%'", a, b) == 0


@pytest.mark.case_id("TRF-003")
def test_transfer_to_yourself_is_rejected(api):
    a = funded_wallet(api, "100.00")
    r = api.transfer(a, a, "10.00")
    assert (r.status_code, r.json()["error_code"]) == (422, "SAME_WALLET")
    assert api.balance(a) == "100.00"


@pytest.mark.case_id("TRF-006")
def test_transfer_to_a_missing_wallet_takes_nothing(api, db):
    """收款方不存在：付款方一分錢都不能少。只扣款不入帳，錢就消失了。"""
    a = funded_wallet(api, "100.00")
    r = api.transfer(a, "w_doesnotexist", "10.00")
    assert r.status_code == 404
    assert api.balance(a) == "100.00"
    assert db.count("ledger", "wallet_id = ? AND type = 'TRANSFER_OUT'", a) == 0


@pytest.mark.limit
@pytest.mark.case_id("TRF-007")
def test_transfer_limit(api, db):
    a, b = db.seed_wallet(6_000_000), funded_wallet(api, "0.00")
    assert api.transfer(a, b, "50000.01").status_code == 422
    assert api.transfer(a, b, "50000.00").status_code == 201
