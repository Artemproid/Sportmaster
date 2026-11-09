"""Каталог, поиск, выдача с рабочими фильтрами и сортировкой, «Поделиться», «Сообщения»."""
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.stacklayout import StackLayout
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from .. import theme as T
from ..common import (lbl, paint, vscroll, hscroll, product_grid, search_header, chat_button, PAD, GAP, fit_w,
                      OutlineChip, RangeSlider, card_width, fade_image, empty_state, TopBar)
from ..data import (CATALOG_TOP, CATALOG_GRID, FILTER_COLORS, APP, PRODUCTS, BRANDS, SECTION_NAMES, tile, search,
                    search_title, suggestions, section_items)
from ..catalog_db import Query, FACETS, CHECKS, PICKUP, SORTS
from ..net import net
from ..common import ErrorView
from ..icons import Icon
from ..widgets import PressBox, IconButton, AppButton, LoadRing, SkeletonBox, SquareCheck, BottomSheet, stagger_in

# плитки каталога, у которых картинка и секция называются по-разному
TILE_SECTION = {"fight": "baseball"}
FACET_TITLE = dict((k, t) for t, k in FACETS)
EXTRA_COLORS = {"Синий": "#1D4ED8", "Оранжевый": "#F28C28", "Коричневый": "#7B4A2A", "Желтый": "#F5D02A",
                "Серый": "#9AA0A6", "Красный": "#E8262C"}


def plural_goods(n):
    return f"{n:,}".replace(",", " ") + " " + T.plural(n, "товар", "товара", "товаров")


def open_section(key, preset=None):
    """Открыть выдачу секции каталога (плитка, баннер, бренд, вид спорта)."""
    app = App.get_running_app()
    if key == "service":
        return app.open_messages()
    if key == "brands":
        return app.push(BrandsScreen())
    title = SECTION_NAMES.get(key, "Товары")
    if preset and "sport" in preset and len(preset["sport"]) == 1:
        title = next(iter(preset["sport"]))
    elif preset and "gender" in preset:
        g = next(v for v in preset["gender"] if v != "Унисекс")
        title = f"{title}: {dict(Мужской='мужчинам', Женский='женщинам', Детский='детям')[g]}"
    app.push(ResultsScreen(title=title, items=section_items(key), preset=preset))


