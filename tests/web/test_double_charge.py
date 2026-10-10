"""WEB-007、008、012、013、014：網頁這一側怎麼防止重複扣款。

情境都是真的會發生的：手指連點、網路在回應回來之前斷掉、使用者等不及按返回再付一次。
每個案例都查 payments 表：畫面說扣一次不算數，資料庫只有一筆才算。
"""
import pytest
from playwright.sync_api import expect

from framework.web.network import SentKeys, block, hold, lose_response
from framework.web.pay_page import PayPage
from framework.web.receipt_page import ReceiptPage
from framework.web.top_up_page import TopUpPage
from testdata.factories import funded_wallet

pytestmark = [pytest.mark.web, pytest.mark.idempotency]


def payments_of(db, wallet) -> list[int]:
    return [r["amount"] for r in db.all("SELECT amount FROM payments WHERE wallet_id = ?", wallet)]


@pytest.mark.case_id("WEB-007")
def test_double_tap_sends_one_payment(page, app_url, api, db):
    wallet = funded_wallet(api, "100.00")
    confirm = PayPage(page, app_url).open(wallet).continue_with("30")
    sent = SentKeys(page, "/payments")

    with hold(page, "**/payments") as held:
        confirm.double_tap_confirm()
        expect(confirm.tid("confirm-pay")).to_be_disabled()
        # 要證明的是「第二個請求沒有出現」，沒有事件可以等，只能給它時間出現
        page.wait_for_timeout(300)
        assert len(held.routes) == 1, f"{len(held.routes)} payment requests were sent"
    ReceiptPage(page, app_url).wait()

    assert len(sent) == 1
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("WEB-008")
def test_lost_response_then_retry_charges_once(page, app_url, api, db):
    """客人按下付款，伺服器扣了款，回應卻在半路遺失。客人只看到沒有回應，按了重試。"""
    wallet = funded_wallet(api, "100.00")
    confirm = PayPage(page, app_url).open(wallet).continue_with("30")
    sent = SentKeys(page, "/payments")

    with lose_response(page, "**/payments"):
        confirm.confirm()
        expect(confirm.tid("no-answer")).to_be_visible()
    assert payments_of(db, wallet) == [3000], "the first request did reach the server"

    confirm.retry()
    receipt = ReceiptPage(page, app_url).wait()
    expect(receipt.tid("replayed")).to_be_visible()
    expect(receipt.tid("result-balance")).to_have_text("70.00")

    assert len(sent) == 2 and sent[0] == sent[1], f"the retry must resend the same key: {sent.keys}"
    assert payments_of(db, wallet) == [3000]
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 7000


@pytest.mark.case_id("WEB-012")
def test_processing_state_blocks_every_way_out(page, app_url, api):
    wallet = funded_wallet(api, "100.00")
    confirm = PayPage(page, app_url).open(wallet).continue_with("30")

    with hold(page, "**/payments"):
        confirm.confirm()
        expect(confirm.tid("confirm-pay")).to_be_disabled()
        expect(confirm.tid("confirm-pay")).to_have_text("Processing…")
        expect(confirm.tid("cancel")).to_be_disabled()
        expect(confirm.tid("back")).to_be_disabled()
    receipt = ReceiptPage(page, app_url).wait()
    expect(receipt.tid("result-amount")).to_have_text("30.00")


@pytest.mark.case_id("WEB-013")
def test_back_and_the_same_amount_resend_the_same_key(page, app_url, api, db):
    """沒有回應之後按返回、再按繼續：同一筆錢還是同一次付款，必須沿用原本的 key。

    金額以錢比較："30" 和 "30.00" 是同一筆。
    """
    wallet = funded_wallet(api, "100.00")
    confirm = PayPage(page, app_url).open(wallet).continue_with("30")
    sent = SentKeys(page, "/payments")

    with lose_response(page, "**/payments"):
        confirm.confirm()
        expect(confirm.tid("no-answer")).to_be_visible()
    confirm = confirm.back().continue_with("30.00")
    expect(confirm.tid("no-answer")).to_be_visible()       # 結果仍然未知，畫面要照實說
    confirm.retry()
    expect(ReceiptPage(page, app_url).wait().tid("replayed")).to_be_visible()

    assert len(sent) == 2 and sent[0] == sent[1], f"same amount after Back must keep the key: {sent.keys}"
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("WEB-013")
def test_back_and_a_new_amount_start_a_new_attempt(page, app_url, api, db):
    """改了金額就是另一筆付款：換新的 key，畫面也不再顯示上一筆的「沒有回應」。"""
    wallet = funded_wallet(api, "100.00")
    confirm = PayPage(page, app_url).open(wallet).continue_with("30")
    sent = SentKeys(page, "/payments")

    with block(page, "**/payments"):
        confirm.confirm()
        expect(confirm.tid("no-answer")).to_be_visible()
    confirm = confirm.back().continue_with("20")
    expect(confirm.tid("no-answer")).to_have_count(0)
    confirm.confirm_and_wait()

    assert len(sent) == 2 and sent[0] != sent[1], f"a new amount must get a new key: {sent.keys}"
    assert payments_of(db, wallet) == [2000]


@pytest.mark.case_id("WEB-014")
def test_top_up_without_an_answer_offers_no_retry(page, app_url, api, db):
    """儲值的 API 不收 Idempotency-Key，重試可能加兩次錢，所以畫面只能請客人先查餘額。"""
    wallet = funded_wallet(api, "0.00")
    top_up = TopUpPage(page, app_url).open(wallet)

    with block(page, "**/topups"):
        top_up.submit("10")
        expect(top_up.tid("no-answer")).to_contain_text("Check the balance before trying again.")
    expect(top_up.tid("retry")).to_have_count(0)
    assert db.balance_cents(wallet) == 0
    assert db.count("ledger", "wallet_id = ?", wallet) == 0
