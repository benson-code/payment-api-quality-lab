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
    _assert_valid(body, _validator(name), f"schema '{name}'")


def assert_documented(body: object, doc: dict, schema: dict, label: str) -> None:
    """跟 API 文件（OpenAPI）裡寫的格式比對。schema 是文件中的一段，可以含 $ref。"""
    _assert_valid(body, Draft202012Validator(_resolve(schema, doc)), f"the API document ({label})")


def _resolve(schema: object, doc: dict) -> object:
    """把 {"$ref": "#/components/schemas/X"} 換成 X 的內容，jsonschema 才能直接用。"""
    if isinstance(schema, dict):
        if "$ref" in schema:
            name = schema["$ref"].removeprefix("#/components/schemas/")
            return _resolve(doc["components"]["schemas"][name], doc)
        return {k: _resolve(v, doc) for k, v in schema.items()}
    if isinstance(schema, list):
        return [_resolve(v, doc) for v in schema]
    return schema


def _assert_valid(body: object, validator: Draft202012Validator, what: str) -> None:
    errors = sorted(validator.iter_errors(body), key=lambda e: list(e.path))
    assert not errors, f"response does not match {what}:\n" + "\n".join(
        f"  {'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors)