# ============================================================================ каталог
class CatalogScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="catalog", **kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(search_header())
        sv, box = vscroll()
        box.spacing = dp(10)
        box.padding = (PAD, dp(6), PAD, box.padding[3])
        top = GridLayout(cols=4, spacing=dp(8), size_hint_y=None)
        top.bind(minimum_height=top.setter("height"))
        tw = (Window.width - PAD * 2 - dp(24)) / 4
        for name, key, section in CATALOG_TOP:
            t = PressBox(orientation="vertical", size_hint_y=None, height=tw + dp(48), spacing=dp(4))
            pic = RelativeLayout(size_hint_y=None, height=tw)
            with pic.canvas.before:
                Color(*T.TILE)
                RoundedRectangle(pos=(0, 0), size=(tw, tw), radius=[dp(10)])
            pic.add_widget(fade_image(tile(key), delay=0.1))
            t.add_widget(pic)
            t.add_widget(lbl(name, 11, halign="center", valign="top"))
            t.bind(on_release=lambda *_, s=section: open_section(s))
            top.add_widget(t)
        box.add_widget(top)
        grid = GridLayout(cols=3, spacing=dp(10), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        gw = (Window.width - PAD * 2 - dp(20)) / 3
        for i, (name, key) in enumerate(CATALOG_GRID):
            t = PressBox(size_hint_y=None, height=gw * 1.2)
            rl = RelativeLayout()
            with rl.canvas.before:
                Color(*T.TILE)
                RoundedRectangle(pos=(0, 0), size=(gw, gw * 1.2), radius=[dp(10)])
            rl.add_widget(fade_image(tile(key), delay=0.05 * (i // 3), size_hint=(1, 0.78), pos_hint={"x": 0, "y": 0}))
            rl.add_widget(lbl(name, 12, valign="top", size_hint=(1, None), height=dp(46), pos_hint={"x": 0, "top": 1},
                              padding=(dp(9), dp(8))))
            t.add_widget(rl)
            t.bind(on_release=lambda *_, k=TILE_SECTION.get(key, key): open_section(k))
            grid.add_widget(t)
        box.add_widget(grid)
        box.add_widget(lbl("Хиты продаж", 21, weight="semi", size_hint_y=None, height=dp(56)))
        from ..common import product_strip
        strip = product_strip(section_items("hits")[:10], width=dp(160))
        strip.children[0].padding = (0, 0)
        box.add_widget(strip)
        root.add_widget(sv)
        self.add_widget(root)


class BrandsScreen(Screen):
    """«Все бренды»: список брендов с количеством товаров."""

    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Все бренды"))
        sv, box = vscroll()
        box.padding = (PAD, 0, PAD, box.padding[3])
        box.spacing = 0
        from collections import Counter
        cnt = Counter(p["brand"] for p in PRODUCTS)
        for b in sorted(cnt):
            r = PressBox(size_hint_y=None, height=dp(54))
            r.add_widget(lbl(b, 16))
            r.add_widget(fit_w(lbl(plural_goods(cnt[b]), 14, color=T.MUTED, weight="reg")))
            r.add_widget(Icon(name="chevron", color=T.MUTED, size_hint_x=None, width=dp(22)))
            r.bind(on_release=lambda *_, b=b: open_brand(b))
            box.add_widget(r)
            sep = Widget(size_hint_y=None, height=1)
            paint(sep, T.LINE)
            box.add_widget(sep)
        root.add_widget(sv)
        self.add_widget(root)


def open_brand(brand):
    App.get_running_app().push(ResultsScreen(title=brand, items=[p for p in PRODUCTS if p["brand"] == brand]))


# ============================================================================ поиск
class SearchScreen(Screen):
    """Поле в фокусе, загрузка, затем подсказки (обновляются при вводе); Enter — поиск."""

    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        bar = BoxLayout(size_hint_y=None, height=dp(62), padding=(dp(6), dp(7), PAD, dp(7)), spacing=dp(4))
        back = IconButton(icon="back", icon_size=dp(28), pos_hint={"center_y": .5})
        back.bind(on_release=lambda *_: App.get_running_app().back())
        bar.add_widget(back)
        field = BoxLayout(padding=(dp(14), 0), spacing=dp(8))
        paint(field, T.GRAY_BG, dp(24))
        field.add_widget(Icon(name="search", color=T.MUTED, size_hint_x=None, width=dp(22)))
        self.inp = TextInput(hint_text=f"Искать в {APP}", multiline=False, font_name="AppReg", font_size="16sp",
                             background_normal="", background_active="", background_color=(0, 0, 0, 0),
                             foreground_color=T.TEXT, cursor_color=T.BLUE, cursor_width=dp(1.6), hint_text_color=T.MUTED,
                             padding=(0, dp(14), 0, 0))
        self.inp.bind(on_text_validate=lambda *_: self.submit(), text=self._typed)
        field.add_widget(self.inp)
        self.clear = IconButton(icon="close", icon_size=dp(20), size=(dp(34), dp(34)), pos_hint={"center_y": .5})
        self.clear.opacity = 0
        self.clear.bind(on_release=lambda *_: setattr(self.inp, "text", ""))
        field.add_widget(self.clear)
        bar.add_widget(field)
        root.add_widget(bar)
        self.body = FloatLayout()
        root.add_widget(self.body)
        self.add_widget(root)
        self.body.add_widget(LoadRing(pos_hint={"center_x": .5, "top": .8}))
        self._ev = None
        Clock.schedule_once(lambda *_: self._suggest(), 0.8)

    def on_enter(self):
        Clock.schedule_once(lambda *_: setattr(self.inp, "focus", True), 0.05)

    def _suggest(self, q=""):
        self.body.clear_widgets()
        sv, box = vscroll()
        sv.pos_hint = {"x": 0, "y": 0}
        box.padding = (PAD, dp(4), PAD, box.padding[3])
        box.spacing = 0
        hist = getattr(App.get_running_app(), "search_history", [])
        rows = []
        if not q and hist:
            box.add_widget(lbl("Вы искали", 17, size_hint_y=None, height=dp(40)))
            for s in hist[:5]:
                rows.append(self._row(box, s, "clock"))
            box.add_widget(lbl("Часто ищут", 17, size_hint_y=None, height=dp(48)))
        for s in suggestions(q, 8 if q else 6):
            n = len(search(s))
            if n:
                rows.append(self._row(box, s, "search", n))
        if q and not rows:
            box.add_widget(lbl("Ничего не нашлось — попробуйте изменить запрос", 15, color=T.MUTED, size_hint_y=None,
                               height=dp(60)))
        self.body.add_widget(sv)
        stagger_in(rows, 0.02)

    def _row(self, box, s, icon, n=None):
        r = PressBox(size_hint_y=None, height=dp(52), spacing=dp(14))
        r.add_widget(Icon(name=icon, color=T.MUTED, size_hint_x=None, width=dp(22)))
        r.add_widget(lbl(s, 16, weight="reg"))
        if n:
            r.add_widget(fit_w(lbl(str(n), 13, color=T.MUTED, weight="reg")))
        r.add_widget(Icon(name="arrow-up-left", color=T.MUTED, size_hint_x=None, width=dp(22)))
        r.bind(on_release=lambda *_, s=s: (setattr(self.inp, "text", s), self.submit()))
        box.add_widget(r)
        return r

    def _typed(self, _i, t):
        Animation(opacity=1 if t else 0, d=0.15).start(self.clear)
        if self._ev:
            self._ev.cancel()
        self._ev = Clock.schedule_once(lambda *_: self._suggest(t.strip()), 0.15)

    def submit(self):
        q = self.inp.text.strip()
        if not q:
            return
        self.inp.focus = False
        app = App.get_running_app()
        hist = getattr(app, "search_history", [])
        app.search_history = [q] + [h for h in hist if h != q]
        items = search(q)
        app.replace(ResultsScreen(title=search_title(q, items), items=items, query=q))


# ============================================================================ выдача
class ResultsScreen(Screen):
    """Список товаров: заголовок, количество, сортировка, фильтр, быстрые чипы, сетка."""

    def __init__(self, title="Товары", items=None, query=None, preset=None, **kw):
        super().__init__(**kw)
        self.title, self.query = title, query
        self.q = Query(items if items is not None else PRODUCTS)
        for key, vals in (preset or {}).items():
            self.q.sel[key] = set(vals)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        if query:
            root.add_widget(search_header(back=True, query=query, on_search=lambda: App.get_running_app().open_search()))
        else:
            root.add_widget(search_header(back=True))
        self.body = FloatLayout()
        root.add_widget(self.body)
        self.add_widget(root)
        self._skeleton()
        self._fetch()

    def _fetch(self):
        net.request(self._load, self._failed, delay=1.0)

    def _failed(self, kind):
        self.body.clear_widgets()

        def retry():
            self.body.clear_widgets()
            self._skeleton()
            self._fetch()
        self.body.add_widget(ErrorView(kind, retry))

    def _skeleton(self):
        sv, box = vscroll()
        sv.pos_hint = {"x": 0, "y": 0}
        box.padding = (PAD, dp(8), PAD, 0)
        box.spacing = dp(14)
        w = Window.width - PAD * 2
        box.add_widget(SkeletonBox(size_hint_y=None, height=dp(96), radius=dp(10)))
        for a, b in ((0.55, 0.25), (1, 0), (0.42, 0.3)):
            r = BoxLayout(size_hint_y=None, height=dp(20), spacing=w * 0.1)
            r.add_widget(SkeletonBox(size_hint_x=a, radius=dp(6)))
            if b:
                r.add_widget(SkeletonBox(size_hint_x=b, radius=dp(6)))
            box.add_widget(r)
        g = GridLayout(cols=2, spacing=GAP, size_hint_y=None)
        g.bind(minimum_height=g.setter("height"))
        for _ in range(2):
            col = BoxLayout(orientation="vertical", size_hint_y=None, height=card_width() * 1.3 + dp(120), spacing=dp(10))
            col.add_widget(SkeletonBox(radius=dp(10), size_hint_y=None, height=card_width() * 1.3))
            for f in (0.6, 1, 0.75, 0.6):
                r = BoxLayout(size_hint_y=None, height=dp(16))
                r.add_widget(SkeletonBox(size_hint_x=f, radius=dp(5)))
                r.add_widget(Widget(size_hint_x=1 - f + 0.001))
                col.add_widget(r)
            g.add_widget(col)
        box.add_widget(g)
        self.sk = sv
        self.body.add_widget(sv)

    def _load(self):
        sv, box = vscroll()
        sv.pos_hint = {"x": 0, "y": 0}
        box.spacing = 0
        head = BoxLayout(size_hint_y=None, height=dp(64), padding=(PAD, dp(4), dp(8), 0))
        col = BoxLayout(orientation="vertical")
        col.add_widget(lbl(self.title, 23, weight="semi", shorten=True))
        self.count_lbl = lbl("", 13, color=T.MUTED, weight="reg")
        col.add_widget(self.count_lbl)
        head.add_widget(col)
        sh = IconButton(icon="share", icon_size=dp(28), pos_hint={"center_y": .5})
        sh.bind(on_release=lambda *_: share_sheet(self.query or self.title))
        head.add_widget(sh)
        box.add_widget(head)
        chips_sv, chips = hscroll(dp(60))
        chips.padding = (PAD, dp(10))
        chips.spacing = dp(8)
        self.sort_chip = OutlineChip("", icon="sort-descending")
        self.sort_chip.bind(on_release=lambda *_: self.sort_sheet())
        self.flt_chip = OutlineChip("", icon="adjustments-horizontal")
        self.flt_chip.bind(on_release=lambda *_: App.get_running_app().push(FilterScreen(self)))
        chips.add_widget(self.sort_chip)
        chips.add_widget(self.flt_chip)
        self.qchips = {}
        pick = OutlineChip("Способ получения")
        pick.bind(on_release=lambda *_: self.pickup_sheet())
        chips.add_widget(pick)
        self.qchips["pickup"] = pick
        own = OutlineChip(f"Товары {APP}")
        own.bind(on_release=lambda *_: self._toggle_own())
        chips.add_widget(own)
        self.qchips["own"] = own
        self.qchips["price"] = OutlineChip("Цена")
        self.qchips["price"].bind(on_release=lambda *_: self.price_sheet())
        chips.add_widget(self.qchips["price"])
        for title, key in FACETS:
            if len({v for p in self.q.base for v in (p["sizes"] and [s for s, _ in p["sizes"]] if key == "sizes"
                                                     else [p.get(key)]) if v}) > 1:
                c = OutlineChip(title)
                c.bind(on_release=lambda *_, k=key: self.facet_sheet(k))
                chips.add_widget(c)
                self.qchips[key] = c
        box.add_widget(chips_sv)
        self.grid_box = BoxLayout(size_hint_y=None)
        box.add_widget(self.grid_box)
        self.body.add_widget(sv)
        self.sv = sv
        sv.opacity = 0
        Animation(opacity=1, d=0.3).start(sv)
        a = Animation(opacity=0, d=0.2)
        old = self.sk
        a.bind(on_complete=lambda *_: (self.body.remove_widget(old), [s.stop() for s in old.walk() if isinstance(s, SkeletonBox)]))
        a.start(old)
        self.refresh()

    # ---- состояние → экран
    def refresh(self, animate=True):
        items = self.q.results()
        self.count_lbl.text = plural_goods(len(items))
        self.grid_box.clear_widgets()
        if not items:
            e = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(230), padding=(dp(32), dp(30)), spacing=dp(12))
            e.add_widget(lbl("Ничего не нашлось", 20, weight="semi", halign="center", size_hint_y=None, height=dp(30)))
            e.add_widget(lbl("Попробуйте изменить условия фильтра", 15, color=T.MUTED, halign="center", weight="reg",
                             size_hint_y=None, height=dp(24)))
            b = AppButton(text="Сбросить фильтры", bg=T.BLUE_LIGHT, fg=T.BLUE, radius=dp(8))
            b.bind(on_release=lambda *_: (self.q.reset(), self.refresh()))
            e.add_widget(b)
            self.grid_box.add_widget(e)
            self.grid_box.height = e.height
        else:
            g = product_grid(items)
            g.padding = (PAD, dp(6), PAD, 0)
            self.grid_box.add_widget(g)
            self.grid_box.height = g.height
            g.bind(height=lambda o, h: setattr(self.grid_box, "height", h))
            if animate:
                stagger_in(g.cards[:8], 0.03)
        q = self.q
        self.qchips["pickup"].active = q.pickup != "Любой"
        self.qchips["own"].active = f"Товары {APP}" in q.checks
        self.qchips["price"].active = q.price is not None
        for key, c in self.qchips.items():
            if key in FACET_TITLE:
                c.active = bool(q.sel.get(key))
        self.flt_chip.active = q.active_count() > 0
        self.sort_chip.active = q.sort != 0

    def _toggle_own(self):
        k = f"Товары {APP}"
        (self.q.checks.discard if k in self.q.checks else self.q.checks.add)(k)
        self.refresh()

    # ---- шторки быстрых фильтров
    def _sheet_list(self, title, options, selected, multi, on_apply):
        """Шторка со списком вариантов (с количеством). multi — несколько, иначе один."""
        app = App.get_running_app()
        cur = set(selected)
        content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(14)), spacing=dp(4))
        content.add_widget(lbl(title, 21, weight="semi", size_hint_y=None, height=dp(46)))
        sv, box = vscroll(bottom=dp(4))
        box.spacing = 0
        checks = {}
        for name, n in options:
            r = PressBox(size_hint_y=None, height=dp(50), spacing=dp(10))
            dead = n == 0 and name not in cur
            r.opacity = 0.4 if dead else 1
            r.add_widget(lbl(name, 16, weight="reg"))
            if n is not None:
                r.add_widget(fit_w(lbl(str(n), 14, color=T.MUTED, weight="reg")))
            cb = SquareCheck(active=name in cur, pos_hint={"center_y": .5})
            checks[name] = cb
            r.add_widget(cb)

            def tap(_w, name=name, dead=dead):
                if dead:
                    return
                if multi:
                    checks[name].active = not checks[name].active
                else:
                    for k, c in checks.items():
                        c.active = k == name
            r.bind(on_release=tap)
            cb.bind(on_release=lambda *_: None)
            box.add_widget(r)
        content.add_widget(sv)
        btn = AppButton(text="Применить", height=dp(52), radius=dp(8))
        sheet = BottomSheet(content, height=min(Window.height * 0.75, dp(50) * len(options) + dp(160)))
        btn.bind(on_release=lambda *_: (on_apply({k for k, c in checks.items() if c.active}), sheet.close()))
        content.add_widget(btn)
        sheet.open(app.root_layout)

    def facet_sheet(self, key):
        def apply(vals):
            self.q.sel[key] = vals
            self.refresh()
        self._sheet_list(FACET_TITLE[key], self.q.facet_values(key), self.q.sel.get(key, set()), True, apply)

    def pickup_sheet(self):
        opts = []
        for name, fn in PICKUP:
            qq = self.q.copy()
            qq.pickup = name
            opts.append((name, qq.count()))

        def apply(vals):
            self.q.pickup = next(iter(vals), "Любой")
            self.refresh()
        self._sheet_list("Способ получения", opts, {self.q.pickup}, False, apply)

    def price_sheet(self):
        app = App.get_running_app()
        lo, hi = self.q.price_bounds()
        cur = self.q.price or (lo, hi)
        content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(16)), spacing=dp(10))
        content.add_widget(lbl("Цена", 21, weight="semi", size_hint_y=None, height=dp(46)))
        pr = PriceRange(lo, hi, cur)
        content.add_widget(pr)
        info = lbl("", 14, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(22))
        content.add_widget(info)

        def upd(*_):
            qq = self.q.copy()
            qq.price = pr.value()
            info.text = f"Найдено: {plural_goods(qq.count())}"
        pr.on_change = upd
        upd()
        btn = AppButton(text="Применить", height=dp(52), radius=dp(8))
        sheet = BottomSheet(content, height=dp(300))

        def apply(*_):
            v = pr.value()
            self.q.price = None if v == (lo, hi) else v
            sheet.close()
            self.refresh()
        btn.bind(on_release=apply)
        content.add_widget(btn)
        sheet.open(app.root_layout)

    def sort_sheet(self):
        def apply(vals):
            name = next(iter(vals), SORTS[0][0])
            self.q.sort = [s for s, _ in SORTS].index(name)
            self.refresh()
            self.sv.scroll_y = 1
        self._sheet_list("Сортировка", [(s, None) for s, _ in SORTS], {SORTS[self.q.sort][0]}, False, apply)


