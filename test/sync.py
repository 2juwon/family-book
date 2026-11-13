# 실시간 동기화 시험: python3 test/sync.py (정적 서버 :8080, 로컬 API :8787)
import json, sys, urllib.request, datetime
from playwright.sync_api import sync_playwright
PAGE = "http://localhost:8080/index.html"; API = "http://127.0.0.1:8787"
n = 0
def ok(name, c):
    global n
    if not c: print("✗", name); sys.exit(1)
    n += 1; print("✓", name)
def call(m, path, body=None, tok=None):
    req = urllib.request.Request(API + path, method=m, data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + tok} if tok else {})})
    return json.load(urllib.request.urlopen(req))
today = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=9)).strftime("%Y-%m-%d")
r = call("POST", "/api/family", {"name": "동기화 시험", "pass": "1234", "member": "아빠"})
code, dad = r["code"], r["token"]
mom = call("POST", "/api/join", {"code": code, "pass": "1234", "member": "엄마"})["token"]
pad = call("POST", "/api/join", {"code": code, "pass": "1234", "member": "엄마"})["token"]  # 엄마의 태블릿

with sync_playwright() as p:
    b = p.chromium.launch()
    def open_as(tok, who):
        pg = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True).new_page()
        pg.goto(PAGE); pg.evaluate("a => localStorage.setItem('fb.auth.v1', a)", json.dumps({"token": tok, "code": code, "member": who, "name": ""}))
        pg.goto(PAGE); pg.wait_for_selector(".fab"); pg.wait_for_selector("#livedot.on", timeout=8000)
        return pg
    phone = open_as(mom, "엄마"); tablet = open_as(pad, "엄마")
    ok("두 기기 모두 실시간 연결(초록 점)", True)

    call("POST", "/api/entries", {"date": today, "type": "out", "amount": 7700, "cat": "cafe", "memo": "빵집"}, dad)
    phone.wait_for_selector("text=빵집", timeout=4000); tablet.wait_for_selector("text=빵집", timeout=4000)
    ok("아빠가 적으면 엄마 휴대폰·태블릿에 새로고침 없이 뜸", True)
    ok("알림: 아빠님이 새 기록을 적었어요", "아빠님이 새 기록을 적었어요" in phone.inner_text("#toast"))

    phone.click(".fab"); phone.wait_for_selector(".sheet.show"); phone.fill("#amt", "12000"); phone.fill("#memo", "약국"); phone.click("#save")
    tablet.wait_for_selector("text=약국", timeout=4000)
    ok("엄마 휴대폰에서 적으면 엄마 태블릿에도 뜸", True)
    phone.wait_for_timeout(500)
    ok("적은 기기엔 '다른 기기' 알림 안 뜸", "다른 기기" not in phone.inner_text("#toast"))
    ok("같은 사람 다른 기기 알림 문구", "다른 기기에서 새 기록을 적었어요" in tablet.inner_text("#toast"))

    call("PUT", "/api/settings", {"budget": {"total": 1000000, "cats": {}}}, dad)
    tablet.click("[data-tab='budget']"); tablet.wait_for_selector("text=1,000,000", timeout=4000)
    ok("예산 바꾼 것도 동기화", True)

    # 화면 내려 두면 끊고, 다시 열면 따라잡기
    tablet.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true}); document.dispatchEvent(new Event('visibilitychange'))")
    tablet.wait_for_timeout(300)
    ok("화면 내리면 연결 끊음", tablet.evaluate("!LIVE.ws"))
    call("POST", "/api/entries", {"date": today, "type": "out", "amount": 3000, "cat": "cafe", "memo": "아이스크림"}, dad)
    tablet.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false}); document.dispatchEvent(new Event('visibilitychange'))")
    tablet.click("[data-tab='list']"); tablet.wait_for_selector("text=아이스크림", timeout=5000)
    ok("다시 열면 놓친 기록 따라잡기 + 재연결", True); tablet.wait_for_selector("#livedot.on", timeout=5000)

    # 암호 바꾸면 다른 기기 끊기 → 로그인 화면
    call("PUT", "/api/password", {"old": "1234", "pass": "5678"}, dad)
    phone.wait_for_selector("#startform", timeout=6000)
    ok("암호 바뀌면 다른 기기는 로그인 화면으로", True)
    b.close()
print(f"\n{n}개 통과")
