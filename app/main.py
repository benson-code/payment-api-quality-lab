"""HTTP 路由。啟動：

    DB_PATH=wallet.db .venv/bin/uvicorn app.main:app --port 8400
"""
from __future__ import annotations

import os
from collections.abc import Iterator

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import bugs, service
from app.db import connect, init_db
from app.errors import ApiError

DB_PATH = os.environ.get("DB_PATH", "wallet.db")
init_db(DB_PATH)

app = FastAPI(title="payment-api-quality-lab")


# ---- 錯誤：全部轉成統一格式 ---------------------------------------------------

@app.exception_handler(ApiError)
def handle_api_error(_: Request, e: ApiError) -> JSONResponse:
    return JSONResponse(status_code=e.status, content={"error_code": e.error_code, "message": e.message})


@app.exception_handler(RequestValidationError)
def handle_validation_error(_: Request, e: RequestValidationError) -> JSONResponse:
    # FastAPI 預設回 422 和一大串細節；改成跟其他錯誤一樣的格式
    first = e.errors()[0]
    field = ".".join(str(p) for p in first["loc"] if p != "body")
    return JSONResponse(status_code=400, content={"error_code": "INVALID_REQUEST",
                                                  "message": f"{field}: {first['msg']}"})


def get_conn() -> Iterator:
    conn = connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


# ---- 請求格式 ------------------------------------------------------------------
# amount 宣告成 object 而不是 str：讓「傳數字」這種錯誤進到 parse_amount，
# 回傳跟其他金額錯誤一樣的 INVALID_AMOUNT，而不是 pydantic 的通用訊息

class CreateWallet(BaseModel):
    owner: str


class AmountBody(BaseModel):
    amount: object = None


class PaymentBody(BaseModel):
    wallet_id: object = None
    amount: object = None


class TransferBody(BaseModel):
    from_wallet_id: object = None
    to_wallet_id: object = None
    amount: object = None


# ---- 路由 ----------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    # 回報目前開了哪些 bug：CI 的「證明測試會紅」那一輪，要先確認開關真的有打開
    return {"status": "ok", "bugs": sorted(bugs.ACTIVE)}


@app.post("/wallets", status_code=201)
def create_wallet(body: CreateWallet, conn=Depends(get_conn)) -> dict:
    return service.create_wallet(conn, body.owner)


@app.get("/wallets/{wallet_id}")
def get_wallet(wallet_id: str, conn=Depends(get_conn)) -> dict:
    return service.wallet_view(service.get_wallet_row(conn, wallet_id))


@app.post("/wallets/{wallet_id}/topups", status_code=201)
def top_up(wallet_id: str, body: AmountBody, conn=Depends(get_conn)) -> dict:
    return service.top_up(conn, wallet_id, body.amount)


@app.post("/payments", status_code=201)
def pay(body: PaymentBody, idempotency_key: str | None = Header(default=None),
        conn=Depends(get_conn)) -> JSONResponse:
    # Header(...) 會把參數名 idempotency_key 對應到 HTTP header「Idempotency-Key」
    status, response, replayed = service.pay(conn, idempotency_key, body.model_dump())
    return JSONResponse(status_code=status, content=response,
                        headers={"Idempotent-Replayed": "true" if replayed else "false"})


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str, conn=Depends(get_conn)) -> dict:
    return service.get_payment(conn, payment_id)


@app.post("/payments/{payment_id}/refunds", status_code=201)
def refund(payment_id: str, body: AmountBody, idempotency_key: str | None = Header(default=None),
           conn=Depends(get_conn)) -> JSONResponse:
    status, response, replayed = service.refund(conn, idempotency_key, payment_id, body.model_dump())
    return JSONResponse(status_code=status, content=response,
                        headers={"Idempotent-Replayed": "true" if replayed else "false"})


@app.get("/wallets/{wallet_id}/transactions")
def transactions(wallet_id: str, conn=Depends(get_conn)) -> dict:
    return service.transactions(conn, wallet_id)


@app.post("/transfers", status_code=201)
def transfer(body: TransferBody, idempotency_key: str | None = Header(default=None),
             conn=Depends(get_conn)) -> JSONResponse:
    status, response, replayed = service.transfer(conn, idempotency_key, body.model_dump())
    return JSONResponse(status_code=status, content=response,
                        headers={"Idempotent-Replayed": "true" if replayed else "false"})
