"""Готовит картинки: вырезает фон у фото товаров, делает баннеры, «карту» и QR-код.

Запуск: .venv/bin/python tools/gen_images.py  (после tools/fetch_products.py)
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app.data import PRODUCTS, BANNERS, BY_ID  # noqa: E402

PHOTOS = os.path.join(ROOT, "assets", "photos")
CUT = os.path.join(PHOTOS, "cut")
IMG = os.path.join(ROOT, "assets", "img")


def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cutout(src, dst, size=560):
    """Белый фон -> прозрачный; светлые тени фона становятся полупрозрачной тенью."""
    im = Image.open(src).convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    w, h = im.size
    marker = (255, 0, 255)
    work = im.copy()
    for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)):
        if sum(work.getpixel((x, y))) > 720:
            ImageDraw.floodfill(work, (x, y), marker, thresh=75)
    out = im.convert("RGBA")
    px, pw, po = im.load(), work.load(), out.load()
    for y in range(h):
        for x in range(w):
            if pw[x, y] == marker:
                r, g, b = px[x, y]
                lum = (r + g + b) / 3
                a = int(max(0, min(255, (255 - lum) * 3.2)))
                po[x, y] = (20, 22, 30, a)
    out.save(dst, optimize=True)


def gray_bg(src, dst, size=720):
    """Фото на светло-сером фоне: умножаем на цвет подложки, белое становится серым."""
    im = Image.open(src).convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    tint = Image.new("RGB", im.size, (243, 244, 246))
    from PIL import ImageChops
    ImageChops.multiply(im, tint).save(dst, "JPEG", quality=86)


def banner(b, path, w=600, h=820):
    c1, c2 = hx(b["c1"]), hx(b["c2"])
    img = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)) + (255,))
    # декоративные диагональные полосы
    deco = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    for i, a in ((0, 34), (1, 22), (2, 14)):
        x0 = 120 + i * 150
        dd.polygon([(x0, h), (x0 + 120, h), (x0 + 520, 0), (x0 + 400, 0)], fill=(255, 255, 255, a))
    img.alpha_composite(deco)
    # товар на белом круге-подложке (фото с белым фоном сливается с кругом без артефактов)
    p = {"photos": [b["photo"]]}
    r = 235
    cx, cy = w - 210, h - 250
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((cx - r + 10, cy - r + 26, cx + r + 10, cy + r + 26), fill=(0, 0, 0, 120))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(26)))
    plate = Image.new("RGBA", (2 * r, 2 * r), (255, 255, 255, 255))
    prod = Image.open(os.path.join(PHOTOS, p["photos"][0])).convert("RGB")
    from PIL import ImageChops, ImageOps
    diff = ImageChops.difference(prod, Image.new("RGB", prod.size, (255, 255, 255))).convert("L")
    bbox = diff.point(lambda v: 255 if v > 18 else 0).getbbox()
    if bbox:
        prod = prod.crop(bbox)
    prod = ImageOps.contain(prod, (int(r * 1.3), int(r * 1.3)), Image.LANCZOS)
    plate.paste(prod, (r - prod.width // 2, r - prod.height // 2))
    mask = Image.new("L", (2 * r * 4, 2 * r * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 2 * r * 4 - 1, 2 * r * 4 - 1), fill=255)
    plate.putalpha(mask.resize((2 * r, 2 * r), Image.LANCZOS))
    img.alpha_composite(plate, (cx - r, cy - r))
    img.convert("RGB").save(path, "JPEG", quality=88)


def fake_map(path, w=900, h=360):
    """Стилизованная карта для блока самовывоза."""
    random.seed(4)
    img = Image.new("RGB", (w, h), (246, 244, 238))
    d = ImageDraw.Draw(img)
    d.ellipse((520, -80, 760, 140), fill=(214, 236, 207))
    d.rectangle((60, 220, 220, 330), fill=(214, 236, 207))
    for _ in range(22):
        x1, y1 = random.randint(-100, w), random.randint(-50, h)
        x2, y2 = x1 + random.randint(-300, 300), y1 + random.randint(-200, 200)
        d.line((x1, y1, x2, y2), fill=(220, 220, 225), width=random.choice((2, 3, 4)))
    for pts in (((0, 90), (300, 140), (520, 60), (900, 120)), ((120, 360), (260, 180), (430, 150), (700, 360)),
                ((620, 0), (640, 180), (900, 260))):
        d.line(pts, fill=(250, 214, 120), width=14, joint="curve")
    d.line(((0, 300), (900, 230)), fill=(170, 200, 235), width=16)
    img.save(path, "JPEG", quality=85)


def tinted(src, dst, tint, size=520):
    """Фото на цветной подложке (белый фон умножается на цвет плитки)."""
    from PIL import ImageChops
    im = Image.open(src).convert("RGB")
    im.thumbnail((size, size), Image.LANCZOS)
    ImageChops.multiply(im, Image.new("RGB", im.size, tint)).save(dst, "JPEG", quality=86)


def city_map(path, w=1080, h=1500, seed=7):
    """Нарисованная «городская карта»: парк с озером, кварталы, улицы, точки интереса."""
    random.seed(seed)
    S = 2
    img = Image.new("RGB", (w * S, h * S), (242, 240, 236))
    d = ImageDraw.Draw(img)
    def sc(pts):
        return [(x * S, y * S) for x, y in pts]
    # кварталы
    for _ in range(70):
        x, y = random.randint(-40, w), random.randint(-40, h)
        bw, bh = random.randint(60, 170), random.randint(50, 150)
        d.rounded_rectangle([x * S, y * S, (x + bw) * S, (y + bh) * S], radius=10 * S, fill=(228, 226, 222),
                            outline=(214, 212, 208), width=2 * S)
    # парк
    park = [(180, 330), (760, 260), (930, 520), (880, 1120), (520, 1210), (160, 1050), (110, 640)]
    d.polygon(sc(park), fill=(198, 232, 182))
    for _ in range(18):
        a, b = random.choice(park), random.choice(park)
        d.line(sc([a, ((a[0] + b[0]) / 2 + random.randint(-80, 80), (a[1] + b[1]) / 2 + random.randint(-80, 80)), b]),
               fill=(236, 240, 228), width=4 * S, joint="curve")
    d.ellipse([300 * S, 560 * S, 760 * S, 960 * S], fill=(164, 210, 240), outline=(140, 190, 225), width=3 * S)
    # улицы
    for pts, wd, col in ((((0, 300), (1080, 120)), 34, (255, 226, 150)), (((0, 1260), (1080, 1180)), 26, (255, 255, 255)),
                         (((980, 0), (900, 700), (1000, 1500)), 26, (255, 255, 255)),
                         (((60, 0), (120, 700), (40, 1500)), 22, (255, 255, 255)),
                         (((0, 900), (140, 880)), 16, (255, 255, 255))):
        d.line(sc(pts), fill=(220, 218, 214), width=(wd + 6) * S, joint="curve")
        d.line(sc(pts), fill=col, width=wd * S, joint="curve")
    # точки интереса
    for (x, y, c) in ((640, 470, (240, 140, 60)), (860, 1290, (236, 90, 120)), (150, 250, (120, 110, 220)),
                      (900, 330, (60, 160, 120)), (420, 160, (240, 140, 60))):
        d.ellipse([(x - 16) * S, (y - 16) * S, (x + 16) * S, (y + 16) * S], fill=c, outline=(255, 255, 255), width=4 * S)
    img.resize((w, h), Image.LANCZOS).save(path, "JPEG", quality=86)


def grid_map(path, w=1080, h=500):
    """Схема рядом с магазином: сетка улиц."""
    img = Image.new("RGB", (w, h), (246, 245, 241))
    d = ImageDraw.Draw(img)
    for x in range(0, w, 46):
        d.line([(x, 0), (x, h)], fill=(232, 230, 226), width=2)
    for y in range(0, h, 46):
        d.line([(0, y), (w, y)], fill=(232, 230, 226), width=2)
    d.rectangle((300, 90, 820, 400), fill=(236, 233, 228), outline=(222, 219, 214), width=3)
    d.line([(0, 470), (w, 440)], fill=(255, 255, 255), width=22)
    d.line([(120, 0), (90, h)], fill=(255, 255, 255), width=18)
    img.save(path, "JPEG", quality=86)


TILES = {
    "women": "extra/women.jpg", "men": "extra/men.jpg", "kids": "extra/kids.jpg", "clothes": "p9_0.jpg",
    "shoes": "p2_0.jpg", "acc": "p24_0.jpg", "fitness": "extra/water.jpg", "run": "p1_0.jpg", "swim": "p25_0.jpg",
    "fight": "p19_0.jpg", "football": "p12_0.jpg", "tennis": "p18_0.jpg", "nutrition": "extra/protein.jpg",
    "electronics": "extra/watch.jpg", "esport": "p26_0.jpg", "hiking": "p24_1.jpg", "ice": "p21_0.jpg",
    "basket": "p13_0.jpg", "volley": "p14_0.jpg", "style": "p4_0.jpg", "premium": "p27_0.jpg", "abroad": "p3_0.jpg",
    "new": "p7_0.jpg", "sport": "p16_0.jpg", "brands": "p5_0.jpg", "sale": "p11_0.jpg", "gift": "p20_0.jpg",
    "service": "p8_0.jpg", "best": "p10_0.jpg", "warm": "p6_0.jpg",
}


def main():
    os.makedirs(CUT, exist_ok=True)
    os.makedirs(IMG, exist_ok=True)
    gray = os.path.join(PHOTOS, "gray")
    os.makedirs(gray, exist_ok=True)
    done = set()
    for p in PRODUCTS:
        for fn in p["photos"]:
            if fn in done or fn.startswith("gift/"):
                continue
            done.add(fn)
            os.makedirs(os.path.dirname(os.path.join(gray, fn)), exist_ok=True)
            gray_bg(os.path.join(PHOTOS, fn), os.path.join(gray, fn))
    for i, b in enumerate(BANNERS):
        banner(b, os.path.join(IMG, f"banner{i}.jpg"))
    fake_map(os.path.join(IMG, "map.jpg"))
    city_map(os.path.join(IMG, "city_map.jpg"))
    grid_map(os.path.join(IMG, "store_map.jpg"))
    from app.catalog_db import gift_images
    gift_images(os.path.join(PHOTOS, "gift"))
    tiles = os.path.join(PHOTOS, "tiles")
    os.makedirs(tiles, exist_ok=True)
    for key, fn in TILES.items():
        tinted(os.path.join(PHOTOS, fn), os.path.join(tiles, key + ".jpg"), (226, 231, 253))
    import qrcode
    qrcode.make("SPORTLY-CARD-2990-4471-0035", box_size=12, border=1).convert("RGBA").save(os.path.join(IMG, "qr.png"))
    print("ok")


if __name__ == "__main__":
    main()
