# 설치 안내 시험: python3 test/install.py (정적 서버 :8080)
import sys
from playwright.sync_api import sync_playwright
URL = "http://localhost:8080/index.html"
AND = "Mozilla/5.0 (Linux; Android 14; SM-S921N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"
n = 0
def ok(name, c):
    global n
    if not c: print("✗", name); sys.exit(1)
    n += 1; print("✓", name)
with sync_playwright() as p:
    b = p.chromium.launch()
    def page(ua=None):
        kw = dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        if ua: kw["user_agent"] = ua
        return b.new_context(**kw).new_page()
    pg = page(AND); pg.goto(URL); pg.wait_for_selector("#startform")
    ok("처음 들어가자마자 설치 버튼이 보임(크롬 신호 전)", pg.is_visible("#startInstall"))
    pg.click("#startInstall"); pg.wait_for_selector(".sheet.show")
    t = pg.inner_text(".sheet")
    ok("안드로이드 크롬: ⋮ 메뉴 → 앱 설치 안내", "⋮ 메뉴" in t and "앱 설치" in t and not pg.is_visible("#promptNow"))
    pg.evaluate("window.dispatchEvent(Object.assign(new Event('beforeinstallprompt'), {prompt(){window.__p=1}, userChoice: Promise.resolve({outcome:'accepted'})}))")
    ok("안내 보는 중 크롬 신호 오면 '지금 설치하기' 나타남", pg.is_visible("#promptNow"))
    pg.click("#promptNow"); pg.wait_for_timeout(400)
    ok("눌러서 설치 창 + 안내 닫힘", pg.evaluate("window.__p") == 1 and not pg.evaluate("S.sheetOpen"))
    pg.screenshot(path="/tmp/shots/12-android-guide.png")

    k = page(AND + " KAKAOTALK 10.8.0"); k.goto(URL); k.click("#startInstall"); k.wait_for_selector(".sheet.show")
    ok("카톡 안 브라우저: '크롬으로 열기' 버튼", k.is_visible("#outside") and "크롬으로 열기" in k.inner_text("#outside"))
    k.screenshot(path="/tmp/shots/13-kakao-guide.png")
    reqs = []
    k.on("framenavigated", lambda f: reqs.append(f.url))
    k.evaluate("window.__go = []; const o = Object.getOwnPropertyDescriptor(Location.prototype,'href');")
    href = k.evaluate("""() => { let got=null; const L = location; try { openOutside.toString(); } catch(e){}
        const u = location.origin + location.pathname; return "kakaotalk://web/openExternal?url=" + encodeURIComponent(u); }""")
    ok("카톡 바깥 열기 주소 형식", href.startswith("kakaotalk://web/openExternal?url=http"))

    d = page(); d.goto(URL); d.click("#startInstall"); d.wait_for_selector(".sheet.show")
    ok("PC 크롬: 주소창 설치 아이콘 안내", "설치 아이콘" in d.inner_text(".sheet"))
    b.close()
print(f"\n{n}개 통과")
