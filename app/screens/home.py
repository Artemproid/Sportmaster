"""Главная (по ролику ДЗ1): тёмный блок с баннерами и поиском, липкая шапка при прокрутке,
бренды, промо, вкладки «Женщинам / Мужчинам / Детям», виды спорта, подборки, популярные сервисы,
плавающая кнопка «Я в магазине»."""
import os
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from .. import theme as T
from .. import catalog_db
from ..common import (lbl, paint, vscroll, hscroll, product_strip, search_header, section_all, title2, PAD, GAP,
                      card_width, fit_w, ErrorView)
from ..net import net
from ..data import BANNERS, BRANDS, PRODUCTS, AUDIENCE_TABS, SPORTS, SERVICE_GROUPS, photo, tile
from ..icons import Icon
from ..widgets import IconButton, PressBox, SkeletonBox, stagger_in, shadow


def banner_size():
    w = Window.width * 0.66
    return w, w * 1.45


class BannerCard(PressBox):
    def __init__(self, i, b, **kw):
        w, h = banner_size()
        super().__init__(orientation="vertical", size_hint=(None, None), size=(w, h), padding=(dp(16), dp(18)), **kw)
        self.cat = b["cat"]
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._img = RoundedRectangle(source=os.path.join(T.IMG, f"banner{i}.jpg"), radius=[dp(16)])
        self.bind(pos=self._upd, size=self._upd)
        self.t1 = lbl(b["title"], 30, color=T.WHITE, weight="bold", valign="top", size_hint_y=None, height=dp(84),
                      line_height=0.92)
        self.add_widget(self.t1)
        self.t2 = lbl(b["sub"], 14, color=T.rgba(T.WHITE, 0.9), size_hint_y=None, height=dp(22))
        self.add_widget(self.t2)
        self.add_widget(Widget())
        self.bind(on_release=lambda *_: _open(self.cat))

    def _upd(self, *_):
        self._img.pos, self._img.size = self.pos, self.size


def _open(section, preset=None):
    from .catalog import open_section
    open_section(section, preset)


class BannerStrip(ScrollView):
    """Лента баннеров: доводка до ближайшего и автопрокрутка."""

    def __init__(self, **kw):
        w, h = banner_size()
        super().__init__(do_scroll_y=False, size_hint_y=None, height=h, bar_width=0, effect_cls="ScrollEffect", **kw)
        self.row = BoxLayout(size_hint_x=None, spacing=dp(10), padding=(PAD, 0))
        self.row.bind(minimum_width=self.row.setter("width"))
        self.cards = [BannerCard(i, b) for i, b in enumerate(BANNERS)]
        for c in self.cards:
            self.row.add_widget(c)
        self.add_widget(self.row)
        self.index = 0
        Clock.schedule_interval(self._auto, 5)

    def _step(self):
        return self.cards[0].width + dp(10)

    def go(self, i, d=0.45):
        i = max(0, min(len(self.cards) - 1, i))
        self.index = i
        span = self.row.width - self.width
        if span > 0:
            Animation.cancel_all(self, "scroll_x")
            Animation(scroll_x=min(1.0, i * self._step() / span), d=d, t="out_cubic").start(self)

    def on_touch_up(self, touch):
        r = super().on_touch_up(touch)
        if touch.grab_current is None and self.collide_point(*touch.opos):
            dx = touch.x - touch.ox
            if abs(dx) > dp(10):
                span = self.row.width - self.width
                cur = self.scroll_x * span / self._step()
                Clock.schedule_once(lambda *_: self.go(round(cur + (-0.35 if dx > 0 else 0.35))), 0.05)
        return r

    def _auto(self, _dt):
        if self.get_root_window() and not self._touch:
            self.go((self.index + 1) % len(self.cards), d=0.7)


