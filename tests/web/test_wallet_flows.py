"""WEB-001～003：網頁上的主要流程。畫面對了還不算，資料庫也要對。"""
import re

import pytest
from playwright.sync_api import expect

from framework.web.base import MINUS
from framework.web.home_page import HomePage
from framework.web.start_page import StartPage
from testdata.factories import funded_wallet

pytestmark = pytest.mark.web

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@pytest.mark.case_id("WEB-001")
def test_new_wallet_starts_at_zero(page, app_url, db):
    home = StartPage(page, app_url).open().create_wallet("Alex")

    expect(home.tid("owner")).to_have_text("Alex")
    expect(home.tid("balance")).to_have_text("0.00")
    expect(home.tid("recent-empty")).to_be_visible()
    row = db.one("SELECT owner, balance FROM wallets WHERE wallet_id = ?", home.wallet_id)
    assert (row["owner"], row["balance"]) == ("Alex", 0)


@pytest.mark.case_id("WEB-002")
def test_top_up_reaches_the_balance_and_the_ledger(page, app_url, api, db):
    wallet = funded_wallet(api, "0.00")

    receipt = HomePage(page, app_url).open(wallet).go_top_up().top_up("100")
    expect(receipt.tid("result-amount")).to_have_text("100.00")
    expect(receipt.tid("result-balance")).to_have_text("100.00")
    home = receipt.done()
    expect(home.tid("balance")).to_have_text("100.00")

    entries = [tuple(r) for r in db.all("SELECT type, amount FROM ledger WHERE wallet_id = ?", wallet)]
    assert entries == [("TOPUP", 10000)]
    assert db.balance_cents(wallet) == db.ledger_sum_cents(wallet) == 10000


@pytest.mark.idempotency
@pytest.mark.case_id("WEB-003")
def test_payment_goes_through_confirm_to_receipt_and_history(page, app_url, api, db):
    wallet = funded_wallet(api, "100.00")

    confirm = HomePage(page, app_url).open(wallet).go_pay().continue_with("30")
    expect(confirm.tid("confirm-amount")).to_have_text("30.00")
    expect(confirm.tid("confirm-balance-after")).to_have_text("70.00")
    assert db.count("payments", "wallet_id = ?", wallet) == 0, "nothing may be sent before Confirm"

    with page.expect_request(lambda r: r.method == "POST" and r.url.endswith("/payments")) as sent:
        receipt = confirm.confirm_and_wait()
    # K-01：按下確認時產生一把 UUID v4 的 Idempotency-Key
    assert UUID4.match(sent.value.headers.get("idempotency-key", "")), sent.value.headers
    expect(receipt.tid("result-amount")).to_have_text("30.00")
    expect(receipt.tid("result-balance")).to_have_text("70.00")

    history = receipt.done().go_history()
    first = history.rows()[0]
    assert (first.type, first.amount, first.balance) == ("PAYMENT", f"{MINUS}30.00", "70.00")
    assert [r["amount"] for r in db.all("SELECT amount FROM payments WHERE wallet_id = ?", wallet)] == [3000]
