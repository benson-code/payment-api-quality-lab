# Wallet clients (web and Android) — Specification

| | |
|---|---|
| Version | 2.4: the app's first Appium cases, APP-001 to APP-006 (see §11) |
| Date | 2026-10-11 |
| Status | **Web: implemented.** Rules marked *script* were checked against the running page with a browser script; *review* means checked by reading the code. **Android app: every screen implemented**; its rules were checked on redroid (Android 14, 360 × 640 dp) with an Appium script, except layout (L-01, L-02), which waits for APP-011. A rule stays *planned* until it is checked in full |
| Code | Web: `web/src/` (React 19 + Vite), served by the API under `/app`. App: `android/` (Kotlin, Jetpack Compose) |
| Tests | Web: Playwright for Python, `tests/web/` (WEB-001 to WEB-014). App: Appium for Python, `tests/app/`: APP-001 to APP-006 implemented, APP-007 to APP-017 planned |

## 1. Purpose

Two clients for the payment API, a mobile web page and a native Android app, with the same screens
and the same behaviour. They exist so that the payment risks this repository tests at the API level
(charging twice, losing a cent, refunding more than was paid) are also tested where a user meets
them: a slow network, a double tap, a lost response, an app killed in the background.

Neither is a product. There is no login: the wallet ID is the only key, exactly as in the API (§10).
There is no transfer screen.

**One specification, two clients.** Every rule has an ID (`R` input, `K` Idempotency-Key attempts,
`N` navigation, `D` display, `L` layout, `E` error messages) and states whether it applies to the web,
the app or both. Test cases cite these IDs, and §9 traces every rule to its WEB and APP cases,
including the ones no case covers yet.

**How the two stay in step.** A feature is done when its rule is in this document, both screens
exist, and both a WEB and an APP case cover it. Both clients use the same test-hook names (§7); a
parity check (planned) fails CI when a hook listed here is missing from either client's code.

## 2. Architecture

```
Browser (phone-sized viewport)              Android app (redroid locally, emulator in CI)
   │  http://<host>/app/#/w/<wallet>/pay       │  http://127.0.0.1:<port>  through adb reverse
   │                                           │  (tests: through the test proxy, §8)
   ▼                                           ▼
FastAPI (uvicorn)
   ├── /app/*      the web page, static files from web/dist
   └── /wallets, /payments, ...   the API
          │
          ▼
       SQLite
```

Neither client holds money logic. Amounts are sent as the strings the user typed and the API decides
whether they are valid (R-02). The only state that matters for money on a client is the current
payment attempt and its Idempotency-Key (§6.2).

The app reaches the API on the host through `adb reverse`: the device's `127.0.0.1:<port>` is
forwarded over the adb connection to the host, so nothing is exposed on the network. The API's base
URL is passed to the app at launch (debug builds only), so tests can point it at the test proxy.

## 3. Design source

The visual design is defined in a Figma file, *Wallet – UI Spec* (private):

- **Foundations**: 18 primitive colours, 25 semantic colour variables aliasing them, 7 spacing and
  5 radius variables, 8 text styles (Inter). Direction: deep navy `#1B2A41` as the only accent, no
  gradients or shadows, hairline borders, line icons, sentence case, debit amounts in the text
  colour (red is kept for errors).
- **Components**: 10 components, most of them with variants, and 11 icons.

The screens are built in code from these foundations and components; the Figma file has no screen
frames. §7 takes their place: each screen with its states and test hooks.

**Tokens.** Both clients take the same Figma variables. A value is changed in Figma first, then in
both places. Components use semantic names only, never primitives.

| Client | Where | Naming |
|---|---|---|
| Web | `web/src/tokens.css` | the variable's WEB code syntax in Figma: `color/bg/page` → `var(--color-bg-page)` |
| App (planned) | `android/.../ui/theme/` | the same path in Kotlin: `color/bg/page` → `WalletColors.bgPage`; text styles as `WalletType.displayBalance` etc. |

**Components.** One component per Figma component in each client:

