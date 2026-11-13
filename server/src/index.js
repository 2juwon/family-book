// 우리집 서랍 서버 (지금은 가계부) — Cloudflare Workers + Durable Objects(SQLite)
// 서랍(가족) 하나가 Durable Object 하나. 우리집 코드(6자리)로 찾아가고, 가족 암호로 들어감.
import { DurableObject } from "cloudflare:workers";

const CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const MAX_AMOUNT = 100_000_000_000; // 1천억
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Max-Age": "86400",
};

export const DEFAULT_CATEGORIES = [
  ["food", "식비", "🍚", "out"], ["cafe", "카페·간식", "☕", "out"], ["mart", "장보기", "🛒", "out"],
  ["living", "생활용품", "🧻", "out"], ["traffic", "교통", "🚌", "out"], ["car", "자동차", "🚗", "out"],
  ["house", "주거·관리비", "🏠", "out"], ["phone", "통신", "📱", "out"], ["kid", "아이", "🧸", "out"],
  ["edu", "교육", "📚", "out"], ["health", "병원·약", "💊", "out"], ["shop", "쇼핑", "👕", "out"],
  ["fun", "여가·여행", "🎡", "out"], ["gift", "경조사·선물", "🎁", "out"], ["insure", "보험", "🛡️", "out"],
  ["sub", "구독", "📺", "out"], ["etc", "기타", "📦", "out"],
  ["salary", "월급", "💰", "in"], ["side", "부수입", "💵", "in"], ["allow", "용돈", "🧧", "in"],
  ["refund", "환급·이자", "↩️", "in"], ["etc_in", "기타 수입", "📥", "in"],
].map(([id, name, icon, type]) => ({ id, name, icon, type }));

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8", ...CORS } });
const fail = (status, msg) => json({ error: msg }, status);

function randomCode(n = 6) {
  const b = crypto.getRandomValues(new Uint8Array(n));
  return Array.from(b, (x) => CODE_CHARS[x % CODE_CHARS.length]).join("");
}
function randomHex(n = 24) {
  return Array.from(crypto.getRandomValues(new Uint8Array(n)), (x) => x.toString(16).padStart(2, "0")).join("");
}
async function hashPass(pass, saltHex) {
  const salt = Uint8Array.from(saltHex.match(/../g), (h) => parseInt(h, 16));
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(pass), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt, iterations: 100000 }, key, 256);
  return Array.from(new Uint8Array(bits), (x) => x.toString(16).padStart(2, "0")).join("");
}
// 한국 시간 기준 오늘
export function kstToday(now = Date.now()) {
  const d = new Date(now + 9 * 3600 * 1000);
  return d.toISOString().slice(0, 10);
}
const monthOf = (date) => date.slice(0, 7);
function addMonths(ym, k) {
  let [y, m] = ym.split("-").map(Number);
  m += k;
  while (m < 1) { m += 12; y--; }
  while (m > 12) { m -= 12; y++; }
  return `${y}-${String(m).padStart(2, "0")}`;
}
function daysIn(ym) {
  const [y, m] = ym.split("-").map(Number);
  return new Date(Date.UTC(y, m, 0)).getUTCDate();
}

const isMonth = (s) => typeof s === "string" && /^\d{4}-(0[1-9]|1[0-2])$/.test(s);
const isDate = (s) => typeof s === "string" && /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/.test(s);
const cleanText = (s, max) => (typeof s === "string" ? s.replace(/[\u0000-\u001f]/g, " ").trim().slice(0, max) : "");
const cleanName = (s) => cleanText(s, 12);

function cleanEntry(b) {
  const type = b.type === "in" ? "in" : "out";
  const amount = Math.round(Number(b.amount));
  if (!isDate(b.date)) return { error: "날짜가 이상해요" };
  if (!Number.isFinite(amount) || amount <= 0 || amount > MAX_AMOUNT) return { error: "금액을 확인해 주세요" };
  const cat = cleanText(b.cat, 40) || (type === "in" ? "etc_in" : "etc");
  const method = cleanText(b.method, 12);
  const memo = cleanText(b.memo, 80);
  return { type, amount, cat, method, memo, date: b.date };
}

