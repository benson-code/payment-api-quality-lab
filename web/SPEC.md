# Wallet web front end — Specification

| | |
|---|---|
| Version | 1.0 |
| Date | 2026-10-10 |
| Status | Implemented. Every rule marked *script* was checked against the running system with a browser script on the date above; rules marked *review* were checked by reading the code |
| Code | `web/src/` (React 19 + Vite), served by the API under `/app` |
| Tests | Playwright for Python, `tests/web/` (cases WEB-001 to WEB-012, §7) |

## 1. Purpose

A mobile-first wallet page in front of the payment API. It exists so that the payment risks this
repository tests at the API level (charging twice, losing a cent, refunding more than was paid) are
also tested where a user meets them: a slow network, a double tap, a lost response.

It is not a product. There is no login: the wallet ID in the URL is the only key, exactly as in the
API (see §9). There is no transfer screen.

Every rule has an ID (`R-xx`, `K-xx`, `D-xx`, `L-xx`, `E-xx`). Test cases cite these IDs, and §8
traces each rule to the cases that cover it, including the rules no case covers yet.

## 2. Architecture

```
Browser (phone-sized viewport)
   │  http://<host>/app/#/w/<wallet>/pay      hash routing: the server only ever serves index.html
   ▼
FastAPI (uvicorn)
   ├── /app/*      static files from web/dist (mounted only if the front end has been built)
   └── /wallets, /payments, ...   the API, same origin: no CORS
          │
          ▼
       SQLite
```

The page holds no money logic. Amounts are sent as the strings the user typed and the API decides
whether they are valid (R-02). The only state that matters for money on the client is the current
payment attempt and its Idempotency-Key (§5.2).

## 3. Design source

The visual design is defined in a Figma file, *Wallet – UI Spec* (private):

- **Foundations**: 18 primitive colours, 25 semantic colour variables aliasing them, 7 spacing and
  5 radius variables, 8 text styles (Inter). Direction: deep navy `#1B2A41` as the only accent, no
  gradients or shadows, hairline borders, line icons, sentence case, debit amounts in the text
  colour (red is kept for errors).
- **Components**: 10 components with variants and 11 icons.

The screens are built in code from these foundations and components; the Figma file has no screen
frames. §6 of this document takes their place: each screen with its states and test hooks.

**Tokens.** `web/src/tokens.css` declares every semantic variable as a CSS custom property named
after the variable's WEB code syntax in Figma: `color/bg/page` → `var(--color-bg-page)`. A value is
changed in Figma first, then in `tokens.css`. Components use semantic names only, never primitives.

**Components.** One React component per Figma component:

| Figma component | Variants | Code |
|---|---|---|
| Top bar | Back = True, False | `components/TopBar.jsx` |
| Tab bar | Active = Home, Pay, History | `components/TabBar.jsx` |
| Button | Style = Primary, Secondary, Ghost × State = Default, Disabled, Loading | `.btn` classes in `styles.css` |
| Amount field | State = Empty, Filled, Focus, Error | `components/Fields.jsx` → `AmountField` |
| — (code only) | | `components/Fields.jsx` → `TextField`, same specs as Amount field at 52 px |
| Balance card | Hidden = False, True | `components/BalanceCard.jsx` |
| Quick action | | `screens/Wallet.jsx` (`.quick-action`) |
| Transaction row | Direction = Credit, Debit; Show chevron | `components/Rows.jsx` → `TransactionRow` |
| Section header | | `components/Rows.jsx` → `SectionHeader` |
| Receipt row | | `components/Rows.jsx` → `ReceiptRow` |
| Message | Kind = Error, Warning, Success | `components/Message.jsx` |
| Icons (11) | | `components/Icon.jsx` |

## 4. Screens and routes

| Route | Screen | Tab bar | Back goes to |
|---|---|---|---|
| `#/` | Start: create or open a wallet | no | — |
| `#/w/<wallet>` | Home: balance, actions, the 3 latest entries | Home | — |
| `#/w/<wallet>/history` | History: the ledger, grouped by day | History | — |
| `#/w/<wallet>/topup` | Top up, then its receipt | no | Home |
| `#/w/<wallet>/pay` | Pay: amount → Confirm → receipt | no | Home (from Confirm: the amount step) |
| `#/w/<wallet>/p/<payment>` | Payment detail and refund | no | History |

