"""讀 cases/*.csv：一列一個案例，case_id、marks、is_run 都在資料裡。"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"


def load(filename: str) -> list:
    out = []
    with (CASES_DIR / filename).open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["is_run"].strip().upper() != "Y":
                continue
            # amount 欄位用 JSON 寫：「"10.50"」是字串、「10.5」是數字、「null」是沒有值
            row["amount"] = json.loads(row["amount"])
            marks = [getattr(pytest.mark, m) for m in row["marks"].split("|") if m]
            out.append(pytest.param(row, id=row["case_id"], marks=marks))
    return out