// ───────────────────────── Worker 입구 ─────────────────────────
export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    const url = new URL(request.url);
    const path = url.pathname;
    try {
      if (path === "/" || path === "/api/health") return json({ ok: true, name: "family-book" });

      if (path === "/api/family" && request.method === "POST") {
        const body = await request.json().catch(() => ({}));
        // 비어 있는 코드를 찾을 때까지 (실제로는 거의 한 번에 됨)
        for (let i = 0; i < 5; i++) {
          const code = randomCode();
          const stub = env.FAMILY.get(env.FAMILY.idFromName(code));
          const res = await stub.create(code, body);
          if (res.error === "taken") continue;
          if (res.error) return fail(400, res.error);
          return json(res);
        }
        return fail(500, "잠시 후 다시 해 주세요");
      }

      if (path === "/api/join" && request.method === "POST") {
        const body = await request.json().catch(() => ({}));
        const code = String(body.code || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
        if (code.length !== 6) return fail(400, "우리집 코드는 6자리예요");
        const stub = env.FAMILY.get(env.FAMILY.idFromName(code));
        const res = await stub.join(body);
        if (res.error) return fail(res.status || 400, res.error);
        return json({ ...res, code });
      }

      if (path.startsWith("/api/")) {
        const auth = (request.headers.get("Authorization") || "").replace(/^Bearer\s+/i, "");
        const [code, token] = auth.split(".");
        if (!code || !token || !/^[A-Z0-9]{6}$/.test(code)) return fail(401, "다시 로그인해 주세요");
        const stub = env.FAMILY.get(env.FAMILY.idFromName(code));
        const body = ["POST", "PUT"].includes(request.method) ? await request.json().catch(() => ({})) : null;
        const res = await stub.handle(token, request.method, path, Object.fromEntries(url.searchParams), body);
        if (res && res.error) return fail(res.status || 400, res.error);
        return json(res);
      }
      return fail(404, "없는 주소예요");
    } catch (e) {
      console.error(e);
      return fail(500, "서버에 문제가 생겼어요");
    }
  },
};