Receipts have no back button: the money has moved, and the way on is **Done**.

## 5. Rules

### 5.1 Input and money

| ID | Rule | Verified |
|---|---|---|
| R-01 | The amount field is a text input with `inputmode="decimal"`, never `type="number"`, which would hand the value over as a float. The amount is sent exactly as typed. | script |
| R-02 | The page does not validate amounts. The API decides, and a refused amount shows the API's reason (§5.5). The only client-side condition: an empty amount (or spaces only) disables Continue, Top up and Refund. | script |
| R-03 | *Left to refund* is computed as payment amount minus refunded, in integer cents. | script |
| R-04 | Pay has two steps. Confirm shows the amount (as `30.00` when it is a plain amount, otherwise as typed), the wallet it is paid from, and *Balance after* when the amount is plain and the result is not negative. | script |

### 5.2 Attempts and the Idempotency-Key

An *attempt* is one amount the user confirmed. Payments and refunds carry one Idempotency-Key per
attempt, so that a retry of a request the server already processed returns the original result
instead of charging again. Implemented in `useAttempt.js`.

| ID | Rule | Verified |
|---|---|---|
| K-01 | A key (UUID v4) is created when **Confirm payment** or **Refund** is tapped, not before. | script |
| K-02 | While a request is in flight the button is disabled and reads *Processing…*; further taps send nothing (a ref blocks the gap before React re-renders). On Confirm, Cancel and Back are disabled too. | script |
| K-03 | No answer (network error, or an answer without a JSON body): the outcome is unknown. A Warning is shown and the primary button becomes **Retry**, which sends the same amount with the same key. | script |
| K-04 | An error answer is definitive and nothing was charged: the attempt ends, and the next confirm creates a new key. | script |
| K-05 | Cancel, Change amount and Back on Confirm, and editing the refund amount, end the attempt: the next confirm creates a new key. | script |
| K-06 | When the API answers `Idempotent-Replayed: true`, the receipt says the payment had already gone through and was not charged again. | script |
| K-07 | Top-ups take no Idempotency-Key (the API accepts none). After no answer the page asks the user to check the balance and offers no Retry, which could add the money twice. | script |

### 5.3 Display

| ID | Rule | Verified |
|---|---|---|
| D-01 | Amounts are formatted from the API's strings and never converted to numbers: two decimals, comma thousands separators (`12,345.60`). | script |
| D-02 | Ledger rows: credits in green with `+`, debits in the text colour with `−` (U+2212, the minus sign, read as "minus" by screen readers). | script |
| D-03 | Times are shown in the device's time zone (the API returns UTC). Rows are grouped under *Today*, *Yesterday*, `9 Oct`, or `9 Oct 2025` in another year. | script |
| D-04 | The wallet ID is shown masked: first 6 characters, `••••`, last 4. The full ID is in the URL. | script |
| D-05 | History is newest first. Only payment rows open a detail (whole row, with a chevron). Home shows the 3 latest entries. | script |
| D-06 | The balance can be hidden (`••••••`); the toggle exposes its state with `aria-pressed`. The choice is not kept across screens. | script |

### 5.4 Layout and accessibility

| ID | Rule | Verified |
|---|---|---|
| L-01 | No horizontal scrolling at viewport widths 360, 390 and 412 px, on every screen. | script |
| L-02 | Every button and link is at least 44 × 44 CSS px. | script |
| L-03 | Every input has a visible label (a placeholder alone is not a label). A field's error is shown under it and linked with `aria-describedby`; feedback appears in `aria-live` regions. | review |

### 5.5 Error messages

The page shows the API's `error_code` in plain words (`messages.js`).

| ID | API error code | Shown as | Where | Verified |
|---|---|---|---|---|
| E-01 | `INVALID_AMOUNT` | Enter an amount like 100 or 100.50: more than 0, at most two decimals. | Confirm; under the field on Top up and Refund | script |
| E-02 | `INSUFFICIENT_BALANCE` | Not enough balance for this payment. | Confirm | script |
| E-03 | `LIMIT_EXCEEDED` | This is above the single-payment limit of 50,000.00. | Confirm | script |
| E-04 | `REFUND_EXCEEDS_PAYMENT` | This refund would exceed what is left to refund on this payment. | Payment detail | script |
| E-05 | `WALLET_NOT_FOUND` | No wallet with this ID. | Start; Home | script |
| E-06 | `PAYMENT_NOT_FOUND` | No payment with this ID. | Payment detail | script |
| E-07 | `INVALID_OWNER` | Enter a name of 1 to 50 characters. | Start | script |
| E-08 | `IDEMPOTENCY_KEY_REUSED` | This request conflicts with an earlier one. Start again. | Confirm, Payment detail | review: the page never reuses a key with a different body (K-03), so it cannot be reached through the page |
| E-09 | any other code | Something went wrong (`<code>`). | anywhere | review |

