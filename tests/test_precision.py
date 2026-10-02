"""PRC. 金額精度：錢從進 API 到存進資料庫，都不能多一分或少一分。"""
import pytest

from testdata.factories import funded_wallet, paid

pytestmark = pytest.mark.precision


@pytest.mark.case_id("PRC-001")
def test_cents_add_up_exactly(api):
    """用浮點數算，0.1 + 0.2 = 0.30000000000000004。"""
    wallet = funded_wallet(api, "0.00")
    api.top_up(wallet, "0.10")
    api.top_up(wallet, "0.20")
    assert api.balance(wallet) == "0.30"


@pytest.mark.case_id("PRC-002")
def test_three_partial_refunds_return_every_cent(api):
    wallet, payment_id = paid(api, "100.00")
    for amount in ["33.33", "33.33", "33.34"]:
        assert api.refund(payment_id, amount).status_code == 201
    assert api.balance(wallet) == "100.00"


@pytest.mark.boundary
@pytest.mark.case_id("PRC-003")
def test_refundable_remainder_is_exact_to_the_cent(api):
    wallet, payment_id = paid(api, "100.00")
    for _ in range(3):
        api.refund(payment_id, "33.33")
    assert api.refund(payment_id, "0.02").status_code == 409     # 只剩 0.01
    assert api.refund(payment_id, "0.01").status_code == 201
    assert api.balance(wallet) == "100.00"


@pytest.mark.case_id("PRC-004")
def test_amounts_always_have_two_decimals(api):
    wallet = funded_wallet(api, "0.00")
    r = api.top_up(wallet, "7")
    assert (r.json()["amount"], r.json()["balance"]) == ("7.00", "7.00")


@pytest.mark.case_id("PRC-005")
@pytest.mark.parametrize("amount", ["19.99", "1.15", "0.29", "4.35"])
def test_float_unsafe_values_round_trip(api, db, amount):
    """這幾個值乘 100 用浮點數會變成 x.9999…：19.99 * 100 = 1998.9999999999998。

    33.33 反而不會出錯，所以測試資料是實際驗證過才挑的。
    """
    wallet = funded_wallet(api, "0.00")
    r = api.top_up(wallet, amount)
    assert r.json()["amount"] == amount
    assert db.balance_cents(wallet) == int(amount.replace(".", ""))