| Figma component | Variants | Web | App (planned) |
|---|---|---|---|
| Top bar | Back = True, False | `components/TopBar.jsx` | `TopBar` |
| Tab bar | Active = Home, Pay, History | `components/TabBar.jsx` | `TabBar` |
| Button | Style = Primary, Secondary, Ghost × State = Default, Disabled, Loading | `.btn` classes in `styles.css` | `WalletButton` |
| Amount field | State = Empty, Filled, Focus, Error | `components/Fields.jsx` → `AmountField` | `AmountField` |
| — (code only) | | `components/Fields.jsx` → `TextField` | `WalletTextField` |
| Balance card | Hidden = False, True | `components/BalanceCard.jsx` | `BalanceCard` |
| Quick action | | `screens/Wallet.jsx` (`.quick-action`) | `QuickAction` |
| Transaction row | Direction = Credit, Debit; Show chevron | `components/Rows.jsx` → `TransactionRow` | `TransactionRow` |
| Section header | | `components/Rows.jsx` → `SectionHeader` | `SectionHeader` |
| Receipt row | | `components/Rows.jsx` → `ReceiptRow` | `ReceiptRow` |
| Message | Kind = Error, Warning, Success | `components/Message.jsx` | `Message` |
| Icons (11) | | `components/Icon.jsx` | vector drawables, same paths |

## 4. Screens and navigation

Both clients have the same screens. The web addresses them by URL hash; the app by navigation
destination.

| Screen | Web route | App destination | Tab bar | Back goes to |
|---|---|---|---|---|
| Start: create or open a wallet | `#/` | `start` | no | — (app: leaves the app) |
| Home: balance, actions, the 3 latest entries | `#/w/<wallet>` | `home/{wallet}` | Home | — (app: leaves the app) |
| History: the ledger, grouped by day | `#/w/<wallet>/history` | `history/{wallet}` | History | — (app: Home tab) |
| Top up, then its receipt | `#/w/<wallet>/topup` | `topup/{wallet}` | no | Home |
| Pay: amount → Confirm → receipt | `#/w/<wallet>/pay` | `pay/{wallet}` | no | Home (from Confirm: the amount step) |
| Payment detail and refund | `#/w/<wallet>/p/<payment>` | `payment/{wallet}/{payment}` | no | History |

Receipts have no back button: the money has moved, and the way on is **Done**.

## 5. Platform differences

The rules are written once; where the platforms differ, this table says how each one meets the rule.

| Topic | Web | App |
|---|---|---|
| Amount input (R-01) | `<input type="text" inputmode="decimal">` | Compose text field with `KeyboardType.Decimal`; the value stays a `String` |
| Money arithmetic (R-03, R-04) | integer cents in JavaScript numbers | integer cents in `Long`; never `Double` or `Float` |
| Idempotency-Key (K-01) | UUID v4 from `crypto.getRandomValues` (works on non-secure origins) | `java.util.UUID.randomUUID()` (version 4) |
| Touch targets (L-02) | at least 44 × 44 CSS px | at least 48 × 48 dp (Android accessibility guideline) |
| Screen sizes (L-01, L-02) | Playwright profiles Pixel 7 (412 × 839) and iPhone 14 (390 × 664) | redroid 720 × 1280 at 320 dpi (360 × 640 dp) and the same device set to 1080 × 2400 at 420 dpi (411 × 914 dp) |
| Test hooks (§7) | `data-testid` | Compose `testTag`, exposed as the resource-id (`testTagsAsResourceId`) |
| A pending attempt survives… | navigation inside the pay screen only | navigation, screen rotation and process death (K-08) |
| System back | the browser's back follows the URL history | defined by N-01 |
| Digits in patterns (R-04) | `[0-9]`; JavaScript's `\d` is ASCII anyway | `[0-9]`: on Android `\d` matches any script's digits (the regex engine is ICU), on the JVM that runs the unit tests it does not. The API writes `[0-9]` too: Python's `\d` accepted `１００` |
| Text that does not fit (L-01) | the browser's flex layout: a label never shrinks below its longest word | Compose has no such floor: rows measure the label's longest word and leave it that width |

## 6. Rules

