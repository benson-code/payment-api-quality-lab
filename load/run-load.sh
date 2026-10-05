#!/usr/bin/env bash
# 起一台 API（暫存資料庫）→ k6 壓測 → 壓完對帳。CI 用這支；共用機器上只跑 smoke。
#
#   SCENARIO=smoke  load/run-load.sh    # 1 個使用者 5 次，確認腳本沒壞（本機可跑）
#   SCENARIO=load   load/run-load.sh    # 每秒 20 筆 × 1 分鐘，門檻沒過就失敗（預設）
#   SCENARIO=stress load/run-load.sh    # 一路加壓到撐不住；門檻破了是預期的，只要帳對就算過
#
# 不管哪個情境，對帳（tools/check_invariants.py）沒過一律失敗：壓到崩潰也不能算錯錢。
set -euo pipefail
cd "$(dirname "$0")/.."

SCENARIO=${SCENARIO:-load}
OUT=${LOAD_OUT:-reports/k6}
mkdir -p "$OUT"
PY=${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}

tmp=$(mktemp -d)
db="$tmp/wallet.db"
port=$("$PY" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
# 壓測時關掉 access log：每個請求寫一行 log 本身就會拖慢 API
DB_PATH="$db" "$PY" -m uvicorn app.main:app --port "$port" --no-access-log > "$OUT/api.log" 2>&1 &
api=$!
trap 'kill $api 2>/dev/null; rm -rf "$tmp"' EXIT
base=http://127.0.0.1:$port
for _ in $(seq 40); do curl -sf "$base/health" > /dev/null && break; sleep 0.5; done
curl -sf "$base/health" > /dev/null || { echo "API did not start"; cat "$OUT/api.log"; exit 1; }

k6_status=0
k6 run -q -e SCENARIO="$SCENARIO" -e BASE_URL="$base" -e REPORT_DIR="$OUT" load/payments.js || k6_status=$?

echo "== 壓測後對帳 =="
inv_status=0
"$PY" tools/check_invariants.py "$db" > "$OUT/invariants.txt" || inv_status=$?
cat "$OUT/invariants.txt"

if [ "$inv_status" -ne 0 ]; then
  echo "對帳沒過：帳算錯了"; exit 1
fi
# stress 只容許「門檻沒過」（k6 exit 99）。k6 本身出錯時資料庫可能是空的，空的帳也會「對帳通過」
if [ "$SCENARIO" = stress ] && [ "$k6_status" -eq 99 ]; then
  echo "stress：門檻在加壓途中被突破（預期中），帳是對的"; exit 0
fi
if [ "$k6_status" -ne 0 ]; then
  echo "k6 沒過（exit $k6_status）"; exit "$k6_status"
fi
