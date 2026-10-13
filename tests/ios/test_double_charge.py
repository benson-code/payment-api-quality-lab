"""IOS-008：iOS App 這一側怎麼防止重複扣款，和 Android 的 APP-008、網頁的 WEB-008 是同一組行為。

網路狀況由測試代理伺服器製造（framework/app/proxy.py）。查 payments 表：畫面說扣一次不算數，
資料庫只有一筆才算。
"""
import pytest

from testdata.factories import funded_wallet

pytestmark = [pytest.mark.ios, pytest.mark.idempotency]


def payments_of(db, wallet) -> list[int]:
    return [r["amount"] for r in db.all("SELECT amount FROM payments WHERE wallet_id = ?", wallet)]


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
