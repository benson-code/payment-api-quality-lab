"""版面檢查（SPEC.md L-01、L-02），從 UiAutomator 的畫面結構（XML）判斷：一次讀整個畫面，
不必對每個元素各問一次 Appium。

    off_screen     文字超出螢幕左右
    overlapping    兩段文字疊在一起（QA 時抓到：名稱很長時壓在「From」標籤上）
    stacked        一個單字被擠成一行一個字（QA 時抓到：「TWD」變成直排）：
                   沒有空白、至少三個字的文字，卻比它的寬度高一倍半以上
    small_targets  可點的元素小於 48 x 48 dp（Android 的無障礙建議）
    incomplete_rows  一列少了一部分：標籤和值、金額和幣別、交易紀錄的類型、金額、餘額

為什麼要有 incomplete_rows：Compose 把被擠到零寬的文字整個從無障礙樹拿掉（連 UiAutomator2 的
allowInvisibleElements 都看不到），所以 QA 時的兩個問題——「From」被長名稱擠成一行一個字、
「TWD」被長餘額擠成直排——畫面上看得到，畫面結構裡卻根本沒有那段文字，比對座標永遠抓不到。
看得到的線索是「這一列少了一段」，所以兩個客戶端的這幾種列都有外框掛鉤（SPEC.md §7），
這裡要求每一列的每個部分都在。量過：拿掉那兩個修正，這一項就會失敗。

Compose 會把小於 48 dp 的可點元件的觸控範圍自動擴大到 48 dp，回報的也是擴大後的範圍：
small_targets 量的就是手指真正點得到的範圍。

被捲動區域切到一半的元素，UiAutomator 回報的是看得到的那一段，所以碰到捲動區域上下緣的元素不檢查
大小和比例。AppScreen.layout_problems() 會把畫面從頭捲到尾，每個元素總有一個位置是完整的。

"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

MIN_TARGET_DP = 48
# 外框掛鉤 → 裡面必須看得到的東西：數字是至少幾段文字，tuple 是一定要有的掛鉤
ROWS = {
    "receipt-row": 2,                                         # 標籤和值
    "balance-row": 2,                                         # 金額和幣別
    "history-item": ("item-title", "item-amount", "item-balance"),
    "recent-item": ("item-title", "item-amount", "item-balance"),
}
_BOUNDS = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


@dataclass(frozen=True)
class Box:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def overlap(self, other: Box) -> int:
        """重疊的面積（像素²）；只是邊碰邊是 0。"""
        w = min(self.x2, other.x2) - max(self.x1, other.x1)
        h = min(self.y2, other.y2) - max(self.y1, other.y1)
        return w * h if w > 0 and h > 0 else 0


@dataclass(frozen=True)
class Node:
    cls: str
    text: str
    tag: str            # testTag（resource-id），沒有就是空字串
    clickable: bool
    scrollable: bool
    box: Box

    def describe(self) -> str:
        name = self.tag or self.text[:24] or self.cls.rsplit(".", 1)[-1]
        return f'{name} ({self.box.width}x{self.box.height} px at {self.box.x1},{self.box.y1})'


def _node(e: ET.Element) -> Node | None:
    m = _BOUNDS.fullmatch(e.get("bounds", ""))
    if not m:
        return None
    return Node(e.get("class", ""), e.get("text", ""), e.get("resource-id", ""),
                e.get("clickable") == "true", e.get("scrollable") == "true", Box(*map(int, m.groups())))


def parse(page_source: str) -> list[Node]:
    return [n for n in map(_node, ET.fromstring(page_source).iter()) if n]


def problems(page_source: str, density: int, screen_width: int) -> dict[str, list[str]]:
    root = ET.fromstring(page_source)
    nodes = [n for n in map(_node, root.iter()) if n]
    area = next((n.box for n in nodes if n.scrollable), None)

    def cut(b: Box) -> bool:
        """在捲動區域裡、碰到它的上緣或下緣：可能只看得到一部分。"""
        inside = area is not None and b.y1 >= area.y1 - 1 and b.y2 <= area.y2 + 1
        return inside and (b.y1 <= area.y1 + 1 or b.y2 >= area.y2 - 1)

    texts = [n for n in nodes if n.cls == "android.widget.TextView" and n.text.strip()]
    found: dict[str, list[str]] = {"off_screen": [], "overlapping": [], "stacked": [], "small_targets": [],
                                   "incomplete_rows": []}

    for t in texts:
        if t.box.x1 < 0 or t.box.x2 > screen_width:
            found["off_screen"].append(t.describe())
        word = t.text.strip()
        if len(word) >= 3 and not any(c.isspace() for c in word) and not cut(t.box) \
                and t.box.height > 1.5 * t.box.width:
            found["stacked"].append(t.describe())
    for i, a in enumerate(texts):
        for b in texts[i + 1:]:
            if a.box.overlap(b.box) > 4:
                found["overlapping"].append(f"{a.describe()} / {b.describe()}")

    for e in root.iter():
        row = _node(e) if e.get("resource-id") in ROWS else None
        if row is None or cut(row.box):
            continue                     # 被捲動區域切到的列，少一部分是正常的
        parts = [n for n in map(_node, list(e.iter())[1:]) if n]
        need = ROWS[row.tag]
        if isinstance(need, int):
            shown = [n.text for n in parts if n.cls == "android.widget.TextView" and n.text.strip()]
            if len(shown) < need:
                found["incomplete_rows"].append(f"{row.describe()} shows {shown}, expected {need} texts")
        else:
            missing = [tag for tag in need if tag not in {n.tag for n in parts}]
            if missing:
                found["incomplete_rows"].append(f"{row.describe()} has no {', '.join(missing)}")

    px_per_dp = density / 160
    for n in nodes:
        if n.clickable and not cut(n.box):
            w, h = n.box.width / px_per_dp, n.box.height / px_per_dp
            if w < MIN_TARGET_DP - 0.5 or h < MIN_TARGET_DP - 0.5:
                found["small_targets"].append(f"{n.describe()} = {w:.0f}x{h:.0f} dp")
    return found
