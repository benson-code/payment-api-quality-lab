"""pytest 的進入點：命令列參數、起被測系統、提供 fixture、依參數挑案例。

兩種跑法：
    pytest                                                  # local：自己起一台 API（隨機 port、暫存資料庫）
    pytest --env=external --base-url=http://127.0.0.1:8400 --db-path=wallet.db
                                                            # external：打一台已經起好的 API（CI 用這個）
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

from framework.db import Database
from framework.wallet_api import WalletAPI

ROOT = Path(__file__).resolve().parent.parent


# ---- 命令列參數 ----------------------------------------------------------------

def pytest_addoption(parser):
    g = parser.getgroup("payment-api-quality-lab")
    g.addoption("--env", default="local", choices=["local", "external"],
                help="local：自己起 API；external：打 --base-url 指定的 API")
    g.addoption("--base-url", default=None, help="external 模式要打的 API")
    g.addoption("--db-path", default=None, help="external 模式那台 API 的 SQLite 檔（資料庫驗證要用）")
    g.addoption("--target_case_ids", default="", help="只跑這些案例編號，逗號分隔")
    g.addoption("--target_marks", default="", help="只跑帶這些標籤的案例，逗號分隔（任一符合即可）")


# ---- 依案例編號、標籤挑案例 ----------------------------------------------------

def case_ids_of(item) -> set[str]:
    ids = {m.args[0] for m in item.iter_markers("case_id")}
    if hasattr(item, "callspec"):
        ids.add(item.callspec.id)          # CSV 資料驅動的案例：param id 就是 case_id
    return ids


def pytest_collection_modifyitems(config, items):
    """收集完、執行前，把不符合條件的案例 deselect 掉。"""
    want_ids = {s for s in config.getoption("--target_case_ids").split(",") if s}
    want_marks = {s for s in config.getoption("--target_marks").split(",") if s}
    if not want_ids and not want_marks:
        return
    keep, drop = [], []
    for item in items:
        ok = (not want_ids or case_ids_of(item) & want_ids) and \
             (not want_marks or {m.name for m in item.iter_markers()} & want_marks)
        (keep if ok else drop).append(item)
    config.hook.pytest_deselected(items=drop)
    items[:] = keep


# ---- 被測系統 ------------------------------------------------------------------

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_healthy(base_url: str, timeout: float = 20) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(base_url + "/health", timeout=1)
            if r.status_code == 200:
                return r.json()
        except requests.ConnectionError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"API at {base_url} did not become healthy in {timeout}s")


@pytest.fixture(scope="session")
def server(request, tmp_path_factory):
    """整個測試過程共用一台 API。每個測試自己建新錢包，所以共用也不會互相干擾。"""
    opt = request.config.getoption
    if opt("--env") == "external":
        base_url = opt("--base-url") or pytest.exit("--env external needs --base-url", 2)
        health = wait_healthy(base_url)
        yield {"base_url": base_url, "db_path": opt("--db-path"), "bugs": health["bugs"]}
        return

    db_path = str(tmp_path_factory.mktemp("db") / "wallet.db")
    port = free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env={**os.environ, "DB_PATH": db_path})     # BUGS 環境變數會一起傳進去
    base_url = f"http://127.0.0.1:{port}"
    try:
        health = wait_healthy(base_url)
        expected = sorted(b for b in os.environ.get("BUGS", "").split(",") if b)
        # 埋 bug 的那一輪，先確認開關真的有打開，不然「測試沒紅」沒有意義
        assert health["bugs"] == expected, f"server reports bugs {health['bugs']}, expected {expected}"
        yield {"base_url": base_url, "db_path": db_path, "bugs": health["bugs"]}
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="session")
def api(server) -> WalletAPI:
    return WalletAPI(server["base_url"])


@pytest.fixture
def api_factory(server):
    """併發測試用：每個執行緒拿自己的 client，不共用連線。"""
    return lambda: WalletAPI(server["base_url"])


@pytest.fixture
def db(server):
    if not server["db_path"]:
        pytest.skip("database checks need --db-path in external mode")
    d = Database(server["db_path"])
    yield d
    d.close()
