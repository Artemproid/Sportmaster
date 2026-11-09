"""Каталог товаров с атрибутами: из него работают категории, поиск, фильтр и сортировка.

Каждый товар описан набором атрибутов (вид, пол, бренд, цвет, сезон, размеры и т. д.).
Товары собираются из «шаблонов» (одно фото — один шаблон) с несколькими вариантами
(бренд, пол, модель, цена). Все данные локальные, сервер не нужен.
"""
import os

SHOE_SIZES = [("38", "24.8 см"), ("39", "25.5 см"), ("40", "26.2 см"), ("41", "26.7 см"), ("41.5", "27.1 см"),
              ("42", "27.5 см"), ("43", "28.2 см"), ("44", "28.8 см"), ("45", "29.5 см")]
CLOTH_SIZES = [("44", "XS"), ("46", "S"), ("48", "M"), ("50", "L"), ("52", "XL"), ("54", "XXL")]
KID_CLOTH = [("110", "4-5 лет"), ("122", "6-7 лет"), ("134", "8-9 лет"), ("146", "10-11 лет")]
KID_SHOES = [("30", "19.0 см"), ("32", "20.3 см"), ("34", "21.6 см"), ("35", "22.3 см")]
BALL5 = [("4", ""), ("5", "")]
BALL7 = [("5", ""), ("6", ""), ("7", "")]

OWN_BRANDS = {"Stridex", "Kinetra", "Aerona", "Velaro", "Polarfox"}     # «Товары SPORTLY»
FOREIGN = {"Nike", "Puma", "Off White", "Fashion Shades", "Urban Chic", "Classic Wear", "Heshe", "Longines"}

# прилагательные пола для названий: kind -> (муж, жен, дет, без пола)
FORMS = {
    "Кроссовки": ("мужские", "женские", "детские", ""), "Кеды": ("мужские", "женские", "детские", ""),
    "Бутсы": ("мужские", "женские", "детские", ""), "Туфли": ("", "женские", "", ""),
    "Футболка": ("мужская", "женская", "детская", ""), "Рубашка": ("мужская", "женская", "детская", ""),
    "Платье": ("", "женское", "для девочек", ""), "Сумка": ("", "женская", "", ""),
    "Часы": ("мужские", "женские", "", ""), "Рюкзак": ("", "", "детский", "городской"),
}
GENDER = {0: "Мужской", 1: "Женский", 2: "Детский", 3: "Унисекс"}
MODELS = ["Swift", "Pulse", "Ridge", "Nova", "Flow", "Core", "Aero", "Peak", "Drift", "Rush", "Vector", "Orbit"]


def T(photos, kind, cat, sections, color, genders=(3,), brands=("Stridex",), price=(1000, 2000), sport="",
      season="Всесезонный", material="", clasp="", sizes=None, name=None, variants=None, desc=None):
    return dict(photos=photos, kind=kind, cat=cat, sections=set(sections), color=color, genders=genders, brands=brands,
                price=price, sport=sport, season=season, material=material, clasp=clasp, sizes=sizes, name=name,
                variants=variants or len(brands), desc=desc)


def ph(base, n):
    return [f"{base}_{i}.jpg" for i in range(n)]


