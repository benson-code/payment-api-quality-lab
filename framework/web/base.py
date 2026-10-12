"""所有畫面共用：用 data-testid 找元素、讀文字。"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Locator, Page

MINUS = "−"       # 交易紀錄的負號是 U+2212（SPEC.md D-02），不是減號鍵的 "-"

# 無障礙掃描用的 axe-core：web/package.json 的 devDependency，版本由 package-lock 固定
AXE = Path(__file__).resolve().parents[2] / "web" / "node_modules" / "axe-core" / "axe.min.js"
# 只用 WCAG 2.2 A 和 AA 的規則（含 2.0、2.1）；axe 的 best-practice 規則不是標準的要求，不算
WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22a", "wcag22aa"]
# 不用的規則和原因。target-size（WCAG 2.5.8，至少 24 x 24 px）：L-02 要求 44 x 44，WEB-011 檢查，比它嚴；
# 而 axe 的這條看的是掃描當下的捲動位置，iPhone 14 的首頁一打開，最下面的連結有一半在分頁列後面，
# 它就算失敗，捲下去卻沒有問題。被固定列蓋住的真正問題是焦點，由 hidden_focus() 檢查（L-06）
AXE_DISABLED = {"target-size": {"enabled": False}}


class WebPage:
    def __init__(self, page: Page, app_url: str) -> None:
        self.page = page
        self.app_url = app_url          # 例如 http://127.0.0.1:8400/app/

    def tid(self, test_id: str) -> Locator:
        return self.page.get_by_test_id(test_id)

    def text(self, test_id: str) -> str:
        """元素的文字（會等元素出現）。"""
        return self.tid(test_id).inner_text().strip()

    def goto(self, route: str) -> None:
        """route 是 # 後面的路徑，例如 /w/w_xxx/pay。

        網址和目前完全相同時（例如付款的確認步驟，網址還是 /pay），瀏覽器什麼都不做，畫面會
        停在原本的步驟；這時改成重新載入，保證從這個畫面的起點開始。
        """
        url = f"{self.app_url}#{route}"
        if self.page.url == url:
            self.page.reload()
        else:
            self.page.goto(url)

    def layout_problems(self) -> dict:
        """目前畫面的版面問題（SPEC.md L-01、L-02）：

        horizontal_scroll  頁面比螢幕寬，要左右捲動
        small_targets      小於 44 x 44 CSS px 的按鈕或連結（觸控目標太小，手指點不準）
        clipped            超出所在卡片的文字或元素：卡片會把它裁掉，頁面卻不會變寬，
                           所以 horizontal_scroll 看不出來（最大金額的餘額就是這樣被裁掉的）
        incomplete_rows    一列裡有一部分被擠到沒有寬度：標籤和值、金額和幣別、交易紀錄的類型、金額、
                           餘額。和 App 的檢查是同一條規則（framework/app/layout.py）；App 曾經這樣壞過
        """
        return self.page.evaluate("""() => ({
            horizontal_scroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
            clipped: [...document.querySelectorAll('.card *')]
                .filter(e => {
                    const card = e.closest('.card').getBoundingClientRect(), r = e.getBoundingClientRect();
                    return r.width > 0 && (r.left < card.left - 0.5 || r.right > card.right + 0.5);
                })
                .map(e => `${e.dataset.testid || e.tagName.toLowerCase()} "${e.textContent.trim().slice(0, 24)}"`),
            incomplete_rows: [
                ...[...document.querySelectorAll('[data-testid="receipt-row"], [data-testid="balance-row"]')]
                    .filter(row => [...row.children].some(c => c.getBoundingClientRect().width < 1)),
                ...[...document.querySelectorAll('[data-testid="history-item"], [data-testid="recent-item"]')]
                    .filter(row => ['item-title', 'item-amount', 'item-balance'].some(tag => {
                        const part = row.querySelector(`[data-testid="${tag}"]`);
                        return !part || part.getBoundingClientRect().width < 1;
                    })),
            ].map(row => `${row.dataset.testid} "${row.textContent.trim().slice(0, 40)}"`),
            small_targets: [...document.querySelectorAll('a, button')]
                .map(e => ({ el: e.dataset.testid || e.textContent.trim(), r: e.getBoundingClientRect() }))
                .filter(x => x.r.width < 44 || x.r.height < 44)
                .map(x => `${x.el} ${Math.round(x.r.width)}x${Math.round(x.r.height)}`),
        })""")

    def accessibility_violations(self) -> list[str]:
        """axe-core 掃描目前的畫面，回傳違反 WCAG 2.2 A、AA 的地方（SPEC.md L-03、L-05），每條一行：
        規則、嚴重程度、哪些元素、axe 的說明。

        自動掃描只看得到一部分問題。axe 把 placeholder 也算成輸入框的名稱，所以 L-03 的「看得到的
        標籤」另外檢查（visible-label）；報讀器實際唸起來順不順，仍然要人來聽。
        """
        if not AXE.is_file():
            raise FileNotFoundError(f"{AXE} does not exist: cd web && npm ci")
        if not self.page.evaluate("() => typeof window.axe === 'object'"):
            self.page.add_script_tag(path=str(AXE))
        result = self.page.evaluate(
            "([tags, rules]) => axe.run(document, { runOnly: { type: 'tag', values: tags }, rules })",
            [WCAG_TAGS, AXE_DISABLED])
        found = [
            f"{v['id']} ({v['impact']}): {', '.join(' '.join(n['target']) for n in v['nodes'][:5])}"
            f"{' ...' if len(v['nodes']) > 5 else ''} | {v['nodes'][0]['failureSummary'].splitlines()[-1].strip()}"
            for v in result["violations"]
        ]
        # axe 補不到的一條（L-03）：輸入框要連到一個看得見、有文字的 <label>。axe 把 placeholder 也算成
        # 名稱，標籤和輸入框脫鉤、只剩 placeholder 0.00 時它照樣通過（tools/web_mutation_check.py
        # 的 amount_label_detached）；placeholder 一打字就不見了
        found += self.page.evaluate("""() => [...document.querySelectorAll('input, select, textarea')]
            .filter(e => e.getClientRects().length > 0)
            .filter(e => ![...e.labels].some(l => l.getClientRects().length > 0 && l.textContent.trim()))
            .map(e => `visible-label (L-03): ${e.dataset.testid || e.id} has no visible <label>`)""")
        return found

    def hidden_focus(self) -> list[str]:
        """用鍵盤走過整個畫面時，焦點完全被固定的標題列或分頁列蓋住的元素（SPEC.md L-06，WCAG 2.2
        的 2.4.11）。用鍵盤的人看不到焦點在哪裡，就不知道 Enter 會按到什麼。

        真的按鍵：從第一個元素按 Tab 走到最後（元素從畫面底部進來），再從最後一個按 Shift+Tab 走回來
        （從頂部進來）。要真的按鍵，不能用 focus()：WebKit 的 focus() 在元素露出一點點時不捲動，
        鍵盤操作卻會。Safari 預設按 Tab 不會停在連結上，要按 Option+Tab，所以 WebKit 用 Alt+Tab。
        標準是「不能完全被蓋住」：Firefox 在元素還露出一部分時不捲動，所以會被蓋住一半。
        只算被固定列蓋住的：Playwright 的 WebKit 用鍵盤移到輸入框時完全不捲動（桌機設定也一樣），
        輸入框整個留在畫面外，這是瀏覽器的行為，頁面的 CSS 改變不了。
        """
        tab = "Alt+Tab" if self.page.context.browser.browser_type.name == "webkit" else "Tab"
        hidden: list[str] = []
        for direction, key, first in (("Tab", tab, 0), ("Shift+Tab", f"Shift+{tab}", -1)):
            seen = set()
            self.page.evaluate("""first => {
                const all = [...document.querySelectorAll('a[href], button:not(:disabled), input:not(:disabled)')]
                    .filter(e => e.getClientRects().length > 0);
                window.scrollTo(0, first === 0 ? 0 : document.documentElement.scrollHeight);
                all.at(first).focus();
            }""", first)
            for _ in range(60):
                state = self.page.evaluate("""() => {
                    const e = document.activeElement;
                    if (!e || e === document.body) return null;
                    const name = `${e.dataset.testid || e.textContent.trim().slice(0, 24)}#${[...document.querySelectorAll('a, button, input')].indexOf(e)}`;
                    if (e.closest('.top-bar, .tab-bar')) return { name, visible: true };
                    const r = e.getBoundingClientRect();
                    // 整個在畫面外：是瀏覽器沒捲動，不是被固定列蓋住（WebKit 對輸入框就不捲動，見上面）
                    if (r.bottom <= 0 || r.top >= innerHeight) return { name, visible: true };
                    const top = Math.max(r.top, document.querySelector('.top-bar')?.getBoundingClientRect().bottom ?? 0, 0);
                    const bottom = Math.min(r.bottom, document.querySelector('.tab-bar')?.getBoundingClientRect().top ?? innerHeight, innerHeight);
                    return { name, visible: bottom - top >= 1 };
                }""")
                if state is None or state["name"] in seen:
                    break
                seen.add(state["name"])
                if not state["visible"]:
                    hidden.append(f"{state['name'].split('#')[0]} ({direction})")
                self.page.keyboard.press(key)
        self.page.evaluate("() => { document.activeElement?.blur(); window.scrollTo(0, 0); }")
        return hidden
