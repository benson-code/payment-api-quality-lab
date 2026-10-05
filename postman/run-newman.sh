#!/usr/bin/env bash
# 用 Newman 跑 Postman collection。
#
#   postman/run-newman.sh                                  # 自己起一台 API（隨機 port、暫存資料庫），跑完就關
#   BASE_URL=http://127.0.0.1:8400 postman/run-newman.sh   # 打一台已經起好的 API
#   BUGS=no_idempotency postman/run-newman.sh              # 起一台開了 bug 的 API，看哪些案例變紅
#
# 跑兩輪：main 跑 01–05 主流程（06 沒有資料會自動跳過）；amounts 只跑 06，讀 CSV 每一列跑一次。
# 報告在 reports/newman/（可用 NEWMAN_OUT 改）：{main,amounts}.html（htmlextra）、.xml（JUnit）、.json（給 fault check 讀）
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=${NEWMAN_OUT:-reports/newman}
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

status=0
run main || status=1
run amounts --folder "06 金額邊界（資料驅動）" -d postman/data/amount-boundaries.csv || status=1
exit $status
