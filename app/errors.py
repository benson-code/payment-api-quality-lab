"""統一的錯誤格式：所有錯誤都回 {"error_code": ..., "message": ...}。"""


class ApiError(Exception):
    def __init__(self, status: int, error_code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.error_code = error_code
        self.message = message
