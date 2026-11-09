"""Проверка, что категории, поиск, фильтр и сортировка реально работают (с автоскриншотами).

Запуск: .venv/bin/python tools/test_flows.py [папка_для_скриншотов]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import tempfile  # noqa: E402
os.environ.setdefault("SPORTLY_DATA_DIR", tempfile.mkdtemp())   # тест не трогает настоящую базу
sys.path.insert(0, ROOT)
os.chdir(ROOT)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "shots_flows")
os.makedirs(OUT, exist_ok=True)

import main  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from app.catalog_db import section_items, search  # noqa: E402

app = main.SportlyApp()
steps, T0, errors = [], [0.0], []


def at(dt, fn):
    T0[0] += dt
    steps.append((T0[0], fn))


def shot(name):
    return lambda: Window.screenshot(os.path.join(OUT, name + ".png"))


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        errors.append(name)


cur = lambda: app.sm.current_screen  # noqa: E731


def n_cards():
    g = cur().grid_box.children
    return len(g[0].cards) if g and hasattr(g[0], "cards") else 0


def sheets():
    return [w for w in app.root_layout.children if w.__class__.__name__ == "BottomSheet"]


# 1. плитка «Обувь» в каталоге
at(3.5, lambda: app.go_tab("catalog"))
at(0.5, lambda: app.open_category("shoes"))
at(2.4, lambda: check("Обувь: только обувь", all(p["cat"] == "shoes" for p in cur().q.results())))
at(0.0, lambda: check("Обувь: карточек = товаров секции", n_cards() == len(section_items("shoes"))))
at(0.1, shot("01_shoes"))
# 2. фильтр: бренд + размер
at(0.2, lambda: app.push(main.FilterScreen(cur())))
at(0.9, lambda: cur()._pick("brand", "Nike"))
at(0.2, lambda: check("Фильтр: в кнопке реальное число (Nike)",
                      cur().btn.text.split()[1] == str(sum(1 for p in section_items("shoes") if p["brand"] == "Nike"))))
at(0.1, lambda: cur()._pick("sizes", "42"))
at(0.3, shot("02_filter"))
at(0.2, lambda: setattr(app, "_expect", cur().q.count()))
at(0.0, lambda: cur().apply())
at(0.8, lambda: check("После фильтра: только Nike с 42", all(p["brand"] == "Nike" and "42" in [s for s, _ in p["sizes"]]
                                                                for p in cur().q.results())))
at(0.0, lambda: check("После фильтра: карточек столько же, сколько в кнопке", n_cards() == app._expect))
at(0.1, shot("03_filtered"))
# 3. сортировка по цене
at(0.2, lambda: (cur().q.sel.clear(), setattr(cur().q, "sort", 1), cur().refresh()))
at(0.4, lambda: check("Сортировка «Сначала дешевле»",
                      [p["price"] for p in cur().q.results()] == sorted(p["price"] for p in cur().q.results())))
at(0.1, shot("04_sorted"))
# 4. шторка цены
at(0.2, lambda: cur().price_sheet())
at(0.7, shot("05_price_sheet"))
at(0.1, lambda: [s.close() for s in sheets()])
# 5. категория «Мужчинам» содержит только мужское/унисекс
at(0.6, lambda: app.go_tab("catalog"))
at(0.4, lambda: app.open_category("men"))
at(2.2, lambda: check("Мужчинам: пол мужской/унисекс", all(p["gender"] in ("Мужской", "Унисекс") for p in cur().q.results())))
at(0.1, shot("06_men"))
# 6. поиск «мяч»
at(0.2, lambda: app.open_search())
at(1.0, lambda: setattr(cur().inp, "text", "мяч"))
at(0.5, shot("07_suggest"))
at(0.1, lambda: cur().submit())
at(2.2, lambda: check("Поиск «мяч»: все результаты — мячи", all("мяч" in p["name"].lower() for p in cur().q.results())))
at(0.0, lambda: check("Поиск «мяч»: число совпадает", n_cards() == len(search("мяч"))))
at(0.1, shot("08_search_ball"))
# 7. быстрый чип «Товары SPORTLY»
at(0.2, lambda: cur()._toggle_own())
at(0.4, lambda: check("Чип «Товары SPORTLY»", all(p["own"] for p in cur().q.results())))
at(0.1, shot("09_own"))
# 8. вид спорта с главной
at(0.3, lambda: app.go_tab("home"))
at(1.6, lambda: app.open_category("sport", {"sport": {"Теннис"}}))
at(2.2, lambda: check("Вид спорта «Теннис»", all(p["sport"] == "Теннис" for p in cur().q.results()) and n_cards() > 0))
at(0.1, shot("10_tennis"))
# 9. все бренды
at(0.2, lambda: app.open_category("brands"))
at(0.7, shot("11_brands"))
at(0.2, lambda: app.open_category("gift"))
at(1.4, shot("12_gift"))
at(0.1, lambda: check("Подарочные карты", all(p["cat"] == "gift" for p in cur().q.results()) and n_cards() == 4))
at(0.5, lambda: (print("ИТОГО ошибок:", len(errors)), app.stop()))

for t, fn in steps:
    Clock.schedule_once(lambda _dt, fn=fn: fn(), t)
app.run()