## 6. Screens, states and test hooks

Test hooks are `data-testid` attributes. Conventions:

- A hook on an amount holds the number only: `63.00`, never `63.00 TWD`.
- `error-message`, `no-answer`, `replayed` and `refund-done` mark the four kinds of feedback, on
  every screen that can show them.
- `back` is the top bar's back button on every screen that has one.

### 6.1 Start

| Hook | Element |
|---|---|
| `owner-input`, `create-wallet` | New wallet: name field and its button |
| `wallet-id-input`, `open-wallet` | Existing wallet: ID field and its button |
| `error-message` | E-05, E-07 |

### 6.2 Home (tab)

| Hook | Element |
|---|---|
| `owner`, `balance`, `wallet-id` | Balance card (`wallet-id` is masked, D-04) |
| `balance-toggle` | Hide / show the balance (D-06) |
| `go-topup`, `go-pay`, `go-history` | Quick actions |
| `recent-item` (`data-type`), `recent-empty` | The 3 latest entries, or the empty state |
| `switch-wallet` | Back to Start |
| `tab-home`, `tab-pay`, `tab-history` | Tab bar; the active tab has `aria-current="page"` |

### 6.3 History (tab)

| Hook | Element |
|---|---|
| `history-item` (`data-entry-id`, `data-type`) | One ledger entry, newest first, grouped by day (D-03, D-05) |
| `item-amount`, `item-balance` | Inside a row: signed amount (D-02) and balance after |
| `open-payment` | The row's button, on payment rows only |
| `empty`, `error-message` | Empty state; load error |

### 6.4 Top up

| State | Hooks |
|---|---|
| Amount entered | `balance`, `amount-input`, `submit` |
| Processing | `submit` disabled, *Processing…* |
| Refused | `error-message` under the field |
| No answer | `no-answer`; no `retry` (K-07) |
| Receipt | `result`, `result-amount`, `result-balance`, `done` |

### 6.5 Pay

| State | Hooks | Rules |
|---|---|---|
| Amount entered | `balance`, `amount-input`, `submit` (*Continue*) | R-01, R-02 |
| Confirm | `confirm-amount`, `confirm-balance-after`, `confirm-pay`, `cancel`, `back` | R-04, K-01 |
| Processing | `confirm-pay` disabled, *Processing…*; `cancel` and `back` disabled | K-02 |
| Refused | `error-message`, `confirm-pay` (new key), `change-amount` | K-04, E-01 to E-03 |
| No answer | `no-answer`, `retry` (same key), `back-to-wallet` | K-03 |
| Receipt | `result`, `result-amount`, `result-payment-id`, `result-balance`, `done`, `view-payment` | |
| Already processed | the receipt plus `replayed` | K-06 |

### 6.6 Payment detail

| State | Hooks | Rules |
|---|---|---|
| Loaded | `payment-amount`, `payment-refunded`, `payment-refundable`, `refund-item` | R-03 |
| Refund entered | `amount-input`, `submit` (*Refund*) | |
| Refunded | `refund-done`; the summary reloads | |
| Refused | `error-message` under the field | E-01, E-04 |
| No answer | `no-answer`, `retry` (same key) | K-03 |

## 7. Test cases

All cases run in Chromium with two device profiles, Pixel 7 (412 × 915) and iPhone 14
(390 × 844). The iPhone profile emulates the viewport, touch and user agent; it is not Safari.

Each case checks the database as well as the page: a page that *shows* one payment is not proof
that there is one.