class PriceRange(BoxLayout):
    """Поля «от / до» (можно вводить) + ползунок с двумя бегунками."""

    def __init__(self, lo, hi, cur, on_change=None, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(100), spacing=dp(6), **kw)
        self.lo, self.hi, self.on_change = lo, hi, on_change
        row = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(20))
        self.f_from = self._box("От", cur[0])
        self.f_to = self._box("До", cur[1])
        row.add_widget(self.f_from)
        row.add_widget(self.f_to)
        self.add_widget(row)
        self.slider = RangeSlider(on_change=self._slide)
        span = max(1, hi - lo)
        self.slider.lo = (cur[0] - lo) / span
        self.slider.hi = (cur[1] - lo) / span
        self.add_widget(self.slider)

    def _box(self, title, value):
        b = BoxLayout(orientation="vertical", padding=(dp(14), dp(4), dp(8), 0))
        paint(b, T.GRAY_BG, dp(2))
        b.add_widget(lbl(title, 12, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(18)))
        inp = TextInput(text=str(int(value)), multiline=False, input_filter="int", font_name="AppReg", font_size="16sp",
                        background_normal="", background_active="", background_color=(0, 0, 0, 0),
                        foreground_color=T.TEXT, cursor_color=T.BLUE, padding=(0, dp(4), 0, 0))
        inp.bind(on_text_validate=lambda *_: self._typed(), focus=lambda i, f: None if f else self._typed())
        b.add_widget(inp)
        b.inp = inp
        return b

    def _val(self, k):
        return int(self.lo + (self.hi - self.lo) * k)

    def _slide(self, a, b, done=False):
        self.f_from.inp.text = str(self._val(a))
        self.f_to.inp.text = str(self._val(b))
        if self.on_change:
            self.on_change()

    def _typed(self):
        try:
            a = max(self.lo, min(self.hi, int(self.f_from.inp.text or self.lo)))
            b = max(self.lo, min(self.hi, int(self.f_to.inp.text or self.hi)))
        except ValueError:
            return
        a, b = min(a, b), max(a, b)
        span = max(1, self.hi - self.lo)
        self.slider.lo, self.slider.hi = (a - self.lo) / span, (b - self.lo) / span
        self.f_from.inp.text, self.f_to.inp.text = str(a), str(b)
        if self.on_change:
            self.on_change()

    def value(self):
        try:
            a, b = int(self.f_from.inp.text), int(self.f_to.inp.text)
        except ValueError:
            return (self.lo, self.hi)
        if self.slider.lo <= 0.001:
            a = self.lo
        if self.slider.hi >= 0.999:
            b = self.hi
        return (min(a, b), max(a, b))


