"""所有畫面共用：用 testTag 找元素、讀文字、輸入、捲動、等待。

Compose 搭配 UiAutomator 的幾個特性都在這裡處理一次（android/README.md 有完整說明）：
- 按鈕的文字在它的子元素上：label()
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
from selenium.webdriver.remote.webelement import WebElement

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

    def scroll(self, direction: str) -> bool:
        """把可捲動的區域往 "down" 或 "up" 捲大半個畫面；回傳還能不能繼續往那個方向捲。"""
        areas = self.driver.find_elements(AppiumBy.ANDROID_UIAUTOMATOR, "new UiSelector().scrollable(true)")
        if not areas:
            return False                     # 內容一個畫面放得下，沒有東西可捲
        return bool(self.driver.execute_script(
            "mobile: scrollGesture", {"elementId": areas[0].id, "direction": direction, "percent": 0.6}))

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

    def label(self, test_id: str) -> str:
        """按鈕上的字。Compose 的按鈕是一個可點的容器（帶 testTag），字在它的子元素 TextView 上。"""
        return self._read(lambda e: e.find_element(AppiumBy.CLASS_NAME, "android.widget.TextView").text, test_id)

    def is_enabled(self, test_id: str) -> bool:
        return self._read(lambda e: e.get_attribute("enabled") == "true", test_id)

    # ---- 等畫面變成預期的樣子 ------------------------------------------------------------

    def expect_text(self, test_id: str, expected: str, timeout: float = TIMEOUT) -> None:
        """等到元素的文字等於 expected；逾時就失敗，訊息裡有最後看到的值。"""
        deadline = time.monotonic() + timeout
        seen = None
        while True:
            try:
                seen = self.text(test_id, timeout=max(0.5, deadline - time.monotonic()))
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
        self.find(test_id).click()

    def type_into(self, test_id: str, value: str) -> None:
        """一次換掉輸入框的整段文字（不是 clear() 再 send_keys()，理由見檔案開頭）。"""
        field = self.find(test_id)
        self.driver.execute_script("mobile: replaceElementValue", {"elementId": field.id, "text": value})

    def system_back(self) -> None:
        """系統的返回鍵或手勢（N-01），不是畫面上方的返回鍵（那是 tap("back")）。"""
        self.driver.back()