TEMPLATES = [
    # ---------------- обувь
    T(ph("p1", 4), "Кроссовки", "shoes", {"shoes", "style", "basket"}, "Красный", (0, 1), ("Nike", "Stridex", "Kinetra"),
      (9000, 16000), "Баскетбол", "Демисезон", "Натуральная кожа", "Шнуровка"),
    T(ph("p2", 4), "Кроссовки", "shoes", {"shoes", "run"}, "Голубой", (0, 1, 2), ("Puma", "Aerona", "Velaro"),
      (5000, 9000), "Бег", "Лето", "Нейлон", "Быстрая шнуровка"),
    T(ph("p3", 4), "Кеды", "shoes", {"shoes", "style"}, "Белый", (0, 1), ("Off White", "Stridex"),
      (8000, 15000), "", "Демисезон", "Искусственная кожа", "Шнуровка"),
    T(ph("p4", 4), "Кроссовки", "shoes", {"shoes", "run", "style"}, "Белый", (0, 1, 2), ("Off White", "Kinetra", "Polarfox"),
      (6000, 12500), "Бег", "Всесезонный", "Натуральная кожа", "Шнуровка"),
    T(ph("p5", 4), "Бутсы", "shoes", {"shoes", "football"}, "Белый", (0, 2), ("Nike", "Stridex"),
      (4000, 8500), "Футбол", "Лето", "Искусственная кожа", "Шнуровка"),
    T(ph("p6", 4), "Туфли", "shoes", {"shoes", "style"}, "Красный", (1,), ("Velaro",), (3500, 6000), "", "Лето",
      "Натуральная кожа", "Без застежки"),
    T(ph("more/pampi", 3), "Туфли", "shoes", {"shoes", "style"}, "Черный", (1,), ("Aerona",), (4000, 6500), "",
      "Демисезон", "Натуральная кожа", "Без застежки"),
    T(ph("more/golden", 3), "Туфли", "shoes", {"shoes", "style", "premium"}, "Бежевый", (1,), ("Polarfox",),
      (11000, 14000), "", "Лето", "Натуральная кожа", "Без застежки"),
    # ---------------- одежда
    T(ph("p7", 4), "Футболка", "clothes", {"clothes", "fitness", "run"}, "Белый", (0, 1, 2), ("Stridex", "Kinetra", "Aerona"),
      (900, 2500), "Бег", "Лето"),
    T(ph("p8", 4), "Рубашка", "clothes", {"clothes", "style"}, "Голубой", (0,), ("Urban Chic", "Velaro"), (2200, 3500),
      "", "Лето"),
    T(ph("p9", 4), "Рубашка", "clothes", {"clothes", "style"}, "Синий", (0, 1), ("Classic Wear", "Kinetra"), (2500, 4200),
      "", "Демисезон"),
    T(ph("p10", 4), "Рубашка", "clothes", {"clothes", "style", "hiking"}, "Красный", (0, 2), ("Polarfox", "Classic Wear"),
      (2300, 3900), "Туризм", "Демисезон"),
    T(ph("p11", 4), "Рубашка", "clothes", {"clothes", "hiking"}, "Бирюзовый", (0,), ("Polarfox", "Urban Chic"),
      (2700, 4300), "Туризм", "Демисезон"),
    T(ph("more/sdress", 3), "Платье", "clothes", {"clothes", "style"}, "Черный", (1,), ("Velaro",), (3500, 5200), "", "Лето"),
    T(ph("more/frock", 3), "Платье", "clothes", {"clothes", "style"}, "Голубой", (1, 2), ("Aerona",), (2200, 4200), "", "Лето"),
    T(ph("more/shortfrock", 3), "Платье", "clothes", {"clothes", "style"}, "Бирюзовый", (1, 2), ("Velaro",), (2600, 4500),
      "", "Лето"),
    T(ph("more/tartan", 3), "Платье", "clothes", {"clothes", "style"}, "Белый", (2,), ("Kinetra",), (1900, 2900), "",
      "Демисезон"),
    # ---------------- мячи
    T(ph("p12", 1), "Мяч", "balls", {"football", "balls"}, "Белый", (3,), ("Stridex", "Nike", "Kinetra"), (1500, 4500),
      "Футбол", sizes=BALL5, name="Мяч футбольный"),
    T(ph("p13", 1), "Мяч", "balls", {"basket", "balls"}, "Оранжевый", (3,), ("Stridex", "Puma"), (1900, 3900), "Баскетбол",
      sizes=BALL7, name="Мяч баскетбольный"),
    T(ph("p14", 1), "Мяч", "balls", {"balls", "volley"}, "Голубой", (3,), ("Aerona", "Kinetra"), (1400, 2900), "Волейбол",
      sizes=BALL5, name="Мяч волейбольный"),
    T(ph("p15", 1), "Мяч", "balls", {"balls"}, "Коричневый", (3,), ("Kinetra",), (1900, 2600), "Регби",
      name="Мяч для американского футбола"),
    T(ph("p16", 1), "Мячи", "balls", {"tennis", "balls"}, "Желтый", (3,), ("Velaro", "Aerona"), (450, 900), "Теннис",
      name="Мячи теннисные, 3 шт"),
    T(ph("p17", 1), "Мяч", "balls", {"balls", "baseball"}, "Белый", (3,), ("Kinetra",), (400, 700), "Бейсбол",
      name="Мяч бейсбольный"),
    # ---------------- инвентарь
    T(ph("p18", 1), "Ракетка", "gear", {"tennis"}, "Красный", (3,), ("Velaro", "Aerona", "Nike"), (3500, 12000), "Теннис",
      name="Ракетка для большого тенниса"),
    T(ph("p20", 1), "Воланы", "gear", {"tennis"}, "Белый", (3,), ("Aerona",), (600, 1100), "Бадминтон",
      name="Воланы для бадминтона, 6 шт"),
    T(ph("p19", 3), "Перчатка", "gear", {"baseball"}, "Коричневый", (3,), ("Kinetra",), (2900, 4900), "Бейсбол",
      name="Перчатка бейсбольная"),
    T(ph("p22", 1), "Бита", "gear", {"baseball"}, "Серый", (3,), ("Kinetra", "Stridex"), (2500, 3900), "Бейсбол",
      name="Бита бейсбольная"),
    T(ph("p21", 4), "Шлем", "gear", {"ice"}, "Голубой", (3,), ("Polarfox", "Stridex"), (4500, 7900), "Хоккей",
      name="Шлем защитный с решеткой", sizes=[("S", ""), ("M", ""), ("L", "")]),
    T(ph("p23", 1), "Кольцо", "gear", {"basket"}, "Оранжевый", (3,), ("Stridex",), (3900, 5200), "Баскетбол",
      name="Кольцо баскетбольное с сеткой"),
    # ---------------- аксессуары
    T(ph("p24", 3), "Рюкзак", "acc", {"acc", "hiking", "style"}, "Белый", (3, 2), ("Urban Chic", "Polarfox"), (2900, 6500),
      "Туризм"),
    T(ph("more/bag_blue", 3), "Сумка", "acc", {"acc", "style"}, "Синий", (1,), ("Velaro",), (3900, 5900)),
    T(ph("more/bag_black", 3), "Сумка", "acc", {"acc", "style"}, "Черный", (1,), ("Aerona",), (4200, 6200)),
    T(ph("more/bag_heshe", 3), "Сумка", "acc", {"acc", "style", "premium"}, "Коричневый", (1,), ("Heshe",), (9900, 13500)),
    T(ph("p25", 3), "Очки", "acc", {"acc", "style", "hiking"}, "Черный", (3,), ("Fashion Shades", "Velaro"), (1500, 3200),
      "Туризм", "Лето", name="Очки солнцезащитные"),
    T(ph("p26", 3), "Очки", "acc", {"acc", "swim", "run"}, "Белый", (3,), ("Fashion Shades", "Aerona"), (1900, 3600),
      "Бег", "Лето", name="Очки спортивные"),
    T(ph("p27", 3), "Часы", "acc", {"acc", "premium"}, "Коричневый", (0,), ("Longines",), (25000, 39000)),
    T(ph("more/wwatch", 3), "Часы", "acc", {"acc", "style"}, "Серый", (0, 1), ("Polarfox",), (6900, 11900)),
    T(ph("more/wwatch2", 3), "Часы", "acc", {"acc", "style", "premium"}, "Бежевый", (1,), ("Velaro",), (10900, 15900)),
    T(ph("more/watch_lng", 3), "Часы", "acc", {"acc", "premium"}, "Серый", (0,), ("Longines",), (32000, 45000)),
    # ---------------- электроника и питание
    T(["extra/watch.jpg"], "Смарт-часы", "electronics", {"electronics", "run", "fitness"}, "Бежевый", (3,),
      ("Kinetra", "Stridex"), (9900, 24900), "Бег", name="Смарт-часы спортивные"),
    T(ph("more/airpods", 3), "Наушники", "electronics", {"electronics", "run", "esport"}, "Белый", (3,), ("Kinetra", "Aerona"),
      (4900, 14900), "Бег", name="Наушники беспроводные"),
    T(ph("more/airmax", 1), "Наушники", "electronics", {"electronics", "esport"}, "Серый", (3,), ("Kinetra",), (19900, 34900),
      "", name="Наушники полноразмерные"),
    T(ph("more/beats", 1), "Наушники", "electronics", {"electronics", "run", "fitness"}, "Желтый", (3,), ("Aerona",),
      (2900, 5900), "Бег", name="Наушники спортивные"),
    T(["extra/protein.jpg"], "Протеин", "nutrition", {"nutrition", "fitness"}, "Черный", (3,), ("Stridex", "Kinetra"),
      (2400, 4900), "Фитнес", name="Протеин сывороточный 900 г"),
    T(["extra/water.jpg"], "Вода", "nutrition", {"nutrition", "fitness", "hiking"}, "Белый", (3,), ("Aerona",), (90, 190),
      "Фитнес", name="Вода питьевая 0,5 л"),
    T(ph("more/juice", 1), "Напиток", "nutrition", {"nutrition", "fitness", "run"}, "Желтый", (3,), ("Kinetra",), (150, 290),
      "Бег", name="Напиток изотонический 0,5 л"),
]

