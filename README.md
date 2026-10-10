# payment-api-quality-lab

[![CI](https://github.com/benson-code/payment-api-quality-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/benson-code/payment-api-quality-lab/actions/workflows/ci.yml)

> **Self-built practice project, not production work.** The wallet/payment API under test was written
> for this project as a target for testing. It is not connected to any real payment system.

A pytest suite for a small wallet/payment API, focused on the failures that cost money in payment
systems: **double charges on retry, overdrafts under concurrency, refunds that exceed the original
payment, rounding errors, and half-completed transfers.**

A **mobile web front end** (React) is served by the same API, and **Playwright for Python** tests it
in the same pytest suite: 14 cases on two phone profiles, checked against the database as well as
the page.

The main flows are also provided as a **Postman collection** for manual use, run by **Newman** in CI.
A **k6** load test, followed by a database reconciliation, can be triggered on demand.

**Six defects are planted in the API behind switches. On every push to main, CI turns each one on and
requires the tests assigned to it to fail.** A test that has never been seen to fail is not
evidence that it checks anything. Rules that exist only in the web page cannot be broken by a server
switch, so for those CI changes the page's code instead and requires the matching case to fail.

| Risk | Representative cases | Planted defect (these tests must fail when it is on) |
|---|---|---|
| A retry after a network timeout charges twice | IDM-001, CON-002, WEB-008 | `no_idempotency`: the Idempotency-Key is ignored |
| Concurrent payments overdraw the wallet | CON-001, DB-001 | `race`: no lock around the balance update |
| Partial refunds add up to more than the payment | REF-002, CON-003, WEB-009 | `refund_overflow`: only the individual refund is checked |
| A negative payment credits the payer | VAL-P08, VAL-T08, WEB-005 | `negative_amount`: negative amounts are accepted |
| Floating-point arithmetic loses a cent | PRC-005, WEB-004 | `float_math`: 19.99 × 100 = 1998.9999… |
| A transfer debits the sender but never credits the receiver | TRF-006, DB-001 | `transfer_not_atomic`: debit and credit run in separate transactions |

---

## Contents

1. [Architecture](#1-architecture)
2. [System under test](#2-system-under-test)
3. [Test strategy](#3-test-strategy)
4. [Web front end and UI tests](#4-web-front-end-and-ui-tests)
5. [Postman and Newman](#5-postman-and-newman)
6. [Load testing (k6)](#6-load-testing-k6)
7. [Running locally](#7-running-locally)
8. [CI](#8-ci)
9. [AI-assisted development](#9-ai-assisted-development)
10. [Issues found during development](#10-issues-found-during-development)

---

## 1. Architecture

```
payment-api-quality-lab/
├── app/                       System under test: FastAPI + SQLite
│   ├── main.py                HTTP routes, uniform error format
│   ├── service.py             Business rules (payments, refunds, transfers, idempotency)
│   ├── money.py               Amounts: string <-> integer cents
│   ├── db.py                  Schema, transactions (BEGIN IMMEDIATE)
│   └── bugs.py                Planted-defect switches
├── framework/                 (1) API client layer
│   ├── base_client.py         BaseClient: base URL, timeout, request logging
│   ├── wallet_api.py          One method per endpoint
│   ├── db.py                  Direct SQLite access: data seeding, seven database invariants
│   └── web/                   Web page objects (one per screen) and network control: hold, lose, block
├── testdata/                  (2) Test data layer
│   ├── schemas/*.json         JSON Schemas for every response type
│   ├── schema.py              Validation that reports every mismatching field
│   ├── factories.py           Factory functions for wallets and payments
│   ├── cases.py               CSV loader; case_id, marks and is_run live in the data
│   └── web.py                 Expected web error texts, copied from SPEC.md
├── cases/
│   └── amount_validation.csv  Amount-format cases (30, one per row)
├── tests/                     (3) Test case layer
│   ├── conftest.py            API startup, fixtures, --env / --target_case_ids / --target_marks
│   ├── test_*.py              95 API tests
│   └── web/                   34 web UI test runs (Playwright): browser, phones, failure evidence
├── SPEC.md                    Specification for both clients (web, Android): rules, screens, hooks, cases
├── android/                   Native Android app: Kotlin + Jetpack Compose (all screens; Appium suite next)
├── web/                       Mobile web front end: React + Vite, served by the API under /app
│   └── src/                   tokens.css (Figma variables), components/ (one per Figma component), screens/
├── postman/                   Postman collection (run by Newman in CI)
│   ├── payment-api.postman_collection.json
│   ├── local.postman_environment.json
│   ├── data/amount-boundaries.csv   Data-driven amount boundaries
│   └── run-newman.sh          Start the API, run Newman, write reports
├── load/                      k6 load test (run in CI only)
│   ├── payments.js            smoke / load / stress scenarios
│   ├── run-load.sh            Start the API, run k6, reconcile the database
│   └── README.md              Test types, threshold rationale, measured results
├── tools/
│   ├── fault_check.py         Turns on each planted defect and checks the named pytest tests fail
│   ├── web_mutation_check.py  Breaks one piece of the web page and checks the named web case fails
│   ├── newman_fault_check.py  The same check for the Postman collection
│   └── check_invariants.py    Reconciliation: runs every invariant against a database (after load tests)
└── .github/workflows/         ci.yml (push to main, pull requests), load.yml (manual)
```

**Why three layers:** test cases state only what is done and what is expected; they do not deal with
URLs or headers. A change to an API path touches only the client layer, and a new amount format is a
single CSV row.

Code comments, test docstrings, Postman request names and the k6 run summary are written in
Traditional Chinese; the web front end (`web/`) is written in English.

## 2. System under test

| Method | Path | Description |
|---|---|---|
| POST | `/wallets` | Create a wallet |
| POST | `/wallets/{id}/topups` | Top up a wallet |
| GET | `/wallets/{id}` | Get the balance |
| GET | `/wallets/{id}/transactions` | Transaction history (ledger) |
| POST | `/payments` | Pay; requires an `Idempotency-Key` header |
| GET | `/payments/{id}` | Payment details, including refunds |
| POST | `/payments/{id}/refunds` | Refund, fully or in several partial refunds; requires an `Idempotency-Key` header |
| POST | `/transfers` | Transfer between wallets; requires an `Idempotency-Key` header |
| GET | `/health` | Health check, including which planted defects are switched on |

**Design decisions**

1. **Amounts travel as strings and are stored as integer cents.** `"100.50"` is stored as `10050`.
   JSON numbers are commonly parsed into floating-point values, and in floating point
   `0.1 + 0.2 = 0.30000000000000004`. Amounts have at most two decimal places; the minimum is `0.01`.
2. **Every balance change goes through a single function, which also writes a ledger entry.**
   The rule "a wallet's balance equals the sum of its ledger entries" therefore always holds,
   and the tests verify it directly in SQL.
3. **Every write runs inside a `BEGIN IMMEDIATE` transaction.** Looking up the Idempotency-Key,
   debiting the wallet and storing the key happen under one lock, so when two requests arrive with
   the same key, the second one waits and then finds the first one's result. If the debit fails,
   the whole transaction is rolled back and the key is not stored, so the client can retry with the
   same key after topping up.

Every error response has the form `{"error_code": "...", "message": "..."}`.

## 3. Test strategy

There are 95 API tests (the web UI tests are described in section 4). Each group starts from the
question "if this breaks, what happens to the money?"

| File | Tests | What it guards against |
|---|---|---|
| `test_smoke.py` | 2 | Run first after a deployment: the service is up and the main money flow works. With the tests in other files marked `smoke`, the smoke set has 4 tests |
| `test_validation.py` | 40 | 30 from the CSV: zero, negative, more than two decimal places, scientific notation, a number instead of a string, whitespace, null, boolean. Also Idempotency-Key, wallet and owner validation |
| `test_business.py` | 8 | Paying exactly the balance and one cent more; a failed payment leaves no trace; the single-payment limit at 49,999.99 / 50,000.00 / 50,000.01 |
| `test_precision.py` | 8 | 0.10 + 0.20; refunds of 33.33 + 33.33 + 33.34 return every cent; the last remaining cent; values such as 19.99 that floating point gets wrong |
| `test_idempotency.py` | 7 | A retry with the same key charges once; the same key with a different body is rejected; different keys are two legitimate purchases; refund and transfer retries |
| `test_concurrency.py` | 4 | 10 simultaneous payments never overdraw; 10 simultaneous retries with one key charge once; simultaneous refunds never exceed the payment; opposing transfers |
| `test_refund.py` | 10 | Cumulative limit, a single refund above the payment, invalid amounts, unknown payments, refund details |
| `test_transfer.py` | 5 | Debit and credit happen together or not at all; unknown receiver; transfer to oneself; limit |
| `test_contract.py` | 3 | Every success and error response is validated against a JSON Schema that allows no extra fields |
| `test_db_invariants.py` | 8 | Seven SQL queries that must return no rows, plus a test proving each query can detect a violation |

**Principles**

- **Assertions go beyond the HTTP response.** A retry test does not stop at the second response; it
  queries the `payments` table and confirms there is exactly one row. The API reporting no double
  charge is not proof; a single row in the database is.
- **Start from a valid request and change one field at a time.** If two fields change and the request
  is rejected, the cause is ambiguous.
- **Boundaries are tested at three points:** the last valid value, the boundary itself, and the first
  invalid value.
- **Concurrency tests check correctness, not performance.** Each case sends 5 to 20 requests and
  finishes within a second. Performance is covered separately by the load test (section 6).
- **A query that never returns rows may simply be wrong.** DB-005 copies the database, corrupts it
  deliberately, and confirms that each of the seven invariant queries detects the corruption.
- **Test data must be verified.** 33.33 was expected to trigger a floating-point error, but
  `33.33 * 100 == 3333.0` exactly; 19.99, 1.15, 0.29 and 4.35 do trigger it. Without the planted
  defect, this mistake in the test data would have gone unnoticed.

**Selecting cases by test data** (as in data-driven frameworks, case_id and marks are part of the data):

```bash
pytest --target_marks=smoke                      # smoke tests only
pytest --target_marks=idempotency,concurrency    # tests with any of these marks
pytest --target_case_ids=CON-001,VAL-P08         # specific cases
```

## 4. Web front end and UI tests

A mobile-first wallet page (React 19 + Vite) in front of the same API, served by FastAPI under
`/app`. It exists so that the risks tested at the API level are also tested where a user meets them:
a double tap, a slow network, a response lost on its way back. There is no login and no transfer
screen. Its specification is [`SPEC.md`](SPEC.md), which also defines the Android app with the
same screens and behaviour (in [`android/`](android/README.md): every screen is built; its Appium suite comes next).

**Screens:** Start (create or open a wallet) · Home and History tabs · Top up · Pay: amount →
Confirm → receipt · Payment detail with refunds.

**Design.** The visual design is a design system in a Figma file (private): 25 colour variables
over 18 primitives, spacing and radius variables, eight text styles and ten components, most of
them with variants. The screens are built in code from it. The Figma file has no screen frames; SPEC.md §7
lists each screen's states and test hooks instead.

- `web/src/tokens.css` declares every Figma variable under the name of its code syntax in Figma:
  `color/bg/page` becomes `var(--color-bg-page)`.
- Each Figma component has one React component of the same name (`TopBar`, `AmountField`,
  `TransactionRow`, ...).

**Specification.** SPEC.md numbers every rule (input `R`, Idempotency-Key attempts `K`, navigation
`N`, display `D`, layout `L`, error messages `E`) and traces each rule to the cases that cover it,
including the rules no case covers yet (none of those can move money). Before the specification was
published, its web rules were checked against the running page with a browser script; the two that
cannot be checked that way are marked as checked by reading the code.

**Idempotency in the page.** One Idempotency-Key is created per payment attempt, when *Confirm
payment* is tapped. After no answer, the attempt is kept: *Retry*, or going back and continuing with
the same amount, resends the same key, so a payment that did go through is returned instead of
charged again. Only a different amount starts a new attempt. While a request is in flight, a
second tap sends nothing.

### UI tests

Playwright for Python, in the same pytest suite as the API tests. The web tests reuse the API's
server, `api` and `db` fixtures, its marks and its `--target_case_ids` / `--target_marks` selection:
`--target_marks=precision` selects the API and the UI precision tests together.

- Every case runs on two Playwright device profiles, Pixel 7 and iPhone 14, both in Chromium. The
  iPhone profile emulates the viewport, touch and user agent; it is not Safari. The time zone is pinned.
- Setup goes through the API; only the behaviour under test goes through the page.
- Every case except the layout check (WEB-011) checks the database as well as the page, and every
  case fails on any uncaught JavaScript error.
- Elements are found by `data-testid` only (SPEC.md §7). Expected texts are copied from the
  specification (`testdata/web.py`), not read from the front end's own code.
- A failure leaves a screenshot and a Playwright trace in `reports/web/`; CI uploads them.

| Case | What it checks | Proven to fail by |
|---|---|---|
| WEB-001 | A new wallet starts at 0.00 | |
| WEB-002 | A top-up reaches the balance and the ledger | |
| WEB-003 | Pay through Confirm to the receipt and History; one UUID v4 key, sent only on Confirm | |
| WEB-004 | A top-up of 19.99 keeps every cent | `float_math` |
| WEB-005 | `-1`, `1e3` and `10.555` are refused and nothing moves | `negative_amount` |
| WEB-006 | A payment above the balance is refused; *Change amount* keeps the input | |
| WEB-007 | Two taps in the same instant send one payment | mutation `no_in_flight_guard` |
| WEB-008 | The server charges, the response is lost, the user retries: same key, "already gone through", one payment | `no_idempotency` |
| WEB-009 | A partial refund, then the cumulative refund limit | `refund_overflow` |
| WEB-010 | History equals the ledger, row by row | |
| WEB-011 | Eight screens: no horizontal scrolling, every button and link at least 44 × 44 px | |
| WEB-012 | While processing, Confirm, Cancel and Back are disabled | mutation `confirm_stays_enabled` |
| WEB-013 | Back after no answer: the same amount keeps the key, a new amount gets a new one | mutation `back_forgets_the_attempt` |
| WEB-014 | No Retry after a top-up gets no answer (the API takes no key for top-ups) | mutation `top_up_offers_retry` |

**Simulating the network.** `framework/web/network.py` uses Playwright's request interception; the
API is not changed.

- `hold`: the request waits in the browser until it is released (processing state, double tap).
- `lose_response`: the request reaches the server and is processed, but the browser sees a dropped
  connection. This is the case that makes reusing the key necessary: the money has moved, and the
  user only knows that there was no answer.
- `block`: the request never leaves the browser.

**Proving the UI tests can fail.** Two mechanisms, both run by CI:

1. **Planted server defects.** `tools/fault_check.py` also requires the web cases in the table to
   fail, on both phones.
2. **Rules that live only in the page.** No server switch can break the in-flight guard, the disabled
   button, the pending attempt or the missing Retry. `tools/web_mutation_check.py` changes one piece
   of the page's code, builds that version, serves it to the tests (through the `WEB_DIST`
   environment variable) and requires the matching case to fail. All four mutations are caught.

**Running**

```bash
(cd web && npm ci && npm run build)        # the API serves /app only once web/dist exists
.venv/bin/pip install -r requirements-web.txt
.venv/bin/python -m playwright install chromium

.venv/bin/pytest tests/web                       # 34 runs, about 25 seconds
.venv/bin/python tools/fault_check.py --web-only # planted defects, web cases only
.venv/bin/python tools/web_mutation_check.py     # page mutations; needs Node on PATH
```

Without Playwright, `tests/web` is skipped and pytest prints why. With Playwright but no build,
every web test fails with "Build it first", so a run in which nothing was tested cannot look like a
pass.

## 5. Postman and Newman

`postman/` holds a Postman collection for the same API. It can be imported into Postman for manual
use, and Newman runs it from the command line and in CI.

**Division of work with pytest**

| | Postman / Newman | pytest |
|---|---|---|
| Purpose | Lets developers and product managers reproduce issues by importing it; exploratory testing; handover | Primary automated regression suite |
| Coverage | Main flows and representative errors (25 requests), plus amount boundaries (9 CSV rows) | 95 API tests |
| Cannot do | Query the database; generate concurrency (one request at a time) | — |

**Collection structure**

| Folder | Cases | Focus |
|---|---|---|
| 01 Health check | PM-01 | Confirms no planted defect is switched on |
| 02 Main flow | PM-02–08 | Create a wallet, top up, pay, refund, reconcile; each request passes saved IDs to the next |
| 03 Idempotency | PM-09–12 | A retry with the same key charges once: the response is marked `Idempotent-Replayed: true` and the balance is unchanged |
| 04 Error handling | PM-13–18 | Insufficient balance by one cent, cumulative over-refund, amount sent as a number, single-payment limit exceeded |
| 05 Transfers | PM-19–25 | After a failed transfer, the balance is read again to confirm nothing was debited |
| 06 Amount boundaries | AMT-01–09 | Reads `postman/data/amount-boundaries.csv` and runs once per row |

Every request also runs collection-level checks: response time under 1 second, a JSON response, and
the uniform error format for error responses. Every test name starts with its case ID, so report
entries map directly to cases.

**Running**

```bash
npm install -g newman@6.2.2 newman-reporter-htmlextra@1.23.1

postman/run-newman.sh                                  # starts its own API (temporary database) and stops it afterwards
BASE_URL=http://127.0.0.1:8400 postman/run-newman.sh   # targets an API that is already running
.venv/bin/python tools/newman_fault_check.py           # proves the collection catches the planted defects
```

Reports are written to `reports/newman/`: `main.html` and `amounts.html` (htmlextra) and JUnit XML.

In Postman, import the collection and the `local` environment; the whole collection can then be run
directly (folder 06 skips itself when no data file is supplied). To run folder 06, select only that
folder in the Collection Runner and choose the CSV file above.

**The collection must also prove that it catches defects**

| Planted defect | Cases that must fail |
|---|---|
| `no_idempotency` | PM-09, PM-10, PM-11 |
| `refund_overflow` | PM-15 |
| `negative_amount` | AMT-05, AMT-06 |
| `float_math` | AMT-03, AMT-04 |
| `transfer_not_atomic` | PM-25 |
| `race` | Excluded: Postman cannot generate concurrency, so this is left to pytest |

With `transfer_not_atomic` on, PM-24 (transfer to a non-existent wallet) still returns 404, so the
status code alone suggests nothing is wrong. Only PM-25, which reads the balance again, detects the
missing money.

## 6. Load testing (k6)

`load/payments.js` sends 80% payments and 20% balance reads; 10% of payments are retried with the same
Idempotency-Key. An arrival-rate executor holds the number of requests per second constant, so the
load does not ease off when the server slows down.

- **load**: 20 requests per second for 1 minute. Thresholds: error rate below 1%, payment p95 below
  500 ms, balance-read p95 below 300 ms.
- **stress**: ramps from 20 to 400 requests per second and stops if a threshold breaks, reporting the
  load at that point. On the CI runner, the run completed every stage without breaking a threshold
  (payment p95 of 4 ms up to 400 requests per second), so the limit was not found. `load/README.md`
  explains why the load was not raised further.

**Every run ends with a reconciliation.** `tools/check_invariants.py` checks eight rules against the
load-test database and fails the run if any rule is broken, in every scenario: a stress run may break
its thresholds, but never the balances. One rule was added because of the load test, "every payment
has a matching Idempotency-Key": when payments are duplicated, the books still balance (each payment
has its own ledger entry), so the original seven rules all pass and only this rule detects the problem.

The load test is triggered manually in CI (Actions → Load test). Scenario design, threshold rationale
and measured results are in [`load/README.md`](load/README.md).

## 7. Running locally

The development environment is Ubuntu on an Oracle Cloud ARM64 instance (Ampere A1), without Docker.
Python 3.12 is required; the web front end and its tests also need Node 20 or later (section 4).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run every test: starts its own API (random port, temporary database) and stops it afterwards
.venv/bin/pytest

# HTML report
.venv/bin/pytest --html=reports/report.html --self-contained-html

# Prove the tests catch the planted defects (API tests only: about 30 seconds)
.venv/bin/python tools/fault_check.py --api-only
# Without --api-only the web cases are included when the web tests can run (section 4)

# Start the API for manual requests
DB_PATH=wallet.db .venv/bin/uvicorn app.main:app --port 8400
BUGS=race DB_PATH=wallet.db .venv/bin/uvicorn app.main:app --port 8400   # with a planted defect on

# Target an API that is already running (this is how CI runs the suite)
.venv/bin/pytest --env=external --base-url=http://127.0.0.1:8400 --db-path=wallet.db
```

> Pass custom options as `--opt=value`. With `--db-path /tmp/x.db` (separated by a space), pytest
> treats `/tmp/x.db` as a test path before reading its configuration and uses it to determine the
> project root. It then finds neither `pytest.ini` nor `conftest.py`, and every custom option is
> reported as unrecognized.

## 8. CI

`.github/workflows/ci.yml` runs five jobs on every push to `main` and on every pull request:

1. **API tests**: starts the API in the background, waits for `/health`, runs the smoke tests and
   stops if they fail, then runs the full regression suite and uploads the pytest-html and JUnit
   reports (also on failure, so the evidence is kept).
2. **Tests catch planted bugs**: `tools/fault_check.py --api-only` turns on each of the six planted
   defects in turn. Each defect lists the tests that must catch it; if any of them passes, CI fails.
3. **Postman collection (Newman)**: runs the main flows and the CSV amount boundaries, uploads the
   htmlextra and JUnit reports, then runs `tools/newman_fault_check.py`, the same defect check for
   the collection.
4. **Web UI tests (Playwright)**: builds the front end (`npm ci`, Node 22), installs Chromium, runs
   the web tests on both phone profiles and uploads the report together with any failure
   screenshots and traces. It then runs `tools/fault_check.py --web-only` (the planted defects
   against the web cases) and `tools/web_mutation_check.py` (the page mutations).
5. **Android app (build and unit tests)**: builds the debug app on an x86-64 runner and runs its unit
   tests, including a check that the app's design tokens equal the web's `tokens.css`; uploads the
   APK. The Appium tests for the app follow once its screens exist (SPEC.md §8).

A separate, manually triggered `load.yml` runs the k6 load test followed by the reconciliation
(section 6).

Which tests fail under `race` depends on timing (six locally, five in CI), so `fault_check.py`
requires only the two that fail every time: CON-001 and the balance-equals-ledger invariant.

CI runs on GitHub's ARM64 runners (`ubuntu-24.04-arm`), the same architecture as the development
machine (OCI Ampere), so a local pass cannot turn into a CI failure through architecture differences.

## 9. AI-assisted development

I built this project with **Claude Code**, an AI coding agent running on my OCI development server.
My background is ten years of manual testing on payment systems; this repository is part of my move
into test automation (SDET). The work was divided as follows:

| My part | Claude Code's part |
|---|---|
| Set the requirements: the scope of the wallet API, which payment risks to cover, no Docker, CI required | Proposed a plan, a folder structure and a test-case list from those requirements |
| Reviewed the test-case list item by item and decided on changes (for example, supporting two decimal places in amounts) | Wrote the API, the test framework and the tests |
| Read the explanation of each step, ran it myself, and moved on only once I understood it | Ran each step, reported the results, and diagnosed failures |
| Decided when to commit and when to make the repository public | Committed in small steps, with messages that explain what changed and why |
| Chose the web scope and tools: Playwright for Python in the same suite, Figma for the design and its visual direction, no transfer screen; asked for WEB-013 and WEB-014 when the traceability table showed two uncovered rules that guard against double charges | Built the Figma design system, the front end, its specification and the UI tests; found and fixed a double-charge regression it had itself introduced (next section) |

**How I verify that the AI-written tests work:** a fully passing suite is not accepted as evidence.
Defects are planted in the system under test, each one must make its assigned tests fail, and CI
checks this automatically on every push to main. During development this approach caught real problems
(see the next section).

## 10. Issues found during development

Each of these is recorded in the commit history.

| Issue | How it was found | Fix |
|---|---|---|
| Balance requests occasionally returned 500 | Running concurrent scenarios by hand after the payment endpoint was written | FastAPI may open and close the same SQLite connection on different threads; `check_same_thread` is now disabled |
| The "empty Idempotency-Key" test never actually sent an empty key | The test failed and was traced to the client layer | `key or new_key()` treated an empty string as missing; a key is now generated only when the argument is `None` |
| The floating-point defect did not show up | With `float_math` on, the precision tests still passed | 33.33 happens to be exact in floating point; it was replaced with values verified to fail, such as 19.99 |
| Custom pytest options were reported as unrecognized | Rehearsing the CI commands locally | Options are passed as `--opt=value` (section 7) |
| With duplicated payments, all seven database invariants still passed | k6 with `no_idempotency` on: the k6 retry checks failed, but the reconciliation passed | The books balanced; the customer had simply been charged twice. A rule was added: every payment has a matching Idempotency-Key |
| Newman sent amounts that differed from the CSV | The case "scientific notation 1e3 must be rejected" received 201 | Newman converts unquoted CSV fields to numbers: `1e3` is sent as `1000` and `10.50` as `10.5`. Amount columns are now always quoted |
| In the web page, pressing *Pay* again after "no answer" would have charged twice | Reviewing the "no answer" screen before any UI test existed: the main button created a new Idempotency-Key | The pending attempt and its key are kept; Retry and the main button both resend them |
| The same double charge came back when Pay was split into two steps: Back from Confirm, then the same amount again, sent a new key | Writing WEB-013. The specification had described this behaviour as correct, and the browser check run for the redesign had asserted it | Only a different amount ends a pending attempt (compared as money: `30` equals `30.00`). WEB-013 covers both paths; the mutation `back_forgets_the_attempt` restores the old behaviour and must make it fail. Recorded in SPEC.md §11 |
| A double-tap test with Playwright's `dblclick` still passed with the in-flight guard removed | The mutation check: the mutant survived | React disables the button between the two clicks, so the guard was never reached. WEB-007 dispatches both clicks in one JavaScript task, the gap the guard exists for |
| One test hook read `100.00` on the top-up receipt and `63.00 TWD` on the payment receipt | Listing the hooks for SPEC.md | Every amount hook now holds the number only |
| On a small phone, the Start screen's error message appeared below the visible area: the user tapped and saw nothing happen | The Android app's first Appium run on a 360 × 640 dp screen could not find the message (UiAutomator sees only what is on screen). The web had the same problem at a 360 × 640 viewport; its Playwright tests had passed, because a text assertion does not require the element to be in view | Both clients show the message under the button that caused it and scroll it into view (SPEC L-04). WEB-011 now checks it on a 360 × 640 viewport and fails without the fix |
| Two more messages out of view, in the Android app only: after a refund, the reloaded refund list pushed the success message down; after a refund got no answer, Retry sat below its warning | The same Appium checks on the 360 × 640 dp screen. The web keeps the first in view through the browser's scroll anchoring, which Compose does not have | The app reloads before it shows the message, and brings the whole refund form into view when its state changes |
