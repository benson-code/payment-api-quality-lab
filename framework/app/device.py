"""用 adb 操作裝置：Appium 管不到、或用 adb 比較直接的事。

安裝 App、轉接 port（adb reverse）、切換螢幕設定、固定時區、帶參數重新啟動 App、讀崩潰紀錄。
"""
from __future__ import annotations

import subprocess

PACKAGE = "lab.wallet"
ACTIVITY = f"{PACKAGE}/.MainActivity"


class AdbError(RuntimeError):
    pass


def connected_serials() -> list[str]:
    out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=30).stdout
    return [line.split()[0] for line in out.splitlines()[1:] if line.endswith("\tdevice")]


class Device:
    def __init__(self, serial: str) -> None:
        self.serial = serial

    def adb(self, *args: str, timeout: float = 60) -> str:
        r = subprocess.run(["adb", "-s", self.serial, *args], capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            raise AdbError(f"adb {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
        return r.stdout

    def shell(self, *args: str, timeout: float = 60) -> str:
        return self.adb("shell", *args, timeout=timeout).replace("\r\n", "\n")

    def is_booted(self) -> bool:
        try:
            return self.shell("getprop", "sys.boot_completed").strip() == "1"
        except (AdbError, subprocess.TimeoutExpired):
            return False

    # ---- App ------------------------------------------------------------------------------

    def install(self, apk: str) -> None:
        """先移除再安裝：本機和 CI 的 debug 簽章不同，直接覆蓋安裝會被拒絕
        （INSTALL_FAILED_UPDATE_INCOMPATIBLE），移除也順便清掉上一輪留下的資料。"""
        try:
            self.adb("uninstall", PACKAGE)
        except AdbError:
            pass                                       # 本來就沒裝
        self.adb("install", apk, timeout=180)

    def start_app(self, api_base_url: str) -> None:
        """強制停止後重新啟動，App 從開始畫面重來，API 位址指向 api_base_url。

        -S 先 force-stop：程序和它保存的畫面狀態一起丟掉，上一個測試的狀態不會留下來。
        -W 等到第一個畫面畫出來才回來。apiBaseUrl 只有 debug 版會讀（ApiConfig.kt）。
        """
        out = self.shell("am", "start", "-W", "-S", "-n", ACTIVITY, "--es", "apiBaseUrl", api_base_url)
        if "Status: ok" not in out:
            raise AdbError(f"the app did not start: {out.strip()}")

    # ---- 網路 -----------------------------------------------------------------------------

    def reverse(self, port: int) -> None:
        """裝置上的 127.0.0.1:port 接到這台機器的 127.0.0.1:port，什麼都不用對外開放。"""
        self.adb("reverse", f"tcp:{port}", f"tcp:{port}")

    def remove_reverse(self, port: int) -> None:
        try:
            self.adb("reverse", "--remove", f"tcp:{port}")
        except AdbError:
            pass

    # ---- 裝置設定 -------------------------------------------------------------------------

    def set_display(self, size: str | None, density: int | None) -> None:
        """改變螢幕大小和密度（SPEC.md §5 的兩種設定）；None 表示還原成裝置原本的。"""
        self.shell("wm", "size", size or "reset")
        self.shell("wm", "density", str(density) if density else "reset")

    def timezone(self) -> str:
        return self.shell("getprop", "persist.sys.timezone").strip()

    def set_timezone(self, tz: str) -> None:
        self.shell("cmd", "alarm", "set-timezone", tz)

    # ---- 崩潰紀錄 -------------------------------------------------------------------------

    def clear_crashes(self) -> None:
        self.adb("logcat", "-b", "crash", "-c")

    def app_crashes(self) -> list[str]:
        """清掉之後這個 App 的崩潰紀錄。裝置上別的程式也會崩潰（redroid 模擬的藍牙服務大約每
        幾小時一次），所以只看 App 自己的：Java 例外的 Process: lab.wallet、原生崩潰的 >>> lab.wallet <<<。"""
        log = self.adb("logcat", "-b", "crash", "-d")
        return [line for line in log.splitlines()
                if f"Process: {PACKAGE}," in line or f">>> {PACKAGE} <<<" in line]
