"""用 jsonschema 驗回應格式：欄位有沒有少、型別對不對、有沒有多出不該有的欄位。"""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).parent / "schemas"


@cache
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMA_DIR / f"{name}.json").read_text()))


def assert_schema(body: object, name: str) -> None:
    """不符合就把每一個錯誤列出來，失敗訊息直接告訴你哪個欄位錯了。"""
    errors = sorted(_validator(name).iter_errors(body), key=lambda e: list(e.path))
    assert not errors, f"response does not match schema '{name}':\n" + "\n".join(
        f"  {'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors)
