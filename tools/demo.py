"""示範用：起一台乾淨的 API，建好一個有交易紀錄的錢包，印出網頁網址。Ctrl+C 結束，資料一起丟掉。

    .venv/bin/python tools/demo.py                    # API 在 127.0.0.1:8400，新的暫存資料庫
    .venv/bin/python tools/demo.py --port 8401        # 8400 被占用時
    .venv/bin/python tools/demo.py --bugs float_math  # 打開埋好的 bug，現場看它錯在哪裡

示範錢包的紀錄：儲值、兩筆付款、其中一筆部分退款、再儲值、再付款，交易紀錄和付款明細都有東西可看。
只聽 127.0.0.1：從別台電腦看要用 SSH 通道（README §7）。Android App 預設連 127.0.0.1:8400，
所以用 8400 時 adb reverse tcp:8400 tcp:8400 之後，App 開同一個錢包就看得到同樣的紀錄。
"""
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from framework.wallet_api import WalletAPI  # noqa: E402

OWNER = "Alex"
STORY = [                  # （動作, 金額）依序執行；refund 退的是上一筆付款
    ("top_up", "5000.00"),
    ("pay", "1280.50"),
    ("pay", "450.00"),
    ("refund", "150.00"),
    ("top_up", "300.00"),
    ("pay", "30.00"),
]


def seed(api: WalletAPI) -> str:
    wallet = api.create_wallet(OWNER).json()["wallet_id"]
    last_payment = None
    for action, amount in STORY:
        if action == "top_up":
            r = api.top_up(wallet, amount)
        elif action == "pay":
            r = api.pay(wallet, amount)
            last_payment = r.json()["payment_id"]
        else:
            r = api.refund(last_payment, amount)
        assert r.status_code == 201, r.text
    return wallet


def _stop(*_) -> None:
    """關掉終端機送的是 SIGTERM：也照 Ctrl+C 的路線收尾，不然 API 會被留在背景。"""
    raise KeyboardInterrupt


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Start a clean API with a demo wallet.")
    parser.add_argument("--port", type=int, default=8400)
    parser.add_argument("--bugs", default="", help="planted defects to turn on, comma-separated (app/bugs.py)")
    args = parser.parse_args()

    if port_in_use(args.port):
        print(f"127.0.0.1:{args.port} is in use (another API?). Stop it, or choose another port with --port.")
        return 2
    if not (ROOT / "web" / "dist" / "index.html").is_file():
        print("The front end is not built, so /app will not be served: cd web && npm ci && npm run build")

    signal.signal(signal.SIGTERM, _stop)
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "DB_PATH": str(Path(tmp) / "demo.db"), "BUGS": args.bugs}
        proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                 "--port", str(args.port), "--log-level", "warning"], cwd=ROOT, env=env)
        base = f"http://127.0.0.1:{args.port}"
        try:
            for _ in range(100):
                try:
                    if requests.get(base + "/health", timeout=1).ok:
                        break
                except requests.ConnectionError:
                    time.sleep(0.2)
            else:
                print("The API did not start.")
                return 1
            wallet = seed(WalletAPI(base))
            print(f"API        {base}   planted defects: {args.bugs or 'none'}", flush=True)
            print(f"Web        {base}/app/#/w/{wallet}", flush=True)
            print(f"Wallet ID  {wallet}   (paste it on the Start screen, web or app)", flush=True)
            if args.port == 8400:
                print("Android    adb reverse tcp:8400 tcp:8400, then open the app", flush=True)
            print("Ctrl+C to stop; the demo data goes with it.", flush=True)
            proc.wait()
        except KeyboardInterrupt:
            pass
        finally:
            proc.terminate()
            proc.wait(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