_VARIANTS = [7, 7, 5, 7, 5, 2, 2, 1, 6, 3, 4, 3, 3, 2, 3, 3, 2, 4, 3, 3, 1, 3, 2, 4, 2, 2, 2, 2, 2,
             4, 2, 2, 1, 3, 3, 1, 2, 2, 1, 4, 3, 1, 2, 3, 1, 2]
for _t, _n in zip(TEMPLATES, _VARIANTS):
    _t["variants"] = _n

DESC = {
    "shoes": "Удобная модель на каждый день и для тренировок. Дышащий верх, амортизирующая подошва и съёмная стелька.",
    "clothes": "Мягкая ткань не сковывает движения и сохраняет форму после стирки. Плоские швы не натирают кожу.",
    "balls": "Прочная покрышка и камера, которая долго держит давление. Подходит для тренировок и игр.",
    "gear": "Надёжный инвентарь для тренировок и игр: прочные материалы и продуманная эргономика.",
    "acc": "Практичный аксессуар на каждый день: аккуратный дизайн и качественные материалы.",
    "electronics": "Электроника для спорта и активной жизни: долгая работа от батареи и защита от влаги.",
    "nutrition": "Спортивное питание для поддержки во время и после тренировок.",
    "gift": "Электронная подарочная карта SPORTLY. Действует 3 года во всех магазинах и в приложении.",
}