| ID | Case | Steps and expected result | Rules | Planted defect it must catch |
|---|---|---|---|---|
| WEB-001 | Smoke | Open `/app`, create a wallet → Home shows the owner and balance `0.00`, and `recent-empty`. One row in `wallets`. | D-01 | |
| WEB-002 | Top up | Top up `100` → receipt `100.00` / `100.00`; Home balance `100.00`. Ledger: one TOPUP of 10000 cents; balance equals the ledger sum. | R-01, D-01 | |
| WEB-003 | Pay | From 100.00, pay `30` → Confirm shows `30.00` and balance after `70.00` → receipt `30.00` / `70.00`; History's first row `−30.00`, balance `70.00`. One row in `payments`. | R-04, K-01, D-02 | |
| WEB-004 | Precision | Top up `19.99` → the page shows `19.99`; the ledger holds 1999 cents. | D-01 | `float_math` |
| WEB-005 | Invalid amounts | Pay `-1`, `1e3`, `10.555` (one run each) → Refused with E-01; balance unchanged; no row in `payments`. | R-02, K-04, E-01 | `negative_amount` (the `-1` run) |
| WEB-006 | Insufficient balance | Pay more than the balance → Refused with E-02; nothing charged; **Change amount** returns to the amount step. | R-02, K-04, E-02 | |
| WEB-007 | Double tap | With the payment request held, double-tap **Confirm payment** → exactly one `POST /payments`, one row in `payments`. | K-02 | none on the server: the guard is in the page (see §8) |
| WEB-008 | Lost response | The payment reaches the server but its response is dropped → `no-answer` → **Retry** → receipt with `replayed`. Both requests carried the same key; one row in `payments`. | K-03, K-06 | `no_idempotency` |
| WEB-009 | Refunds | Pay `30`, refund `10` → `refund-done`, refunded `10.00`, left `20.00`; then refund `25` → E-04. Refunds in the database total 1000 cents. | R-03, K-04, E-04 | `refund_overflow` |
| WEB-010 | History matches the ledger | After a top-up, a payment and a refund, every `history-item` matches the `ledger` table: order, type, amount, balance after. | D-02, D-05 | |
| WEB-011 | Layout | On both profiles and on every screen: no horizontal scroll; every button and link at least 44 × 44 px. | L-01, L-02 | |
| WEB-012 | Processing state | With the request held: `confirm-pay` disabled and reading *Processing…*, `cancel` and `back` disabled. After release: the receipt. | K-02 | |

`tools/fault_check.py` gains these mappings, so that switching each defect on must turn its case red:
`float_math` → WEB-004, `negative_amount` → WEB-005 (`-1`), `no_idempotency` → WEB-008,
`refund_overflow` → WEB-009. `race` and `transfer_not_atomic` have no web case: one user cannot
produce concurrent requests through one page, and there is no transfer screen.

## 8. Traceability

| Rule | Cases | | Rule | Cases |
|---|---|---|---|---|
| R-01 | WEB-002 | | D-01 | WEB-001, 002, 004 |
| R-02 | WEB-005, 006 | | D-02 | WEB-003, 010 |
| R-03 | WEB-009 | | D-03 | — |
| R-04 | WEB-003 | | D-04 | — |
| K-01 | WEB-003 | | D-05 | WEB-010 |
| K-02 | WEB-007, 012 | | D-06 | — |
| K-03 | WEB-008 | | L-01 | WEB-011 |
| K-04 | WEB-005, 006, 009 | | L-02 | WEB-011 |
| K-05 | — | | L-03 | — |
| K-06 | WEB-008 | | E-01, 02, 04 | WEB-005, 006, 009 |
| K-07 | — | | E-03, 05 to 09 | — |

**Not covered by a WEB case yet:** K-05 (a new key after Cancel or Back), K-07 (no Retry after a
top-up gets no answer), D-03 (time zone and grouping), D-04 (masking), D-06 (hiding the balance),
L-03 and the remaining error messages. They were checked once by script (§5), but nothing checks
them on every change. K-05 and K-07 matter most: each guards against charging twice.

**WEB-007 and the planted defects.** The double-tap guard lives in the page, so no server switch
can break it. To show the case can fail, it is also run once against a build with the guard removed.

## 9. Known limitations

- **No authentication.** Anyone with a wallet ID can use the wallet. The API has the same
  limitation; this is a practice system.
- **No transfer screen.** Transfers are tested at the API level only.
- **iPhone is emulated in Chromium**, not run in Safari: the suite installs and runs Chromium only.
- **One currency (TWD)** and English text only.
- **The balance-hidden choice is not remembered**, by design: it resets on every screen.
