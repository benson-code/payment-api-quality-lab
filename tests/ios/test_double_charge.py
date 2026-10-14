"""IOS-008、014：iOS App 這一側怎麼防止重複扣款、重複儲值，和 Android 的 APP-008、014、網頁的 WEB-008、014
是同一組行為。

網路狀況由測試代理伺服器製造（framework/app/proxy.py）。查 payments 表：畫面說扣一次不算數，
資料庫只有一筆才算。
"""
import pytest

from testdata.factories import funded_wallet

pytestmark = pytest.mark.ios


def payments_of(db, wallet) -> list[int]:
    return [r["amount"] for r in db.all("SELECT amount FROM payments WHERE wallet_id = ?", wallet)]


@pytest.mark.idempotency
@pytest.mark.case_id("IOS-008")
def test_lost_response_then_retry_charges_once(app, api, db, proxy):
    """客人按下付款，伺服器扣了款，回應卻在半路遺失。客人只看到沒有回應，按了重試。"""
    wallet = funded_wallet(api, "100.00")
    confirm = app.open_wallet(wallet).go_pay().continue_with("30")

    with proxy.lose_response("/payments"):
        confirm.confirm()
        confirm.expect_shown("no-answer")
    assert payments_of(db, wallet) == [3000], "the first request did reach the server"

    confirm.retry()
    receipt = confirm.wait_for_receipt()
    receipt.expect_shown("replayed")
    receipt.expect_text("result-balance", "70.00")

    keys = proxy.keys("/payments")
    assert len(keys) == 2 and keys[0] == keys[1], f"the retry must resend the same key: {keys}"
    assert payments_of(db, wallet) == [3000]
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 7000


@pytest.mark.case_id("IOS-014")
def test_top_up_without_an_answer_offers_no_retry(app, api, db, proxy):
    """儲值的 API 不收 Idempotency-Key，重試可能加兩次錢，所以畫面只能請客人先查餘額。"""
    wallet = funded_wallet(api, "0.00")
    top_up = app.open_wallet(wallet).go_top_up()

    with proxy.block("/topups"):
        top_up.submit("10")
        top_up.expect_shown("no-answer")
    assert "Check the balance before trying again." in top_up.text("no-answer")
    top_up.expect_absent("retry")
    assert proxy.keys("/topups") == [None], "a top-up carries no Idempotency-Key"
    assert db.balance_cents(wallet) == 0
    assert db.count("ledger", "wallet_id = ?", wallet) == 0