# секции каталога (ключ плитки -> название)
SECTION_NAMES = {
    "women": "Женщинам", "men": "Мужчинам", "kids": "Детям и подросткам", "clothes": "Одежда", "shoes": "Обувь",
    "acc": "Аксессуары", "fitness": "Тренажеры, фитнес", "run": "Бег, ходьба", "swim": "Плавание",
    "baseball": "Бейсбол", "football": "Футбол", "tennis": "Теннис, бадминтон", "nutrition": "Спортивное питание",
    "electronics": "Электроника", "esport": "Киберспорт", "hiking": "Походы, треккинг", "ice": "Ледовый спорт, хоккей",
    "basket": "Баскетбол", "volley": "Волейбол", "balls": "Мячи", "style": "Стиль", "premium": "Премиум",
    "abroad": "Из-за рубежа", "new": "Новинки", "sport": "Виды спорта", "sale": "Выгодная скидка каждому",
    "deals": "Скидки и акции", "gift": "Подарочные карты", "hits": "Хиты продаж", "all": "Все товары",
}


def _sizes(t, gender, pid):
    if t["sizes"] is not None:
        return list(t["sizes"])
    if t["cat"] == "shoes":
        full = KID_SHOES if gender == 2 else SHOE_SIZES
    elif t["cat"] == "clothes":
        full = KID_CLOTH if gender == 2 else CLOTH_SIZES
    else:
        return []
    # часть размеров «раскуплена» — у разных товаров разный набор
    return [s for i, s in enumerate(full) if (i + pid) % 4 != 0]


