// k6 壓測：以付款為主、混著查餘額，一部分付款模擬「逾時後用同一把 key 重送」。
//
//   k6 run load/payments.js                       # load：每秒 20 筆，持續 1 分鐘，看門檻有沒有過
//   k6 run -e SCENARIO=stress load/payments.js    # stress：一路加到每秒 400 筆，撐不住就停，看停在哪
//   k6 run -e SCENARIO=smoke load/payments.js     # smoke：1 個使用者跑 5 次，只確認腳本本身沒壞
//   -e BASE_URL=http://127.0.0.1:8400（預設）
//
// 壓完一定要對帳（load/run-load.sh 會自動做）：回應再快，帳算錯就是沒過。
import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8400';
const SCENARIO = __ENV.SCENARIO || 'load';
const WALLETS = 20;
const PAY_RATIO = 0.8;                                  // 80% 付款、20% 查餘額
const RETRY_RATIO = SCENARIO === 'smoke' ? 1 : 0.1;     // smoke 每一筆都重送，確保重送路徑有跑到

const STRESS_STAGES = [
    { target: 50, duration: '1m' },
    { target: 100, duration: '1m' },
    { target: 200, duration: '1m' },
    { target: 400, duration: '1m' },
];

const SCENARIOS = {
    smoke: { executor: 'shared-iterations', vus: 1, iterations: 5 },
    // arrival-rate：不管伺服器多慢，每秒都送出固定筆數（像真實的客人），而不是等上一筆回來才送下一筆
    load: { executor: 'constant-arrival-rate', rate: 20, timeUnit: '1s', duration: '1m',
            preAllocatedVUs: 20, maxVUs: 100 },
    stress: { executor: 'ramping-arrival-rate', startRate: 20, timeUnit: '1s', stages: STRESS_STAGES,
              preAllocatedVUs: 50, maxVUs: 500 },
};

// stress 的門檻一旦破了就停下來：停下來的時間點，就是系統撐不住的負載
const abort = SCENARIO === 'stress' ? { abortOnFail: true, delayAbortEval: '10s' } : {};

export const options = {
    scenarios: { [SCENARIO]: SCENARIOS[SCENARIO] },
    thresholds: {
        http_req_failed: [{ threshold: 'rate<0.01', ...abort }],
        'http_req_duration{name:pay}': [{ threshold: 'p(95)<500', ...abort }],
        'http_req_duration{name:balance}': ['p(95)<300'],
        checks: ['rate>0.99'],
    },
};

const retries = new Counter('payment_retries');

export function setup() {
    const wallets = [];
    for (let i = 0; i < WALLETS; i++) {
        const w = http.post(`${BASE_URL}/wallets`, JSON.stringify({ owner: `load-${i}` }), json('setup'));
        const id = w.json('wallet_id');
        // 每個錢包儲值夠多，整場壓測都不會遇到餘額不足
        http.post(`${BASE_URL}/wallets/${id}/topups`, JSON.stringify({ amount: '1000000.00' }), json('setup'));
        wallets.push(id);
    }
    return { wallets };
}

export default function (data) {
    const wallet = data.wallets[Math.floor(Math.random() * data.wallets.length)];
    if (Math.random() < PAY_RATIO) {
        pay(wallet);
    } else {
        const r = http.get(`${BASE_URL}/wallets/${wallet}`, { tags: { name: 'balance' } });
        check(r, { '查餘額 200': (res) => res.status === 200 });
    }
}

function pay(wallet) {
    const body = JSON.stringify({ wallet_id: wallet, amount: randomAmount() });
    const params = json('pay', { 'Idempotency-Key': crypto.randomUUID() });
    const first = http.post(`${BASE_URL}/payments`, body, params);
    check(first, { '付款 201': (r) => r.status === 201 });
    if (first.status !== 201 || Math.random() >= RETRY_RATIO) {
        return;
    }
    // 同一把 key、同一個內容再送一次：必須回原本那筆，不能再扣一次
    retries.add(1);
    params.tags = { name: 'pay_retry' };
    const again = http.post(`${BASE_URL}/payments`, body, params);
    check(again, {
        '重送回 201': (r) => r.status === 201,
        '重送標示 Idempotent-Replayed': (r) => r.headers['Idempotent-Replayed'] === 'true',
        '重送回同一筆付款': (r) => r.status === 201 && r.json('payment_id') === first.json('payment_id'),
    });
}

function json(name, extraHeaders = {}) {
    return { headers: { 'Content-Type': 'application/json', ...extraHeaders }, tags: { name } };
}

// 1.00～99.99，金額一律用字串
function randomAmount() {
    const cents = 100 + Math.floor(Math.random() * 9900);
    return `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, '0')}`;
}

// ---- 報告：終端機、GitHub 執行摘要（markdown）、原始 JSON -----------------------------

export function handleSummary(data) {
    const md = summaryMarkdown(data);
    const out = __ENV.REPORT_DIR || 'reports/k6';
    return { stdout: md + '\n', [`${out}/summary.md`]: md, [`${out}/summary.json`]: JSON.stringify(data, null, 2) };
}

function summaryMarkdown(data) {
    const m = data.metrics;
    const val = (name, key) => (m[name] ? m[name].values[key] : undefined);
    const ms = (x) => (x === undefined ? '-' : `${x.toFixed(0)} ms`);
    const seconds = data.state.testRunDurationMs / 1000;
    const lines = [
        `## k6 ${SCENARIO}`,
        '',
        '| 指標 | 數值 |',
        '|---|---|',
        `| 執行時間 | ${seconds.toFixed(1)} s |`,
        `| 請求數 | ${val('http_reqs', 'count')}（平均每秒 ${val('http_reqs', 'rate').toFixed(1)}） |`,
        `| 失敗率 | ${(100 * val('http_req_failed', 'rate')).toFixed(2)}% |`,
        `| 付款 p95 | ${ms(val('http_req_duration{name:pay}', 'p(95)'))} |`,
        `| 查餘額 p95 | ${ms(val('http_req_duration{name:balance}', 'p(95)'))} |`,
        `| 重送次數 | ${val('payment_retries', 'count') || 0} |`,
        `| 來不及送出的請求（dropped） | ${val('dropped_iterations', 'count') || 0} |`,
    ];
    if (SCENARIO === 'stress') {
        lines.push(`| 停下時的目標負載 | 約每秒 ${stressRateAt(seconds).toFixed(0)} 筆 |`);
    }
    lines.push('', '| 門檻 | 結果 |', '|---|---|');
    for (const [name, metric] of Object.entries(m)) {
        for (const [rule, r] of Object.entries(metric.thresholds || {})) {
            lines.push(`| \`${name}\` ${rule} | ${r.ok ? '通過' : '**沒過**'} |`);
        }
    }
    return lines.join('\n');
}

// ramping-arrival-rate 在第 t 秒的目標負載（各階段之間是線性爬升）
function stressRateAt(t) {
    let rate = SCENARIOS.stress.startRate;
    for (const s of STRESS_STAGES) {
        const d = parseInt(s.duration, 10) * 60;
        if (t <= d) {
            return rate + (s.target - rate) * (t / d);
        }
        t -= d;
        rate = s.target;
    }
    return rate;
}
