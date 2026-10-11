"""APP-015、016、017：只有原生 App 才有的情況：程序被系統殺掉、系統的返回鍵（SPEC.md K-08、N-01）。

網頁沒有對應的案例：重新整理網頁就是從頭開始（SPEC.md §10）。App 被放到背景、系統記憶體不足時，
程序可能被殺掉，使用者回來時 Android 用保存的狀態重建畫面。這時錢的狀態不能錯：結果未知的付款
要能用同一把 key 重試，已經完成的付款不能再被確認一次。
"""
import pytest

from framework.app.pay_screen import ConfirmScreen, PayScreen
from framework.app.receipt_screen import ReceiptScreen
from testdata.factories import funded_wallet

pytestmark = [pytest.mark.app, pytest.mark.idempotency]


def payments_of(db, wallet) -> list[int]:
    return [r["amount"] for r in db.all("SELECT amount FROM payments WHERE wallet_id = ?", wallet)]


def kill_and_reopen(device) -> None:
    """放到背景、像系統那樣殺掉程序、再從桌面圖示回來。"""
    device.send_to_background()
    device.kill_background_process()
    device.reopen_from_launcher()


@pytest.mark.case_id("APP-015")
def test_process_death_with_the_outcome_unknown(app, api, db, proxy, device):
    """付款結果未知時程序被殺掉：回來還是確認頁、還是「沒有回應」，重試用的是存起來的同一把 key。"""
    wallet = funded_wallet(api, "100.00")
    confirm = app.open_wallet(wallet).go_pay().continue_with("30")
    with proxy.lose_response("/payments"):
        confirm.confirm()
        confirm.expect_shown("no-answer")

    kill_and_reopen(device)

    confirm = ConfirmScreen(app.driver).wait()
    confirm.expect_shown("no-answer")
    confirm.expect_text("confirm-amount", "30.00")
    confirm.retry()
    confirm.wait_for_receipt().expect_shown("replayed")
    keys = proxy.keys("/payments")
    assert len(keys) == 2 and keys[0] == keys[1], f"the retry after process death must resend the saved key: {keys}"
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("APP-016")
def test_system_back_on_confirm_keeps_the_pending_attempt(app, api, db, proxy):
    """(a) 確認頁按系統返回鍵：回到輸入金額，等待結果的那次付款還在，同一筆錢再繼續就是同一把 key。"""
    wallet = funded_wallet(api, "100.00")
    confirm = app.open_wallet(wallet).go_pay().continue_with("30")
    with proxy.lose_response("/payments"):
        confirm.confirm()
        confirm.expect_shown("no-answer")

    confirm.system_back()
    pay = PayScreen(app.driver).wait()
    pay.expect_text("amount-input", "30")
    confirm = pay.continue_with("30")
    confirm.expect_shown("no-answer")
    confirm.retry()
    confirm.wait_for_receipt().expect_shown("replayed")
    keys = proxy.keys("/payments")
    assert len(keys) == 2 and keys[0] == keys[1], keys
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("APP-016")
def test_system_back_does_nothing_while_processing(app, api, db, proxy):
    """(b) 處理中按系統返回鍵：什麼都不發生，請求回來之後照樣到收據。"""
    wallet = funded_wallet(api, "100.00")
    confirm = app.open_wallet(wallet).go_pay().continue_with("30")
    with proxy.hold("/payments"):
        confirm.confirm()
        confirm.expect_label("confirm-pay", "Processing…")
        confirm.system_back()
        confirm.expect_label("confirm-pay", "Processing…")     # 還在確認頁、還在處理中
        confirm.expect_absent("amount-input")
    confirm.wait_for_receipt().expect_text("result-amount", "30.00")
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("APP-016")
def test_system_back_on_the_receipt_goes_home(app, api, db):
    """(c) 收據頁按系統返回鍵：回首頁，不會回到確認頁，所以不可能靠返回鍵再付一次。"""
    wallet = funded_wallet(api, "100.00")
    receipt = app.open_wallet(wallet).go_pay().pay("30")

    receipt.system_back()
    receipt.wait_for("go-pay")                                 # 首頁
    receipt.expect_text("balance", "70.00")
    receipt.expect_absent("confirm-pay")
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("APP-017")
def test_process_death_on_the_receipt(app, api, db, device):
    """收據頁時程序被殺掉：回來還是同一張收據，沒有「Confirm payment」。

    2.3 之前會回到確認頁，再按一次就是第二筆付款（QA 時在裝置上重現過，SPEC.md §11）。
    """
    wallet = funded_wallet(api, "100.00")
    receipt = app.open_wallet(wallet).go_pay().pay("30")
    payment_id = receipt.payment_id()

    kill_and_reopen(device)

    receipt = ReceiptScreen(app.driver).wait()
    receipt.expect_text("result-payment-id", payment_id)
    receipt.expect_text("result-balance", "70.00")
    receipt.expect_absent("confirm-pay")
    receipt.system_back()
    receipt.wait_for("go-pay")
    assert payments_of(db, wallet) == [3000]


@pytest.mark.case_id("APP-017")
def test_process_death_on_a_replayed_receipt(app, api, db, proxy, device):
    """重試後的收據（「這筆付款之前已經完成」）在程序被殺掉之後也照實顯示。"""
    wallet = funded_wallet(api, "100.00")
    confirm = app.open_wallet(wallet).go_pay().continue_with("30")
    with proxy.lose_response("/payments"):
        confirm.confirm()
        confirm.expect_shown("no-answer")
    confirm.retry()
    confirm.wait_for_receipt().expect_shown("replayed")

    kill_and_reopen(device)

    receipt = ReceiptScreen(app.driver).wait()
    receipt.expect_shown("replayed")
    receipt.expect_absent("confirm-pay")
    assert payments_of(db, wallet) == [3000]
