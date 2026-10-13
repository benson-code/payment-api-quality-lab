"""IOS-019：金額的數字用等寬字（tabular figures，SPEC.md D-07），和網頁的 WEB-017 是同一條規則。

XCUITest 讀不到字型設定，所以比寬度：兩個錢包走同一條路，一個的金額全是 1（1,111.11），另一個
全是 0（1,000.00），位數和標點都一樣。等寬字兩邊一樣寬；一般的數字 1 比 0 窄很多，五個數字就差
十幾 pt。2.13 以前，收據列的值（Balance after）用的是一般數字，這裡就會失敗。
"""
import pytest

from framework.ios.start_screen import StartScreen
from testdata.factories import funded_wallet

pytestmark = pytest.mark.ios

TOLERANCE = 1          # pt：外框會四捨五入；一般數字的 1 和 0 每個差將近 3 pt
# 畫面 → 那個畫面上要用等寬字的金額（D-07）。Pay 的「Available …」在句子裡，不算
CONFIRM = ["confirm-amount", "confirm-balance-after"]
RECEIPT = ["result-amount", "result-balance"]
HOME = ["balance", "item-amount", "item-balance"]


def widths(start: StartScreen, api, funded: str, pay: str) -> tuple[dict[str, float], StartScreen]:
    """建錢包、付款，記下每個金額 hook 的寬度（同一個 hook 有好幾個時取最上面那個：最新的一筆），
    最後用「Use another wallet」回到開始畫面。"""
    wallet = funded_wallet(api, funded)
    seen = {}

    def measure(screen, hooks):
        for hook in hooks:
            screen.wait_for(hook)
            seen[hook] = screen.frames(hook)[0][2]

    confirm = start.open_wallet(wallet).go_pay().continue_with(pay)
    measure(confirm, CONFIRM)
    receipt = confirm.confirm_and_wait()
    measure(receipt, RECEIPT)
    home = receipt.done()
    home.recent_rows()                                        # 等最近活動載入（最新的是這筆付款）
    measure(home, HOME)
    home.tap("switch-wallet")
    return seen, StartScreen(home.driver).wait()


@pytest.mark.case_id("IOS-019")
def test_amounts_use_tabular_figures(app, api):
    ones, start = widths(app, api, "2222.22", "1111.11")      # 每個金額都是 1,111.11（付款列是 −1,111.11）
    zeros, _ = widths(start, api, "2000.00", "1000.00")       # 每個金額都是 1,000.00

    different = {hook: (ones[hook], zeros[hook]) for hook in ones if abs(ones[hook] - zeros[hook]) > TOLERANCE}
    assert not different, f"proportional figures (width of 1,111.11 vs 1,000.00, in pt): {different}"
