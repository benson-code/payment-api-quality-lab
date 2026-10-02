"""F. 回應格式：用 jsonschema 驗欄位、型別、金額格式，也確認沒有多出不該有的欄位。"""
import pytest

from testdata.factories import funded_wallet, paid
from testdata.schema import assert_schema

pytestmark = pytest.mark.contract


@pytest.mark.case_id("CTR-001")
def test_success_responses_match_schemas(api):
    w = api.create_wallet("contract")
    assert_schema(w.json(), "wallet")
    wallet = w.json()["wallet_id"]
    assert_schema(api.top_up(wallet, "50.00").json(), "topup")
    p = api.pay(wallet, "20.00").json()
    assert_schema(p, "payment")
    assert_schema(api.refund(p["payment_id"], "5.00").json(), "refund")
    assert_schema(api.get_payment(p["payment_id"]).json(), "payment_detail")
    other = funded_wallet(api, "0.00")
    assert_schema(api.transfer(wallet, other, "1.00").json(), "transfer")
    assert_schema(api.transactions(wallet).json(), "transactions")
    assert_schema(api.get_wallet(wallet).json(), "wallet")


@pytest.mark.case_id("CTR-002")
def test_every_error_has_the_same_shape(api):
    wallet, payment_id = paid(api, "10.00")
    errors = [
        api.create_wallet(""),                         # 400 INVALID_OWNER
        api.request("POST", "/wallets", json={}),      # 400 INVALID_REQUEST（FastAPI 的驗證錯誤也要轉成同格式）
        api.get_wallet("w_nope"),                      # 404
        api.pay(wallet, "1.00"),                       # 409 餘額不足
        api.pay(wallet, "abc"),                        # 400
        api.refund(payment_id, "10.01"),               # 409 超退
        api.refund("p_nope", "1.00"),                  # 404
        api.transfer(wallet, wallet, "1.00"),          # 422
    ]
    for r in errors:
        assert r.status_code >= 400, r.text
        assert_schema(r.json(), "error")


@pytest.mark.case_id("CTR-003")
def test_replay_header(api):
    wallet = funded_wallet(api, "10.00")
    first = api.pay(wallet, "1.00", key="ctr-003-" + wallet)
    again = api.pay(wallet, "1.00", key="ctr-003-" + wallet)
    assert (first.headers["Idempotent-Replayed"], again.headers["Idempotent-Replayed"]) == ("false", "true")
