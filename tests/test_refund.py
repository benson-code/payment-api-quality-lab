"""E. 退款：可以分很多次，但累計不能超過原付款。"""
import pytest

from testdata.factories import paid

pytestmark = pytest.mark.refund


@pytest.mark.smoke
@pytest.mark.case_id("REF-001")
def test_full_refund(api):
    wallet, payment_id = paid(api, "100.00")
    r = api.refund(payment_id, "100.00")
    assert r.status_code == 201
    assert (r.json()["payment_refundable"], r.json()["balance_after"]) == ("0.00", "100.00")


@pytest.mark.boundary
@pytest.mark.case_id("REF-002")
def test_partial_refunds_cannot_add_up_past_the_payment(api):
    """只檢查「單筆 ≤ 付款」的系統會讓第三筆過關——要檢查的是累計。"""
    wallet, payment_id = paid(api, "100.00")
    assert api.refund(payment_id, "40.00").status_code == 201
    assert api.refund(payment_id, "60.00").status_code == 201
    r = api.refund(payment_id, "0.01")
    assert (r.status_code, r.json()["error_code"]) == (409, "REFUND_EXCEEDS_PAYMENT")
    assert api.balance(wallet) == "100.00"


@pytest.mark.boundary
@pytest.mark.case_id("REF-003")
def test_single_refund_larger_than_the_payment(api):
    wallet, payment_id = paid(api, "100.00")
    assert api.refund(payment_id, "100.01").status_code == 409
    assert api.balance(wallet) == "0.00"


@pytest.mark.case_id("REF-005")
def test_refund_unknown_payment(api):
    r = api.refund("p_doesnotexist", "1.00")
    assert (r.status_code, r.json()["error_code"]) == (404, "PAYMENT_NOT_FOUND")


@pytest.mark.validation
@pytest.mark.case_id("REF-006")
@pytest.mark.parametrize("amount", ["0", "0.00", "-1", "0.001", 5], ids=["zero", "zero-cents", "negative", "sub-cent", "number"])
def test_refund_amount_must_be_valid(api, amount):
    wallet, payment_id = paid(api, "100.00")
    assert api.refund(payment_id, amount).status_code == 400
    assert api.balance(wallet) == "0.00"


@pytest.mark.case_id("REF-007")
def test_refunds_are_listed_on_the_payment(api):
    wallet, payment_id = paid(api, "100.00")
    api.refund(payment_id, "10.00")
    api.refund(payment_id, "15.50")
    detail = api.get_payment(payment_id).json()
    assert [r["amount"] for r in detail["refunds"]] == ["10.00", "15.50"]
    assert detail["refunded"] == "25.50"
