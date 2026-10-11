"""測試代理伺服器：站在 Android App 和 API 中間，做出網頁測試（framework/web/network.py）那幾種網路狀況。

瀏覽器的每個請求 Playwright 都攔得到，原生 App 的不行。所以 App 啟動時把 API 位址指到這裡
（debug 版的啟動參數 apiBaseUrl），由這裡轉給真正的 API；有規則的請求才另外處理：

    hold           請求先停在這裡，release() 才送出：用來看「處理中」的畫面、測連點
    lose_response  請求送到 API、也處理完了，但回應丟掉：App 看到連線中斷，錢其實已經扣了。
                   這是重送必須用同一把 key 的原因（APP-008）
    block          請求根本沒送到 API：App 一樣看到連線中斷，但什麼都沒發生

和網頁測試一樣只攔 POST：GET /payments/{id} 這類讀取不受影響。
每個請求都記下來（方法、路徑、Idempotency-Key、狀態碼、回應的 JSON），測試可以檢查 App 送了
哪些 key，也可以從建立錢包的回應拿到錢包編號（畫面上的編號是遮罩過的，D-04）。

每個回應都關掉連線。連線若被重複使用，App 可能拿舊的 socket 送出規則生效後的請求，規則就會漏接。
"""
from __future__ import annotations

import http.client
import http.server
import json
import socketserver
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlsplit

HOLD_LIMIT = 60          # 被 hold 的請求最多等幾秒；測試忘了 release 也不會永遠卡住


@dataclass(frozen=True)
class Exchange:
    """代理伺服器看到的一個請求。"""
    method: str
    path: str
    key: str | None                  # Idempotency-Key 標頭，沒帶就是 None
    status: int | None               # API 的狀態碼；App 沒收到回應（lose、block）時是 None
    body: object = None              # API 回應的 JSON（是 JSON 的話）


class Held:
    """hold() 擋住、等 release() 的請求。"""

    def __init__(self) -> None:
        self._released = threading.Event()
        self._lock = threading.Lock()
        self._count = 0

    def _wait(self) -> None:
        with self._lock:
            self._count += 1
        self._released.wait(HOLD_LIMIT)

    @property
    def count(self) -> int:
        """被擋住過幾個請求。"""
        with self._lock:
            return self._count

    def release(self) -> None:
        self._released.set()


class _Rule:
    def __init__(self, suffix: str, mode: str, times: int | None, held: Held | None = None) -> None:
        self.suffix, self.mode, self.left, self.held = suffix, mode, times, held

    def take(self, method: str, path: str) -> bool:
        if method != "POST" or not path.split("?")[0].endswith(self.suffix) or self.left == 0:
            return False
        if self.left is not None:
            self.left -= 1
        return True


class TestProxy:
    __test__ = False                 # 名字有 Test，但不是 pytest 的測試類別

    def __init__(self, upstream: str) -> None:
        u = urlsplit(upstream)
        self._upstream = (u.hostname, u.port or 80)
        self._lock = threading.Lock()
        self._rules: list[_Rule] = []
        self._log: list[Exchange] = []
        self._server: _Server | None = None

    # ---- 起停 ----------------------------------------------------------------------------

    def start(self) -> TestProxy:
        """只聽 127.0.0.1 的一個空 port：不對外開放。裝置經由 adb reverse 連進來。"""
        self._server = _Server(("127.0.0.1", 0), _handler_for(self))
        threading.Thread(target=self._server.serve_forever, name="test-proxy", daemon=True).start()
        return self

    def stop(self) -> None:
        if self._server:
            self.reset()                 # 先放行被擋住的請求再關
            self._server.shutdown()
            self._server.server_close()

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def reset(self) -> None:
        """清掉規則和紀錄，放行被擋住的請求。每個測試開始前呼叫。"""
        with self._lock:
            for rule in self._rules:
                if rule.held:
                    rule.held.release()
            self._rules.clear()
            self._log.clear()

    # ---- 規則 ----------------------------------------------------------------------------

    @contextmanager
    def hold(self, path_suffix: str):
        """路徑結尾是 path_suffix 的 POST 全部擋住，直到 release() 或離開 with。"""
        held = Held()
        rule = self._add(_Rule(path_suffix, "hold", None, held))
        try:
            yield held
        finally:
            held.release()
            self._remove(rule)

    @contextmanager
    def lose_response(self, path_suffix: str, times: int = 1):
        """前 times 個 POST 送到 API、等它處理完，再把回應丟掉。"""
        rule = self._add(_Rule(path_suffix, "lose", times))
        try:
            yield
        finally:
            self._remove(rule)

    @contextmanager
    def block(self, path_suffix: str):
        """POST 完全送不到 API。"""
        rule = self._add(_Rule(path_suffix, "block", None))
        try:
            yield
        finally:
            self._remove(rule)

    # ---- 送了什麼 ------------------------------------------------------------------------

    def exchanges(self, path_suffix: str = "", method: str = "POST") -> list[Exchange]:
        """路徑結尾是 path_suffix 的請求，依到達順序。"""
        with self._lock:
            return [e for e in self._log
                    if e.method == method and e.path.split("?")[0].endswith(path_suffix)]

    def keys(self, path_suffix: str) -> list[str | None]:
        """每個 POST 帶的 Idempotency-Key，依順序（沒帶就是 None）。"""
        return [e.key for e in self.exchanges(path_suffix)]

    # ---- 內部 ----------------------------------------------------------------------------

    def _add(self, rule: _Rule) -> _Rule:
        with self._lock:
            self._rules.append(rule)
        return rule

    def _remove(self, rule: _Rule) -> None:
        with self._lock:
            if rule in self._rules:
                self._rules.remove(rule)

    def _match(self, method: str, path: str) -> _Rule | None:
        with self._lock:
            return next((r for r in self._rules if r.take(method, path)), None)

    def _record(self, exchange: Exchange) -> None:
        with self._lock:
            self._log.append(exchange)


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True            # 被擋住的請求不能讓測試結束不了


def _handler_for(proxy: TestProxy):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args) -> None:          # 不印：紀錄在 proxy.exchanges()
            pass

        def _forward(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            key = self.headers.get("Idempotency-Key")
            rule = proxy._match(self.command, self.path)
            mode = rule.mode if rule else None

            if mode == "block":
                proxy._record(Exchange(self.command, self.path, key, None))
                self.close_connection = True           # 不回應就關掉；API 什麼都沒收到
                return
            if mode == "hold":
                rule.held._wait()

            upstream = http.client.HTTPConnection(*proxy._upstream, timeout=30)
            headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "connection")}
            upstream.request(self.command, self.path, body=body, headers=headers)
            answer = upstream.getresponse()
            data = answer.read()
            upstream.close()
            try:
                parsed = json.loads(data) if data else None
            except ValueError:
                parsed = None

            if mode == "lose":
                proxy._record(Exchange(self.command, self.path, key, None, parsed))
                self.close_connection = True           # API 處理完了，App 卻收不到回應
                return
            proxy._record(Exchange(self.command, self.path, key, answer.status, parsed))
            self.send_response(answer.status)
            for name, value in answer.getheaders():
                if name.lower() not in ("transfer-encoding", "connection", "content-length"):
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            self.close_connection = True

        do_GET = do_POST = _forward

    return Handler
