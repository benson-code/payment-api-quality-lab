"""所有畫面共用：用 testTag 找元素、讀文字、輸入、捲動、等待。

Compose 搭配 UiAutomator 的幾個特性都在這裡處理一次（android/README.md 有完整說明）：
- 按鈕的文字在它的子元素上：expect_label()
- UiAutomator 只看得到畫面上的元素，畫面外的要先捲過去：find()
- clear() 再 send_keys() 會搶時間（send_keys 是接在它讀到的舊文字後面），所以輸入一律一次
  換掉整段文字：type_into()
- 畫面會在資料回來後重組，元素可能剛好被換掉：讀值的地方都會重試到逾時為止

和網頁的 expect(...).to_have_text 一樣，expect_text() 會等畫面變成預期的樣子，逾時才失敗。
"""
from __future__ import annotations

import time

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.remote.webelement import WebElement

from framework.app import layout

MINUS = "−"       # 交易紀錄的負號是 U+2212（SPEC.md D-02），不是減號鍵的 "-"
TIMEOUT = 15      # 秒；畫面要等 API 回來，API 在同一台機器上，正常不到一秒


class AppScreen:
    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    # ---- 找元素 --------------------------------------------------------------------------

    def _all(self, test_id: str) -> list[WebElement]:
        return self.driver.find_elements(AppiumBy.ID, test_id)

    def is_shown(self, test_id: str) -> bool:
        """現在畫面上有沒有這個元素（不等、不捲動）。"""
        return bool(self._all(test_id))

    def wait_for(self, test_id: str, timeout: float = TIMEOUT) -> WebElement:
        """等元素出現，不捲動：用在操作之後才出現的東西，例如收據、訊息（訊息會自己捲進畫面，L-04）。"""
        deadline = time.monotonic() + timeout
        while True:
            found = self._all(test_id)
            if found:
                return found[0]
            if time.monotonic() > deadline:
                raise AssertionError(f'"{test_id}" did not appear within {timeout:.0f} s')
            time.sleep(0.2)

    def wait_for_any(self, *test_ids: str, timeout: float = TIMEOUT) -> str:
        """等其中一個出現，回傳是哪一個：送出之後可能是收據、錯誤訊息或「沒有回應」。"""
        deadline = time.monotonic() + timeout
        while True:
            for test_id in test_ids:
                if self._all(test_id):
                    return test_id
            if time.monotonic() > deadline:
                raise AssertionError(f"none of {test_ids} appeared within {timeout:.0f} s")
            time.sleep(0.2)

    def find(self, test_id: str, timeout: float = TIMEOUT) -> WebElement:
        """畫面上的元素；不在畫面上就捲動去找（先往下到底，再往上到頂）。

        先等一下下：畫面可能還在載入，這時捲動沒有意義。捲完兩個方向都找不到，再等到逾時，
        因為元素可能在一個還在出現的畫面上。
        """
        deadline = time.monotonic() + timeout
        try:
            return self.wait_for(test_id, timeout=min(2, timeout))
        except AssertionError:
            pass
        for direction in ("down", "up"):
            for _ in range(10):
                found = self._all(test_id)
                if found:
                    return found[0]
                if not self.scroll(direction):
                    break
        return self.wait_for(test_id, timeout=max(0.0, deadline - time.monotonic()))

    def _scroll_area(self) -> WebElement | None:
        areas = self.driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().scrollable(true)")
        return areas[0] if areas else None   # 內容一個畫面放得下時沒有可捲動的區域

    def scroll(self, direction: str, percent: float = 0.6) -> bool:
        """把可捲動的區域往 "down" 或 "up" 捲 percent 個畫面高；回傳畫面有沒有動（沒動就是到底了）。

        不用 mobile: scrollGesture 自己的回傳值：它說「不能再捲」時，Compose 的交易紀錄下面還有三列
        （量到的，APP-010）。所以比對捲動前後的畫面結構。
        """
        area = self._scroll_area()
        if area is None:
            return False
        before = self.driver.page_source
        self.driver.execute_script(
            "mobile: scrollGesture", {"elementId": area.id, "direction": direction, "percent": percent})
        return self.driver.page_source != before

    def scroll_to_top(self) -> None:
        for _ in range(20):
            if not self.scroll("up", percent=1.0):
                return

    def is_fully_visible(self, test_id: str) -> bool:
        """元素整個在看得到的地方（L-04）。

        被捲動區域切到的元素，UiAutomator 只回報看得到的那一段，所以「碰到區域邊緣」的元素無法只靠
        座標判斷：往那個方向捲一點點，元素變高了就表示剛才被切到（捲完再捲回來）。Compose 的
        bringIntoView 會剛好把元素捲到邊緣上，這種情況照樣算看得到。
        """
        found = self._all(test_id)
        if not found:
            return False
        area = self._scroll_area()
        r = found[0].rect
        if area is None:
            return True
        a = area.rect
        top, bottom = a["y"], a["y"] + a["height"]
        if r["y"] < top - 1 or r["y"] + r["height"] > bottom + 1:
            return True                       # 不在捲動區域裡：上方的標題列、下方的按鈕區
        at_bottom, at_top = r["y"] + r["height"] >= bottom - 1, r["y"] <= top + 1
        if not at_bottom and not at_top:
            return True
        direction, back = ("down", "up") if at_bottom else ("up", "down")
        self.scroll(direction, percent=0.2)
        moved = self._all(test_id)
        if not moved:
            return False
        after = moved[0].rect
        if after["y"] != r["y"]:
            self.scroll(back, percent=0.2)
        return after["height"] <= r["height"] + 1

    # ---- 讀 ------------------------------------------------------------------------------

    def _read(self, read, test_id: str, timeout: float = TIMEOUT):
        """畫面重組時元素可能剛好被換掉（stale）：重新找一次再讀。"""
        deadline = time.monotonic() + timeout
        while True:
            try:
                return read(self.find(test_id, timeout=max(0.5, deadline - time.monotonic())))
            except (StaleElementReferenceException, WebDriverException):
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.2)

    def text(self, test_id: str, timeout: float = TIMEOUT) -> str:
        """元素的文字。Compose 的 Text 直接帶 testTag，文字就在元素上。"""
        return self._read(lambda e: e.text, test_id, timeout)

    def is_enabled(self, test_id: str) -> bool:
        return self._read(lambda e: e.get_attribute("enabled") == "true", test_id)

    # ---- 等畫面變成預期的樣子 ------------------------------------------------------------

    def expect_text(self, test_id: str, expected: str, timeout: float = TIMEOUT) -> None:
        """等到元素的文字等於 expected；逾時就失敗，訊息裡有最後看到的值。"""
        self._expect(lambda e: e.text, test_id, expected, timeout, "shows")

    def expect_label(self, test_id: str, expected: str, timeout: float = TIMEOUT) -> None:
        """等到按鈕上的字等於 expected（例如處理中的「Processing…」）。Compose 的按鈕是一個可點的容器
        （帶 testTag），字在它的子元素 TextView 上。"""
        self._expect(lambda e: e.find_element(AppiumBy.CLASS_NAME, "android.widget.TextView").text,
                     test_id, expected, timeout, "reads")

    def _expect(self, read, test_id: str, expected: str, timeout: float, verb: str) -> None:
        deadline = time.monotonic() + timeout
        seen = None
        while True:
            try:
                seen = self._read(read, test_id, timeout=max(0.5, deadline - time.monotonic()))
            except (AssertionError, WebDriverException):
                seen = None
            if seen == expected:
                return
            if time.monotonic() > deadline:
                raise AssertionError(f'"{test_id}" {verb} {seen!r}, expected {expected!r}')
            time.sleep(0.2)

    def expect_shown(self, test_id: str, timeout: float = TIMEOUT) -> None:
        self.wait_for(test_id, timeout)

    def expect_absent(self, test_id: str, settle: float = 0.5) -> None:
        """要證明的是「沒有出現」，沒有事件可以等：給畫面一點時間，然後確認不在。
        只用在畫面上其他東西已經證明載入完成之後，否則「還沒出現」會被當成「不會出現」。"""
        time.sleep(settle)
        assert not self.is_shown(test_id), f'"{test_id}" is on the screen'

    # ---- 版面 ----------------------------------------------------------------------------

    def layout_problems(self) -> dict[str, list[str]]:
        """目前畫面的版面問題（framework/app/layout.py），從頭捲到尾每個位置都看一次，看完捲回最上面：
        Compose 會記住捲動位置，回到這個畫面時若停在底部，上方的元素（例如首頁的餘額）就看不到了。"""
        density = int(self.driver.execute_script("mobile: getDisplayDensity"))
        width = self.driver.get_window_size()["width"]
        found: dict[str, list[str]] = {}

        def collect() -> None:
            for kind, items in layout.problems(self.driver.page_source, density, width).items():
                bucket = found.setdefault(kind, [])
                bucket.extend(i for i in items if i not in bucket)

        more = self._scroll_area() is not None
        if more:
            self.scroll_to_top()
        collect()
        for _ in range(15):
            if not more:
                break
            more = self.scroll("down")
            collect()
        if self._scroll_area() is not None:
            self.scroll_to_top()
        return {k: v for k, v in found.items() if v}

    # ---- 操作 ----------------------------------------------------------------------------

    def tap(self, test_id: str) -> None:
        self.find(test_id).click()

    def double_tap(self, test_id: str) -> None:
        """很快地點兩下（W3C Actions，兩下之間 5 毫秒；UiAutomator2 不接受完全沒有停頓）。

        這碰不到「同一個畫面更新之內的第二下」：UiAutomator 每注入一個事件都等它處理完，第二下到的時候
        按鈕已經重畫成停用了（拿掉 App 的「送出中」防護，APP-007 照樣通過，量過）。防護本身由 App 的
        單元測試 AttemptTest.aSecondSubmitWhileInFlightSendsNothing 證明；APP-007 證明的是整條路上
        連點只送出一個請求。網頁的 WEB-007 能在同一個 JavaScript 工作裡點兩下，所以碰得到。
        """
        r = self.find(test_id).rect
        x, y = r["x"] + r["width"] // 2, r["y"] + r["height"] // 2
        finger = PointerInput(interaction.POINTER_TOUCH, "finger")
        actions = ActionBuilder(self.driver, mouse=finger, duration=0)
        actions.pointer_action.move_to_location(x, y).pointer_down().pointer_up().pause(0.005).pointer_down().pointer_up()
        actions.perform()

    def type_into(self, test_id: str, value: str) -> None:
        """一次換掉輸入框的整段文字（不是 clear() 再 send_keys()，理由見檔案開頭），等輸入框顯示出新的值
        才回來：依輸入而變的東西（例如送出鈕能不能按）要等 Compose 重組一次，太早讀會讀到上一個狀態
        （tools/parity_check.py 第一次跑時，有 5 個輸入因此被誤判）。空的輸入框顯示提示文字，等不到
        就最多等一秒。"""
        field = self.find(test_id)
        self.driver.execute_script("mobile: replaceElementValue", {"elementId": field.id, "text": value})
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            try:
                if self._all(test_id)[0].text == value:
                    return
            except (IndexError, WebDriverException):
                pass
            time.sleep(0.1)

    def system_back(self) -> None:
        """系統的返回鍵或手勢（N-01），不是畫面上方的返回鍵（那是 tap("back")）。"""
        self.driver.back()
