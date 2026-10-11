"""APP-007、008、012、013、014：App 這一側怎麼防止重複扣款，和網頁的 WEB-007、008、012～014 是同一組行為。

網路狀況由測試代理伺服器製造（framework/app/proxy.py）。每個案例都查 payments 表：
畫面說扣一次不算數，資料庫只有一筆才算。
"""
import time

import pytest

from testdata.factories import funded_wallet

pytestmark = [pytest.mark.app, pytest.mark.idempotency]


def payments_of(db, wallet) -> list[int]:
    return [r["amount"] for r in db.all("SELECT amount FROM payments WHERE wallet_id = ?", wallet)]


@pytest.mark.case_id("APP-007")
def test_double_tap_sends_one_payment(app, api, db, proxy):
    """連點兩下只送出一個請求。從 Appium 點不到「同一個畫面更新之內的第二下」（AppScreen.double_tap
    說明原因），那個空檔由 App 的「送出中」防護擋住，防護本身由單元測試證明（SPEC.md §9）。"""
    wallet = funded_wallet(api, "100.00")
    confirm = app.open_wallet(wallet).go_pay().continue_with("30")

    with proxy.hold("/payments") as held:
        confirm.double_tap("confirm-pay")
        assert not confirm.is_enabled("confirm-pay")
        # 要證明的是「第二個請求沒有出現」，沒有事件可以等，只能給它時間出現
        time.sleep(0.5)
        assert held.count == 1, f"{held.count} payment requests were sent"
    confirm.wait_for_receipt()

    assert len(proxy.keys("/payments")) == 1
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("APP-008")
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


@pytest.mark.case_id("APP-012")
def test_processing_state_blocks_every_way_out(app, api, db, proxy):
    wallet = funded_wallet(api, "100.00")
    confirm = app.open_wallet(wallet).go_pay().continue_with("30")

    with proxy.hold("/payments"):
        confirm.confirm()
        confirm.expect_label("confirm-pay", "Processing…")
        assert not confirm.is_enabled("confirm-pay")
        assert not confirm.is_enabled("cancel")
        assert not confirm.is_enabled("back")
    receipt = confirm.wait_for_receipt()
    receipt.expect_text("result-amount", "30.00")
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("APP-013")
def test_back_and_the_same_amount_resend_the_same_key(app, api, db, proxy):
    """沒有回應之後按返回、再按繼續：同一筆錢還是同一次付款，必須沿用原本的 key。

    金額以錢比較："30" 和 "30.00" 是同一筆。
    """
    wallet = funded_wallet(api, "100.00")
    confirm = app.open_wallet(wallet).go_pay().continue_with("30")

    with proxy.lose_response("/payments"):
        confirm.confirm()
        confirm.expect_shown("no-answer")
    confirm = confirm.back().continue_with("30.00")
    confirm.expect_shown("no-answer")                  # 結果仍然未知，畫面要照實說
    confirm.retry()
    confirm.wait_for_receipt().expect_shown("replayed")

    keys = proxy.keys("/payments")
    assert len(keys) == 2 and keys[0] == keys[1], f"same amount after Back must keep the key: {keys}"
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("APP-013")
def test_back_and_a_new_amount_start_a_new_attempt(app, api, db, proxy):
    """改了金額就是另一筆付款：換新的 key，畫面也不再顯示上一筆的「沒有回應」。"""
    wallet = funded_wallet(api, "100.00")
    confirm = app.open_wallet(wallet).go_pay().continue_with("30")

    with proxy.block("/payments"):
        confirm.confirm()
        confirm.expect_shown("no-answer")
    confirm = confirm.back().continue_with("20")
    confirm.expect_absent("no-answer")
    confirm.confirm_and_wait()

    keys = proxy.keys("/payments")
    assert len(keys) == 2 and keys[0] != keys[1], f"a new amount must get a new key: {keys}"
    assert payments_of(db, wallet) == [2000]


@pytest.mark.case_id("APP-014")
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
