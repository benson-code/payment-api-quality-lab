"""B. 商業規則：餘額、限額、交易紀錄。"""
import pytest

from testdata.factories import funded_wallet

pytestmark = pytest.mark.business


@pytest.mark.boundary
@pytest.mark.case_id("BIZ-001")
def test_pay_exactly_the_balance(api):
    wallet = funded_wallet(api, "100.00")
    r = api.pay(wallet, "100.00")
    assert r.status_code == 201
    assert r.json()["balance_after"] == "0.00"
    assert api.balance(wallet) == "0.00"


@pytest.mark.boundary
@pytest.mark.case_id("BIZ-002")
def test_pay_one_cent_more_than_the_balance(api):
    wallet = funded_wallet(api, "100.00")
    r = api.pay(wallet, "100.01")
    assert (r.status_code, r.json()["error_code"]) == (409, "INSUFFICIENT_BALANCE")
    assert api.balance(wallet) == "100.00"


@pytest.mark.case_id("BIZ-003")
def test_top_up_shows_in_balance_and_history(api):
    wallet = funded_wallet(api, "0.00")
    api.top_up(wallet, "10.00")
    api.top_up(wallet, "5.25")
    assert api.balance(wallet) == "15.25"
    history = api.transactions(wallet).json()["transactions"]
    assert [(t["type"], t["amount"], t["balance_after"]) for t in history] == [
        ("TOPUP", "10.00", "10.00"), ("TOPUP", "5.25", "15.25")]


@pytest.mark.case_id("BIZ-004")
def test_payment_shows_in_history_as_negative(api):
    wallet = funded_wallet(api, "100.00")
    payment_id = api.pay(wallet, "30.00").json()["payment_id"]
    last = api.transactions(wallet).json()["transactions"][-1]
    assert (last["type"], last["amount"], last["balance_after"], last["ref_id"]) == \
        ("PAYMENT", "-30.00", "70.00", payment_id)


@pytest.mark.case_id("BIZ-005")
def test_failed_payment_leaves_no_trace(api, db):
    """餘額不足被拒絕：不能有付款紀錄、不能有 ledger、餘額不變。"""
    wallet = funded_wallet(api, "10.00")
    api.pay(wallet, "10.01")
    assert db.count("payments", "wallet_id = ?", wallet) == 0
    assert db.count("ledger", "wallet_id = ? AND type = 'PAYMENT'", wallet) == 0
    assert db.balance_cents(wallet) == 1000


@pytest.mark.limit
@pytest.mark.boundary
@pytest.mark.case_id("LIM-001")
@pytest.mark.parametrize("amount, status", [("49999.99", 201), ("50000.00", 201), ("50000.01", 422)])
def test_single_payment_limit(api, db, amount, status):
    wallet = db.seed_wallet(6_000_000)              # 60,000.00：用 SQL 直接準備大額錢包
    r = api.pay(wallet, amount)
    assert r.status_code == status, r.text
    if status == 422:
        assert r.json()["error_code"] == "LIMIT_EXCEEDED"
        assert api.balance(wallet) == "60000.00"
