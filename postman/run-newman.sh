#!/usr/bin/env bash
# 用 Newman 跑 Postman collection。
#
#   postman/run-newman.sh                                  # 自己起一台 API（隨機 port、暫存資料庫），跑完就關
#   BASE_URL=http://127.0.0.1:8400 postman/run-newman.sh   # 打一台已經起好的 API
#   BUGS=no_idempotency postman/run-newman.sh              # 起一台開了 bug 的 API，看哪些案例變紅
#
# 報告在 reports/newman/：main.html（htmlextra）、main.xml（JUnit）、main.json（給 fault check 讀）
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=reports/newman
mkdir -p "$OUT"
PY=${PYTHON:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}

if [ -z "${BASE_URL:-}" ]; then
  tmp=$(mktemp -d)
  port=$("$PY" -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')
  # BUGS 若有設定，會跟著環境變數傳給 API
  DB_PATH="$tmp/wallet.db" "$PY" -m uvicorn app.main:app --port "$port" > "$OUT/api.log" 2>&1 &
  api=$!
  trap 'kill $api 2>/dev/null; rm -rf "$tmp"' EXIT
  BASE_URL=http://127.0.0.1:$port
  for _ in $(seq 40); do curl -sf "$BASE_URL/health" > /dev/null && break; sleep 0.5; done
  curl -sf "$BASE_URL/health" > /dev/null || { echo "API did not start"; cat "$OUT/api.log"; exit 1; }
fi

# $1 是報告檔名，其餘參數直接交給 newman
run() {
  local name=$1; shift
  newman run postman/payment-api.postman_collection.json \
    -e postman/local.postman_environment.json --env-var "baseUrl=$BASE_URL" \
    -r cli,junit,htmlextra,json \
    --reporter-junit-export "$OUT/$name.xml" \
    --reporter-htmlextra-export "$OUT/$name.html" \
    --reporter-json-export "$OUT/$name.json" \
    "$@"
}

run main
