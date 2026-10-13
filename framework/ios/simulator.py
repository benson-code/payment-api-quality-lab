"""用 xcrun simctl 操作 iOS 模擬器：Appium 管不到、或用 simctl 比較直接的事（Android 的 device.py）。

模擬器和 Mac 共用網路：App 裡的 127.0.0.1 就是這台 Mac，不需要 Android 的 adb reverse。
"""
from __future__ import annotations

import json
import subprocess

BUNDLE_ID = "lab.wallet"


class SimctlError(RuntimeError):
    pass


def simctl(*args: str, timeout: float = 120) -> str:
    r = subprocess.run(["xcrun", "simctl", *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise SimctlError(f"simctl {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def booted() -> list[dict]:
    """開著的模擬器：每台是 simctl 的一筆資料（udid、name、state …），另外加上它的 iOS 版本 os。"""
    devices = json.loads(simctl("list", "devices", "booted", "--json"))["devices"]
    # runtime 的名字像 com.apple.CoreSimulator.SimRuntime.iOS-26-0
    return [{**d, "os": runtime.rsplit(".", 1)[-1].replace("-", " ", 1).replace("-", ".")}
            for runtime, ds in devices.items() for d in ds if d["state"] == "Booted"]


class Simulator:
    def __init__(self, udid: str, name: str = "", os: str = "") -> None:
        self.udid, self.name, self.os = udid, name, os

    def install(self, app_path: str) -> None:
        """先移除再安裝：上一輪留下的資料一起清掉。"""
        try:
            simctl("uninstall", self.udid, BUNDLE_ID)
        except SimctlError:
            pass                                       # 本來就沒裝
        simctl("install", self.udid, app_path)