def build():
    items, pid = [], 1
    for ti, t in enumerate(TEMPLATES):
        for v in range(t["variants"]):
            brand = t["brands"][v % len(t["brands"])]
            g = t["genders"][(v + ti) % len(t["genders"])]
            lo, hi = t["price"]
            price = int(lo + (hi - lo) * (((pid * 37) % 11) / 10)) // 100 * 100 - 1
            disc = [0, 10, 15, 0, 20, 28, 0, 15, 30, 0][(pid * 3) % 10]
            old = int(price / (1 - disc / 100)) // 100 * 100 - 1 if disc else None
            model = f"{MODELS[(pid * 5) % len(MODELS)]} {1 + pid % 5}"
            if t["name"]:
                name = f"{t['name']} {brand}"
            else:
                forms = FORMS.get(t["kind"], ("", "", "", ""))
                adj = forms[g] if g in (0, 1, 2) else forms[3]
                name = " ".join(x for x in (t["kind"], adj, brand, model) if x)
            sections = set(t["sections"])
            if g == 0:
                sections.add("men")
            elif g == 1:
                sections.add("women")
            elif g == 2:
                sections.add("kids")
            else:
                if t["cat"] in ("clothes", "shoes"):
                    sections |= {"men", "women"}
            if brand in FOREIGN:
                sections.add("abroad")
            if price >= 10000:
                sections.add("premium")
            if t["sport"]:
                sections.add("sport")
            is_new = pid % 4 == 0
            if is_new:
                sections.add("new")
            if old:
                sections |= {"sale", "deals"}
            rating = round(3.9 + ((pid * 29) % 12) / 10, 1)
            p = {
                "id": pid, "name": name, "brand": brand, "kind": t["kind"], "cat": t["cat"], "sections": sections,
                "gender": GENDER[g], "color": t["color"], "sport": t["sport"], "season": t["season"],
                "material": t["material"], "clasp": t["clasp"], "price": price, "old_price": old,
                "rating": min(5.0, rating), "reviews": 5 + (pid * 53) % 900, "photos": t["photos"],
                "image": t["photos"][0], "sizes": _sizes(t, g, pid), "desc": DESC[t["cat"]],
                "own": brand in OWN_BRANDS, "new": is_new, "eco": pid % 7 == 0,
                "only_here": brand in OWN_BRANDS and pid % 3 == 0, "best": bool(old) and disc >= 20,
                "pickup_today": pid % 5 != 0, "express": pid % 3 != 2,
            }
            p["hit"] = p["reviews"] > 450
            p["promo"] = bool(old) and disc >= 15
            items.append(p)
            pid += 1
    # подарочные карты
    for nominal in (1000, 3000, 5000, 10000):
        items.append({"id": pid, "name": f"Подарочная карта SPORTLY на {nominal:,} ₽".replace(",", " "), "brand": "SPORTLY",
                      "kind": "Подарочная карта", "cat": "gift", "sections": {"gift"}, "gender": "Унисекс",
                      "color": "Синий", "sport": "", "season": "", "material": "", "clasp": "", "price": nominal,
                      "old_price": None, "rating": 5.0, "reviews": 40 + nominal // 100, "photos": [f"gift/gift{nominal}.jpg"],
                      "image": f"gift/gift{nominal}.jpg", "sizes": [], "desc": DESC["gift"], "own": True, "new": False,
                      "eco": True, "only_here": True, "best": False, "pickup_today": True, "express": True, "hit": False,
                      "promo": False})
        pid += 1
    return items


PRODUCTS = build()
BY_ID = {p["id"]: p for p in PRODUCTS}


# ---------------------------------------------------------------- поиск
SYNONYMS = {"обувь": "shoes", "одежда": "clothes", "мяч": "balls", "мячи": "balls", "теннис": "tennis",
            "футбол": "football", "баскетбол": "basket", "бег": "run", "часы": "acc", "питание": "nutrition"}


def _stem(w):
    w = w.lower().strip(".,!?")
    return w if len(w) <= 4 else w[:max(4, len(w) - 2)]


def _text(p):
    parts = [p["name"], p["kind"], p["brand"], p["gender"], p["sport"], p["color"], p["season"]]
    parts += [SECTION_NAMES.get(s, "") for s in p["sections"]]
    g = {"Мужской": "мужские мужская мужской мужчинам", "Женский": "женские женская женский женщинам",
         "Детский": "детские детская детский детям"}.get(p["gender"], "")
    return " ".join(parts + [g]).lower()


_TEXT = {p["id"]: _text(p) for p in PRODUCTS}


def search(q):
    words = [w for w in q.lower().split() if w]
    if not words:
        return []
    out = []
    for p in PRODUCTS:
        t = _TEXT[p["id"]]
        if all(_stem(w) in t for w in words):
            out.append(p)
    return out


def search_title(q, items):
    """Заголовок выдачи: самый частый вид товара во множественном числе («Кроссовки»), иначе сам запрос."""
    if not items:
        return q.capitalize()
    from collections import Counter
    kind, n = Counter(p["kind"] for p in items).most_common(1)[0]
    plural = {"Футболка": "Футболки", "Рубашка": "Рубашки", "Платье": "Платья", "Мяч": "Мячи", "Сумка": "Сумки",
              "Ракетка": "Ракетки", "Рюкзак": "Рюкзаки", "Перчатка": "Перчатки", "Бита": "Биты", "Шлем": "Шлемы",
              "Кольцо": "Кольца", "Смарт-часы": "Смарт-часы", "Наушники": "Наушники"}.get(kind, kind)
    return plural if n >= len(items) * 0.6 else q.capitalize()