// ───────────────────────── 서랍(가족) 하나 ─────────────────────────
export class Family extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    this.sql.exec(`
      CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
      CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, member TEXT, created INTEGER, seen INTEGER);
      CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, type TEXT NOT NULL, amount INTEGER NOT NULL,
        cat TEXT, method TEXT, memo TEXT, member TEXT, fixed_id INTEGER, created INTEGER, updated INTEGER);
      CREATE INDEX IF NOT EXISTS entries_date ON entries(date);
      CREATE TABLE IF NOT EXISTS fixed (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, type TEXT, amount INTEGER, cat TEXT, method TEXT,
        day INTEGER, start TEXT, active INTEGER DEFAULT 1, member TEXT);
      CREATE TABLE IF NOT EXISTS fixed_applied (fixed_id INTEGER, month TEXT, PRIMARY KEY (fixed_id, month));
    `);
  }

  get(k, def = null) {
    const r = this.sql.exec("SELECT v FROM meta WHERE k=?", k).toArray()[0];
    return r ? JSON.parse(r.v) : def;
  }
  set(k, v) {
    this.sql.exec("INSERT INTO meta (k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", k, JSON.stringify(v));
  }
  // 이름을 '우리집 서랍'으로 바꾸기 전에 기본 이름으로 만든 서랍은 새 기본 이름으로
  migrate() {
    if (this.get("name") === "우리집 가계부") this.set("name", "우리집 서랍");
  }
  now() { return Date.now(); }
  today() { return kstToday(this.now()); }

  newSession(member) {
    const token = randomHex();
    this.sql.exec("INSERT INTO sessions VALUES (?,?,?,?)", token, member, this.now(), this.now());
    const members = this.get("members", []);
    if (!members.includes(member)) { members.push(member); this.set("members", members.slice(0, 20)); }
    return token;
  }

  async create(code, body) {
    if (this.get("name")) return { error: "taken" };
    const name = cleanText(body.name, 20) || "우리집 서랍";
    const member = cleanName(body.member);
    const pass = typeof body.pass === "string" ? body.pass : "";
    if (!member) return { error: "내 이름(호칭)을 적어 주세요" };
    if (pass.length < 4 || pass.length > 64) return { error: "가족 암호는 4자 이상으로 해 주세요" };
    const salt = randomHex(16);
    this.set("salt", salt);
    this.set("hash", await hashPass(pass, salt));
    this.set("code", code);
    this.set("name", name);
    this.set("categories", DEFAULT_CATEGORIES);
    this.set("budget", { total: 0, cats: {} });
    this.set("created", this.now());
    const token = this.newSession(member);
    return { code, token: `${code}.${token}`, member, name };
  }

  async join(body) {
    if (!this.get("name")) return { error: "그런 서랍이 없어요. 코드를 확인해 주세요", status: 404 };
    this.migrate();
    const lock = this.get("lock", { fails: 0, until: 0 });
    if (lock.until > this.now()) {
      const min = Math.ceil((lock.until - this.now()) / 60000);
      return { error: `암호를 여러 번 틀려서 ${min}분 동안 잠겼어요`, status: 429 };
    }
    const member = cleanName(body.member);
    if (!member) return { error: "내 이름(호칭)을 적어 주세요" };
    const pass = typeof body.pass === "string" ? body.pass : "";
    const ok = (await hashPass(pass, this.get("salt"))) === this.get("hash");
    if (!ok) {
      lock.fails++;
      if (lock.fails >= 8) { lock.until = this.now() + 10 * 60000; lock.fails = 0; }
      this.set("lock", lock);
      return { error: "암호가 맞지 않아요", status: 403 };
    }
    this.set("lock", { fails: 0, until: 0 });
    const token = this.newSession(member);
    return { token: `${this.get("code")}.${token}`, member, name: this.get("name") };
  }

  async handle(token, method, path, query, body) {
    const s = this.sql.exec("SELECT member FROM sessions WHERE token=?", token).toArray()[0];
    if (!s) return { error: "다시 로그인해 주세요", status: 401 };
    this.migrate();
    this.sql.exec("UPDATE sessions SET seen=? WHERE token=?", this.now(), token);
    const me = s.member;
    const m = path.match(/^\/api\/(entries|fixed)\/(\d+)$/);

    if (path === "/api/state" && method === "GET") return this.state(query.month);
    if (path === "/api/entries" && method === "POST") return this.addEntry(body, me);
    if (path === "/api/entries" && method === "GET") return this.allEntries(query);
    if (m && m[1] === "entries" && method === "PUT") return this.editEntry(+m[2], body);
    if (m && m[1] === "entries" && method === "DELETE") {
      this.sql.exec("DELETE FROM entries WHERE id=?", +m[2]);
      return { ok: true };
    }
    if (path === "/api/fixed" && method === "POST") return this.saveFixed(null, body, me);
    if (m && m[1] === "fixed" && method === "PUT") return this.saveFixed(+m[2], body, me);
    if (m && m[1] === "fixed" && method === "DELETE") {
      this.sql.exec("DELETE FROM fixed WHERE id=?", +m[2]);
      return { ok: true };
    }
    if (path === "/api/settings" && method === "PUT") return this.saveSettings(body);
    if (path === "/api/logout" && method === "POST") {
      this.sql.exec("DELETE FROM sessions WHERE token=?", token);
      return { ok: true };
    }
    if (path === "/api/password" && method === "PUT") return this.changePass(body, token);
    return { error: "없는 주소예요", status: 404 };
  }

  // 고정 지출·수입을 그 달 기록으로 넣어 줌 (이미 넣은 달은 다시 안 넣음 — 지워도 되살아나지 않음)
  applyFixed(month) {
    const today = this.today();
    const thisMonth = monthOf(today);
    if (month > thisMonth) return;
    const items = this.sql.exec("SELECT * FROM fixed WHERE active=1 AND start<=?", month).toArray();
    for (const f of items) {
      const done = this.sql.exec("SELECT 1 FROM fixed_applied WHERE fixed_id=? AND month=?", f.id, month).toArray().length;
      if (done) continue;
      const day = Math.min(f.day, daysIn(month));
      const date = `${month}-${String(day).padStart(2, "0")}`;
      if (date > today) continue;
      this.sql.exec(
        "INSERT INTO entries (date,type,amount,cat,method,memo,member,fixed_id,created,updated) VALUES (?,?,?,?,?,?,?,?,?,?)",
        date, f.type, f.amount, f.cat, f.method, f.title, "자동", f.id, this.now(), this.now()
      );
      this.sql.exec("INSERT INTO fixed_applied VALUES (?,?)", f.id, month);
    }
  }

  state(month) {
    if (!isMonth(month)) month = monthOf(this.today());
    this.applyFixed(month);
    const from = `${month}-01`, to = `${month}-31`;
    const entries = this.sql.exec("SELECT * FROM entries WHERE date>=? AND date<=? ORDER BY date DESC, id DESC", from, to).toArray();
    // 지난 6개월(이번 달 포함) 합계 + 지난달 분류별
    const start = addMonths(month, -5);
    const trend = this.sql.exec(
      "SELECT substr(date,1,7) AS m, type, SUM(amount) AS sum FROM entries WHERE date>=? AND date<=? GROUP BY m, type",
      `${start}-01`, to
    ).toArray();
    const prev = addMonths(month, -1);
    const prevCats = this.sql.exec(
      "SELECT cat, type, SUM(amount) AS sum FROM entries WHERE date>=? AND date<=? GROUP BY cat, type",
      `${prev}-01`, `${prev}-31`
    ).toArray();
    return {
      month, today: this.today(),
      family: { name: this.get("name"), code: this.get("code"), members: this.get("members", []) },
      categories: this.get("categories", DEFAULT_CATEGORIES),
      budget: this.get("budget", { total: 0, cats: {} }),
      fixed: this.sql.exec("SELECT * FROM fixed ORDER BY day, id").toArray(),
      entries, trend, prevCats,
    };
  }

  allEntries(query) {
    const from = isDate(query.from) ? query.from : "0000-01-01";
    const to = isDate(query.to) ? query.to : "9999-12-31";
    return { entries: this.sql.exec("SELECT * FROM entries WHERE date>=? AND date<=? ORDER BY date, id", from, to).toArray() };
  }

  addEntry(body, me) {
    const e = cleanEntry(body || {});
    if (e.error) return e;
    const count = this.sql.exec("SELECT COUNT(*) AS n FROM entries").one().n;
    if (count > 200000) return { error: "기록이 너무 많아요" };
    const row = this.sql.exec(
      "INSERT INTO entries (date,type,amount,cat,method,memo,member,fixed_id,created,updated) VALUES (?,?,?,?,?,?,?,NULL,?,?) RETURNING *",
      e.date, e.type, e.amount, e.cat, e.method, e.memo, me, this.now(), this.now()
    ).one();
    return { entry: row };
  }

  editEntry(id, body) {
    const e = cleanEntry(body || {});
    if (e.error) return e;
    const rows = this.sql.exec(
      "UPDATE entries SET date=?,type=?,amount=?,cat=?,method=?,memo=?,updated=? WHERE id=? RETURNING *",
      e.date, e.type, e.amount, e.cat, e.method, e.memo, this.now(), id
    ).toArray();
    if (!rows.length) return { error: "이미 지워진 기록이에요", status: 404 };
    return { entry: rows[0] };
  }

  saveFixed(id, b, me) {
    b = b || {};
    const type = b.type === "in" ? "in" : "out";
    const title = cleanText(b.title, 30);
    const amount = Math.round(Number(b.amount));
    const day = Math.round(Number(b.day));
    if (!title) return { error: "이름을 적어 주세요" };
    if (!Number.isFinite(amount) || amount <= 0 || amount > MAX_AMOUNT) return { error: "금액을 확인해 주세요" };
    if (!(day >= 1 && day <= 31)) return { error: "날짜는 1~31일 사이로 골라 주세요" };
    const cat = cleanText(b.cat, 40) || (type === "in" ? "etc_in" : "etc");
    const method = cleanText(b.method, 12);
    const active = b.active === false ? 0 : 1;
    if (id == null) {
      const n = this.sql.exec("SELECT COUNT(*) AS n FROM fixed").one().n;
      if (n >= 100) return { error: "고정 항목은 100개까지예요" };
      // 기본은 이번 달부터, skipThisMonth면 다음 달부터 (이번 달 건 이미 직접 적었을 때)
      const thisMonth = monthOf(this.today());
      const start = b.skipThisMonth ? addMonths(thisMonth, 1) : thisMonth;
      const row = this.sql.exec(
        "INSERT INTO fixed (title,type,amount,cat,method,day,start,active,member) VALUES (?,?,?,?,?,?,?,?,?) RETURNING *",
        title, type, amount, cat, method, day, start, active, me
      ).one();
      return { fixed: row };
    }
    const rows = this.sql.exec(
      "UPDATE fixed SET title=?,type=?,amount=?,cat=?,method=?,day=?,active=? WHERE id=? RETURNING *",
      title, type, amount, cat, method, day, active, id
    ).toArray();
    if (!rows.length) return { error: "이미 지워진 항목이에요", status: 404 };
    return { fixed: rows[0] };
  }

  saveSettings(b) {
    b = b || {};
    if (b.name !== undefined) {
      const name = cleanText(b.name, 20);
      if (name) this.set("name", name);
    }
    if (Array.isArray(b.categories)) {
      const seen = new Set();
      const cats = [];
      for (const c of b.categories.slice(0, 60)) {
        const id = cleanText(c && c.id, 40);
        const name = cleanText(c && c.name, 12);
        if (!id || !name || seen.has(id)) continue;
        seen.add(id);
        cats.push({ id, name, icon: cleanText(c.icon, 8) || "📦", type: c.type === "in" ? "in" : "out" });
      }
      if (cats.some((c) => c.type === "out") && cats.some((c) => c.type === "in")) this.set("categories", cats);
      else return { error: "지출·수입 분류가 하나씩은 있어야 해요" };
    }
    if (b.budget && typeof b.budget === "object") {
      const total = Math.max(0, Math.min(MAX_AMOUNT, Math.round(Number(b.budget.total) || 0)));
      const cats = {};
      for (const [k, v] of Object.entries(b.budget.cats || {}).slice(0, 60)) {
        const n = Math.round(Number(v) || 0);
        if (n > 0 && n <= MAX_AMOUNT) cats[cleanText(k, 40)] = n;
      }
      this.set("budget", { total, cats });
    }
    return { ok: true, name: this.get("name"), categories: this.get("categories"), budget: this.get("budget") };
  }

  async changePass(b, token) {
    const pass = typeof b?.pass === "string" ? b.pass : "";
    const old = typeof b?.old === "string" ? b.old : "";
    if ((await hashPass(old, this.get("salt"))) !== this.get("hash")) return { error: "지금 암호가 맞지 않아요", status: 403 };
    if (pass.length < 4 || pass.length > 64) return { error: "새 암호는 4자 이상으로 해 주세요" };
    const salt = randomHex(16);
    this.set("salt", salt);
    this.set("hash", await hashPass(pass, salt));
    // 다른 기기는 모두 다시 로그인
    this.sql.exec("DELETE FROM sessions WHERE token<>?", token);
    return { ok: true };
  }
}