# ============================================================================ фильтр
class FilterScreen(Screen):
    """Полноэкранный фильтр по реальным атрибутам товаров. Кнопка показывает точное количество."""

    def __init__(self, results, **kw):
        super().__init__(**kw)
        self.results = results
        self.q = results.q.copy()
        root = FloatLayout()
        paint(root, T.BG)
        col = BoxLayout(orientation="vertical", pos_hint={"x": 0, "y": 0})
        bar = BoxLayout(size_hint_y=None, height=dp(62), padding=(dp(6), 0, PAD, 0), spacing=dp(6))
        x = IconButton(icon="close", icon_size=dp(30), pos_hint={"center_y": .5})
        x.bind(on_release=lambda *_: App.get_running_app().back())
        bar.add_widget(x)
        bar.add_widget(lbl("Фильтр", 21, weight="semi"))
        self.reset = PressBox(size_hint_x=None, width=dp(90))
        self.reset.add_widget(lbl("Сбросить", 15, color=T.BLUE, halign="right"))
        self.reset.bind(on_release=lambda *_: self.reset_all())
        bar.add_widget(self.reset)
        col.add_widget(bar)
        self.body = FloatLayout()
        col.add_widget(self.body)
        root.add_widget(col)
        btn_wrap = BoxLayout(size_hint=(1, None), height=dp(80), padding=(PAD, dp(10), PAD, dp(16)), pos_hint={"x": 0, "y": 0})
        paint(btn_wrap, T.BG)
        self.btn = AppButton(text="", height=dp(54), radius=dp(8))
        self.btn.bind(on_release=lambda *_: self.apply())
        btn_wrap.add_widget(self.btn)
        root.add_widget(btn_wrap)
        self.add_widget(root)
        self.chips = {}      # (key, value) -> chip
        self.update(rebuild=False)
        Clock.schedule_once(lambda *_: self._build(), 0.4)   # как в оригинале: сначала пусто, потом список

    def _sep(self, box):
        w = Widget(size_hint_y=None, height=1)
        paint(w, T.LINE)
        box.add_widget(w)

    def _build(self):
        self.body.clear_widgets()
        self.chips = {}
        self.checkboxes = {}
        sv, box = vscroll(bottom=dp(100))
        sv.pos_hint = {"x": 0, "y": 0}
        box.padding = (PAD, 0, PAD, dp(100))
        box.spacing = 0
        r = PressBox(size_hint_y=None, height=dp(52))
        r.add_widget(lbl("Способ получения", 16))
        self.pick_lbl = fit_w(lbl(self.q.pickup, 15, color=T.MUTED, weight="reg"))
        r.add_widget(self.pick_lbl)
        r.add_widget(Icon(name="chevron", color=T.MUTED, size_hint_x=None, width=dp(22)))
        r.bind(on_release=lambda *_: self._pickup())
        box.add_widget(r)
        self._sep(box)
        box.add_widget(self._check_row(f"Товары {APP}"))
        self._sep(box)
        lo, hi = self.q.price_bounds()
        if hi > lo:
            box.add_widget(lbl("Цена", 17, size_hint_y=None, height=dp(48)))
            self.pr = PriceRange(lo, hi, self.q.price or (lo, hi), on_change=self._price)
            box.add_widget(self.pr)
            box.add_widget(Widget(size_hint_y=None, height=dp(6)))
            self._sep(box)
        for title, key in FACETS:
            vals = self.q.facet_values(key)
            if len(vals) < 2 and not self.q.sel.get(key):
                continue
            self._chips_section(box, title, key, vals)
        for title, _ in CHECKS:
            if title != f"Товары {APP}":
                box.add_widget(self._check_row(title))
        self.body.add_widget(sv)
        sv.opacity = 0
        Animation(opacity=1, d=0.25).start(sv)
        self.update(rebuild=False)

    def _price(self):
        lo, hi = self.q.price_bounds()
        v = self.pr.value()
        self.q.price = None if v == (lo, hi) else v
        self.update()

    def _pickup(self):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(16)))
        content.add_widget(lbl("Способ получения", 21, weight="semi", size_hint_y=None, height=dp(46)))
        sheet = None
        for name, _ in PICKUP:
            qq = self.q.copy()
            qq.pickup = name
            r = PressBox(size_hint_y=None, height=dp(52), spacing=dp(10))
            r.add_widget(lbl(name, 16, weight="reg"))
            r.add_widget(fit_w(lbl(str(qq.count()), 14, color=T.MUTED, weight="reg")))
            r.add_widget(Icon(name="check", color=T.BLUE if self.q.pickup == name else (0, 0, 0, 0), size_hint_x=None,
                              width=dp(24)))

            def pick(_w, name=name):
                self.q.pickup = name
                self.pick_lbl.text = name
                sheet.close()
                self.update()
            r.bind(on_release=pick)
            content.add_widget(r)
        sheet = BottomSheet(content, height=dp(52) * len(PICKUP) + dp(90))
        sheet.open(app.root_layout)

    def _check_row(self, name):
        r = PressBox(size_hint_y=None, height=dp(52))
        r.add_widget(lbl(name, 16))
        cb = SquareCheck(active=name in self.q.checks, pos_hint={"center_y": .5})

        def changed(_w, on):
            (self.q.checks.add if on else self.q.checks.discard)(name)
            self.update()
        cb.bind(active=changed)
        r.add_widget(cb)
        r.bind(on_release=lambda *_: setattr(cb, "active", not cb.active))
        self.checkboxes[name] = cb
        return r

    def _chips_section(self, box, title, key, vals):
        hdr = BoxLayout(size_hint_y=None, height=dp(48))
        hl = BoxLayout(spacing=dp(6))
        hl.add_widget(fit_w(lbl(title, 17)))
        hl.add_widget(Widget())
        hdr.add_widget(hl)
        allb = PressBox(size_hint_x=None, width=dp(64))
        allb.add_widget(lbl("Все", 15, color=T.MUTED, halign="right"))
        hdr.add_widget(allb)
        box.add_widget(hdr)
        st = StackLayout(size_hint_y=None, spacing=dp(8), padding=(0, 0, 0, dp(14)))
        st.bind(minimum_height=st.setter("height"))
        for v, n in vals:
            dot = FILTER_COLORS.get(v) or EXTRA_COLORS.get(v) if key == "color" else None
            c = OutlineChip(v, dot=dot, height=dp(38))
            c.active = v in self.q.sel.get(key, set())
            c.bind(on_release=lambda w, k=key, v=v: self._pick(k, v))
            st.add_widget(c)
            self.chips[(key, v)] = c
        allb.bind(on_release=lambda *_, k=key, vs=[v for v, _ in vals]: self._all(k, vs))
        box.add_widget(st)
        self._sep(box)

    def _pick(self, key, v):
        c = self.chips.get((key, v))
        if c is not None and getattr(c, "dead", False):
            return App.get_running_app().toast("С выбранными фильтрами таких товаров нет")
        s = self.q.sel.setdefault(key, set())
        (s.discard if v in s else s.add)(v)
        self.update()

    def _all(self, key, vs):
        s = self.q.sel.setdefault(key, set())
        if set(vs) <= s:
            s.clear()
        else:
            s.update(vs)
        self.update()

    def update(self, rebuild=True):
        """Пересчёт: активность чипов, недоступные значения, число товаров в кнопке."""
        q = self.q
        for (key, v), c in self.chips.items():
            c.active = v in q.sel.get(key, set())
        if rebuild:
            avail = {key: dict(q.facet_values(key)) for _, key in FACETS}
            for (key, v), c in self.chips.items():
                n = avail.get(key, {}).get(v, 0)
                dead = n == 0 and not c.active
                c.dead = dead          # недоступное значение: бледное и не нажимается
                Animation(opacity=0.35 if dead else 1, d=0.15).start(c)
        n = q.count()
        self.reset.opacity = 1 if q.active_count() else 0
        self.reset.disabled = not q.active_count()
        self.btn.text = f"Показать {plural_goods(n)}" if n else "Ничего не найдено"
        Animation(bg=T.BLUE if n else T.rgba(T.BLUE, 0.4), d=0.15).start(self.btn)
        self.btn.pscale = 0.97
        Animation(pscale=1, d=0.25, t="out_back").start(self.btn)

    def reset_all(self):
        self.q.reset()
        self._build()
        self.update()

    def apply(self):
        if not self.q.count():
            return App.get_running_app().toast("По этим условиям товаров нет")
        self.results.q = self.q
        self.results.refresh()
        if hasattr(self.results, "sv"):
            self.results.sv.scroll_y = 1
        App.get_running_app().back()