def suggestions(prefix, limit=8):
    """Подсказки поиска: виды товаров с полом, бренды, названия."""
    pool = []
    for p in PRODUCTS:
        forms = FORMS.get(p["kind"])
        if forms:
            gi = {"Мужской": 0, "Женский": 1, "Детский": 2}.get(p["gender"], 3)
            if forms[gi]:
                pool.append(f"{p['kind']} {forms[gi]}".lower())
        pool.append(p["kind"].lower())
        pool.append(p["brand"].lower())
    seen, out = set(), []
    pre = prefix.lower().strip()
    for s in pool:
        if s not in seen and (not pre or pre in s):
            seen.add(s)
            out.append(s)
    out.sort(key=lambda s: (not s.startswith(pre), len(s)))
    return out[:limit]


def section_items(key):
    if key == "all":
        return list(PRODUCTS)
    if key == "hits":
        return [p for p in PRODUCTS if p["hit"]]
    return [p for p in PRODUCTS if key in p["sections"]]


# ---------------------------------------------------------------- фильтр
FACETS = [  # заголовок, ключ атрибута
    ("Вид товара", "kind"), ("Пол", "gender"), ("Размер", "sizes"), ("Бренд", "brand"), ("Вид спорта", "sport"),
    ("Цвет", "color"), ("Сезон", "season"), ("Застежка", "clasp"), ("Материал верха", "material"),
]
CHECKS = [  # заголовок, предикат
    ("Товары SPORTLY", lambda p: p["own"]), ("Товары со скидкой", lambda p: bool(p["old_price"])),
    ("Лучшая цена", lambda p: p["best"]), ("Новая коллекция", lambda p: p["new"]),
    ("Только у нас", lambda p: p["only_here"]), ("Экотовар", lambda p: p["eco"]),
]
CHECK_FN = dict(CHECKS)
PICKUP = [("Любой", lambda p: True), ("Самовывоз сегодня", lambda p: p["pickup_today"]),
          ("Экспресс-доставка", lambda p: p["express"])]
PICKUP_FN = dict(PICKUP)
SORTS = [("Популярные", lambda p: -p["reviews"]), ("Сначала дешевле", lambda p: p["price"]),
         ("Сначала дороже", lambda p: -p["price"]),
         ("По размеру скидки", lambda p: -(((p["old_price"] or p["price"]) - p["price"]) / (p["old_price"] or p["price"]))),
         ("По рейтингу", lambda p: (-p["rating"], -p["reviews"])), ("Новинки", lambda p: (not p["new"], -p["id"]))]
SIZE_ORDER = {s: i for i, s in enumerate([s for s, _ in KID_SHOES + SHOE_SIZES + KID_CLOTH + CLOTH_SIZES] +
                                         ["4", "5", "6", "7", "S", "M", "L"])}


def values(p, key):
    if key == "sizes":
        return [s for s, _ in p["sizes"]]
    v = p.get(key)
    return [v] if v else []


class Query:
    """Состояние фильтра над базовым набором товаров."""

    def __init__(self, base):
        self.base = list(base)
        self.sel = {}           # ключ атрибута -> set значений (внутри — ИЛИ, между атрибутами — И)
        self.checks = set()     # заголовки отмеченных чекбоксов
        self.pickup = "Любой"
        self.price = None       # (от, до) или None
        self.sort = 0

    def copy(self):
        q = Query(self.base)
        q.sel = {k: set(v) for k, v in self.sel.items()}
        q.checks, q.pickup, q.price, q.sort = set(self.checks), self.pickup, self.price, self.sort
        return q

    def price_bounds(self):
        ps = [p["price"] for p in self.base] or [0]
        return min(ps), max(ps)

    def match(self, p, skip=None):
        for key, vals in self.sel.items():
            if key == skip or not vals:
                continue
            if not set(values(p, key)) & vals:
                return False
        for c in self.checks:
            if not CHECK_FN[c](p):
                return False
        if not PICKUP_FN[self.pickup](p):
            return False
        if self.price and not (self.price[0] <= p["price"] <= self.price[1]):
            return False
        return True

    def results(self):
        return sorted((p for p in self.base if self.match(p)), key=SORTS[self.sort][1])

    def count(self):
        return sum(1 for p in self.base if self.match(p))

    def facet_values(self, key):
        """Значения атрибута с количеством товаров (с учётом остальных фильтров)."""
        cnt = {}
        for p in self.base:
            for v in values(p, key):
                cnt.setdefault(v, 0)
            if self.match(p, skip=key):
                for v in values(p, key):
                    cnt[v] += 1
        order = (lambda v: SIZE_ORDER.get(v, 999)) if key == "sizes" else (lambda v: v)
        return sorted(cnt.items(), key=lambda kv: order(kv[0]))

    def active_count(self):
        return (sum(1 for v in self.sel.values() if v) + len(self.checks) + (self.pickup != "Любой")
                + (self.price is not None))

    def reset(self):
        self.sel, self.checks, self.pickup, self.price = {}, set(), "Любой", None


