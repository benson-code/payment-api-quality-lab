# Load testing (k6)

Functional tests answer whether the system is correct. Performance tests answer how much load it can
take while staying correct and fast enough. A payment system adds one requirement: **reconcile the
database after every run. A fast response with wrong balances is a failure.**

## Types of performance test

| Type | Question | Method | This project |
|---|---|---|---|
| Load | Does it handle the expected traffic? | Hold the expected rate for a period and check the thresholds | ✅ `SCENARIO=load` |
| Stress | Where is the limit, and what happens beyond it? | Increase the load until a threshold breaks | ✅ `SCENARIO=stress` |
| Spike | What happens when traffic jumps suddenly (for example, a flash sale)? | Jump from low to high traffic instantly | ❌ Not covered |
| Soak | Does it leak memory or slow down over several hours? | Moderate traffic for a long time | ❌ Not covered: free CI runners are not suited to multi-hour runs |

## What the test does

`load/payments.js`:

- **Traffic mix**: 80% payments and 20% balance reads against 20 wallets funded in advance.
- **Retries**: 10% of payments are sent a second time with the same Idempotency-Key, simulating a
  client retry after a timeout. Each retry must return the original payment (the same `payment_id`
  and `Idempotent-Replayed: true`).
- **Arrival rate rather than a fixed number of users**: a fixed number of requests is sent every
  second, however slowly the server responds. With a fixed number of virtual users, each user waits
  for a response before sending the next request, so a slower server automatically receives less
  load, which hides the problem; real customers do not arrive less often because the system is slow.
  Requests that cannot be sent in time are counted as `dropped_iterations`.

| Scenario | Load | When a threshold breaks |
|---|---|---|
| smoke | 1 virtual user, 5 iterations | The run fails. Used only to check that the script works; safe to run locally |
| load | 20 requests per second for 1 minute | The run fails |
| stress | 20 → 50 → 100 → 200 → 400 requests per second, 1 minute per stage | The ramp stops, and the load at that point is the limit. If every stage completes, the limit is above 400 requests per second |

## Thresholds

| Threshold | Value | Rationale |
|---|---|---|
| Error rate | < 1% | Normal load should produce no errors; 1% allows for occasional runner noise |
| Payment p95 | < 500 ms | Payments write and take a lock, so they are slower than reads |
| Balance-read p95 | < 300 ms | Read-only, so clearly faster than a payment |
| Check pass rate | > 99% | Includes "a retry returns the original payment", which must not fail |

p95 is used instead of the average because a large number of fast requests pulls the average down
and hides the slowest 5% of customers.

## Reconciliation after every run

After every run, `load/run-load.sh` runs `tools/check_invariants.py`, which checks eight rules, each
written as a query that must return no rows. Seven are shared with the pytest database tests (balance
equals the ledger sum, no negative balances, refunds do not exceed the payment, and so on). The eighth
was added for the load test: **every payment has a matching Idempotency-Key**.

The reason for the eighth rule: with the `no_idempotency` defect on, retries become duplicate charges,
yet the original seven rules all pass, because each duplicated payment has its own ledger entry and
the books balance. Balanced books do not mean correct charges: the customer was charged twice, and
both charges are recorded accurately.

```
balance_equals_ledger            OK
...
no_orphan_transfer_entries       OK
payments_have_idempotency_keys   BROKEN (1 rows)
    (6, 0)                       <- 6 payments, 0 keys
```

**A failed reconciliation fails the run in every scenario.** A stress run may break its thresholds,
but never the balances.

## What the numbers mean

The system under test is a single uvicorn worker with SQLite, and CI runs on GitHub's free runners.
The numbers measured here **describe only this practice system on that runner, not the capacity of
any production environment**.

They are useful for **comparison**: with the same script on the same runner, a clearly worse p95 after
a code change may indicate a performance regression. However, the runner itself can vary by several
times (see the results below), so a single run is not conclusive; compare several runs. The point of
this test is the method: how the scenarios are designed, how the thresholds are set, and how data
correctness is verified afterwards.

## Results

GitHub ARM64 runner (`ubuntu-24.04-arm`), three manual runs of the same commit on 2026-10-05:

| Scenario | Requests | Failure rate | Payment p95 | Balance-read p95 | Retries | Dropped | Reconciliation |
|---|---|---|---|---|---|---|---|
| load (run 1) | 1,330 | 0% | 19 ms | 2 ms | 89 | 0 | All 8 rules pass (964 payments) |
| load (run 2) | 1,347 | 0% | 3 ms | 2 ms | 106 | 0 | All 8 rules pass (969 payments) |
| stress | 36,313 | 0% | 4 ms | 2 ms | 2,674 | 0 | All 8 rules pass (26,746 payments) |

**The stress run did not find the limit.** All four stages completed, up to 400 requests per second,
without breaking a threshold. The supported conclusion is only that the system handles up to 400
requests per second with a payment p95 of 4 ms; where the limit lies was not measured.

The load was not raised further because k6 and the API run on the same runner and compete for CPU.
At higher rates, k6 itself may become the bottleneck (requests it cannot send are counted as dropped),
so the measurement would reflect the runner's limit rather than the API's. Measuring the real limit
requires running the load generator and the system under test on separate machines.

**The two load runs differ sixfold in payment p95** (19 ms and 3 ms), while the far heavier stress run
measured 4 ms. All three runs used the same commit, so the difference comes from the execution
environment. This is why a single run is not conclusive.

## Running

```bash
SCENARIO=smoke load/run-load.sh     # locally: checks that the script works (a few seconds)
```

The load and stress scenarios run only in CI: GitHub → Actions → **Load test** → Run workflow →
choose a scenario. Results appear on the run's summary page; the raw JSON and the API log are uploaded
as an artifact.

The load test is not run on the development machine, which is shared with other services.
