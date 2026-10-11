"""F. 回應格式：用 jsonschema 驗欄位、型別、金額格式，也確認沒有多出不該有的欄位。

CTR-004 另外檢查 API 自己發布的文件（/openapi.json）跟實際回應一致。
"""
import pytest

from framework.wallet_api import NO_KEY, new_key
from testdata.factories import funded_wallet, paid
from testdata.schema import assert_documented, assert_schema

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


@pytest.mark.case_id("CTR-004")
def test_the_api_document_lists_exactly_the_real_responses(api):
    """/openapi.json 是 API 對外發布的合約，/docs 的 Swagger 畫面畫的就是它。兩個方向都要對：

    - 實際回應的狀態碼，文件上有；回應的格式（和承諾的 header）符合文件寫的
    - 文件列出的每一個狀態碼，都真的會出現

    FastAPI 自動產生的文件曾在每個路由寫著「422 Validation Error」和 {"detail": [...]}，成功的回應
    寫成任意內容；實際的驗證錯誤卻是 400 和 {error_code, message}。準備 demo 時從 Swagger 畫面發現。
    """
    doc = api.request("GET", "/openapi.json").json()
    wallet, other = funded_wallet(api, "100.00"), funded_wallet(api, "1.00")
    payment = api.pay(wallet, "10.00").json()["payment_id"]
    pay_key, refund_key = new_key(), new_key()
    api.pay(wallet, "1.00", key=pay_key)
    api.refund(payment, "1.00", key=refund_key)

    answers = [            # （方法, 文件上的路徑, 回應），每個文件列出的狀態碼至少一次
        ("get", "/health", api.health()),
        ("post", "/wallets", api.create_wallet("doc")),
        ("post", "/wallets", api.create_wallet("")),                                   # 400
        ("get", "/wallets/{wallet_id}", api.get_wallet(wallet)),
        ("get", "/wallets/{wallet_id}", api.get_wallet("w_nope")),                     # 404
        ("post", "/wallets/{wallet_id}/topups", api.top_up(wallet, "5.00")),
        ("post", "/wallets/{wallet_id}/topups", api.top_up(wallet, 5)),                # 400
        ("post", "/wallets/{wallet_id}/topups", api.top_up("w_nope", "5.00")),         # 404
        ("post", "/payments", api.pay(wallet, "1.00")),
        ("post", "/payments", api.pay(wallet, "1.00", key=NO_KEY)),                    # 400
        ("post", "/payments", api.pay("w_nope", "1.00")),                              # 404
        ("post", "/payments", api.pay(other, "2.00")),                                 # 409
        ("post", "/payments", api.pay(wallet, "2.00", key=pay_key)),                   # 422
        ("get", "/payments/{payment_id}", api.get_payment(payment)),
        ("get", "/payments/{payment_id}", api.get_payment("p_nope")),                  # 404
        ("post", "/payments/{payment_id}/refunds", api.refund(payment, "1.00")),
        ("post", "/payments/{payment_id}/refunds", api.refund(payment, "0")),          # 400
        ("post", "/payments/{payment_id}/refunds", api.refund("p_nope", "1.00")),      # 404
        ("post", "/payments/{payment_id}/refunds", api.refund(payment, "9.00")),       # 409
        ("post", "/payments/{payment_id}/refunds", api.refund(payment, "2.00", key=refund_key)),  # 422
        ("get", "/wallets/{wallet_id}/transactions", api.transactions(wallet)),
        ("get", "/wallets/{wallet_id}/transactions", api.transactions("w_nope")),      # 404
        ("post", "/transfers", api.transfer(wallet, other, "1.00")),
        ("post", "/transfers", api.transfer(wallet, other, "abc")),                    # 400
        ("post", "/transfers", api.transfer(wallet, "w_nope", "1.00")),                # 404
        ("post", "/transfers", api.transfer(other, wallet, "5.00")),                   # 409
        ("post", "/transfers", api.transfer(wallet, wallet, "1.00")),                  # 422
    ]

    for method, path, r in answers:
        label = f"{method.upper()} {path} answered {r.status_code}"
        listed = doc["paths"][path][method]["responses"]
        assert str(r.status_code) in listed, f"{label}, which the document does not list"
        response = listed[str(r.status_code)]
        assert_documented(r.json(), doc, response["content"]["application/json"]["schema"], label)
        for header in response.get("headers", {}):
            assert header in r.headers, f"{label} without the {header} header the document promises"

    listed = {(m, p, s) for p, ops in doc["paths"].items() for m, op in ops.items() for s in op["responses"]}
    answered = {(m, p, str(r.status_code)) for m, p, r in answers}
    assert listed == answered, (f"listed but never answered: {sorted(listed - answered)}; "
                                f"answered but not listed: {sorted(answered - listed)}")