# ============================================================================ «Поделиться ссылкой»
def share_sheet(query):
    """Тёмная шторка «Поделиться ссылкой» (имитация системного меню Android)."""
    app = App.get_running_app()
    content = BoxLayout(orientation="vertical", padding=(dp(18), dp(4), dp(18), dp(24)), spacing=dp(14))
    content.add_widget(lbl("Поделиться ссылкой", 19, weight="semi", color=T.WHITE, size_hint_y=None, height=dp(34)))
    link = BoxLayout(size_hint_y=None, height=dp(62), padding=(dp(10), dp(8)), spacing=dp(12))
    paint(link, (0.24, 0.25, 0.28, 1), dp(14))
    ic = BoxLayout(size_hint_x=None, width=dp(44), padding=dp(9))
    paint(ic, (0.9, 0.9, 0.92, 1), dp(10))
    ic.add_widget(Icon(name="file-text", color=(0.3, 0.3, 0.32, 1)))
    link.add_widget(ic)
    url = f"https://sportly.example/catalog/muzhskaya_obuv/krossovki/?q={query.replace(' ', '+')}"
    link.add_widget(lbl(url, 12, color=T.rgba(T.WHITE, 0.6), weight="reg", shorten=True, max_lines=2))
    cp = IconButton(icon="copy", icon_color=T.WHITE, icon_size=dp(24))
    link.add_widget(cp)
    content.add_widget(link)
    sheet = None
    rows = [[("Истории", "circle-plus", "#7C6CF0"), ("Мама", "user", "#E0884A"), ("Работа", "users", "#4AA0E0"),
             ("Заметки", "notes", "#F0B43C"), ("Новый пост", "pencil", "#E6E6EA")],
            [("Быстрая\nотправка", "share-2", "#4C6FE0"), ("Почта", "mail", "#E05A4A"), ("Мессенджер", "message-circle", "#3CB46A"),
             ("Сообщения", "message-2", "#4AA0E0"), ("Ещё", "dots", "#8A8A8E")]]
    from kivy.utils import get_color_from_hex as hx
    for row in rows:
        r = BoxLayout(size_hint_y=None, height=dp(92))
        for name, icon, c in row:
            b = PressBox(orientation="vertical", spacing=dp(4))
            circ = BoxLayout(size_hint=(None, None), size=(dp(52), dp(52)), padding=dp(12), pos_hint={"center_x": .5})
            paint(circ, hx(c), dp(26))
            circ.add_widget(Icon(name=icon, color=T.WHITE if c != "#E6E6EA" else T.BLUE))
            b.add_widget(circ)
            b.add_widget(lbl(name, 11, color=T.rgba(T.WHITE, 0.85), halign="center", valign="top"))
            b.bind(on_release=lambda *_, n=name: (sheet.close(), app.toast(f"Отправлено: {n.replace(chr(10), ' ')}")))
            r.add_widget(b)
        content.add_widget(r)
    sheet = BottomSheet(content, height=dp(410), color=(0.13, 0.13, 0.15, 1), radius=dp(24), margin=dp(8))
    cp.bind(on_release=lambda *_: (sheet.close(), app.toast("Ссылка скопирована")))
    sheet.open(app.root_layout)


