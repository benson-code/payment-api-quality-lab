"""網頁測試的預期值，抄自 web/SPEC.md §5.5。

刻意不讀前端的 messages.js：預期值要來自規格，不是來自被測的程式。前端改了文案而規格沒改，
測試就該紅。
"""
ERROR_TEXT = {
    "INVALID_AMOUNT": "Enter an amount like 100 or 100.50: more than 0, at most two decimals.",   # E-01
    "INSUFFICIENT_BALANCE": "Not enough balance for this payment.",                               # E-02
    "LIMIT_EXCEEDED": "This is above the single-payment limit of 50,000.00.",                     # E-03
    "REFUND_EXCEEDS_PAYMENT": "This refund would exceed what is left to refund on this payment.", # E-04
    "WALLET_NOT_FOUND": "No wallet with this ID.",                                                 # E-05
    "PAYMENT_NOT_FOUND": "No payment with this ID.",                                               # E-06
    "INVALID_OWNER": "Enter a name of 1 to 50 characters.",                                        # E-07
}
