# 앱 설치 조건 시험: python3 test/pwa.py (정적 서버 :8080, 로컬 API :8787)
import sys
from playwright.sync_api import sync_playwright
URL = "http://localhost:8080/index.html"
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1500)
    sw = pg.evaluate("navigator.serviceWorker.ready.then(r => r.active && r.active.state)")
    print("서비스 워커:", sw)
    cdp = ctx.new_cdp_session(pg)
    m = cdp.send("Page.getAppManifest")
    print("manifest 오류:", m.get("errors"))
    inst = cdp.send("Page.getInstallabilityErrors")
    print("설치 조건 오류:", inst.get("installabilityErrors"))
    # 시작 화면 설치 버튼: beforeinstallprompt 흉내
    pg.evaluate("window.dispatchEvent(Object.assign(new Event('beforeinstallprompt'), {prompt(){window.__p=1}, userChoice: Promise.resolve({outcome:'accepted'})}))")
    pg.fill("#f-me", "아빠")
    pg.evaluate("window.dispatchEvent(Object.assign(new Event('beforeinstallprompt'), {prompt(){window.__p=1}, userChoice: Promise.resolve({outcome:'accepted'})}))")
    vis = pg.is_visible("#startInstall"); kept = pg.input_value("#f-me") == "아빠"
    print("설치 버튼 보임:", vis, "/ 입력 유지:", kept)
    pg.click("#startInstall"); pg.wait_for_timeout(300)
    print("설치 창 호출:", pg.evaluate("window.__p") == 1)
    pg.screenshot(path="/tmp/shots/10-start-install.png")
    # 인터넷 끊고 다시 열기
    ctx.set_offline(True)
    pg.reload(); pg.wait_for_selector("h1")
    off = pg.inner_text("h1")
    print("끊긴 상태로 열림:", off)
    # 아이폰 안내
    ip = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1").new_page()
    ip.goto(URL); ip.click("#startInstall"); ip.wait_for_selector(".sheet.show"); ip.wait_for_timeout(300)
    ip.screenshot(path="/tmp/shots/11-ios-guide.png")
    print("아이폰 안내:", "홈 화면에 추가" in ip.inner_text(".sheet"))
    ok = sw == "activated" and not m.get("errors") and not inst.get("installabilityErrors") and vis and kept and off == "우리집 서랍" and not errs
    print("페이지 오류:", errs)
    print("통과" if ok else "실패"); b.close(); sys.exit(0 if ok else 1)