def gift_images(out_dir):
    """Картинки подарочных карт (рисуются Pillow)."""
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(out_dir, exist_ok=True)
    font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "Montserrat-Bold.ttf")
    for nominal, (c1, c2) in zip((1000, 3000, 5000, 10000), (((29, 78, 216), (59, 111, 240)), ((24, 29, 48), (60, 70, 110)),
                                                              ((226, 38, 77), (255, 120, 90)), ((20, 120, 80), (60, 190, 120)))):
        W = 720
        img = Image.new("RGB", (W, W), (243, 244, 246))
        card = Image.new("RGB", (560, 350))
        d = ImageDraw.Draw(card)
        for x in range(560):
            t = x / 559
            d.line([(x, 0), (x, 350)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)))
        f1 = ImageFont.truetype(font_path, 40)
        f2 = ImageFont.truetype(font_path, 64)
        d.text((36, 30), "SPORTLY", font=f1, fill="white")
        d.text((36, 220), f"{nominal:,} ₽".replace(",", " "), font=f2, fill="white")
        mask = Image.new("L", (560, 350), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, 559, 349), radius=28, fill=255)
        img.paste(card, (80, 185), mask)
        img.save(os.path.join(out_dir, f"gift{nominal}.jpg"), quality=90)


# ---------------------------------------------------------------- правки каталога из админ-панели
ALL_PRODUCTS = list(PRODUCTS)    # все товары, включая скрытые (PRODUCTS — только видимые покупателям)
EDITABLE = ("name", "brand", "price", "old_price", "hidden")
version = 0                      # растёт при каждом изменении: экраны понимают, что витрину надо обновить


def _touch():
    """Обновить список видимых товаров, производные разделы и поисковый индекс."""
    global version
    PRODUCTS[:] = [p for p in ALL_PRODUCTS if not p.get("hidden")]
    for p in ALL_PRODUCTS:
        p["sections"] = set(p["sections"])
        if p["cat"] != "gift":
            (p["sections"].add if p["old_price"] else p["sections"].discard)("sale")
            (p["sections"].add if p["old_price"] else p["sections"].discard)("deals")
            (p["sections"].add if p["price"] >= 10000 else p["sections"].discard)("premium")
        _TEXT[p["id"]] = _text(p)
    version += 1


def _clone(base, cid, fields):
    p = dict(BY_ID[base])
    p.update(id=cid, base=base, custom=True, reviews=0, rating=5.0, hit=False, new=True)
    p["sections"] = set(BY_ID[base]["sections"]) | {"new"}
    p.update(fields)
    ALL_PRODUCTS.append(p)
    BY_ID[cid] = p
    return p


def apply_saved(saved):
    """Применить при запуске правки, сохранённые в локальной базе."""
    for item in saved.get("custom", []):
        if item["base"] in BY_ID:
            _clone(item["base"], item["id"], {k: item[k] for k in EDITABLE if k in item})
    for pid, fields in saved.get("overrides", {}).items():
        p = BY_ID.get(int(pid))
        if p:
            p.update(fields)
    _touch()


def edit_product(pid, fields, saved):
    p = BY_ID[pid]
    p.update(fields)
    if p.get("custom"):
        rec = next(r for r in saved["custom"] if r["id"] == pid)
        rec.update(fields)
    else:
        saved["overrides"].setdefault(str(pid), {}).update(fields)
    _touch()
    return p


def add_product(base, fields, saved):
    cid = max([10000] + [p["id"] for p in ALL_PRODUCTS]) + 1
    p = _clone(base, cid, fields)
    saved["custom"].append(dict(fields, id=cid, base=base))
    _touch()
    return p
