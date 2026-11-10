# 브라우저 시험: 로컬 서버(wrangler dev :8787) + 정적 서버(:8080) 켠 뒤  python3 test/e2e.py
import json, urllib.request, datetime, os, sys
from playwright.sync_api import sync_playwright

PAGE = "http://localhost:8080/index.html"
API = "http://127.0.0.1:8787"
OUT = os.environ.get("SHOTS", "/tmp/shots")
os.makedirs(OUT, exist_ok=True)
errors = []
checks = 0

def ok(name, cond):
    global checks
    if not cond:
        print("✗", name); sys.exit(1)
    checks += 1; print("✓", name)

def call(method, path, body=None, token=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    return json.load(urllib.request.urlopen(req))

kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
today = kst.strftime("%Y-%m-%d"); month = today[:7]
def mback(k):
    y, m = int(month[:4]), int(month[5:])
    m -= k
    while m < 1: m += 12; y -= 1
    return f"{y}-{m:02d}"

with sync_playwright() as p:
    b = p.chromium.launch()
    phone = dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale="ko-KR")
    dad = b.new_context(**phone).new_page()
    dad.on("pageerror", lambda e: errors.append(str(e)))
    dad.on("dialog", lambda d: d.accept())
    dad.goto(PAGE)
    dad.screenshot(path=f"{OUT}/01-start.png")
    dad.fill("#f-name", "주원이네 가계부"); dad.fill("#f-pass", "우리집1234"); dad.fill("#f-me", "아빠")
    dad.click("#go")
    dad.wait_for_selector(".fab")
    dad.wait_for_selector("text=아직 기록이 없어요")
    ok("가계부 만들기 → 빈 내역", True)
    auth = dad.evaluate("JSON.parse(localStorage.getItem('fb.auth.v1'))")
    code, token = auth["code"], auth["token"]

    # 화면으로 기록 하나
    dad.click(".fab"); dad.wait_for_selector(".sheet.show")
    dad.fill("#amt", "12500")
    ok("금액 쉼표", dad.input_value("#amt") == "12,500")
    dad.click("[data-plus='10000']")
    ok("+1만 버튼", dad.input_value("#amt") == "22,500")
    dad.click("[data-c='food']"); dad.fill("#memo", "동네 김밥집")
    dad.screenshot(path=f"{OUT}/02-entry-sheet.png")
    dad.click("#save")
    dad.wait_for_selector("text=동네 김밥집")
    ok("화면으로 지출 저장", "22,500" in dad.inner_text(".summary"))

    # 데이터 채우기 (API)
    rows = [("out", 86000, "mart", "카드", "이마트 장보기"), ("out", 4500, "cafe", "카드", "아아"), ("out", 58000, "kid", "카드", "어린이집 준비물"),
            ("out", 32000, "traffic", "카드", "교통카드 충전"), ("out", 150000, "health", "카드", "소아과·약국"), ("in", 3200000, "salary", "이체", "11월 월급"),
            ("out", 45000, "fun", "현금", "키즈카페")]
    for i, (t, a, c, m, memo) in enumerate(rows):
        d = f"{month}-{max(1, int(today[8:]) - i):02d}"
        call("POST", "/api/entries", {"date": d, "type": t, "amount": a, "cat": c, "method": m, "memo": memo}, token)
    for k, (o, inn) in enumerate([(1800000, 3200000), (2100000, 3200000), (1650000, 3400000), (2400000, 3200000), (1950000, 3200000)], start=1):
        mm = mback(k)
        call("POST", "/api/entries", {"date": mm + "-10", "type": "out", "amount": o * 0.6, "cat": "food"}, token)
        call("POST", "/api/entries", {"date": mm + "-12", "type": "out", "amount": o * 0.4, "cat": "mart"}, token)
        call("POST", "/api/entries", {"date": mm + "-25", "type": "in", "amount": inn, "cat": "salary"}, token)

    # 엄마: 초대 링크로 들어가기
    mom = b.new_context(**phone).new_page()
    mom.on("pageerror", lambda e: errors.append(str(e)))
    mom.on("dialog", lambda d: d.accept())
    mom.goto(PAGE + "#join=" + code)
    ok("초대 링크 → 들어가기 탭 + 코드 채움", mom.input_value("#f-code") == code)
    mom.fill("#f-pass", "틀린암호"); mom.fill("#f-me", "엄마"); mom.click("#go")
    mom.wait_for_selector("text=암호가 맞지 않아요")
    ok("틀린 암호 안내", True)
    mom.fill("#f-pass", "우리집1234"); mom.click("#go")
    mom.wait_for_selector("text=이마트 장보기")
    ok("엄마가 아빠 기록을 봄", "동네 김밥집" in mom.inner_text("main"))
    mom.screenshot(path=f"{OUT}/03-list.png", full_page=True)

    # 엄마가 기록 고치기
    mom.click("text=아아"); mom.wait_for_selector(".sheet.show")
    ok("고치기 시트에 적은 사람", "아빠님이 적었어요" in mom.inner_text(".sheet"))
    mom.fill("#amt", "5000"); mom.click("#save")
    mom.wait_for_selector(".row:has-text('아아') >> text=−5,000")
    ok("엄마가 고침", True)

    # 통계
    mom.click("[data-tab='stat']"); mom.wait_for_selector("#trend svg")
    mom.click("#trend rect[data-i='3']")
    ok("6개월 차트 툴팁", mom.is_visible("#tip"))
    mom.screenshot(path=f"{OUT}/04-stat.png", full_page=True)

    # 예산 + 고정
    mom.click("[data-tab='budget']"); mom.click("[data-act='budget']"); mom.wait_for_selector(".sheet.show")
    mom.fill("#amt", "2000000"); mom.fill("[data-bc='food']", "500000"); mom.fill("[data-bc='kid']", "50000")
    mom.click("#save"); mom.wait_for_selector("text=썼어요")
    ok("예산 저장", "2,000,000" in mom.inner_text("main"))
    ok("아이 예산 초과 표시", "넘었어요" in mom.inner_text("main"))
    mom.click("[data-act='addfixed']"); mom.wait_for_selector(".sheet.show")
    mom.fill("#ft", "아파트 관리비"); mom.fill("#amt", "230000"); mom.click("[data-c='house']"); mom.select_option("#fd", "1")
    mom.click("#save"); mom.wait_for_selector("text=아파트 관리비")
    mom.click("[data-act='addfixed']"); mom.wait_for_selector(".sheet.show")
    mom.fill("#ft", "인터넷·휴대폰"); mom.fill("#amt", "89000"); mom.click("[data-c='phone']"); mom.select_option("#fd", "28")
    mom.click("#save"); mom.wait_for_selector("text=인터넷·휴대폰")
    mom.wait_for_timeout(500)
    mom.screenshot(path=f"{OUT}/05-budget.png", full_page=True)
    mom.click("[data-tab='list']"); mom.wait_for_selector("text=아파트 관리비")
    ok("관리비(1일) 이번 달 내역에 자동으로", "고정" in mom.inner_text("main"))

    # 아빠 화면도 새로고침하면 보임
    dad.reload(); dad.wait_for_selector("text=아파트 관리비")
    ok("아빠 화면에도 반영", True)

    # 달 이동
    dad.click("[data-act='prev']"); dad.wait_for_selector("text=이번 달")
    dad.wait_for_selector(".row")
    ok("지난달로 이동", mback(1)[5:].lstrip("0") + "월" in dad.inner_text("header"))
    dad.click("[data-act='thism']")

    # 설정
    dad.click("[data-tab='set']"); dad.wait_for_selector(".code")
    ok("설정: 코드 + 가족 2명", code in dad.inner_text(".code") and "엄마" in dad.inner_text("main"))
    dad.click("[data-act='addcat']"); dad.fill("#ci", "🐶"); dad.fill("#cn", "반려동물"); dad.click(".sheet #save")
    dad.wait_for_selector("text=반려동물")
    ok("분류 추가", True)
    dad.screenshot(path=f"{OUT}/06-settings.png", full_page=True)
    with dad.expect_download() as dl:
        dad.click("[data-act='csv']")
    path = dl.value.path()
    csv = open(path, encoding="utf-8-sig").read()
    ok("CSV 내려받기", csv.startswith("날짜,구분") and "동네 김밥집" in csv)

    # 어두운 화면
    dk = b.new_context(**phone, color_scheme="dark").new_page()
    dk.goto(PAGE); dk.evaluate(f"localStorage.setItem('fb.auth.v1', JSON.stringify({json.dumps(auth)}))")
    dk.reload(); dk.wait_for_selector(".row")
    dk.screenshot(path=f"{OUT}/07-dark-list.png")
    dk.click("[data-tab='stat']"); dk.wait_for_selector("#trend svg")
    dk.screenshot(path=f"{OUT}/08-dark-stat.png", full_page=True)

    # 나가기
    dad.click("[data-act='logout']"); dad.wait_for_selector("#startform")
    ok("나가기", dad.evaluate("localStorage.getItem('fb.auth.v1')") is None)

    # PC 폭
    pc = b.new_context(viewport={"width": 1280, "height": 860}).new_page()
    mom_auth = mom.evaluate("localStorage.getItem('fb.auth.v1')")
    pc.goto(PAGE); pc.evaluate("a => localStorage.setItem('fb.auth.v1', a)", mom_auth)
    pc.reload(); pc.wait_for_selector(".row")
    pc.screenshot(path=f"{OUT}/09-pc.png")
    b.close()

ok("페이지 오류 없음 " + "; ".join(errors), not errors)
print(f"\n{checks}개 통과, 스크린샷: {OUT}")
