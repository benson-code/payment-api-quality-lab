"""所有畫面共用：用 accessibility id 找元素、讀文字、輸入、等待。

XCUITest 和 Android 的 UiAutomator 不同的地方，在這裡處理一次：
- 捲動區域外的元素也在畫面結構裡，找得到；點它時 XCUITest 會自己捲過去。所以不像 Android 版
  要邊捲邊找。
- 按鈕的字就是按鈕的 label（SwiftUI 把按鈕裡的文字合併成一個元素），讀 text 就是按鈕上的字。
- 空的輸入框，text 讀到的是提示文字（placeholder），不是空字串。
- 畫面會在資料回來後重畫，元素可能剛好被換掉：讀值的地方都會重試到逾時為止。

和網頁的 expect(...).to_have_text 一樣，expect_text() 會等畫面變成預期的樣子，逾時才失敗。
"""
from __future__ import annotations

import time
import xml.etree.ElementTree as ET

from appium.webdriver.common.appiumby import AppiumBy
from appium.webdriver.webdriver import WebDriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement

MINUS = "−"       # 交易紀錄的負號是 U+2212（SPEC.md D-02），不是減號鍵的 "-"
TIMEOUT = 15      # 秒；畫面要等 API 回來，API 在同一台機器上，正常不到一秒


class IosScreen:
    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    # ---- 找元素 --------------------------------------------------------------------------

    def _all(self, test_id: str) -> list[WebElement]:
        return self.driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)

    def is_shown(self, test_id: str) -> bool:
        """現在畫面上有沒有這個元素（不等）。"""
        return bool(self._all(test_id))

    def wait_for(self, test_id: str, timeout: float = TIMEOUT) -> WebElement:
        """等元素出現。"""
        deadline = time.monotonic() + timeout
        while True:
            found = self._all(test_id)
            if found:
                return found[0]
            if time.monotonic() > deadline:
                raise AssertionError(f'"{test_id}" did not appear within {timeout:.0f} s')
            time.sleep(0.2)

    def tree(self) -> ET.Element:
        """整個畫面結構，一次讀完：要讀很多個元素時（例如列表的每一列），比一個一個找快得多。"""
        return ET.fromstring(self.driver.page_source.encode("utf-8"))

    def frames(self, test_id: str) -> list[tuple[float, float, float, float]]:
        """這個 hook 的每個元素在畫面上的位置：(x, y, 寬, 高)，單位是 pt，由上到下排好。
        捲動區域外的元素也在畫面結構裡，所以也量得到。"""
        found = [(float(e.get("x")), float(e.get("y")), float(e.get("width")), float(e.get("height")))
                 for e in self.tree().iter() if e.get("name") == test_id]
        return sorted(found, key=lambda f: f[1])

    # ---- 讀 ------------------------------------------------------------------------------

    def _read(self, read, test_id: str, timeout: float = TIMEOUT):
        """畫面重畫時元素可能剛好被換掉（stale）：重新找一次再讀。"""
        deadline = time.monotonic() + timeout
        while True:
            try:
                return read(self.wait_for(test_id, timeout=max(0.5, deadline - time.monotonic())))
            except (StaleElementReferenceException, WebDriverException):
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.2)

    def text(self, test_id: str, timeout: float = TIMEOUT) -> str:
        return self._read(lambda e: e.text, test_id, timeout)

    def is_enabled(self, test_id: str) -> bool:
        return self._read(lambda e: e.is_enabled(), test_id)

    # ---- 等畫面變成預期的樣子 ------------------------------------------------------------

    def expect_text(self, test_id: str, expected: str, timeout: float = TIMEOUT) -> None:
        """等到元素的文字等於 expected；逾時就失敗，訊息裡有最後看到的值。按鈕上的字也用這個。"""
        deadline = time.monotonic() + timeout
        seen = None
        while True:
            try:
                seen = self._read(lambda e: e.text, test_id, timeout=max(0.5, deadline - time.monotonic()))
            except (AssertionError, WebDriverException):
                seen = None
            if seen == expected:
                return
            if time.monotonic() > deadline:
                raise AssertionError(f'"{test_id}" shows {seen!r}, expected {expected!r}')
            time.sleep(0.2)

    def expect_shown(self, test_id: str, timeout: float = TIMEOUT) -> None:
        self.wait_for(test_id, timeout)

    def expect_absent(self, test_id: str, settle: float = 0.5) -> None:
        """要證明的是「沒有出現」，沒有事件可以等：給畫面一點時間，然後確認不在。
        只用在畫面上其他東西已經證明載入完成之後，否則「還沒出現」會被當成「不會出現」。"""
        time.sleep(settle)
        assert not self.is_shown(test_id), f'"{test_id}" is on the screen'

    # ---- 操作 ----------------------------------------------------------------------------

    def tap(self, test_id: str) -> None:
        self.wait_for(test_id).click()

    def type_into(self, test_id: str, value: str) -> None:
        """點進輸入框、清掉原本的字、用鍵盤打進 value，等輸入框顯示出 value 才回來：依輸入而變的
        東西（例如送出鈕能不能按）要等 SwiftUI 重畫一次，太早讀會讀到上一個狀態。"""
        field = self.wait_for(test_id)
        field.click()
        field.clear()
        field.send_keys(value)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                if self._all(test_id)[0].text == value:
                    return
            except (IndexError, WebDriverException):
                pass
            time.sleep(0.1)
        raise AssertionError(f'"{test_id}" shows {self.text(test_id)!r} after typing {value!r}')
