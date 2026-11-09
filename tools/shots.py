"""Автопрогон сценария из ролика ДЗ1 со скриншотами каждого шага."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import tempfile  # noqa: E402
os.environ.setdefault("SPORTLY_DATA_DIR", tempfile.mkdtemp())   # тест не трогает настоящую базу
sys.path.insert(0, ROOT)
os.chdir(ROOT)
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "shots")
os.makedirs(OUT, exist_ok=True)

import main  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from app.data import PICKUP_POINTS  # noqa: E402

app = main.SportlyApp()
steps, T0 = [], [0.0]


def at(dt, fn):
    T0[0] += dt
    steps.append((T0[0], fn))


def shot(name):
    return lambda: Window.screenshot(os.path.join(OUT, name + ".png"))


cur = lambda: app.sm.current_screen  # noqa: E731


def sheets():
    return [w for w in app.root_layout.children if w.__class__.__name__ in ("BottomSheet", "GeoDialog")]


at(2.6, shot("01_home_skeleton"))
at(1.6, shot("02_home"))
at(0.1, lambda: setattr(app.tabs["home"].sv, "scroll_y", 0.86))
at(0.6, shot("03_home_scroll_brands"))
at(0.1, lambda: setattr(app.tabs["home"].sv, "scroll_y", 0.62))
at(0.6, shot("04_home_tabs"))
at(0.1, lambda: app.tabs["home"].sv.children[0].children[-7].select(1) if False else None)
at(0.1, lambda: setattr(app.tabs["home"].sv, "scroll_y", 0.25))
at(0.7, shot("05_home_services"))
at(0.1, lambda: app.go_tab("catalog"))
at(1.0, shot("06_catalog"))
at(0.1, lambda: app.go_tab("services"))
at(0.5, shot("07_services_loading"))
at(1.0, shot("08_services"))
at(0.1, lambda: app.go_tab("catalog"))
at(0.4, lambda: app.open_search())
at(0.5, shot("09_search"))
at(0.6, lambda: setattr(cur().inp, "text", "кроссовки мужские"))
at(0.4, shot("10_search_typed"))
at(0.1, lambda: cur().submit())
at(0.7, shot("11_results_skeleton"))
at(1.4, shot("12_results"))
at(0.1, lambda: app.push(main.FilterScreen(cur())))
at(0.4, shot("13_filter_empty"))
at(0.7, shot("14_filter"))
at(0.1, lambda: cur()._pick("sizes", "42"))
at(0.1, lambda: setattr(cur().body.children[0], "scroll_y", 0.5))
at(0.5, shot("15_filter_scrolled"))
at(0.1, lambda: app.back())
at(0.6, lambda: __import__("app.screens.catalog", fromlist=["share_sheet"]).share_sheet("кроссовки мужские"))
at(0.7, shot("16_share"))
at(0.1, lambda: [s.close() for s in sheets()])
at(0.5, lambda: app.open_messages())
at(0.7, shot("17_messages"))
at(0.1, lambda: app.go_tab("cart"))
at(0.5, shot("18_cart_loading"))
at(1.2, shot("19_cart"))
at(0.1, lambda: setattr(cur().sv, "scroll_y", 0.45))
at(0.6, shot("20_cart_scrolled"))
at(0.1, lambda: setattr(cur().sv, "scroll_y", 0.0))
at(0.6, shot("21_cart_bottom"))
at(0.1, lambda: app.open_checkout())
at(0.5, shot("22_checkout_loading"))
at(1.3, shot("23_checkout"))
at(0.1, lambda: cur().choose_point())
at(0.9, shot("24_geo_dialog"))
at(0.1, lambda: [s.close(True) for s in sheets()])
at(0.9, shot("25_map_hint"))
at(2.4, shot("26_map"))
at(0.1, lambda: cur().pick(PICKUP_POINTS[0]))
at(0.8, shot("27_store"))
at(0.1, lambda: cur().toggle())
at(0.5, lambda: cur().take())
at(0.4, shot("28_wait"))
at(1.4, shot("29_checkout_store"))
at(0.1, lambda: cur().select_pay(cur().pay_chips[1]))
at(0.4, shot("30_pay_wait"))
at(1.0, lambda: cur().submit())
at(0.3, shot("31_toast_contacts"))
at(0.4, lambda: cur().open_contacts())
at(0.6, lambda: (setattr(cur().f_name.inp, "text", "Анна Иванова"), setattr(cur().f_phone.inp, "text", "9501198196"),
                 setattr(cur().f_mail.inp, "focus", True)))
at(0.5, shot("32_contacts"))
at(0.1, lambda: cur().save())
at(0.7, shot("33_checkout_ready"))
at(0.1, lambda: cur().submit())
at(1.6, shot("34_order"))
at(0.3, lambda: app.stop())

for t, fn in steps:
    Clock.schedule_once(lambda _dt, fn=fn: fn(), t)
app.run()
