"""Карточка товара: галерея, цена, размеры, наличие, плавающая панель «В корзину»."""
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.carousel import Carousel
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget

from .. import theme as T
from ..common import lbl, paint, vscroll, hscroll, product_strip, ShakeBox, PAD, fit_w, NAV_SPACE
from ..data import PRODUCTS, BY_ID, discount, photo, size_in
from ..icons import Icon
from ..store import store
from ..widgets import IconButton, SizeChip, AppButton, PressBox, ProductCard, BottomSheet, shadow


class Dots(BoxLayout):
    """Точки галереи: активная тёмная и чуть больше."""

    def __init__(self, n, **kw):
        super().__init__(size_hint=(None, None), height=dp(8), spacing=dp(6), **kw)
        self.dots = []
        for _ in range(n):
            d = Widget(size_hint=(None, None), size=(dp(7), dp(7)))
            d.col = paint(d, T.LINE, dp(4))
            self.dots.append(d)
            self.add_widget(d)
        self.width = n * dp(9) + (n - 1) * dp(6)
        self.set(0)

    def set(self, idx):
        for i, d in enumerate(self.dots):
            on = i == idx
            Animation(size=(dp(9), dp(9)) if on else (dp(7), dp(7)), d=0.25, t="out_back").start(d)
            Animation(rgba=T.TEXT if on else T.LINE, d=0.25).start(d.col)


class Toggle(IconButton):
    """Иконка-переключатель в шапке (сердце / сравнение)."""

    def __init__(self, kind, pid, **kw):
        super().__init__(icon_size=dp(28), **kw)
        self.kind, self.pid = kind, pid
        store.bind(favorites=self._sync, compare=self._sync)
        self._sync()
        self.bind(on_release=self._toggle)

    def _sync(self, *_):
        if self.kind == "fav":
            on = self.pid in store.favorites
            self.icon, self.icon_color = ("heart_fill", T.RED) if on else ("heart", T.TEXT)
        else:
            on = self.pid in store.compare
            self.icon, self.icon_color = "compare", (T.BLUE if on else T.TEXT)

    def _toggle(self, *_):
        app = App.get_running_app()
        if self.kind == "fav":
            on = store.toggle_fav(self.pid)
            app.toast("Добавлено в избранное" if on else "Удалено из избранного")
        else:
            on = store.toggle_compare(self.pid)
            app.toast("Добавлено к сравнению" if on else "Удалено из сравнения")
        self.icon_size = dp(34)
        Animation(icon_size=dp(28), d=0.4, t="out_elastic").start(self)


def tag(text, bg, fg, bold=True):
    b = BoxLayout(size_hint=(None, None), height=dp(28), padding=(dp(8), 0))
    paint(b, bg, dp(7))
    l = fit_w(lbl(text, 13, bold=bold, color=fg, halign="center"))
    b.add_widget(l)
    b.width = l.width + dp(16)
    return b


