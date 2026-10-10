"""交易紀錄（History 分頁）：最新的在最上面，依日期分組。"""
from __future__ import annotations

from dataclasses import dataclass

from framework.web.base import WebPage


@dataclass(frozen=True)
class HistoryRow:
    entry_id: int
    type: str           # TOPUP、PAYMENT、REFUND…（data-type，和資料庫 ledger.type 相同）
    amount: str         # 畫面上的樣子，例如 "+100.00"、"−30.00"
    balance: str        # 這筆之後的餘額，例如 "70.00"


class HistoryPage(WebPage):
    def open(self, wallet_id: str) -> HistoryPage:
        self.goto(f"/w/{wallet_id}/history")
        return self.wait()

    def wait(self) -> HistoryPage:
        self.page.locator('[data-testid="history-item"], [data-testid="empty"]').first.wait_for()
        return self

    def rows(self) -> list[HistoryRow]:
        rows = []
        for item in self.tid("history-item").all():
            rows.append(HistoryRow(
                entry_id=int(item.get_attribute("data-entry-id")),
                type=item.get_attribute("data-type"),
                amount=item.get_by_test_id("item-amount").inner_text().strip(),
                balance=item.get_by_test_id("item-balance").inner_text().strip(),
            ))
        return rows