# ============================================================================ «Сообщения»
class MessagesScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        from ..common import TopBar
        root.add_widget(TopBar("Сообщения"))
        box = BoxLayout(orientation="vertical", padding=(PAD, dp(4)))
        r = PressBox(size_hint_y=None, height=dp(72), spacing=dp(14))
        ic = BoxLayout(size_hint=(None, None), size=(dp(50), dp(50)), padding=dp(11), pos_hint={"center_y": .5})
        paint(ic, T.BLUE_LIGHT, dp(12))
        ic.add_widget(Icon(name="messages", color=T.BLUE))
        r.add_widget(ic)
        c = BoxLayout(orientation="vertical", padding=(0, dp(14)))
        c.add_widget(lbl("Чат поддержки", 16))
        c.add_widget(lbl("Мы здесь, чтобы помочь", 14, color=T.MUTED, weight="reg"))
        r.add_widget(c)
        r.bind(on_release=lambda *_: App.get_running_app().push(ChatScreen()))
        box.add_widget(r)
        sep = Widget(size_hint_y=None, height=1)
        paint(sep, T.LINE)
        box.add_widget(sep)
        box.add_widget(Widget())
        root.add_widget(box)
        self.add_widget(root)


class ChatScreen(Screen):
    """Простой чат поддержки с автоответом (заглушка)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        from ..common import TopBar
        root.add_widget(TopBar("Чат поддержки"))
        self.sv, self.box = vscroll(bottom=dp(10))
        self.box.padding = (PAD, dp(10), PAD, dp(10))
        root.add_widget(self.sv)
        bar = BoxLayout(size_hint_y=None, height=dp(64), padding=(PAD, dp(8)), spacing=dp(8))
        field = BoxLayout(padding=(dp(14), 0))
        paint(field, T.GRAY_BG, dp(22))
        self.inp = TextInput(hint_text="Сообщение", multiline=False, font_name="AppReg", font_size="16sp",
                             background_normal="", background_active="", background_color=(0, 0, 0, 0),
                             foreground_color=T.TEXT, cursor_color=T.BLUE, hint_text_color=T.MUTED, padding=(0, dp(13), 0, 0))
        self.inp.bind(on_text_validate=lambda *_: self.send())
        field.add_widget(self.inp)
        bar.add_widget(field)
        s = IconButton(icon="send", icon_color=T.WHITE, bg=T.BLUE, icon_size=dp(22), pos_hint={"center_y": .5})
        s.bind(on_release=lambda *_: self.send())
        bar.add_widget(s)
        root.add_widget(bar)
        self.add_widget(root)
        self.bubble("Здравствуйте! Я помощник SPORTLY. Чем могу помочь?", me=False)

    def bubble(self, text, me=True):
        row = BoxLayout(size_hint_y=None)
        l = lbl(text, 15, color=T.WHITE if me else T.TEXT, weight="reg", wrap=True, padding=(dp(12), dp(9)))
        holder = BoxLayout(size_hint=(0.78, None))
        paint(holder, T.BLUE if me else T.GRAY_BG, dp(14))
        holder.add_widget(l)
        l.bind(height=lambda o, h: (setattr(holder, "height", h), setattr(row, "height", h + dp(8))))
        if me:
            row.add_widget(Widget())
        row.add_widget(holder)
        if not me:
            row.add_widget(Widget())
        row.opacity = 0
        self.box.add_widget(row)
        Animation(opacity=1, d=0.25).start(row)
        Clock.schedule_once(lambda *_: setattr(self.sv, "scroll_y", 0), 0.05)

    def send(self):
        t = self.inp.text.strip()
        if not t:
            return
        self.inp.text = ""
        self.bubble(t)

        def failed(kind):
            self.bubble("Сообщение не доставлено: нет связи с сервером. Отправьте его ещё раз.", me=False)
            self.inp.text = t
        net.request(lambda: self.bubble("Спасибо! Оператор ответит в течение пары минут.", me=False), failed, delay=1.0)
