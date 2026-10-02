"""A. 輸入驗證。金額的各種寫法放在 cases/amount_validation.csv，一列一個案例。"""
import pytest

from framework.wallet_api import NO_KEY
from testdata import cases
from testdata.factories import funded_wallet
from testdata.schema import assert_schema


@pytest.mark.parametrize("case", cases.load("amount_validation.csv"))
def test_amount_formats(api, case):
    """從一個合法的請求開始，只換金額這一個欄位，才知道是哪個值造成的結果。"""
    wallet = funded_wallet(api, "100.00")
    before = api.balance(wallet)
    if case["endpoint"] == "payment":
        r = api.pay(wallet, case["amount"])
    else:
        r = api.top_up(wallet, case["amount"])

    assert r.status_code == int(case["expected_status"]), f'{case["title"]}: {r.text}'
    if case["expected_error_code"]:
        assert_schema(r.json(), "error")
        assert r.json()["error_code"] == case["expected_error_code"]
        assert api.balance(wallet) == before, "被拒絕的請求不能動到餘額"


@pytest.mark.validation
@pytest.mark.case_id("VAL-003")
@pytest.mark.parametrize("key", [NO_KEY, "", "k" * 65], ids=["missing", "empty", "too-long"])
def test_payment_needs_idempotency_key(api, key):
    wallet = funded_wallet(api, "100.00")
    r = api.pay(wallet, "10.00", key=key)
    assert r.status_code == 400
    assert r.json()["error_code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert api.balance(wallet) == "100.00"


@pytest.mark.validation
@pytest.mark.case_id("VAL-004")
def test_unknown_wallet(api):
    assert api.get_wallet("w_doesnotexist").status_code == 404
    r = api.pay("w_doesnotexist", "1.00")
    assert (r.status_code, r.json()["error_code"]) == (404, "WALLET_NOT_FOUND")
    assert api.top_up("w_doesnotexist", "1.00").status_code == 404


@pytest.mark.validation
@pytest.mark.case_id("VAL-005")
@pytest.mark.parametrize("wallet_id", [None, "", 123], ids=["null", "empty", "number"])
def test_payment_wallet_id_must_be_a_string(api, wallet_id):
    r = api.pay(wallet_id, "1.00")
    assert (r.status_code, r.json()["error_code"]) == (400, "INVALID_REQUEST")


@pytest.mark.validation
@pytest.mark.case_id("VAL-006")
@pytest.mark.parametrize("owner", ["", "   ", "x" * 51], ids=["empty", "blank", "too-long"])
def test_wallet_owner(api, owner):
    assert api.create_wallet(owner).status_code == 400