The **Web** and **App** columns say how each rule was checked on that client: *script* (checked
against the running client by a script), *unit* (the client's logic is checked by unit tests, not
yet on a screen), *review* (checked by reading the code), *planned* (not implemented, or not yet in
full), or *n/a* (does not apply).

### 6.1 Input and money

| ID | Rule | Web | App |
|---|---|---|---|
| R-01 | The amount field is a text field for decimals, never a numeric type that would hand the value over as a float. The amount is sent exactly as typed. | script | review |
| R-02 | The client does not validate amounts. The API decides, and a refused amount shows the API's reason (§6.6). The only client-side condition: an empty amount (or spaces only) disables Continue, Top up and Refund. | script | script |
| R-03 | *Left to refund* is computed as payment amount minus refunded, in integer cents. | script | script |
| R-04 | Pay has two steps. Confirm shows the amount (as `30.00` when it is a plain amount, otherwise as typed; *plain* is the API's own grammar, digits `0`-`9` with at most two decimals and nothing else, not even spaces), the wallet it is paid from, and *Balance after* when the amount is plain and the result is not negative. | script | script |

### 6.2 Attempts and the Idempotency-Key

An *attempt* is one amount the user confirmed. Payments and refunds carry one Idempotency-Key per
attempt, so that a retry of a request the server already processed returns the original result
instead of charging again. Web: `useAttempt.js`. App: the pay and payment-detail view models.

| ID | Rule | Web | App |
|---|---|---|---|
| K-01 | A key (UUID v4) is created when **Confirm payment** or **Refund** is tapped, not before. | script | script |
| K-02 | While a request is in flight the button is disabled and reads *Processing…*; further taps send nothing, including a second tap that arrives before the screen has redrawn the disabled button. On Confirm, Cancel and Back are disabled too. | script | script |
| K-03 | No answer (network error, or an answer without a JSON body): the outcome is unknown. A Warning is shown and the primary button becomes **Retry**, which sends the same amount with the same key. | script | script |
| K-04 | An error answer is definitive and nothing was charged: the attempt ends, and the next confirm creates a new key. | script | script |
| K-05 | Only a different amount ends an attempt that is still waiting for an answer. Amounts are compared as money (`30` and `30.00` are the same); anything that is not a plain amount, exactly as typed. Going back from Confirm and continuing with the same amount shows *no answer* again and Retry resends the same key; continuing with a different amount starts a new attempt with a new key. Refunds: the field can be edited; the button reads Retry only while it holds the pending amount. | script | script |
| K-06 | When the API answers `Idempotent-Replayed: true`, the receipt says the payment had already gone through and was not charged again. | script | script |
| K-07 | Top-ups take no Idempotency-Key (the API accepts none). After no answer the client asks the user to check the balance and offers no Retry, which could add the money twice. | script | script |
| K-08 | A pending attempt (amount, key and *no answer* state) survives screen rotation and the app's process being killed in the background: reopened, the app shows Confirm with *no answer*, and Retry resends the same key. | n/a (§10) | script |

### 6.3 Navigation

| ID | Rule | Web | App |
|---|---|---|---|
| N-01 | The system Back button or gesture does what the top bar's back does on that screen. On Confirm it returns to the amount step and keeps a pending attempt (K-05). While a request is in flight it does nothing. On a receipt it goes to Home, never back to Confirm, so a payment cannot be confirmed twice by going back. The receipt survives the app's process being killed: reopened, the app shows the receipt, never Confirm. | n/a | script |

### 6.4 Display

| ID | Rule | Web | App |
|---|---|---|---|
| D-01 | Amounts are formatted from the API's strings and never converted to floating point: two decimals, comma thousands separators (`12,345.60`). | script | script |
| D-02 | Ledger rows: credits in green with `+`, debits in the text colour with `−` (U+2212, the minus sign, read as "minus" by screen readers). | script | script |
| D-03 | Times are shown in the device's time zone (the API returns UTC). Rows are grouped under *Today*, *Yesterday*, `9 Oct`, or `9 Oct 2025` in another year. | script | unit |
| D-04 | The wallet ID is shown masked: first 6 characters, `••••`, last 4. Web: the full ID is in the URL. App: the full ID is in the navigation arguments; tests take it from the API response that created the wallet. | script | script |
| D-05 | History is newest first. Only payment rows open a detail (whole row, with a chevron). Home shows the 3 latest entries. | script | script |
| D-06 | The balance can be hidden (`••••••`); the toggle exposes its state to assistive technology (web: `aria-pressed`; app: a toggleable state description). The choice is not kept across screens. | script | script |

### 6.5 Layout and accessibility

| ID | Rule | Web | App |
|---|---|---|---|
| L-01 | Nothing is cut off, overlapped or needs horizontal scrolling on the screen sizes of §5, on every screen, with the longest values the API allows (a 50-character name, a balance of `999,999,999,999.99`). The balance steps down a text style by its length as shown: up to 10 characters *Display/Balance*, up to 14 *Amount/Large*, longer *Title/Large*. A currency that does not fit moves to the next line; a label wraps between words but never shrinks below its longest word; an amount is never broken. | script | planned |
| L-02 | Every interactive element meets the platform's minimum touch target (§5). | script | planned |
| L-03 | Every input has a visible label (a placeholder alone is not a label), and icon-only buttons have an accessible name. A field's error is shown under it and announced. | review | review |
| L-04 | A message that appears after an action is in view without scrolling: it is shown next to the control that caused it, and it scrolls itself into view when it appears. | script | script |

### 6.6 Error messages

Both clients show the API's `error_code` in the same plain words (web: `messages.js`).

| ID | API error code | Shown as | Where | Web | App |
|---|---|---|---|---|---|
| E-01 | `INVALID_AMOUNT` | Enter an amount like 100 or 100.50: more than 0, at most two decimals. | Confirm; under the field on Top up and Refund | script | script |
| E-02 | `INSUFFICIENT_BALANCE` | Not enough balance for this payment. | Confirm | script | script |
| E-03 | `LIMIT_EXCEEDED` | This is above the single-payment limit of 50,000.00. | Confirm | script | script |
| E-04 | `REFUND_EXCEEDS_PAYMENT` | This refund would exceed what is left to refund on this payment. | Payment detail | script | script |
| E-05 | `WALLET_NOT_FOUND` | No wallet with this ID. | Start; Home | script | script |
| E-06 | `PAYMENT_NOT_FOUND` | No payment with this ID. | Payment detail | script | n/a: the app opens payments only from the ledger, so an unknown ID cannot be reached |
| E-07 | `INVALID_OWNER` | Enter a name of 1 to 50 characters. | Start | script | script |
| E-08 | `IDEMPOTENCY_KEY_REUSED` | This request conflicts with an earlier one. Start again. | Confirm, Payment detail | review: neither client reuses a key with a different body (K-03), so it cannot be reached through a client | review |
| E-09 | any other code | Something went wrong (`<code>`). | anywhere | review | unit |

## 7. Screens, states and test hooks

Both clients use the same hook names: `data-testid` on the web, the Compose `testTag` (exposed as
the resource-id) in the app. Conventions:

- A hook on an amount holds the number only: `63.00`, never `63.00 TWD`.
- `error-message`, `no-answer`, `replayed` and `refund-done` mark the four kinds of feedback, on
  every screen that can show them.
- `back` is the top bar's back button on every screen that has one.
- Each list row has an `item-title` (the entry type as the user reads it). The web's rows also carry
  `data-type` and `data-entry-id`; the app's do not, because hiding machine-readable text in a row
  would be read out by screen readers. App tests match rows to the ledger by position and title.

### 7.1 Start

| Hook | Element |
|---|---|
| `owner-input`, `create-wallet` | New wallet: name field and its button |
| `wallet-id-input`, `open-wallet` | Existing wallet: ID field and its button |
| `error-message` | E-05, E-07 |

### 7.2 Home (tab)

| Hook | Element |
|---|---|
| `owner`, `balance`, `wallet-id` | Balance card (`wallet-id` is masked, D-04) |
| `balance-toggle` | Hide / show the balance (D-06) |
| `go-topup`, `go-pay`, `go-history` | Quick actions |
| `recent-item`, `recent-empty` | The 3 latest entries, or the empty state |
| `switch-wallet` | Back to Start |
| `tab-home`, `tab-pay`, `tab-history` | Tab bar; the active tab is marked selected (web: `aria-current="page"`) |

### 7.3 History (tab)

| Hook | Element |
|---|---|
| `history-item` | One ledger entry, newest first, grouped by day (D-03, D-05) |
| `item-title`, `item-amount`, `item-balance` | Inside a row: entry type, signed amount (D-02) and balance after |
| `open-payment` | The row's button, on payment rows only |
| `empty`, `error-message` | Empty state; load error |

### 7.4 Top up

| State | Hooks |
|---|---|
| Amount entered | `balance`, `amount-input`, `submit` |
| Processing | `submit` disabled, *Processing…* |
| Refused | `error-message` under the field |
| No answer | `no-answer`; no `retry` (K-07) |
| Receipt | `result`, `result-amount`, `result-balance`, `done` |

### 7.5 Pay

| State | Hooks | Rules |
|---|---|---|
| Amount entered | `balance`, `amount-input`, `submit` (*Continue*) | R-01, R-02 |
| Confirm | `confirm-amount`, `confirm-balance-after`, `confirm-pay`, `cancel`, `back` | R-04, K-01 |
| Processing | `confirm-pay` disabled, *Processing…*; `cancel` and `back` disabled | K-02 |
| Refused | `error-message`, `confirm-pay` (new key), `change-amount` | K-04, E-01 to E-03 |
| No answer | `no-answer`, `retry` (same key), `back-to-wallet` | K-03 |
| Receipt | `result`, `result-amount`, `result-payment-id`, `result-balance`, `done`, `view-payment` | |
| Already processed | the receipt plus `replayed` | K-06 |

### 7.6 Payment detail

| State | Hooks | Rules |
|---|---|---|
| Loaded | `payment-amount`, `payment-refunded`, `payment-refundable`, `refund-item` | R-03 |
| Refund entered | `amount-input`, `submit` (*Refund*) | |
| Refunded | `refund-done`; the summary reloads | |
| Refused | `error-message` under the field | E-01, E-04 |
| No answer | `no-answer`, `retry` (same key) | K-03 |

## 8. Test cases

**Both clients.** Every case except the layout cases (WEB-011, APP-011) checks the database as well
as the screen: a screen that *shows* one payment is not proof that there is one. Setup goes through
the API; only the behaviour under test goes through the client. Expected texts are copied from §6.6,
not read from either client's code.

**Web.** Chromium with Playwright's device profiles Pixel 7 and iPhone 14 (the iPhone profile
emulates the viewport, touch and user agent; it is not Safari). Time zone pinned to Asia/Taipei.
Network conditions are produced with Playwright's request interception.

