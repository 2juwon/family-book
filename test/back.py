# 뒤로 버튼 시험: python3 test/back.py (정적 서버 :8080, 로컬 API :8787)
import json, sys, urllib.request
from playwright.sync_api import sync_playwright
PAGE = "http://localhost:8080/index.html"
API = "http://127.0.0.1:8787"
n = 0
def ok(name, c):
    global n
    if not c: print("✗", name); sys.exit(1)
    n += 1; print("✓", name)
req = urllib.request.Request(API + "/api/family", method="POST", data=json.dumps({"name": "뒤로 시험", "pass": "1234", "member": "나"}).encode(), headers={"Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req))
auth = json.dumps({"token": r["token"], "code": r["code"], "member": "나", "name": "뒤로 시험"})

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True).new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: d.accept())
    pg.goto("http://localhost:8080/sw.js")            # '이전 사이트' 역할
    pg.goto(PAGE); pg.evaluate("a => localStorage.setItem('fb.auth.v1', a)", auth)
    pg.goto(PAGE); pg.wait_for_selector(".fab"); pg.wait_for_timeout(300)
    tab = lambda: pg.evaluate("S.tab")
    sheet = lambda: pg.evaluate("S.sheetOpen") or pg.is_visible(".sheet.show")
    back = lambda: (pg.go_back(wait_until="commit") if False else pg.evaluate("history.back()"), pg.wait_for_timeout(350))

    pg.click(".fab"); pg.wait_for_selector(".sheet.show"); back()
    ok("내역: 입력 창 → 뒤로 → 창만 닫힘", not sheet() and tab() == "list" and "index.html" in pg.url)

    pg.click("[data-tab='stat']"); back()
    ok("통계 → 뒤로 → 내역", tab() == "list")

    pg.click("[data-tab='stat']"); pg.click("[data-tab='budget']"); pg.click("[data-tab='set']"); back()
    ok("통계→예산→설정 → 뒤로 한 번에 내역", tab() == "list")

    pg.click("[data-tab='budget']"); pg.click("[data-act='addfixed']"); pg.wait_for_selector(".sheet.show"); back()
    ok("예산: 고정 항목 창 → 뒤로 → 창만 닫히고 예산 그대로", not sheet() and tab() == "budget")
    back()
    ok("예산 → 뒤로 → 내역", tab() == "list")

    pg.click("[data-tab='stat']"); pg.click(".fab"); pg.wait_for_selector(".sheet.show"); pg.click(".sheet [data-close]"); pg.wait_for_timeout(350)
    back()
    ok("✕로 닫은 뒤 뒤로 → 한 번에 내역(빈 칸 없음)", tab() == "list" and not sheet())

    pg.click(".fab"); pg.wait_for_selector(".sheet.show"); pg.fill("#amt", "5000"); pg.click("#save"); pg.wait_for_selector(".row"); pg.wait_for_timeout(350)
    pg.click("[data-tab='set']"); pg.click("[data-tab='list']"); pg.wait_for_timeout(300)
    ok("저장 후·탭 오간 뒤에도 기록 칸 그대로", pg.evaluate("history.state.fb") == "app")

    pg.click("[data-act='budget']") if False else None
    pg.click("[data-tab='set']"); pg.click("[data-act='rename']"); pg.wait_for_selector(".sheet.show"); pg.click(".dim", position={"x": 20, "y": 20}); pg.wait_for_timeout(350)
    ok("바깥 눌러 닫기 → 기록 칸 되돌림", pg.evaluate("history.state.fb") == "tab"); back()

    back()
    ok("내역에서 뒤로 → '한 번 더 누르면 나가요'", "한 번 더" in pg.inner_text("#toast") and "index.html" in pg.url)
    back(); pg.wait_for_timeout(600)
    ok("2초 안에 한 번 더 → 나감", "sw.js" in pg.url)

    # 2초 넘게 기다리면 다시 안내만
    pg.goto(PAGE); pg.wait_for_selector(".fab"); pg.wait_for_timeout(300)
    back(); pg.wait_for_timeout(2200); back()
    ok("2초 지나서 누르면 다시 안내", "index.html" in pg.url)

    # 새로고침 뒤에도
    pg.click("[data-tab='stat']"); pg.reload(); pg.wait_for_selector(".fab"); pg.wait_for_timeout(300)
    pg.click("[data-tab='budget']"); back()
    ok("새로고침 뒤 예산 → 뒤로 → 내역", tab() == "list")
    back(); back(); pg.wait_for_timeout(1500)
    ok("새로고침 뒤에도 두 번 눌러 나감", "index.html" not in pg.url)
    ok("페이지 오류 없음", not errs)
    b.close()
print(f"\n{n}개 통과")
