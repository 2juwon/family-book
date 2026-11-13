# 앱 아이콘 만들기: python3 tools/icons.py  → icon-192.png, icon-512.png(마스커블), apple-touch-icon.png
# 그림: 초록 바탕에 크림색 집(지붕·굴뚝·창문), 집 아래쪽에 손잡이 달린 서랍 하나 — '우리집 서랍'
from PIL import Image, ImageDraw
import os
S = 1024
GREEN, DARK, CREAM, GOLD, GOLD2 = (47, 107, 79), (33, 80, 58), (255, 250, 238), (245, 184, 46), (214, 150, 20)

def draw():
    im = Image.new("RGB", (S, S), GREEN)
    d = ImageDraw.Draw(im)
    cx = S // 2
    d.rectangle([cx + 135, 270, cx + 215, 430], fill=CREAM)                        # 굴뚝
    d.polygon([(cx, 210), (cx - 320, 480), (cx + 320, 480)], fill=CREAM)          # 지붕
    d.rounded_rectangle([cx - 250, 440, cx + 250, 800], 40, fill=CREAM)           # 몸통
    # 창문 (따뜻한 불빛)
    d.rounded_rectangle([cx - 85, 480, cx + 85, 600], 22, fill=GOLD)
    d.line([(cx, 480), (cx, 600)], fill=CREAM, width=14)
    d.line([(cx - 85, 540), (cx + 85, 540)], fill=CREAM, width=14)
    # 서랍
    d.rounded_rectangle([cx - 195, 640, cx + 195, 760], 22, fill=CREAM, outline=DARK, width=16)
    d.rounded_rectangle([cx - 62, 686, cx + 62, 714], 14, fill=DARK)
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
dd.text((474, 410), "가계부 · 주차 위치 · 사진함은 곧", font=font("Bold", 36), fill=GREEN)
og.save(os.path.join(here, "og.png"))
print("og ok")
