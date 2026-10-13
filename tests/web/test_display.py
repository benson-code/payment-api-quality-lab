"""WEB-017：金額的數字用等寬字（tabular figures，SPEC.md D-07）。

等寬字每個數字一樣寬：列表裡的金額上下對齊，金額變動時也不會忽寬忽窄。只用 1 和 0 的金額，
兩種字差最多（一般的 1 比 0 窄很多），一眼就看得出來。句子裡的金額（Pay 的「Available …」）是
一般文字，不在這條規則裡。
"""
import pytest

from framework.web.history_page import HistoryPage
from framework.web.home_page import HomePage
from framework.web.pay_page import PayPage
from framework.web.payment_detail_page import PaymentDetailPage
from framework.web.top_up_page import TopUpPage
from testdata.factories import funded_wallet

pytestmark = pytest.mark.web


@pytest.mark.case_id("WEB-017")
def test_amounts_use_tabular_figures(page, app_url, api):
    wallet = funded_wallet(api, "1111.11")
    payment_id = api.pay(wallet, "111.10").json()["payment_id"]
    api.refund(payment_id, "11.10")

    # 畫面 → 那個畫面上一定要有、而且要用等寬字的金額
    screens = {
        "home": (lambda: HomePage(page, app_url).open(wallet), ["balance", "item-amount", "item-balance"]),
        "history": (lambda: HistoryPage(page, app_url).open(wallet), ["item-amount", "item-balance"]),
        "payment detail": (lambda: PaymentDetailPage(page, app_url).open(wallet, payment_id),
                           ["payment-amount", "payment-refunded", "payment-refundable", "item-amount", "amount-input"]),
        "top up": (lambda: TopUpPage(page, app_url).open(wallet), ["amount-input"]),
        "top-up receipt": (lambda: TopUpPage(page, app_url).open(wallet).top_up("10"), ["result-amount", "result-balance"]),
        "pay": (lambda: PayPage(page, app_url).open(wallet), ["amount-input"]),
        "confirm": (lambda: PayPage(page, app_url).open(wallet).continue_with("11"),
                    ["confirm-amount", "confirm-balance-after"]),
        "receipt": (lambda: PayPage(page, app_url).open(wallet).pay("11"), ["result-amount", "result-balance"]),
    }
    problems = {}
    for name, (show, hooks) in screens.items():
        found = show().proportional_amounts(hooks)
        if found:
            problems[name] = found
    assert not problems, problems
