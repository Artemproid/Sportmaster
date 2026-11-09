"""Скачивает фото товаров из открытого демо-API dummyjson.com и пишет app/catalog.json.

Фото — демонстрационные данные сервиса dummyjson (для учебных/тестовых проектов).
"""
import io
import json
import os
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "photos")
API = "https://dummyjson.com/products/{}"

# id из dummyjson -> (категория, русское название, цена, старая цена или None, бренд для показа)
ITEMS = {
    88: ("shoes", "Кроссовки мужские Nike Air Jordan 1", 15999, 18999, "Nike"),
    90: ("shoes", "Кроссовки мужские Puma Future Rider", 8999, None, "Puma"),
    91: ("shoes", "Кеды мужские Off White Sport", 12499, 14999, "Off White"),
    92: ("shoes", "Кроссовки Off White Red Line", 11999, None, "Off White"),
    89: ("shoes", "Бутсы бейсбольные Nike Cleats", 6999, 8499, "Nike"),
    189: ("shoes", "Туфли женские Red Step", 4599, None, "Fashion Express"),
    84: ("clothes", "Футболка мужская Aorus", 1999, 2499, "Gigabyte"),
    86: ("clothes", "Рубашка мужская с коротким рукавом", 2799, None, "Casual Comfort"),
    83: ("clothes", "Рубашка в клетку Blue & Black", 3299, 3999, "Fashion Trends"),
    85: ("clothes", "Рубашка мужская Plaid", 2999, None, "Classic Wear"),
    87: ("clothes", "Рубашка мужская Check", 3499, 4299, "Urban Chic"),
    147: ("balls", "Мяч футбольный Classic", 1999, 2499, "Stridex"),
    140: ("balls", "Мяч баскетбольный Street", 2499, None, "Stridex"),
    153: ("balls", "Мяч волейбольный Beach", 1799, 2199, "Aerona"),
    137: ("balls", "Мяч для американского футбола", 2299, None, "Kinetra"),
    151: ("balls", "Мячи теннисные, 3 шт", 599, 799, "Velaro"),
    138: ("balls", "Мяч бейсбольный", 499, None, "Kinetra"),
    152: ("gear", "Ракетка теннисная Pro Tour", 7499, 8999, "Velaro"),
    139: ("gear", "Перчатка бейсбольная", 3999, None, "Kinetra"),
    146: ("gear", "Воланы перьевые, 6 шт", 899, 1099, "Aerona"),
    144: ("gear", "Шлем защитный для крикета", 5499, None, "Polarfox"),
    150: ("gear", "Бита бейсбольная металлическая", 3299, 3799, "Kinetra"),
    141: ("gear", "Кольцо баскетбольное с сеткой", 4299, None, "Stridex"),
    175: ("acc", "Рюкзак городской белый", 4999, 5999, "Urban Chic"),
    154: ("acc", "Очки солнцезащитные Black", 1999, None, "Fashion Shades"),
    158: ("acc", "Очки спортивные Sunglasses", 2499, 2999, "Fashion Shades"),
    93: ("acc", "Часы с кожаным ремешком", 6999, None, "Fashion Timepieces"),
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "sportly-study-app/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def save_photo(data, path):
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    im = bg.convert("RGB")
    im.thumbnail((720, 720), Image.LANCZOS)
    # квадратный холст со светло-серым фоном, как у карточек
    side = max(im.size)
    canvas = Image.new("RGB", (side, side), (255, 255, 255))
    canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    canvas.save(path, "JPEG", quality=86)


# дополнительные фото для плиток каталога (только картинки, без товаров)
EXTRA = {"women": 163, "men": 86, "kids": 165, "watch": 106, "protein": 36, "water": 42, "dress2": 164}


def fetch_extra():
    out = os.path.join(OUT, "extra")
    os.makedirs(out, exist_ok=True)
    for key, pid in EXTRA.items():
        path = os.path.join(out, key + ".jpg")
        if not os.path.exists(path):
            info = json.loads(get(API.format(pid)))
            save_photo(get(info["images"][0].replace(" ", "%20")), path)
        print("extra", key)


# ещё фото для полного каталога: ключ -> id в dummyjson (берём все ракурсы)
MORE = {"airpods": 100, "airmax": 101, "beats": 107, "wwatch": 194, "wwatch2": 193, "frock": 162, "sdress": 163,
        "shortfrock": 165, "tartan": 166, "bag_blue": 172, "bag_black": 176, "bag_heshe": 173, "slipper": 185,
        "pampi": 188, "golden": 187, "juice": 29, "watch_lng": 94}


def fetch_more():
    out = os.path.join(OUT, "more")
    os.makedirs(out, exist_ok=True)
    for key, pid in MORE.items():
        info = json.loads(get(API.format(pid)))
        for i, url in enumerate(info["images"][:3]):
            path = os.path.join(out, f"{key}_{i}.jpg")
            if not os.path.exists(path):
                save_photo(get(url.replace(" ", "%20")), path)
        print("more", key, len(info["images"][:3]))


def main():
    os.makedirs(OUT, exist_ok=True)
    catalog = []
    for n, (pid, (cat, name, price, old, brand)) in enumerate(ITEMS.items(), start=1):
        info = json.loads(get(API.format(pid)))
        photos = []
        for i, url in enumerate(info["images"][:4]):
            fn = f"p{n}_{i}.jpg"
            path = os.path.join(OUT, fn)
            if not os.path.exists(path):
                save_photo(get(url.replace(" ", "%20")), path)
            photos.append(fn)
        catalog.append({"id": n, "cat": cat, "name": name, "price": price, "old_price": old, "brand": brand,
                        "rating": round(float(info.get("rating", 4.5)), 1),
                        "reviews": 10 + (pid * 37) % 400, "photos": photos})
        print(n, name, len(photos))
    with open(os.path.join(ROOT, "app", "catalog.json"), "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    import sys
    if "--extra" in sys.argv:
        fetch_extra()
    elif "--more" in sys.argv:
        fetch_more()
    else:
        main()
