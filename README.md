# 🏠 우리집 가계부

가족이 함께 쓰는 무료 가계부. 누가 적어도 모두의 휴대폰에 바로 보여요.

- 화면: https://2juwon.github.io/family-book/
- 서버: https://family-book.2juwon.workers.dev (Cloudflare Workers + Durable Objects, 무료 플랜)

## 쓰는 법
1. 한 사람이 **새로 만들기** — 가계부 이름, 가족 암호, 내 호칭(아빠·엄마…)
2. 설정 → **가족 초대하기**에서 링크를 보내고, 가족 암호는 따로 알려 주기
3. 가족은 링크를 열고 암호와 호칭을 넣으면 같은 가계부를 봄

## 기능 (1차)
- 지출·수입 기록: 금액(+1천·+1만… 빠른 버튼), 분류 아이콘, 날짜, 결제(카드·현금·이체), 메모, 적은 사람
- 내역: 달 넘기기, 날짜별 묶음·하루 합계, 지출/수입 거르기, 눌러서 고치기·지우기
- 통계: 분류별 지출·수입(비율, 지난달과 비교), 최근 6개월 지출·수입 막대
- 예산: 한 달 예산·분류별 예산, 남은 돈과 하루에 쓸 수 있는 돈, 80%·100% 넘으면 색과 문구로 알림
- 고정 지출·수입: 매달 n일(말일 넘으면 마지막 날)에 내역에 자동으로 들어감. 지운 자동 기록은 되살아나지 않음. 켜기/끄기
- 설정: 분류 추가·지우기, 가계부 이름, 엑셀용 CSV 내려받기, 가족 암호 바꾸기(다른 기기는 다시 로그인), 이 기기에서 나가기
- 어두운 화면, 휴대폰·PC

## 다음 단계
- 📷 가족 사진함 — 구글 드라이브 같은 저장공간에 연결해 사진 보관·공유

## 구조
- `index.html` — 화면 전체(라이브러리 없음, 글꼴만 Pretendard CDN). 서버 주소는 위쪽 `PROD_API`, `?api=` 로 바꿔 시험 가능
- `server/src/index.js` — Worker(입구) + `Family` Durable Object(가계부 하나 = 코드 하나, SQLite 표: meta·sessions·entries·fixed·fixed_applied)
- 보안: 암호는 PBKDF2(10만 번)로만 저장, 8번 틀리면 10분 잠금, 기기마다 로그인 열쇠(token)
- 시험: `server/test/api.test.mjs`(API 31개), `test/e2e.py`(브라우저 20개)

## 배포
- 화면: 저장소 Settings → Pages → `main` / root
- 서버: `server/`가 바뀌어 `main`에 올라가면 Actions '서버 배포'가 Cloudflare에 올림
  (Secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` — 나일롱뽕과 같은 값)

## 로컬 시험
```
cd server && npm install && npx wrangler dev          # 서버 :8787
python3 -m http.server 8080                             # 화면 (localhost면 로컬 서버로 붙음)
node server/test/api.test.mjs && python3 test/e2e.py
```
