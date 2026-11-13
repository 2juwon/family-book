# 주차 시험: python3 test/park.py (정적 서버 :8080, 로컬 API :8787)
import json, sys, urllib.request
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
r = call("POST", "/api/family", {"name": "주원이네", "pass": "1234", "member": "아빠"}); code, dad = r["code"], r["token"]
mom = call("POST", "/api/join", {"code": code, "pass": "1234", "member": "엄마"})["token"]
with sync_playwright() as p:
    b = p.chromium.launch()
    def open_as(tok, who, dark=False):
        pg = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, color_scheme="dark" if dark else "light").new_page()
        pg.on("dialog", lambda d: d.accept()); pg.on("pageerror", lambda e: print("ERR", e))
        pg.goto(PAGE); pg.evaluate("a => localStorage.setItem('fb.auth.v1', a)", json.dumps({"token": tok, "code": code, "member": who, "name": ""}))
        pg.goto(PAGE); pg.wait_for_selector(".fab"); pg.wait_for_selector("#livedot.on", timeout=8000); return pg
    a = open_as(dad, "아빠"); m = open_as(mom, "엄마")
    a.click("[data-tab='park']"); a.wait_for_selector("text=주차 위치가 없어요")
    ok("주차 탭: 빈 상태, 달 넘기기·+ 버튼 없음", not a.is_visible(".monthbar") and not a.is_visible(".fab"))
    a.screenshot(path="/tmp/shots/p1-empty.png")
    a.click("[data-act='parkset']"); a.wait_for_selector(".sheet.show")
    a.click("#save"); ok("자리 안 누르면 안내", "자리를 눌러" in a.inner_text("#err"))
    a.click("[data-pl='회사']"); a.fill("#pnew", "아파트")
    a.click("[data-fl='B3']"); a.click("#pmap [data-zone='D2']")
    a.fill("#ppillar", "D-21"); a.fill("#pmemo", "엘베 오른쪽")
    a.wait_for_timeout(500); a.screenshot(path="/tmp/shots/p2-sheet.png", full_page=False)
    a.click("#save"); a.wait_for_selector(".fbadge")
    ok("남기면 카드에 B3 · D구역 2줄 · 기둥", "B3" in a.inner_text(".fbadge") and "D구역 2줄" in a.inner_text("main") and "D-21" in a.inner_text("main"))
    a.wait_for_timeout(600); a.screenshot(path="/tmp/shots/p3-card.png")
    m.wait_for_selector("text=주차 위치를 남겼어요", timeout=4000)
    ok("엄마 휴대폰에 '아빠님이 주차 위치를 남겼어요' 알림", "아빠님이 주차 위치를 남겼어요" in m.inner_text("#toast"))
    m.click("[data-tab='park']"); m.wait_for_selector(".fbadge")
    ok("엄마 화면에도 같은 위치 + 아빠·방금", "D구역 2줄" in m.inner_text("main") and "아빠" in m.inner_text(".pmeta") and "방금" in m.inner_text(".pmeta"))
    # 두 번째 차
    m.click("[data-act='carmenu']"); m.fill("#cnew", "엄마 차"); m.click("#cadd"); m.wait_for_selector("text=엄마 차 주차 위치가 없어요")
    ok("차 추가 → 새 차 선택", True)
    m.click("[data-act='parkset']"); m.wait_for_selector(".sheet.show")
    ok("다시 열면 최근 장소·층 기억", m.evaluate("document.querySelector('[data-pl].on').textContent") == "아파트" and "on" in m.get_attribute("[data-fl='B3']", "class"))
    m.click("[data-fl='1F']"); m.click("#pmap [data-zone='A4']"); m.click("#save"); m.wait_for_selector(".fbadge")
    ok("엄마 차 1F A4", "1F" in m.inner_text(".fbadge"))
    ok("차 칩에 층 표시", "B3" in m.inner_text(".chips") and "1F" in m.inner_text(".chips"))
    # 뒤로 버튼: 시트 → 닫기, 주차 → 내역
    m.click("[data-act='parkset']"); m.wait_for_selector(".sheet.show"); m.evaluate("history.back()"); m.wait_for_timeout(400)
    ok("주차 시트 뒤로 → 닫힘", not m.evaluate("S.sheetOpen") and m.evaluate("S.tab") == "park")
    m.evaluate("history.back()"); m.wait_for_timeout(400); ok("주차 탭 뒤로 → 내역", m.evaluate("S.tab") == "list")
    # 출차
    a.click("[data-act='parkout']"); a.wait_for_selector("text=주차 위치가 없어요")
    ok("출차 → 위치 지움", True)
    d = open_as(mom, "엄마", dark=True); d.click("[data-tab='park']"); d.click("[data-car]:nth-child(2)"); d.wait_for_selector(".fbadge"); d.wait_for_timeout(600)
    d.screenshot(path="/tmp/shots/p4-dark.png")
    b.close()
print(f"\n{n}개 통과")
