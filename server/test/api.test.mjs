// 서버 API 시험: BASE=http://127.0.0.1:8787 node test/api.test.mjs  (먼저 npx wrangler dev 실행)
import assert from "node:assert/strict";
const BASE = process.env.BASE || "http://127.0.0.1:8787";
let passed = 0;
async function call(method, path, body, token) {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, data: await res.json() };
}
function ok(name, cond) { assert.ok(cond, name); passed++; console.log("✓", name); }

const kst = new Date(Date.now() + 9 * 3600e3).toISOString();
const today = kst.slice(0, 10), month = kst.slice(0, 7);

// 만들기
let r = await call("POST", "/api/family", { name: "테스트집", pass: "12", member: "아빠" });
ok("짧은 암호 거절", r.status === 400);
r = await call("POST", "/api/family", { name: "테스트집", pass: "우리집1234", member: "아빠" });
ok("가계부 만들기", r.status === 200 && /^[A-Z0-9]{6}$/.test(r.data.code));
const code = r.data.code, dad = r.data.token;

// 들어가기
r = await call("POST", "/api/join", { code, pass: "틀림", member: "엄마" });
ok("틀린 암호 거절", r.status === 403);
r = await call("POST", "/api/join", { code: code.toLowerCase(), pass: "우리집1234", member: "엄마" });
ok("소문자 코드로도 입장", r.status === 200);
const mom = r.data.token;
r = await call("POST", "/api/join", { code: "ZZZZZZ", pass: "x", member: "x" });
ok("없는 가계부", r.status === 404);
r = await call("GET", "/api/state", null, code + ".nope");
ok("엉터리 토큰 거절", r.status === 401);

// 기록
r = await call("POST", "/api/entries", { date: today, type: "out", amount: 12000, cat: "food", method: "카드", memo: "김밥" }, dad);
ok("지출 기록", r.status === 200 && r.data.entry.member === "아빠");
const id1 = r.data.entry.id;
r = await call("POST", "/api/entries", { date: today, type: "in", amount: 3000000, cat: "salary" }, mom);
ok("수입 기록", r.status === 200 && r.data.entry.member === "엄마");
r = await call("POST", "/api/entries", { date: today, amount: -5 }, mom);
ok("음수 금액 거절", r.status === 400);
r = await call("POST", "/api/entries", { date: "2026-13-01", amount: 5 }, mom);
ok("이상한 날짜 거절", r.status === 400);
r = await call("PUT", "/api/entries/" + id1, { date: today, type: "out", amount: 15000, cat: "food", memo: "김밥+라면" }, mom);
ok("다른 가족이 고치기", r.status === 200 && r.data.entry.amount === 15000);

r = await call("GET", "/api/state?month=" + month, null, mom);
ok("상태: 기록 2개", r.data.entries.length === 2);
ok("상태: 가족 2명", r.data.family.members.join() === "아빠,엄마");
ok("상태: 기본 분류", r.data.categories.length > 10);

// 예산·분류
r = await call("PUT", "/api/settings", { budget: { total: 2000000, cats: { food: 500000, x: -3 } } }, dad);
ok("예산 저장(이상한 값은 버림)", r.data.budget.total === 2000000 && r.data.budget.cats.food === 500000 && !("x" in r.data.budget.cats));
r = await call("PUT", "/api/settings", { categories: [{ id: "a", name: "식비", type: "out" }] }, dad);
ok("수입 분류 없으면 거절", r.status === 400);

// 고정 지출: 1일로 등록하면 이번 달에 바로 들어감
r = await call("POST", "/api/fixed", { title: "관리비", type: "out", amount: 250000, cat: "house", day: 1 }, dad);
ok("고정 지출 등록", r.status === 200);
const fid = r.data.fixed.id;
r = await call("POST", "/api/fixed", { title: "보험", type: "out", amount: 100000, cat: "insure", day: 1, skipThisMonth: true }, dad);
ok("다음 달부터 고정 지출", r.data.fixed.start > month);
r = await call("GET", "/api/state?month=" + month, null, mom);
const auto = r.data.entries.filter((e) => e.fixed_id);
ok("이번 달 자동 기록은 관리비 1건", auto.length === 1 && auto[0].memo === "관리비" && auto[0].date === month + "-01");
r = await call("GET", "/api/state?month=" + month, null, mom);
ok("두 번 열어도 한 번만", r.data.entries.filter((e) => e.fixed_id).length === 1);
await call("DELETE", "/api/entries/" + auto[0].id, null, mom);
r = await call("GET", "/api/state?month=" + month, null, mom);
ok("자동 기록 지우면 되살아나지 않음", r.data.entries.filter((e) => e.fixed_id).length === 0);
r = await call("GET", "/api/state?month=2020-01", null, mom);
ok("등록 전 달에는 안 넣음", r.data.entries.length === 0);
r = await call("GET", "/api/state?month=2099-01", null, mom);
ok("미래 달에는 안 넣음", r.data.entries.length === 0);
r = await call("PUT", "/api/fixed/" + fid, { title: "관리비", amount: 260000, day: 5, active: false }, dad);
ok("고정 지출 고치기", r.data.fixed.amount === 260000 && r.data.fixed.active === 0);

// 추세·내보내기
r = await call("GET", "/api/state?month=" + month, null, dad);
ok("6개월 추세", r.data.trend.some((t) => t.m === month && t.type === "in" && t.sum === 3000000));
r = await call("GET", "/api/entries", null, dad);
ok("전체 내보내기", r.data.entries.length === 2);

// 암호 바꾸기 → 다른 기기 로그아웃
r = await call("PUT", "/api/password", { old: "우리집1234", pass: "새암호5678" }, dad);
ok("암호 바꾸기", r.status === 200);
r = await call("GET", "/api/state", null, mom);
ok("다른 기기는 다시 로그인", r.status === 401);
r = await call("GET", "/api/state", null, dad);
ok("바꾼 기기는 그대로", r.status === 200);

// 잠금
for (let i = 0; i < 8; i++) await call("POST", "/api/join", { code, pass: "x" + i, member: "누구" });
r = await call("POST", "/api/join", { code, pass: "새암호5678", member: "엄마" });
ok("8번 틀리면 잠김", r.status === 429);

r = await call("POST", "/api/logout", null, dad);
r = await call("GET", "/api/state", null, dad);
ok("로그아웃", r.status === 401);

console.log(`\n${passed}개 통과`);