class BrandTile(PressBox):
    def __init__(self, name, **kw):
        super().__init__(size_hint=(None, None), size=(dp(118), dp(66)), **kw)
        paint(self, T.BLUE_LIGHT, dp(12))
        self.add_widget(lbl(name.upper(), 14, weight="bold", halign="center"))
        from .catalog import open_brand
        self.bind(on_release=lambda *_: open_brand(name))


class BonusPromo(PressBox):
    """Синяя полоса «Как увеличить свою скидку?»."""

    def __init__(self, **kw):
        super().__init__(size_hint_y=None, height=dp(72), padding=(dp(18), dp(8)), **kw)
        from .profile import gradient
        with self.canvas.before:
            Color(1, 1, 1, 1)
            r = RoundedRectangle(radius=[dp(12)], texture=gradient((0.07, 0.24, 0.8), (0.12, 0.13, 0.45), horizontal=True))
        self.bind(pos=lambda *_: setattr(r, "pos", self.pos), size=lambda *_: setattr(r, "size", self.size))
        self.add_widget(lbl("Как увеличить\nсвою скидку?", 20, weight="semi", color=T.WHITE))
        b = BoxLayout(size_hint=(None, None), size=(dp(50), dp(50)), padding=dp(11), pos_hint={"center_y": .5})
        paint(b, T.RED, dp(12))
        b.add_widget(Icon(name="percentage", color=T.WHITE))
        self.add_widget(b)
        self.bind(on_release=lambda *_: App.get_running_app().go_tab("profile"))


class PromoCarousel(BoxLayout):
    """Большие промо-баннеры с точками (горизонтальная прокрутка)."""
    PROMOS = [("Кеды и кроссовки", "товары, которые есть\nтолько в SPORTLY", "shoes", (0.33, 0.27, 0.22), (0.62, 0.55, 0.47)),
              ("Рубашки и платья\nсо скидкой", "новая коллекция", "style", (0.15, 0.2, 0.33), (0.4, 0.48, 0.66)),
              ("Всё для тенниса", "ракетки, мячи и воланы", "tennis", (0.06, 0.36, 0.27), (0.17, 0.62, 0.45))]

    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(10), **kw)
        from .profile import gradient
        w = Window.width - PAD * 2
        h = w * 0.5
        self.sv = ScrollView(do_scroll_y=False, size_hint_y=None, height=h, bar_width=0, effect_cls="ScrollEffect")
        row = BoxLayout(size_hint_x=None, spacing=dp(10), padding=(PAD, 0))
        row.bind(minimum_width=row.setter("width"))
        from ..data import section_items
        for title, sub, section, c1, c2 in self.PROMOS:
            card = PressBox(size_hint=(None, None), size=(w, h), padding=(dp(18), dp(16)))
            with card.canvas.before:
                Color(1, 1, 1, 1)
                bg = RoundedRectangle(radius=[dp(14)], texture=gradient(c1, c2, horizontal=True))
            card.bind(pos=lambda o, *_, bg=bg: setattr(bg, "pos", o.pos), size=lambda o, *_, bg=bg: setattr(bg, "size", o.size))
            bg.size = card.size
            col = BoxLayout(orientation="vertical")
            col.add_widget(lbl(title, 21, weight="semi", color=T.WHITE, valign="top"))
            col.add_widget(lbl(sub, 13, color=T.rgba(T.WHITE, 0.85), valign="bottom"))
            card.add_widget(col)
            pic = RelativeLayout(size_hint_x=0.85)
            pic.add_widget(Image(source=photo(section_items(section)[0]["image"]), fit_mode="contain"))
            card.add_widget(pic)
            card.bind(on_release=lambda *_, s=section: _open(s))
            row.add_widget(card)
        self.sv.add_widget(row)
        self.add_widget(self.sv)
        from .product import Dots
        dr = BoxLayout(size_hint_y=None, height=dp(10))
        dr.add_widget(Widget())
        self.dots = Dots(len(self.PROMOS))
        dr.add_widget(self.dots)
        dr.add_widget(Widget())
        self.add_widget(dr)
        self.height = h + dp(20)
        self.sv.bind(scroll_x=lambda o, v: self.dots.set(int(round(v * (len(self.PROMOS) - 1)))))


