"""API 文件（/docs 的 Swagger 畫面、/openapi.json）用的回應格式。

只用來產生文件：實際的回應由 service.py 組成，這裡的類別不參與，也不驗證任何東西。
路由直接回 dict 或 JSONResponse 時，FastAPI 不知道回應長什麼樣，文件只寫得出「任意內容」，
錯誤也只會列它自己預設的「422 Validation Error」，跟實際回應對不上。
文件和實際回應一致由 CTR-004 檢查（tests/test_contract.py）。
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Money = Annotated[str, Field(pattern=r"^-?[0-9]+\.[0-9]{2}$", examples=["100.50"])]
Timestamp = Annotated[str, Field(examples=["2026-10-11T10:31:25.410+00:00"])]
WalletId = Annotated[str, Field(pattern=r"^w_[0-9a-z]+$", examples=["w_2b440cba3a8c4d27"])]
TopUpId = Annotated[str, Field(pattern=r"^t_[0-9a-z]+$")]
PaymentId = Annotated[str, Field(pattern=r"^p_[0-9a-z]+$", examples=["p_00d3f28e80184e3b"])]
RefundId = Annotated[str, Field(pattern=r"^r_[0-9a-z]+$")]
TransferId = Annotated[str, Field(pattern=r"^x_[0-9a-z]+$")]


class Doc(BaseModel):
    model_config = ConfigDict(extra="forbid")       # 文件寫明：不會有其他欄位


class Health(Doc):
    status: Literal["ok"]
    bugs: list[str] = Field(description="planted defects switched on (BUGS)")


class Wallet(Doc):
    wallet_id: WalletId
    owner: str
    currency: Literal["TWD"]
    balance: Money
    created_at: Timestamp


class TopUp(Doc):
    topup_id: TopUpId
    wallet_id: WalletId
    amount: Money
    balance: Money


class Payment(Doc):
    payment_id: PaymentId
    wallet_id: WalletId
    amount: Money
    refunded: Money
    created_at: Timestamp
    balance_after: Money


class RefundLine(Doc):
    refund_id: RefundId
    amount: Money
    created_at: Timestamp


class PaymentDetail(Doc):
    payment_id: PaymentId
    wallet_id: WalletId
    amount: Money
    refunded: Money
    created_at: Timestamp
    refunds: list[RefundLine]


class Refund(Doc):
    refund_id: RefundId
    payment_id: PaymentId
    amount: Money
    payment_refunded: Money
    payment_refundable: Money
    balance_after: Money
    created_at: Timestamp


class Transfer(Doc):
    transfer_id: TransferId
    from_wallet_id: WalletId
    to_wallet_id: WalletId
    amount: Money
    from_balance_after: Money
    created_at: Timestamp


class Entry(Doc):
    entry_id: int
    type: Literal["TOPUP", "PAYMENT", "REFUND", "TRANSFER_OUT", "TRANSFER_IN"]
    amount: Money
    balance_after: Money
    ref_id: str | None
    created_at: Timestamp


class Transactions(Doc):
    wallet_id: WalletId
    transactions: list[Entry]


class Error(Doc):
    error_code: str = Field(pattern=r"^[A-Z_]+$", description="what clients act on")
    message: str = Field(description="an explanation for people")


REPLAYED = {"Idempotent-Replayed": {
    "description": "true when this is the stored result of an earlier request with the same Idempotency-Key",
    "schema": {"type": "string", "enum": ["true", "false"]},
}}


def ok(model: type[Doc], status: int = 200, replay: bool = False) -> dict:
    """成功的回應。replay：這支 API 收 Idempotency-Key，回應帶 Idempotent-Replayed header。"""
    response: dict = {"model": model}
    if replay:
        response["headers"] = REPLAYED
    return {status: response}


def errors(codes: dict[int, str]) -> dict:
    """這支 API 會回的錯誤：{狀態碼: 可能的 error_code}。格式一律是 Error，範例用第一個 error_code。"""
    return {status: {"model": Error, "description": f"error_code: {names}",
                     "content": {"application/json": {"example": {
                         "error_code": names.split(",")[0], "message": "an explanation for people"}}}}
            for status, names in codes.items()}
