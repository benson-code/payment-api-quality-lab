"""D. 併發：同時發生的請求，錢也不能算錯。

這是正確性測試，不是壓力測試：每個案例 10 個左右的請求，一秒內跑完。
"""
from concurrent.futures import ThreadPoolExecutor

import pytest

from framework.wallet_api import new_key
from testdata.factories import funded_wallet, paid

pytestmark = pytest.mark.concurrency


def at_once(n: int, fn) -> list:
    """同時送 n 個請求。每個執行緒用自己的 client。"""
    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(fn, range(n)))


@pytest.mark.case_id("CON-001")
def test_parallel_payments_never_overdraw(api, api_factory, db):
    """餘額 100，同時 10 筆各 20：剛好 5 筆成功，餘額 0，不會變負，帳要對得上。"""
    wallet = funded_wallet(api, "100.00")
    codes = at_once(10, lambda _: api_factory().pay(wallet, "20.00").status_code)
    assert sorted(codes) == [201] * 5 + [409] * 5
    assert api.balance(wallet) == "0.00"
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet)


@pytest.mark.idempotency
@pytest.mark.case_id("CON-002")
def test_parallel_retries_with_one_key_charge_once(api, api_factory, db):
    wallet = funded_wallet(api, "100.00")
    key = new_key()
    responses = at_once(10, lambda _: api_factory().pay(wallet, "20.00", key=key))
    assert {r.status_code for r in responses} == {201}
    assert len({r.json()["payment_id"] for r in responses}) == 1
    assert api.balance(wallet) == "80.00"
    assert db.count("payments", "wallet_id = ?", wallet) == 1


@pytest.mark.refund
@pytest.mark.case_id("CON-003")
def test_parallel_refunds_never_exceed_the_payment(api, api_factory):
    wallet, payment_id = paid(api, "100.00")
    codes = at_once(5, lambda _: api_factory().refund(payment_id, "30.00").status_code)
    assert sorted(codes) == [201] * 3 + [409] * 2
    assert api.get_payment(payment_id).json()["refunded"] == "90.00"
    assert api.balance(wallet) == "90.00"


@pytest.mark.transfer
@pytest.mark.case_id("TRF-004")
def test_opposite_transfers_at_the_same_time(api, api_factory, db):
    """A→B 和 B→A 同時大量發生：不能卡死，兩邊加總不變，每個錢包帳都對。"""
    a, b = funded_wallet(api, "1000.00"), funded_wallet(api, "1000.00")
    codes = at_once(20, lambda i: (api_factory().transfer(a, b, "10.00") if i % 2
                                   else api_factory().transfer(b, a, "10.00")).status_code)
    assert set(codes) == {201}
    assert (api.balance(a), api.balance(b)) == ("1000.00", "1000.00")
    for w in (a, b):
        assert db.balance_cents(w) == db.ledger_sum_cents(w)