class ProductScreen(Screen):
    def __init__(self, pid, pick_size=False, **kw):
        super().__init__(**kw)
        p = self.p = BY_ID[pid]
        self.size_sel = None if p["sizes"] else "—"
        self.system = "RUS"
        self.pick_size = pick_size

        root = FloatLayout()
        paint(root, T.BG)
        main = BoxLayout(orientation="vertical", pos_hint={"x": 0, "y": 0})
        # --- шапка
        bar = BoxLayout(size_hint_y=None, height=dp(60), padding=(dp(6), 0, dp(8), 0), spacing=dp(2))
        paint(bar, T.BG)
        back = IconButton(icon="back", icon_size=dp(28), pos_hint={"center_y": .5})
        back.bind(on_release=lambda *_: App.get_running_app().back())
        bar.add_widget(back)
        self.bar_title = lbl(p["name"], 16, bold=True, shorten=True, shorten_from="right")
        self.bar_title.opacity = 0
        bar.add_widget(self.bar_title)
        for kind in ("fav", "compare"):
            bar.add_widget(Toggle(kind, p["id"], pos_hint={"center_y": .5}))
        share = IconButton(icon="share", icon_size=dp(28), pos_hint={"center_y": .5})
        share.bind(on_release=lambda *_: App.get_running_app().toast("Ссылка на товар скопирована"))
        bar.add_widget(share)
        main.add_widget(bar)

        self.sv, box = vscroll(bottom=NAV_SPACE + dp(90))
        box.spacing = 0
        main.add_widget(self.sv)
        root.add_widget(main)

        # --- галерея
        gal = FloatLayout(size_hint_y=None, height=Window.width * 1.0)
        paint(gal, T.GRAY_BG, [0, 0, dp(22), dp(22)])
        self.car = Carousel(loop=False, anim_move_duration=0.35, anim_type="out_cubic", scroll_distance=dp(10),
                            pos_hint={"x": 0, "y": 0})
        self.photos = []
        for fn in p["photos"]:
            img = Image(source=photo(fn), fit_mode="contain")
            self.car.add_widget(img)
            self.photos.append(img)
        gal.add_widget(self.car)
        sim = PressBox(size_hint=(None, None), size=(dp(132), dp(42)), pos_hint={"right": .96, "y": .04}, spacing=dp(6),
                       padding=(dp(12), 0))
        paint(sim, T.rgba(T.NAVY, 0.55), dp(12))
        sim.add_widget(Icon(name="copy", color=T.WHITE, size_hint_x=None, width=dp(20)))
        sim.add_widget(lbl("Похожие", 15, color=T.WHITE))
        sim.bind(on_release=lambda *_: self.sv.scroll_to(self.similar_title, padding=dp(10)))
        gal.add_widget(sim)
        box.add_widget(gal)
        drow = BoxLayout(size_hint_y=None, height=dp(30))
        drow.add_widget(Widget())
        dots = Dots(len(self.photos))
        self.car.bind(index=lambda c, i: dots.set(i or 0))
        drow.add_widget(dots)
        drow.add_widget(Widget())
        box.add_widget(drow)

        body = BoxLayout(orientation="vertical", size_hint_y=None, padding=(PAD, 0), spacing=dp(14))
        body.bind(minimum_height=body.setter("height"))
        box.add_widget(body)

        # --- метки
        tags = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
        if discount(p):
            tags.add_widget(tag(f"-{discount(p)}%", T.RED, T.WHITE))
            tags.add_widget(tag("Выгодная цена", T.RED_SOFT, T.RED, bold=False))
        if p["hit"]:
            tags.add_widget(tag("Хит продаж", T.BLUE_LIGHT, T.BLUE, bold=False))
        tags.add_widget(tag("Оригинал", T.rgba(T.NAVY, 0.85), T.WHITE, bold=False))
        tags.add_widget(Widget())
        body.add_widget(tags)

        video = PressBox(size_hint_y=None, height=dp(50), spacing=dp(8))
        paint(video, T.BLUE_LIGHT, dp(12))
        video.add_widget(Widget())
        video.add_widget(Icon(name="play", color=T.BLUE, size_hint_x=None, width=dp(24)))
        video.add_widget(fit_w(lbl("Смотреть обзор", 14, color=T.BLUE)))
        video.add_widget(Widget())
        video.bind(on_release=lambda *_: App.get_running_app().toast("Видеообзор недоступен в демо-версии"))
        body.add_widget(video)

        # --- бренд и рейтинг
        br = BoxLayout(size_hint_y=None, height=dp(40))
        br.add_widget(lbl(p["brand"].upper(), 22, weight="bold"))
        stars = BoxLayout(size_hint_x=None, width=dp(190), spacing=dp(1))
        for i in range(5):
            stars.add_widget(Icon(name="star", color=T.BLUE if i < round(p["rating"]) else T.LINE,
                                  size_hint_x=None, width=dp(20)))
        stars.add_widget(lbl(f"  {p['rating']} [color=8b909c]({p['reviews']})[/color]", 15, markup=True))
        br.add_widget(stars)
        body.add_widget(br)
        body.add_widget(lbl(p["name"], 21, wrap=True))

        # --- карточка цены
        from .profile import gradient
        pc = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(150), padding=(dp(18), dp(14), dp(14), dp(6)))
        with pc.canvas.before:
            Color(1, 1, 1, 1)
            pc_bg = RoundedRectangle(radius=[dp(16)], texture=gradient(T.BLUE, T.BLUE_2, horizontal=True))
            Color(1, 1, 1, 0.08)
            deco = RoundedRectangle(radius=[dp(60)])
        def upd(*_):
            pc_bg.pos, pc_bg.size = pc.pos, pc.size
            deco.pos, deco.size = (pc.right - dp(110), pc.top - dp(100)), (dp(150), dp(150))
        pc.bind(pos=upd, size=upd)
        h1 = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(6))
        h1.add_widget(fit_w(lbl("Цена в приложении", 17, color=T.WHITE)))
        info = IconButton(icon="info", icon_color=T.WHITE, icon_size=dp(22), size=(dp(28), dp(28)), pos_hint={"center_y": .5})
        info.bind(on_release=lambda *_: App.get_running_app().toast("Цена действует при заказе в приложении"))
        h1.add_widget(info)
        h1.add_widget(Widget())
        pc.add_widget(h1)
        h2 = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(12))
        h2.add_widget(fit_w(lbl(T.price(p["price"]), 32, weight="bold", color=T.WHITE)))
        if p["old_price"]:
            h2.add_widget(fit_w(lbl(f"[s]{T.price(p['old_price'])}[/s]", 18, color=T.rgba(T.WHITE, 0.7), markup=True,
                                    weight="reg")))
        h2.add_widget(Widget())
        pc.add_widget(h2)
        line = Widget(size_hint_y=None, height=1)
        paint(line, T.rgba(T.WHITE, 0.25))
        pc.add_widget(line)
        h3 = PressBox(spacing=dp(6))
        h3.add_widget(lbl("Забронировать в магазине", 15, color=T.WHITE))
        circ = BoxLayout(size_hint=(None, None), size=(dp(30), dp(30)), pos_hint={"center_y": .5}, padding=dp(4))
        paint(circ, T.WHITE, dp(15))
        circ.add_widget(Icon(name="chevron", color=T.TEXT))
        h3.add_widget(circ)
        h3.bind(on_release=lambda *_: App.get_running_app().push(__import__("app.screens.extra", fromlist=["x"]).StoresScreen(product=p)))
        pc.add_widget(h3)
        body.add_widget(pc)

        inst = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(14), 0), spacing=dp(10))
        paint(inst, T.GRAY_BG, dp(12))
        chip = BoxLayout(size_hint=(None, None), size=(dp(70), dp(28)), pos_hint={"center_y": .5})
        paint(chip, T.NAVY, dp(7))
        chip.add_widget(lbl("Частями", 11, bold=True, color=T.WHITE, halign="center"))
        inst.add_widget(chip)
        inst.add_widget(lbl(f"4 платежа по {T.price(p['price'] / 4)}", 15))
        inst.add_widget(Icon(name="info", color=T.MUTED, size_hint_x=None, width=dp(22)))
        body.add_widget(inst)

        # --- размеры
        self.size_box = None
        if p["sizes"]:
            sz = ShakeBox(orientation="vertical", size_hint_y=None, spacing=dp(12), padding=(0, dp(10), 0, 0))
            sz.bind(minimum_height=sz.setter("height"))
            hdr = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(16))
            self.sys_labels = {}
            for s in ("RUS", "US", "EUR"):
                b = PressBox(size_hint_x=None, width=dp(48))
                l = lbl(s, 17, color=T.BLUE if s == "RUS" else T.TEXT)
                b.add_widget(l)
                b.bind(on_release=lambda *_, s=s: self.set_system(s))
                self.sys_labels[s] = l
                hdr.add_widget(b)
            hdr.add_widget(Widget())
            tb = PressBox(size_hint_x=None)
            tl = fit_w(lbl("Таблица размеров", 15, color=T.BLUE))
            tb.width = tl.width
            tb.add_widget(tl)
            from .extra import size_table_sheet
            tb.bind(on_release=lambda *_: size_table_sheet(p))
            hdr.add_widget(tb)
            sz.add_widget(hdr)
            self.size_title = lbl("Выберите размер", 14, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(18))
            sz.add_widget(self.size_title)
            chips_sv, chips = hscroll(dp(62))
            chips.padding = (0, 0)
            chips.spacing = dp(10)
            self.size_chips = []
            for rus, hint in p["sizes"]:
                c = SizeChip(text=rus, sub=hint if p["cat"] == "shoes" else "", value=rus)
                c.bind(on_release=lambda w: self.pick(w))
                chips.add_widget(c)
                self.size_chips.append(c)
            sz.add_widget(chips_sv)
            if p["cat"] == "shoes":
                fl = PressBox(size_hint_y=None, height=dp(26))
                fl.add_widget(lbl("Как узнать длину стопы?", 15, color=T.BLUE))
                fl.bind(on_release=lambda *_: size_table_sheet(p))
                sz.add_widget(fl)
            self.size_box = sz
            body.add_widget(sz)

        # --- наличие
        av = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(178), padding=(dp(16), dp(14)), spacing=dp(6))
        paint(av, T.GRAY_BG, dp(16))
        av.add_widget(lbl("Доступность товара", 19, bold=True, size_hint_y=None, height=dp(30)))
        for icon, a, b in (("store", "Самовывоз", "Сегодня из 12 магазинов, бесплатно"),
                           ("delivery", "Доставка курьером", "Завтра, бесплатно от 3 000 ₽")):
            r = PressBox(spacing=dp(12))
            ic = BoxLayout(size_hint_x=None, width=dp(38), padding=(0, dp(12)))
            ic.add_widget(Icon(name=icon, color=T.BLUE))
            r.add_widget(ic)
            c = BoxLayout(orientation="vertical", padding=(0, dp(8)))
            c.add_widget(lbl(a, 15, bold=True))
            c.add_widget(lbl(b, 13, color=T.MUTED, weight="reg"))
            r.add_widget(c)
            r.add_widget(Icon(name="chevron", color=T.MUTED, size_hint_x=None, width=dp(20)))
            av.add_widget(r)
        body.add_widget(av)

        # --- описание
        body.add_widget(lbl("О товаре", 19, bold=True, size_hint_y=None, height=dp(28)))
        self.desc_clip = BoxLayout(size_hint_y=None, height=dp(66))
        clip = StencilView()
        self.desc = lbl(p["desc"], 15, wrap=True, weight="reg")
        self.desc.line_height = 1.3
        clip.add_widget(self.desc)
        clip.bind(pos=self._place_desc, size=self._place_desc)
        self.desc.bind(height=self._place_desc)
        self._clip = clip
        self.desc_clip.add_widget(clip)
        body.add_widget(self.desc_clip)
        more = PressBox(size_hint_y=None, height=dp(26), spacing=dp(4))
        self.more_lbl = fit_w(lbl("Читать полностью", 15, color=T.BLUE))
        more.add_widget(self.more_lbl)
        self.more_ic = Icon(name="chevron_down", color=T.BLUE, size_hint_x=None, width=dp(20))
        more.add_widget(self.more_ic)
        more.add_widget(Widget())
        more.bind(on_release=lambda *_: self.toggle_desc())
        body.add_widget(more)
        self.expanded = False

        # --- похожие
        self.similar_title = lbl("Похожие товары", 22, bold=True, size_hint_y=None, height=dp(64), padding=(PAD, 0))
        box.add_widget(self.similar_title)
        same = [x for x in PRODUCTS if x["cat"] == p["cat"] and x["id"] != p["id"]]
        box.add_widget(product_strip(same or PRODUCTS[:6]))

        # --- плавающая тёмная панель покупки
        self.buybar = BoxLayout(size_hint=(None, None), height=dp(76), padding=(dp(18), dp(10), dp(10), dp(10)),
                                spacing=dp(10))
        shadow(self.buybar, radius=dp(18), alpha=0.25)
        paint(self.buybar, T.NAVY, dp(18))
        pcol = BoxLayout(orientation="vertical", size_hint_x=0.42, padding=(0, dp(4)))
        if p["old_price"]:
            pcol.add_widget(lbl(f"[s]{T.price(p['old_price'])}[/s]", 13, color=T.rgba(T.WHITE, 0.6), markup=True,
                                weight="reg"))
        pcol.add_widget(lbl(T.price(p["price"]), 21, weight="bold", color=T.WHITE))
        self.buybar.add_widget(pcol)
        self.buy = AppButton(text="В корзину", height=dp(56))
        self.buy.pos_hint = {"center_y": .5}
        self.buy.bind(on_release=lambda *_: self.add_to_cart())
        self.buybar.add_widget(self.buy)
        root.add_widget(self.buybar)
        Window.bind(size=self._place_bar)
        self.bind(size=self._place_bar)
        self._place_bar()

        self.add_widget(root)
        self.sv.bind(scroll_y=self._on_scroll)
        if store.in_cart(p["id"]):
            self.buy.text, self.buy.icon = "В корзине", "check"

    # ----- поведение
    def on_enter(self):
        if self.pick_size and self.size_box:
            self.pick_size = False
            Clock.schedule_once(lambda *_: self._ask_size(), 0.15)

    def _place_bar(self, *_):
        self.buybar.width = Window.width - PAD * 2
        self.buybar.x = PAD
        self.buybar.y = dp(88)

    def _place_desc(self, *_):
        self.desc.width = self._clip.width
        self.desc.x = self._clip.x
        self.desc.top = self._clip.top

    def toggle_desc(self):
        self.expanded = not self.expanded
        target = self.desc.height + dp(4) if self.expanded else dp(66)
        Animation(height=target, d=0.35, t="out_cubic").start(self.desc_clip)
        self.more_lbl.text = "Свернуть" if self.expanded else "Читать полностью"
        self.more_ic.name = "chevron_up" if self.expanded else "chevron_down"

    def _on_scroll(self, sv, y):
        if sv.viewport_size[1] <= sv.height:
            return
        scrolled = (1 - y) * (sv.viewport_size[1] - sv.height)
        k = max(0.0, min(1.0, (scrolled - Window.width * 0.7) / dp(60)))
        self.bar_title.opacity = k

    def set_system(self, s):
        self.system = s
        for k, l in self.sys_labels.items():
            Animation(color=T.BLUE if k == s else T.TEXT, d=0.2).start(l)
        for c in self.size_chips:
            c.text = size_in(s, self.p["cat"], c.value)
            c.pscale = 0.9
            Animation(pscale=1, d=0.3, t="out_back").start(c)

    def pick(self, chip):
        for c in self.size_chips:
            c.active = c is chip
        self.size_sel = chip.value
        self.size_title.text = f"Размер: {chip.text} ({self.system})"
        self.size_title.color = T.TEXT

    def _ask_size(self):
        self.sv.scroll_to(self.size_box, padding=dp(60))
        Clock.schedule_once(lambda *_: self.size_box.shake(), 0.3)
        self.size_title.color = T.RED
        self.size_title.text = "Выберите размер"

    def add_to_cart(self):
        app = App.get_running_app()
        if self.buy.text == "В корзине":
            app.go_tab("cart")
            return
        if not self.size_sel:
            self._ask_size()
            app.toast("Выберите размер")
            return
        store.add(self.p["id"], self.size_sel)
        img = self.photos[self.car.index or 0]
        app.fly_to_cart(img, toast=False)
        self.buy.text, self.buy.icon = "В корзине", "check"
        Animation(bg=T.SUCCESS, d=0.25).start(self.buy)
        Clock.schedule_once(lambda *_: Animation(bg=T.BLUE, d=0.4).start(self.buy), 1.2)
        Clock.schedule_once(lambda *_: self.show_upsell(), 0.75)

    def show_upsell(self):
        """Шторка «С этим товаром часто покупают»."""
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=(0, dp(6), 0, dp(20)), spacing=dp(14))
        content.add_widget(lbl("С этим товаром часто покупают", 21, bold=True, size_hint_y=None, height=dp(34),
                               padding=(PAD, 0)))
        others = [x for x in PRODUCTS if x["cat"] != self.p["cat"]][:6]
        content.add_widget(product_strip(others, width=dp(176)))
        btns = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(116), spacing=dp(10), padding=(PAD, 0))
        sheet = None
        go = AppButton(text="Перейти в корзину")
        cont = AppButton.light(text="Продолжить покупки")
        btns.add_widget(go)
        btns.add_widget(cont)
        content.add_widget(btns)
        sheet = BottomSheet(content, height=dp(176) * 1.2 + dp(330))
        go.bind(on_release=lambda *_: (sheet.close(), Clock.schedule_once(lambda *_: app.go_tab("cart"), 0.25)))
        cont.bind(on_release=lambda *_: sheet.close())
        sheet.open(app.root_layout)
