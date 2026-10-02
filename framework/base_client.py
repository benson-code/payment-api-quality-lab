"""BaseClient：所有 API 呼叫都經過這裡。

統一處理 base URL、timeout、log。測試案例不直接用 requests，
這樣換環境、加 header、改 log 格式都只要改一個地方。
"""
from __future__ import annotations

import logging

import requests

log = logging.getLogger("api")


class BaseClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def request(self, method: str, path: str, *, json: object = None,
                headers: dict | None = None) -> requests.Response:
        r = self.session.request(method, self.base_url + path, json=json,
                                 headers=headers, timeout=self.timeout)
        log.info("%s %s %s -> %s %s", method, path, json if json is not None else "",
                 r.status_code, r.text[:300])
        return r