**App.** Appium (UiAutomator2) on redroid locally (Google's emulator in CI is planned), in the two
display configurations of §5, set with `wm size` and `wm density` and restored afterwards. Time zone
pinned on the device. Native apps cannot be intercepted like a browser, so network conditions come
from a **test proxy** (`framework/app/proxy.py`) between the app and the API, with the same three
modes as the web tests: *hold* (the request waits until released), *lose response* (the server
processes the request, the app sees a dropped connection) and *block* (the request never reaches
the server). The proxy also records the Idempotency-Key and the answer of every request: APP-001
takes the full wallet ID, which the screen shows masked (D-04), from the answer it recorded. Each
test starts the app fresh and fails if the app crashed. The app tests need a device, so pytest
collects them only with `--app`.

Each pair of cases tests the same behaviour on both clients:

| Behaviour | Web | App | Rules | Proven to fail by |
|---|---|---|---|---|
| A new wallet starts at 0.00: owner, balance and the empty state shown; one row in `wallets` | WEB-001 | APP-001 | D-01 | |
| Top up `100` → receipt `100.00` / `100.00`; Home balance `100.00`; one TOPUP of 10000 cents in the ledger | WEB-002 | APP-002 | R-01, D-01 | |
| From 100.00, pay `30` → Confirm `30.00`, balance after `70.00` → receipt → History's first row `−30.00`; one row in `payments`; one UUID v4 key, sent only on Confirm | WEB-003 | APP-003 | R-04, K-01, D-02 | |
| Top up `19.99` → shown as `19.99`; the ledger holds 1999 cents | WEB-004 | APP-004 | D-01 | `float_math` |
| Pay `-1`, `1e3`, `10.555`, ` 5 ` (one run each) → Confirm shows it as typed, with no *Balance after*; refused with E-01; nothing moves | WEB-005 | APP-005 | R-02, R-04, K-04, E-01 | `negative_amount` (`-1`) |
| Pay more than the balance → refused with E-02; nothing charged; **Change amount** keeps the input | WEB-006 | APP-006 | R-02, K-04, E-02 | |
| Two taps on **Confirm payment** in quick succession, request held → one request, one row in `payments` | WEB-007 | APP-007 | K-02 | web: mutation `no_in_flight_guard`; app: §9 |
| The server charges, the response is lost → *no answer* → **Retry** → receipt with `replayed`; both requests carried the same key; one row | WEB-008 | APP-008 | K-03, K-06 | `no_idempotency` |
| Pay `30`, refund `10` → refunded `10.00`, left `20.00`; refund `25` → E-04; refunds total 1000 cents | WEB-009 | APP-009 | R-03, K-04, E-04 | `refund_overflow` |
| After a top-up, a payment and a refund, every History row matches the `ledger` table: order, type, amount, balance after | WEB-010 | APP-010 | D-02, D-05 | |
| Every screen in both screen sizes, also with a 50-character name and a balance of `999,999,999,999.99`: nothing cut off by the screen or by its card, every interactive element at least the platform minimum; a message shown after an action is in view on a 360 × 640 screen | WEB-011 | APP-011 | L-01, L-02, L-04 | |
| While processing: Confirm disabled and reading *Processing…*, Cancel and Back disabled; after release, the receipt and one row | WEB-012 | APP-012 | K-02 | web: mutation `confirm_stays_enabled`; app: §9 |
| Back after no answer: (a) the same amount (as `30.00`) keeps the key, Retry → `replayed`, one row; (b) a new amount gets a new key | WEB-013 | APP-013 | K-05 | web: mutation `back_forgets_the_attempt`; app: §9 |
| Top-up with no answer: the user is asked to check the balance; no Retry; balance unchanged | WEB-014 | APP-014 | K-07 | web: mutation `top_up_offers_retry`; app: §9 |

App-only cases:

| ID | Case | Steps and expected result | Rules | Proven to fail by |
|---|---|---|---|---|
| APP-015 | Process death while the outcome is unknown | Pay `30`; the server processes it, the response is lost → *no answer*. Send the app to the background and kill its process (`am kill`, as Android does under memory pressure). Reopen it → Confirm with *no answer* and Retry → **Retry** → receipt with `replayed`; both requests carried the same key; one row in `payments`. | K-08 | `no_idempotency` |
| APP-016 | System back | (a) On Confirm, system Back returns to the amount step and keeps the pending attempt. (b) While processing, system Back does nothing. (c) On the payment receipt, system Back goes to Home, not to Confirm; one row in `payments`. | N-01 | |
| APP-017 | Process death on the receipt | Pay `30` → receipt. Send the app to the background and kill its process. Reopen it → the same receipt (same payment ID and balance after), no **Confirm payment**; system Back goes to Home; one row in `payments`. Also after a replayed receipt (APP-015): reopened, it still says the payment had already gone through. | N-01, K-08 | the defect itself: before 2.3 the reopened app showed Confirm, and confirming again charged a second time (§11) |

`tools/fault_check.py` requires these cases to fail under their defect, on every device profile:
`float_math` → WEB-004, APP-004; `negative_amount` → WEB-005 and APP-005 (`-1`); `no_idempotency` →
WEB-008, APP-008, APP-015; `refund_overflow` → WEB-009, APP-009. `race` and `transfer_not_atomic` have
no client case: one user cannot produce concurrent requests through one screen, and there is no
transfer screen.

## 9. Traceability

| Rule | Web | App | | Rule | Web | App |
|---|---|---|---|---|---|---|
| R-01 | WEB-002 | APP-002 | | N-01 | n/a | APP-016, 017 |
| R-02 | WEB-005, 006 | APP-005, 006 | | D-01 | WEB-001, 002, 004 | APP-001, 002, 004 |
| R-03 | WEB-009 | APP-009 | | D-02 | WEB-003, 010 | APP-003, 010 |
| R-04 | WEB-003, 005 | APP-003, 005 | | D-03 | — | — |
| K-01 | WEB-003 | APP-003 | | D-04 | — | — |
| K-02 | WEB-007, 012 | APP-007, 012 | | D-05 | WEB-010 | APP-010 |
| K-03 | WEB-008 | APP-008 | | D-06 | — | — |
| K-04 | WEB-005, 006, 009 | APP-005, 006, 009 | | L-01 | WEB-011 | APP-011 |
| K-05 | WEB-013 | APP-013 | | L-02 | WEB-011 | APP-011 |
| K-06 | WEB-008 | APP-008 | | L-03 | — | — |
| | | | | L-04 | WEB-011 | APP-011 |
| K-07 | WEB-014 | APP-014 | | E-01, 02, 04 | WEB-005, 006, 009 | APP-005, 006, 009 |
| K-08 | n/a | APP-015 | | E-03, 05 to 09 | — | — |

**Not covered by a case yet, on either client:** D-03 (time zone and grouping), D-04 (masking), D-06
(hiding the balance), L-03 and the remaining error messages. On the web they were checked once by
script (§6), but nothing checks them on every change. None of them can move money.

**Rules that live only in the client.** WEB-007, 012, 013, 014 and APP-007, 012, 013, 014, 016, 017 test
rules that live in the client (the in-flight guard, the disabled button, the pending attempt, the
missing Retry, system Back, the saved receipt), so no server switch can break them. APP-017 was
seen to fail before its fix (§11, 2.3). On the web,
`tools/web_mutation_check.py` proves they can fail: it changes one piece of the page's code, builds
that version, serves it to the tests and requires the case to fail.

| Mutation | Change to the page | Case that must fail |
|---|---|---|
| `no_in_flight_guard` | A second tap while a request is in flight is no longer ignored | WEB-007 |
| `confirm_stays_enabled` | Confirm payment stays enabled while processing | WEB-012 |
| `back_forgets_the_attempt` | Back from Confirm drops the pending attempt (what version 1.1 specified) | WEB-013 |
| `top_up_offers_retry` | A Retry button appears after a top-up gets no answer | WEB-014 |

**App mutations are not planned for the first version.** Each mutation needs its own build of the
app (a few minutes each in CI). Until they exist, APP-007, 012, 013, 014 and 016 are not proven to
fail, and this document says so.

## 10. Known limitations

- **No authentication.** Anyone with a wallet ID can use the wallet. The API has the same
  limitation; this is a practice system.
- **No transfer screen.** Transfers are tested at the API level only.
- **iPhone is emulated in Chromium** on the web, not run in Safari, and there is no iOS app: iOS
  cannot be built or run on this project's Linux machines.
- **The app is tested on redroid and Google's emulator**, not on physical phones: no real camera,
  sensors, vendor skins or Google Play services. None of the app's features need them.
- **One currency (TWD)** and English text only.
- **The balance-hidden choice is not remembered**, by design: it resets on every screen.
- **Web: a pending attempt lives in the page.** Leaving the pay screen after *no answer* (Back to
  wallet, a reload, closing the tab) forgets it, and a new payment gets a new key. The message tells
  the user the payment may have gone through; History shows whether it did. The app keeps it (K-08).
- **A top-up can still be sent twice after no answer.** The API takes no Idempotency-Key for
  top-ups (K-07); both clients withhold Retry and ask the user to check the balance, but the Top up
  button stays available.

## 11. Changes

| Version | Change |
|---|---|
| 2.4 | **APP-001 to APP-006 implemented** in `tests/app/`, with screen objects in `framework/app/` named after the web's page objects and the test proxy described in §8. Each case runs in both display configurations: 18 runs, passing three times in a row on redroid. Seen to fail by hand: APP-004 with `float_math` (the receipt showed `19.98`), APP-005 with `negative_amount` (the payment of `-1` went through and the balance rose to `101.00`), and APP-005's ` 5 ` case with the app's old space trimming put back (Confirm showed `5.00`). `tools/fault_check.py` gains the app cases with APP-007 to APP-017. |
| 2.3 | **The first full QA pass**: every automated check, the device checks, a probe that sends the same 40 inputs through both clients and compares what each shows and what the server did, and screenshots with the longest values the API allows. Fixed: (1) **a double charge in the app**: killed on the payment receipt, the app reopened on Confirm (the step and amount were saved, the receipt was not), and confirming again was a second payment with a new key; the receipt is now saved too (N-01, APP-017). (2) **The API accepted digits from other scripts**: Python's `\d` matched `１００`, which was charged as 100.00; the app showed it as `100.00` on Confirm because Android's `\d` matches them too, while its JVM unit tests could not see this. The API and both clients now write `[0-9]` (VAL-P16, P17, T16, T17; a unit test compiles the app's pattern in Unicode mode, as the device does). (3) **Confirm showed ` 5 ` as `5.00`** with a *Balance after*, and the API then refused it: both clients trimmed spaces, the API does not. *Plain* is now the API's grammar (R-04, WEB-005). (4) **Layout with long values**: on the web, a balance of `999,999,999,999.99` was clipped by its card (the page did not get wider, so the horizontal-scroll check missed it) and a long name squeezed the hide-balance button to 30 px; in the app, *From* was crushed to one letter per line and overlapped by a long name, and *TWD* was stacked into a column next to a 7-digit balance. Both clients now follow the rules in L-01; WEB-011 checks clipping inside cards and the longest values. Also: the app declares backup rules for Android 12 and later. |
| 2.2 | **Every app screen implemented** (Pay with Confirm and receipt, Payment detail and refunds) and checked on redroid: 43 checks, three runs in a row, through a proxy that holds, loses or blocks requests. K-08 checked by killing the app's process while a payment's outcome was unknown: reopened, it showed Confirm with Retry, and Retry resent the saved key; charged once. Two L-04 defects found and fixed on the app: after a refund, the reloaded refund list pushed the success message below the visible area (the web keeps it in view through the browser's scroll anchoring; Compose has none), and after a refund got no answer, the Retry button sat below the visible area under its message. |
| 2.1 | **L-04 added.** The app's first Appium run, on a 360 × 640 dp screen, could not find the Start screen's error message: it appeared below the visible area, so the user saw nothing happen after tapping. The web had the same problem at a 360 × 640 viewport; its Playwright tests had passed because a text assertion does not require the element to be in view. Both clients now show the message under the button that caused it and scroll it into view; WEB-011 checks this and fails without the fix. Also: the `item-title` hook on both clients, and the app column updated for Start, Home, History and Top up. |
| 2.0 | **One specification for two clients.** Moved from `web/SPEC.md` to the repository root. Every rule states whether it applies to the web, the app or both; §5 lists the platform differences; new rules K-08 (a pending attempt survives process death, app) and N-01 (system Back, app); APP-001 to APP-016 planned beside WEB-001 to WEB-014. The web's behaviour is unchanged. |
| 1.2 | **K-05 corrected.** Version 1.1 said Back from Confirm ends the attempt, so continuing with the same amount created a new key. If the first request had gone through and only its response was lost, that is a second charge. Found while writing WEB-013; the page now keeps the attempt until the amount changes, and WEB-013 (a) covers it. The browser check run for version 1.0 had asserted the old behaviour as correct. |
| 1.1 | WEB-013 and WEB-014 added: K-05 and K-07 guard against double charges and had no case. |
| 1.0 | First version (web only). |
