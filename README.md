# payment-api-quality-lab

[![CI](https://github.com/benson-code/payment-api-quality-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/benson-code/payment-api-quality-lab/actions/workflows/ci.yml)

> **這是自建模擬系統的練習作品，不是正式工作專案。** 被測的錢包／支付 API 是為了練習測試而寫的，
> 不連任何真實金流。

用 pytest 測一個自建的錢包／支付 API，重點放在支付系統真正會出事的地方：
**重複扣款、併發超扣、退款超額、金額精度、轉帳只做一半。**

主流程另外做成 **Postman collection**，可以匯入 Postman 手動操作，也用 **Newman** 在 CI 自動執行。

和一般 API 測試練習不同的地方：**被測系統裡埋了 6 個可以開關的 bug，CI 每次都會逐一打開，
確認對應的測試真的會變紅。** 一個從來沒紅過的測試，不能證明它有在測東西。

| 風險 | 代表案例 | 埋的 bug（打開後這些測試必須失敗） |
|---|---|---|
| 網路逾時後重送，重複扣款 | IDM-001、CON-002 | `no_idempotency`：不檢查 Idempotency-Key |
| 同時扣款，餘額被扣成負數 | CON-001、DB-001 | `race`：扣款沒有鎖 |
| 分次退款，累計超過原付款 | REF-002、CON-003 | `refund_overflow`：只檢查單筆退款 |
| 負數付款等於幫自己加錢 | VAL-P08、VAL-T08 | `negative_amount`：允許負數 |
| 用浮點數算錢，少一分錢 | PRC-005 | `float_math`：19.99 × 100 = 1998.9999… |
| 轉帳扣了款卻沒入帳 | TRF-006、DB-001 | `transfer_not_atomic`：扣款與入帳分兩個交易 |

---

## 目錄

1. [架構](#1-架構)
2. [被測系統](#2-被測系統)
3. [測試策略：為什麼是這些案例](#3-測試策略為什麼是這些案例)
4. [Postman 與 Newman](#4-postman-與-newman)
5. [本機執行](#5-本機執行)
6. [CI](#6-ci)
7. [AI 輔助開發流程](#7-ai-輔助開發流程)
8. [開發過程中抓到的問題](#8-開發過程中抓到的問題)
9. [English summary](#9-english-summary)

---

## 1. 架構

```
payment-api-quality-lab/
├── app/                       被測系統：FastAPI + SQLite
│   ├── main.py                HTTP 路由、統一錯誤格式
│   ├── service.py             商業規則（付款、退款、轉帳、冪等）
│   ├── money.py               金額：字串 ⇄ 整數「分」
│   ├── db.py                  建表、交易（BEGIN IMMEDIATE）
│   └── bugs.py                埋 bug 開關
├── framework/                 ① API client 層
│   ├── base_client.py         BaseClient：base URL、timeout、log
│   ├── wallet_api.py          每支 API 一個方法
│   └── db.py                  直接查 SQLite：準備資料、7 條資料庫不變式
├── testdata/                  ② 測試資料層
│   ├── schemas/*.json         jsonschema 回應格式
│   ├── schema.py              驗證並列出每一個不符合的欄位
│   ├── factories.py           產生錢包、付款的工廠函式
│   └── cases.py               讀 CSV，case_id／marks／is_run 都在資料裡
├── cases/
│   └── amount_validation.csv  金額格式案例（30 個，一列一個）
├── tests/                     ③ 測試案例層
│   ├── conftest.py            起 API、fixture、--env／--target_case_ids／--target_marks
│   └── test_*.py              95 個測試
├── postman/                   Postman collection（Newman 在 CI 跑）
│   ├── payment-api.postman_collection.json
│   ├── local.postman_environment.json
│   ├── data/amount-boundaries.csv   金額邊界，資料驅動
│   └── run-newman.sh          起 API → 跑 Newman → 出報告
├── tools/
│   ├── fault_check.py         逐一打開 bug 開關，確認指定的 pytest 測試會失敗
│   └── newman_fault_check.py  同上，對象是 Postman collection
└── .github/workflows/ci.yml
```

**分層的理由**：測試案例只寫「做什麼、預期什麼」，不管 URL 長什麼樣、header 怎麼帶。
API 路徑改了只改 client 層；金額格式案例要加，只改 CSV。

## 2. 被測系統

| 方法 | 路徑 | 說明 |
|---|---|---|
| POST | `/wallets` | 建立錢包 |
| POST | `/wallets/{id}/topups` | 儲值 |
| GET | `/wallets/{id}` | 查餘額 |
| GET | `/wallets/{id}/transactions` | 交易紀錄（ledger） |
| POST | `/payments` | 付款，必須帶 `Idempotency-Key` |
| GET | `/payments/{id}` | 付款明細與退款紀錄 |
| POST | `/payments/{id}/refunds` | 退款，可多次部分退款，必須帶 `Idempotency-Key` |
| POST | `/transfers` | 錢包之間轉帳，必須帶 `Idempotency-Key` |
| GET | `/health` | 健康檢查，並回報開了哪些 bug |

**三個設計決定**

1. **金額用字串傳、用整數「分」存。** `"100.50"` → `10050`。JSON 數字到程式裡常變成浮點數，
   而 `0.1 + 0.2 = 0.30000000000000004`。最多兩位小數，最小 `0.01`。
2. **所有餘額變動只走一個函式，並同時寫 ledger。** 所以「錢包餘額 = ledger 加總」永遠成立，
   測試可以用 SQL 直接驗。
3. **寫入一律在 `BEGIN IMMEDIATE` 交易裡。** 查 Idempotency-Key、扣款、記住 key 三件事一起鎖住：
   同一把 key 同時到兩次，第二個要等第一個做完才查得到「用過了」。扣款失敗整筆 ROLLBACK，
   key 不會被記住，客人儲值後可以用同一把 key 再試。

錯誤一律回 `{"error_code": "...", "message": "..."}`。

## 3. 測試策略：為什麼是這些案例

95 個測試，每一類都先問「這裡壞掉，錢會怎樣」：

| 檔案 | 數量 | 在防什麼 |
|---|---|---|
| `test_smoke.py` | 2 | 部署後第一個跑：服務活著、主要金流走得通。加上其他檔案標了 `smoke` 的，smoke 共 4 個 |
| `test_validation.py` | 40 | 30 個來自 CSV：零、負數、超過兩位小數、科學記號、數字而非字串、空白、null、布林；另有 Idempotency-Key、錢包、owner 驗證 |
| `test_business.py` | 8 | 餘額剛好用完／差一分；失敗的付款不留任何資料；單筆上限 49,999.99／50,000.00／50,000.01 |
| `test_precision.py` | 8 | 0.10 + 0.20；33.33 × 2 + 33.34 退回一分不差；最後一分錢；19.99 等浮點數會出錯的值 |
| `test_idempotency.py` | 7 | 同 key 重送只扣一次；同 key 不同內容拒絕；不同 key 是兩筆合法購買；退款、轉帳重送 |
| `test_concurrency.py` | 4 | 10 筆同時扣款不超扣；同 key 同時 10 次只扣一次；同時退款不超退；對向轉帳 |
| `test_refund.py` | 10 | 累計上限、單筆超退、不合法金額、不存在的付款、退款明細 |
| `test_transfer.py` | 5 | 扣款與入帳要嘛都成功要嘛都沒發生、收款方不存在、轉給自己、限額 |
| `test_contract.py` | 3 | 每一種成功與錯誤回應都用 jsonschema 驗，不允許多出欄位 |
| `test_db_invariants.py` | 8 | 7 條「應該查不到任何資料」的 SQL，加上一個證明它們會抓到錯的測試 |

**幾個原則**

- **斷言不只看回應。** 重送測試不是看第二次回什麼，是去查 `payments` 表確認只有一筆。
  API 說「沒有重複扣款」不算數，帳上只有一筆才算。
- **從一個合法的請求開始，每次只改一個地方。** 一次改兩個欄位，被拒絕了也不知道是哪一個造成的。
- **邊界測三個點**：界線內最後一個、剛好界線、界線外第一個。
- **併發測試驗的是正確性，不是效能。** 每個案例 5～20 個請求，一秒內跑完。壓力測試是另一件事。
- **一條永遠查不到東西的 SQL，可能是 SQL 寫錯了。** DB-005 把資料庫複製一份、故意弄髒，
  確認 7 條查詢每一條都抓得到。
- **測試資料要驗證過才算數。** 原本以為 33.33 會觸發浮點數誤差，實測 `33.33 * 100 == 3333.0`，
  不會出錯；19.99、1.15、0.29、4.35 才會。沒有埋 bug 開關，這個錯誤不會被發現。

**用測試資料挑案例**（跟資料驅動框架的慣例一樣，case_id 與 marks 寫在資料裡）：

```bash
pytest --target_marks=smoke                      # 只跑 smoke
pytest --target_marks=idempotency,concurrency    # 任一標籤符合
pytest --target_case_ids=CON-001,VAL-P08         # 指定案例
```

## 4. Postman 與 Newman

`postman/` 是同一個 API 的 Postman collection，可以匯入 Postman 手動操作，也可以用 Newman
在命令列和 CI 執行。

**跟 pytest 的分工**

| | Postman／Newman | pytest |
|---|---|---|
| 用途 | 開發、PM 匯入就能重現問題；探索式測試、交接 | 自動化回歸的主力 |
| 涵蓋 | 主流程與代表性錯誤（25 支 request）＋ 金額邊界（CSV 9 列） | 95 個測試 |
| 做不到的 | 直接查資料庫；併發（一次只送一個請求） | — |

**collection 結構**

| 資料夾 | 案例 | 重點 |
|---|---|---|
| 01 健康檢查 | PM-01 | 確認沒有打開任何 bug 開關 |
| 02 主流程 | PM-02～08 | 建錢包 → 儲值 → 付款 → 退款 → 對帳；前一支存下的 ID 給後一支用 |
| 03 冪等 | PM-09～12 | 同一把 key 重送只扣一次：回應標示 `Idempotent-Replayed: true`，而且餘額沒變 |
| 04 錯誤處理 | PM-13～18 | 差一分錢的餘額不足、累計超退、金額傳數字、超過單筆上限 |
| 05 轉帳 | PM-19～25 | 轉帳失敗後再查一次餘額，確認錢沒有被扣 |
| 06 金額邊界 | AMT-01～09 | 讀 `postman/data/amount-boundaries.csv`，每一列跑一次 |

每支 request 都會經過 collection 層的共同檢查：回應時間 < 1 秒、回應是 JSON、錯誤回應格式統一。
測試名稱一律以案例編號開頭，報告裡可以直接對回案例。

**執行**

```bash
npm install -g newman@6.2.2 newman-reporter-htmlextra@1.23.1

postman/run-newman.sh                                  # 自己起一台 API（暫存資料庫），跑完就關
BASE_URL=http://127.0.0.1:8400 postman/run-newman.sh   # 打一台已經起好的 API
.venv/bin/python tools/newman_fault_check.py           # 證明 collection 抓得到 bug
```

報告在 `reports/newman/`：`main.html`、`amounts.html`（htmlextra）與 JUnit XML。

在 Postman 裡：匯入 collection 與 `local` 環境後，整個 collection 可以直接 Run（06 沒有資料會自動跳過）；
要跑 06 時，用 Collection Runner 只選這個資料夾，並選擇上面那個 CSV。

**collection 也要證明自己抓得到 bug**

| bug 開關 | 必須失敗的案例 |
|---|---|
| `no_idempotency` | PM-09、PM-10、PM-11 |
| `refund_overflow` | PM-15 |
| `negative_amount` | AMT-05、AMT-06 |
| `float_math` | AMT-03、AMT-04 |
| `transfer_not_atomic` | PM-25 |
| `race` | 不列入：Postman 造不出併發，交給 pytest |

`transfer_not_atomic` 打開時，PM-24「轉給不存在的錢包」照樣回 404，只看狀態碼會以為沒事；
要靠 PM-25 再查一次餘額才抓得到。

## 5. 本機執行

開發環境是 Oracle Cloud 的 Ubuntu ARM64（Ampere A1），不用 Docker。需要 Python 3.12。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 跑全部測試：會自己起一台 API（隨機 port、暫存資料庫），跑完就關
.venv/bin/pytest

# HTML 報告
.venv/bin/pytest --html=reports/report.html --self-contained-html

# 證明測試抓得到 bug（約 30 秒）
.venv/bin/python tools/fault_check.py

# 自己起 API 手動打
DB_PATH=wallet.db .venv/bin/uvicorn app.main:app --port 8400
BUGS=race DB_PATH=wallet.db .venv/bin/uvicorn app.main:app --port 8400   # 開著 bug 起

# 打一台已經起好的 API（CI 用這個方式）
.venv/bin/pytest --env=external --base-url=http://127.0.0.1:8400 --db-path=wallet.db
```

> 自訂參數請用 `--opt=value`。寫成 `--db-path /tmp/x.db`（空格隔開）時，pytest 在讀設定檔之前
> 會把 `/tmp/x.db` 當成測試路徑來決定專案根目錄，結果找不到 `pytest.ini` 與 `conftest.py`，
> 自訂參數全部變成「不認識」。

## 6. CI

`.github/workflows/ci.yml`，每次 push 都跑三個 job：

1. **API tests**：背景啟動 API → 等 `/health` → 先跑 smoke，失敗就停 → 跑完整回歸 →
   上傳 pytest-html 與 JUnit 報告（失敗也會上傳，保留證據）
2. **Tests catch planted bugs**：`tools/fault_check.py` 逐一打開 6 個 bug 開關，
   每個開關都列出「應該被哪些測試抓到」，少一個就讓 CI 失敗
3. **Postman collection (Newman)**：跑主流程與 CSV 金額邊界，上傳 htmlextra 與 JUnit 報告，
   再用 `tools/newman_fault_check.py` 對 collection 做同樣的 bug 開關檢查

`race` 會讓哪些測試失敗跟執行時機有關（本機 6 個、CI 上 5 個），所以 fault_check 只要求
每次都穩定抓得到的 CON-001 與「餘額 = ledger」。

目前用 x64 runner；repo 公開後改成 `ubuntu-24.04-arm`，跟開發機同架構。

## 7. AI 輔助開發流程

這個專案是我用 **Claude Code**（在 OCI 主機上執行的 AI coding agent）協作完成的。我的背景是
十年支付系統的手工測試，這個 repo 是我轉型 SDET 的練習。分工如下：

| 我做的 | Claude Code 做的 |
|---|---|
| 定需求：錢包 API 的範圍、要涵蓋哪些支付風險、不用 Docker、要有 CI | 依需求提出計畫、資料夾結構、測試案例清單 |
| 逐條審核案例清單，決定調整（例如金額要支援小數兩位） | 撰寫 API、測試框架與測試程式碼 |
| 每一步看完說明、自己執行、看懂才進下一步 | 每一步實際執行並回報結果，失敗時找出原因 |
| 決定什麼時候 commit、repo 何時公開 | 依約定小步 commit，commit 訊息寫清楚改了什麼與為什麼 |

**我怎麼確認 AI 寫的測試是有效的**：不相信「測試全綠」。被測系統裡埋了 bug 開關，
每個開關打開後，指定的測試必須失敗，CI 每次都自動檢查。開發過程中這個做法真的抓到了問題（見下一節）。

## 8. 開發過程中抓到的問題

這些都記錄在 commit 訊息裡：

| 問題 | 怎麼發現 | 修正 |
|---|---|---|
| 查餘額偶爾回 500 | 寫完付款 API 手動跑併發情境 | FastAPI 可能在不同執行緒開、關同一條 SQLite 連線，關掉 `check_same_thread` |
| 「空的 Idempotency-Key」測試根本沒送出空 key | 測試失敗，追到 client 層 | `key or new_key()` 把空字串當成沒給，改成只有 `None` 才自動產生 |
| 浮點數 bug 開關沒有現形 | 打開 `float_math`，精度測試仍是綠的 | 33.33 剛好不會出錯，改用實測會出錯的 19.99 等值 |
| 自訂參數「不認識」 | 本機排練 CI 指令 | 改用 `--opt=value` 寫法（見第 5 節） |
| Newman 送出的金額跟 CSV 寫的不一樣 | 「科學記號 1e3 應該被拒絕」的案例拿到 201 | Newman 會把沒加引號的 CSV 欄位轉成數字：`1e3` 送出去變成 `1000`、`10.50` 變成 `10.5`。金額欄位一律加引號 |

## 9. English summary

**payment-api-quality-lab** is a self-built practice project, not production work: a small
FastAPI + SQLite wallet/payment API and a pytest suite aimed at the failures that matter in
payments — double charging on retries, overdrafts under concurrency, refunds exceeding the
payment, rounding errors, and half-completed transfers.

- **API**: wallets, top-ups, payments and refunds with `Idempotency-Key`, transfers, balance
  and ledger history. Amounts travel as strings (`"100.50"`) and are stored as integer cents.
  Every balance change writes a ledger row, and writes run inside `BEGIN IMMEDIATE`.
- **Test framework**: three layers — API client (`framework/`), test data (`testdata/`, JSON
  schemas, CSV-driven cases with case_id/marks/is_run), and test cases (`tests/`). Fixtures,
  `parametrize`, and a `conftest.py` that spawns a hermetic API or targets an external one.
  SQL is used both to seed data and to check seven database invariants.
- **95 tests**: validation, business rules and limits, precision, idempotency, concurrency,
  refunds, transfers, JSON-schema contracts, and database invariants.
- **Proof the tests work**: six switchable defects are planted in the API. CI turns each one on
  and fails unless the tests named for that defect go red.
- **Postman / Newman**: the main flows (25 requests, chained through collection variables) and
  CSV-driven amount boundaries as a Postman collection, run by Newman in CI. A separate fault
  check proves the collection catches five of the six planted defects; the race condition is left
  to pytest, since Postman sends one request at a time.
- **CI**: GitHub Actions starts the API, runs smoke then the full suite, runs the Newman
  collection, and uploads pytest-html, htmlextra and JUnit reports as artifacts.
- **AI-assisted**: built with Claude Code. I set the requirements and reviewed the test list;
  Claude Code drafted and wrote the code; every step was run and explained before moving on.