class AudienceTabs(BoxLayout):
    """Вкладки «Женщинам / Мужчинам / Детям» с переезжающим подчёркиванием и сеткой 2×2."""
    ux = NumericProperty(0)
    uw = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, spacing=dp(14), **kw)
        bar = BoxLayout(size_hint_y=None, height=dp(48), padding=(PAD, 0), spacing=dp(22))
        self.tabs = []
        for i, name in enumerate(AUDIENCE_TABS):
            b = PressBox(size_hint_x=None)
            l = fit_w(lbl(name, 21, weight="semi", color=T.TEXT if i == 0 else T.MUTED))
            b.width = l.width
            b.add_widget(l)
            b.bind(on_release=lambda *_, i=i: self.select(i))
            self.tabs.append((b, l))
            bar.add_widget(b)
        with bar.canvas.after:
            Color(*T.LINE)
            self._base = Rectangle()
            Color(*T.BLUE)
            self._u = Rectangle()
        self.bar = bar
        bar.bind(pos=self._draw, size=self._draw)
        self.bind(ux=self._draw, uw=self._draw)
        self.add_widget(bar)
        self.grid = GridLayout(cols=2, spacing=dp(10), padding=(PAD, 0), size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.add_widget(self.grid)
        self.idx = 0
        self._fill(animate=False)
        self.bind(minimum_height=self.setter("height"))
        Clock.schedule_once(lambda *_: self._move(0, False), 0)

    def _draw(self, *_):
        self._base.pos, self._base.size = self.bar.pos, (self.bar.width, 1)
        self._u.pos, self._u.size = (self.ux, self.bar.y), (self.uw, dp(2.5))

    def _move(self, i, animate=True):
        b, _ = self.tabs[i]
        x, w = b.x - dp(14), b.width + dp(28)
        if i == 0:
            x, w = self.bar.x, b.right - self.bar.x + dp(14)
        if animate:
            Animation(ux=x, uw=w, d=0.3, t="out_cubic").start(self)
        else:
            self.ux, self.uw = x, w

    def select(self, i):
        if i == self.idx:
            return
        self.idx = i
        for j, (_, l) in enumerate(self.tabs):
            Animation(color=T.TEXT if j == i else T.MUTED, d=0.2).start(l)
        self._move(i)
        self._fill()

    def _fill(self, animate=True):
        self.grid.clear_widgets()
        name = list(AUDIENCE_TABS)[self.idx]
        w = (Window.width - PAD * 2 - dp(10)) / 2
        tiles = []
        gender = {"Женщинам": "Женский", "Мужчинам": "Мужской", "Детям": "Детский"}[name]
        sec_of = {"Одежда": "clothes", "Обувь": "shoes", "Аксессуары": "acc", "Стиль": "style", "Игры": "balls"}
        for title, key in AUDIENCE_TABS[name]:
            t = PressBox(size_hint_y=None, height=w * 0.58)
            paint(t, T.TILE, dp(12))
            fl = FloatLayout()
            fl.add_widget(Image(source=tile(key), fit_mode="contain", size_hint=(0.6, 0.92), pos_hint={"right": 1, "y": 0}))
            fl.add_widget(lbl(title, 16, valign="top", padding=(dp(14), dp(12)), pos_hint={"x": 0, "y": 0}))
            t.add_widget(fl)
            sec = sec_of[title]
            t.bind(on_release=lambda *_, s=sec: _open(s, None if s == "balls" else {"gender": {gender, "Унисекс"}}))
            self.grid.add_widget(t)
            tiles.append(t)
        if animate:
            stagger_in(tiles, 0.04)


class SportTile(PressBox):
    def __init__(self, name, key, color, **kw):
        super().__init__(size_hint=(None, None), size=(dp(176), dp(100)), **kw)
        paint(self, color, dp(12))
        fl = FloatLayout()
        fl.add_widget(Image(source=tile(key), fit_mode="contain", size_hint=(0.55, 0.9), pos_hint={"right": 1, "y": 0}))
        fl.add_widget(lbl(name, 16, valign="top", padding=(dp(12), dp(10)), pos_hint={"x": 0, "y": 0}))
        self.add_widget(fl)
        self.bind(on_release=lambda *_: _open("sport", {"sport": {name}}))


class FeatureBlock(RelativeLayout):
    """Большой фото-блок с заголовком и наезжающей лентой карточек («Утепленная обувь»)."""

    def __init__(self, title, items, **kw):
        cw = dp(170)
        strip = product_strip(items, width=cw)
        top = Window.width * 0.62
        super().__init__(size_hint_y=None, height=top + strip.height - dp(110), **kw)
        from .profile import gradient
        bg = Widget(size_hint=(1, None), height=top, pos_hint={"x": 0, "top": 1})
        with bg.canvas:
            Color(1, 1, 1, 1)
            r = Rectangle(texture=gradient((0.55, 0.56, 0.6), (0.85, 0.86, 0.88)))
        bg.bind(pos=lambda *_: setattr(r, "pos", bg.pos), size=lambda *_: setattr(r, "size", bg.size))
        self.add_widget(bg)
        self.add_widget(Image(source=photo(items[0]["image"]), fit_mode="contain", size_hint=(0.6, None), height=top * 0.75,
                              pos_hint={"right": 1, "top": 1}))
        self.add_widget(lbl(title, 24, weight="semi", color=T.WHITE, valign="top", size_hint=(0.6, None), height=dp(80),
                            pos_hint={"x": 0, "top": 1}, padding=(PAD, dp(20))))
        strip.pos_hint = {"x": 0, "y": 0}
        self.add_widget(strip)


class PopularServices(BoxLayout):
    def __init__(self, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(300), padding=(0, dp(18), 0, dp(16)), spacing=dp(14),
                         **kw)
        paint(self, T.NAVY, dp(16))
        self.add_widget(lbl("Популярные сервисы", 22, weight="semi", color=T.WHITE, size_hint_y=None, height=dp(34),
                            padding=(PAD, 0)))
        items = [it for g in SERVICE_GROUPS for it in g[1]]
        sv = ScrollView(do_scroll_y=False, bar_width=0, effect_cls="ScrollEffect")
        grid = GridLayout(rows=2, size_hint_x=None, spacing=(dp(6), dp(12)), padding=(dp(10), 0))
        grid.bind(minimum_width=grid.setter("width"))
        for name, icon, c1, c2 in items:
            grid.add_widget(service_icon(name, icon, c1, c2, dark=True))
        sv.add_widget(grid)
        self.add_widget(sv)


def service_icon(name, icon, c1, c2, dark=False):
    """Иконка сервиса: градиентный квадрат с иконкой + подпись."""
    from kivy.utils import get_color_from_hex as hx
    from .profile import gradient
    b = PressBox(orientation="vertical", size_hint=(None, None), size=(dp(86), dp(108)), spacing=dp(4))
    sq = RelativeLayout(size_hint=(None, None), size=(dp(64), dp(64)), pos_hint={"center_x": .5})
    with sq.canvas.before:
        Color(1, 1, 1, 1)
        RoundedRectangle(pos=(0, 0), size=(dp(64), dp(64)), radius=[dp(16)], texture=gradient(hx(c1), hx(c2)))
    sq.add_widget(Icon(name=icon, color=T.WHITE, size_hint=(None, None), size=(dp(34), dp(34)),
                       pos=(dp(15), dp(15))))
    b.add_widget(sq)
    b.add_widget(lbl(name, 12, color=T.WHITE if dark else T.TEXT, halign="center", valign="top"))
    from .extra import service_action
    b.bind(on_release=lambda *_: service_action(name))
    return b


class InStoreButton(PressBox):
    """Плавающая кнопка «Я в магазине»: при прокрутке вниз сворачивается в круг."""
    wide = NumericProperty(1)

    def __init__(self, **kw):
        super().__init__(size_hint=(None, None), size=(dp(178), dp(58)), padding=(dp(12), 0), spacing=dp(10), **kw)
        shadow(self, radius=dp(29), alpha=0.25)
        paint(self, T.NAVY, dp(29))
        c = BoxLayout(size_hint=(None, None), size=(dp(34), dp(34)), padding=dp(7), pos_hint={"center_y": .5})
        paint(c, (0.55, 0.65, 0.95, 1), dp(17))
        c.add_widget(Icon(name="navigation-filled", color=T.NAVY))
        self.add_widget(c)
        self.txt = lbl("Я в магазине", 16, color=T.WHITE)
        self.add_widget(self.txt)
        self.bind(wide=self._w)
        self.bind(on_release=lambda *_: App.get_running_app().show_card())

    def _w(self, *_):
        self.width = dp(58) + (dp(178) - dp(58)) * self.wide
        self.txt.opacity = max(0, self.wide * 1.4 - 0.4)

    def collapse(self, c):
        target = 0 if c else 1
        if abs(self.wide - target) > 0.01 and getattr(self, "_t", None) != target:
            self._t = target
            Animation.cancel_all(self, "wide")
            Animation(wide=target, d=0.3, t="out_cubic").start(self)


class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="home", **kw)
        self.body = FloatLayout()
        paint(self.body, T.BG)
        self.add_widget(self.body)
        self.loaded = False
        self._show_skeleton()

    def _dark_head(self, content):
        head = BoxLayout(orientation="vertical", size_hint_y=None, padding=(0, dp(14), 0, dp(14)), spacing=dp(12))
        head.bind(minimum_height=head.setter("height"))
        paint(head, T.NAVY, [0, 0, dp(22), dp(22)])
        for w in content:
            head.add_widget(w)
        return head

    def _show_skeleton(self):
        sv, box = vscroll()
        box.spacing = dp(16)
        w, h = banner_size()
        strip = BoxLayout(size_hint_y=None, height=h, padding=(PAD, 0), spacing=dp(10))
        for _ in range(2):
            strip.add_widget(SkeletonBox(radius=dp(16), size_hint_x=None, width=w))
        box.add_widget(self._dark_head([strip, search_header(dark=True)]))
        row = BoxLayout(size_hint_y=None, height=dp(66), padding=(PAD, 0), spacing=dp(10))
        for _ in range(3):
            row.add_widget(SkeletonBox(radius=dp(12), size_hint_x=None, width=dp(118)))
        box.add_widget(row)
        sv.pos_hint = {"x": 0, "y": 0}
        self.skeleton = sv
        self.body.add_widget(sv)

    def on_enter(self):
        if not getattr(App.get_running_app(), "ready", False):
            return
        if not self.loaded:
            self.loaded = True
            self._fetch()
        elif self.version != catalog_db.version:      # администратор изменил товары — обновляем витрину
            self.body.clear_widgets()
            self._load()

    def _fetch(self):
        net.request(self._load, self._failed, delay=0.8)

    def _failed(self, kind):
        self.body.clear_widgets()

        def retry():
            self.body.clear_widgets()
            self._show_skeleton()
            self._fetch()
        self.body.add_widget(ErrorView(kind, retry))

    def _load(self):
        self.version = catalog_db.version
        sv, box = vscroll()
        box.spacing = 0
        self.banners = BannerStrip()
        self.head = self._dark_head([self.banners, search_header(dark=True)])
        box.add_widget(self.head)

        box.add_widget(section_all("Бренды", lambda: App.get_running_app().go_tab("catalog")))
        br_sv, br = hscroll(dp(66))
        tiles = [BrandTile(b) for b in BRANDS]
        for t in tiles:
            br.add_widget(t)
        box.add_widget(br_sv)
        box.add_widget(Widget(size_hint_y=None, height=dp(20)))
        pw = BoxLayout(size_hint_y=None, height=dp(72), padding=(PAD, 0))
        pw.add_widget(BonusPromo())
        box.add_widget(pw)
        box.add_widget(Widget(size_hint_y=None, height=dp(16)))
        box.add_widget(PromoCarousel())
        box.add_widget(Widget(size_hint_y=None, height=dp(14)))
        box.add_widget(AudienceTabs())

        box.add_widget(section_all("Виды спорта", lambda: App.get_running_app().go_tab("catalog")))
        sp_sv, sp = hscroll(dp(100))
        colors = [(0.89, 0.95, 0.93, 1), (0.95, 0.9, 0.98, 1), (0.92, 0.93, 0.98, 1), (0.99, 0.94, 0.88, 1), (0.9, 0.94, 0.99, 1)]
        for (n, k), c in zip(SPORTS, colors):
            sp.add_widget(SportTile(n, k, c))
        box.add_widget(sp_sv)
        box.add_widget(Widget(size_hint_y=None, height=dp(24)))

        from ..data import section_items
        shoes = [p for p in PRODUCTS if p["kind"] in ("Кроссовки", "Кеды")]
        box.add_widget(FeatureBlock("Утепленная\nобувь", shoes[:6]))
        box.add_widget(title2("Выгодные цены на кроссовки"))
        box.add_widget(product_strip([p for p in shoes if p["old_price"]], width=dp(170)))
        box.add_widget(title2("Одежда для тренировок и города"))
        box.add_widget(product_strip([p for p in PRODUCTS if p["cat"] == "clothes"], width=dp(170)))
        box.add_widget(Widget(size_hint_y=None, height=dp(20)))
        ps = BoxLayout(size_hint_y=None, height=dp(300), padding=(PAD, 0))
        ps.add_widget(PopularServices())
        box.add_widget(ps)
        box.add_widget(title2("Мячи и инвентарь: подойдут на все случаи"))
        box.add_widget(product_strip([p for p in PRODUCTS if p["cat"] in ("balls", "gear")][:12], width=dp(170)))

        sv.opacity = 0
        sv.pos_hint = {"x": 0, "y": 0}
        self.body.add_widget(sv)
        self.sv = sv
        Animation(opacity=1, d=0.35).start(sv)
        old = self.skeleton
        a = Animation(opacity=0, d=0.25)
        a.bind(on_complete=lambda *_: (self.body.remove_widget(old),
                                       [s.stop() for s in old.walk() if isinstance(s, SkeletonBox)]))
        a.start(old)
        stagger_in(tiles, 0.05)

        # липкая тёмная шапка с поиском (появляется, когда баннеры уехали вверх)
        self.sticky = BoxLayout(size_hint=(1, None), height=dp(74), pos_hint={"x": 0, "top": 1}, padding=(0, dp(4), 0, dp(8)))
        paint(self.sticky, T.NAVY, [0, 0, dp(22), dp(22)])
        self.sticky.add_widget(search_header(dark=True))
        self.sticky.opacity = 0
        self.sticky.disabled = True
        self.body.add_widget(self.sticky)

        self.instore = InStoreButton(pos_hint={"right": 0.97}, y=dp(96))
        self.body.add_widget(self.instore)
        self._last_y = 1
        sv.bind(scroll_y=self._on_scroll)

    def _on_scroll(self, sv, y):
        span = max(1, sv.viewport_size[1] - sv.height)
        scrolled = (1 - y) * span
        show = scrolled > self.head.height - dp(70)
        if show != (not self.sticky.disabled):
            self.sticky.disabled = not show
            Animation.cancel_all(self.sticky, "opacity")
            Animation(opacity=1 if show else 0, d=0.18).start(self.sticky)
        self.instore.collapse(y < self._last_y - 0.0005 and scrolled > dp(60))
        if y > self._last_y + 0.002 or scrolled < dp(60):
            self.instore.collapse(False)
        self._last_y = y
