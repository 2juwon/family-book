# 앱 아이콘 만들기: python3 tools/icons.py  → icon-192.png, icon-512.png(마스커블), apple-touch-icon.png
# 그림: 초록 바탕에 지붕 달린 서랍장(우리집 서랍), 가운데 서랍이 살짝 열려 금화가 보임
from PIL import Image, ImageDraw
import os
S = 1024
GREEN, DARK, CREAM, SHADE, GOLD, GOLD2 = (47, 107, 79), (33, 80, 58), (255, 250, 238), (226, 218, 198), (245, 184, 46), (214, 150, 20)

def draw():
    im = Image.new("RGB", (S, S), GREEN)
    d = ImageDraw.Draw(im)
    cx = S // 2
    L, R = cx - 250, cx + 250
    d.polygon([(cx, 215), (L - 45, 385), (R + 45, 385)], fill=CREAM)              # 지붕
    d.rounded_rectangle([L, 360, R, 805], 30, fill=CREAM)                          # 몸통
    d.rectangle([L + 30, 805, L + 80, 840], fill=CREAM); d.rectangle([R - 80, 805, R - 30, 840], fill=CREAM)  # 다리
    def drawer(y0, y1, dx=0, dy=0):
        d.rounded_rectangle([L + 34 + dx, y0 + dy, R - 34 + dx, y1 + dy], 18, fill=CREAM, outline=DARK, width=12)
        hy = (y0 + y1) // 2 + dy
        d.rounded_rectangle([cx - 55 + dx, hy - 13, cx + 55 + dx, hy + 13], 13, fill=DARK)
    drawer(400, 525)
    # 가운데 서랍: 앞으로 빠져나온 느낌(조금 크게, 아래로) + 안에서 금화
    d.rectangle([L + 34, 540, R - 34, 600], fill=SHADE)
    r = 50
    for ox in (cx - 90, cx + 5, cx + 100):
        d.ellipse([ox - r, 568 - r + 8, ox + r, 568 + r + 8], fill=GOLD2)
        d.ellipse([ox - r, 568 - r, ox + r, 568 + r], fill=GOLD)
        d.ellipse([ox - r + 14, 568 - r + 12, ox + r - 12, 568 + r - 12], outline=GOLD2, width=6)
    d.rounded_rectangle([L + 6, 590, R - 6, 700], 18, fill=CREAM, outline=DARK, width=12)
    d.rounded_rectangle([cx - 60, 631, cx + 60, 659], 14, fill=DARK)
    drawer(715, 795)
    return im

base = draw()
here = os.path.join(os.path.dirname(__file__), "..")
base.resize((512, 512), Image.LANCZOS).save(os.path.join(here, "icon-512.png"))
base.resize((192, 192), Image.LANCZOS).save(os.path.join(here, "icon-192.png"))
base.resize((180, 180), Image.LANCZOS).save(os.path.join(here, "apple-touch-icon.png"))
print("ok")

# 링크 미리보기 그림 og.png (1200x630)
from PIL import ImageFont
og = Image.new("RGB", (1200, 630), (246, 244, 239))
icon = base.resize((300, 300), Image.LANCZOS)
mask = Image.new("L", (300, 300), 0); ImageDraw.Draw(mask).rounded_rectangle([0, 0, 299, 299], 70, fill=255)
og.paste(icon, (110, 165), mask)
dd = ImageDraw.Draw(og)
def font(w, size):
    for p in [f"/usr/share/fonts/opentype/noto/NotoSansCJK-{w}.ttc"]:
        if os.path.exists(p): return ImageFont.truetype(p, size, index=1)  # index 1 = KR
    return ImageFont.load_default()
dd.text((470, 200), "우리집 서랍", font=font("Black", 104), fill=(29, 28, 26))
dd.text((474, 345), "가족이 함께 쓰는 우리집 서랍", font=font("Bold", 44), fill=(93, 90, 84))
dd.text((474, 410), "가계부부터 · 사진함 · 주차 위치는 곧", font=font("Bold", 36), fill=GREEN)
og.save(os.path.join(here, "og.png"))
print("og ok")
