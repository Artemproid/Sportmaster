from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line, Ellipse
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from .. import theme as T
from ..common import (lbl, paint, vscroll, hscroll, product_grid, product_strip, TopBar, CountLabel, empty_state, PAD,
                      fit_w, city_row, NAV_SPACE)
from ..common import ErrorView
from ..data import BY_ID, PRODUCTS, discount, photo
from ..net import net
from ..icons import Icon
from ..store import store
from ..widgets import IconButton, AppButton, PressBox, LoadRing, SquareCheck, Toggle, BottomSheet, stagger_in, shadow


def bonus_chip(n, h=dp(26)):
    """Жёлтая «монетка» с числом бонусов."""
    b = BoxLayout(size_hint=(None, None), height=h, padding=(dp(3), dp(3), dp(9), dp(3)), spacing=dp(4))
    with b.canvas.before:
        Color(*T.YELLOW)
        r = RoundedRectangle(radius=[h / 2])
        Color(1, 1, 1, 1)
        inner = RoundedRectangle(radius=[h / 2 - dp(2)])
    def upd(*_):
        r.pos, r.size = b.pos, b.size
        inner.pos, inner.size = (b.x + dp(2), b.y + dp(2)), (b.width - dp(4), b.height - dp(4))
    b.bind(pos=upd, size=upd)
    coin = Widget(size_hint_x=None, width=h - dp(6))
    with coin.canvas:
        Color(*T.YELLOW)
        ce = Ellipse()
        Color(0.93, 0.68, 0.0, 1)
        cl = Line(width=1)
    coin.bind(pos=lambda *_: (setattr(ce, "pos", coin.pos), setattr(ce, "size", coin.size),
                              setattr(cl, "circle", (coin.center_x, coin.center_y, coin.width * 0.3))),
              size=lambda *_: (setattr(ce, "pos", coin.pos), setattr(ce, "size", coin.size)))
    b.add_widget(coin)
    t = fit_w(lbl(str(n), 12, weight="bold", italic=True))
    b.add_widget(t)
    b.width = t.width + h + dp(8)
    b.num = t
    return b


class QtyBox(PressBox):
    """Серый выпадающий «1 ▾» — открывает шторку выбора количества."""

    def __init__(self, qty, on_change, **kw):
        super().__init__(size_hint=(None, None), size=(dp(60), dp(44)), padding=(dp(14), 0), **kw)
        paint(self, T.GRAY_BG, dp(4))
        self.l = lbl(str(qty), 16)
        self.add_widget(self.l)
        self.add_widget(Icon(name="caret-down-filled", color=T.MUTED, size_hint_x=None, width=dp(14)))
        self.cb = on_change
        self.bind(on_release=lambda *_: self.choose())

    def choose(self):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(16)))
        content.add_widget(lbl("Количество", 21, weight="semi", size_hint_y=None, height=dp(46)))
        sv, row = hscroll(dp(58))
        row.padding = (0, dp(4))
        row.spacing = dp(8)
        sheet = None
        for q in range(1, 11):
            c = PressBox(size_hint_x=None, width=dp(50))
            paint(c, T.BLUE_LIGHT if str(q) == self.l.text else T.GRAY_BG, dp(10))
            c.add_widget(lbl(str(q), 17, halign="center", color=T.BLUE if str(q) == self.l.text else T.TEXT))
            c.bind(on_release=lambda *_, q=q: (setattr(self.l, "text", str(q)), sheet.close(), self.cb(q)))
            row.add_widget(c)
        content.add_widget(sv)
        sheet = BottomSheet(content, height=dp(150))
        sheet.open(app.root_layout)


class CartItem(BoxLayout):
    def __init__(self, key, p, size, qty, screen, **kw):
        super().__init__(size_hint_y=None, height=dp(250), padding=(dp(6), dp(14), PAD, dp(10)), spacing=dp(10), **kw)
        self.key, self.screen = key, screen
        cbw = BoxLayout(size_hint_x=None, width=dp(30), padding=(0, 0, 0, dp(150)))
        self.cb = SquareCheck(active=key in store.selected)
        self.cb.bind(active=self._sel)
        cbw.add_widget(self.cb)
        self.add_widget(cbw)
        th = BoxLayout(size_hint=(None, None), size=(dp(70), dp(86)), pos_hint={"top": 1})
        paint(th, T.GRAY_BG, dp(6))
        th.add_widget(Image(source=photo(p["image"]), fit_mode="contain"))
        thw = BoxLayout(size_hint_x=None, width=dp(70), orientation="vertical")
        thw.add_widget(th)
        thw.add_widget(Widget())
        th.bind(on_touch_up=lambda w, t: w.collide_point(*t.pos) and t.grab_current is None and
                abs(t.ox - t.x) < dp(6) and App.get_running_app().open_product(p["id"]))
        self.add_widget(thw)
        col = BoxLayout(orientation="vertical", spacing=dp(2))
        tags = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(4))
        d = discount(p)
        if d:
            t1 = BoxLayout(size_hint_x=None, padding=(dp(6), 0))
            paint(t1, T.RED, dp(4))
            l1 = fit_w(lbl(f"-{d}%", 12, color=T.WHITE))
            t1.add_widget(l1)
            t1.width = l1.width + dp(12)
            tags.add_widget(t1)
            t2 = BoxLayout(size_hint_x=None, padding=(dp(6), 0))
            paint(t2, T.PINK_TAG, dp(4))
            l2 = fit_w(lbl("Выгодная скидка", 12, color=T.PINK_TEXT))
            t2.add_widget(l2)
            t2.width = l2.width + dp(12)
            tags.add_widget(t2)
        tags.add_widget(Widget())
        more = IconButton(icon="dots", icon_color=T.MUTED, icon_size=dp(22), size=(dp(34), dp(24)))
        more.bind(on_release=lambda *_: self.menu(p))
        tags.add_widget(more)
        col.add_widget(tags)
        col.add_widget(lbl(p["name"], 15, weight="reg", max_lines=2, valign="top", size_hint_y=None, height=dp(42)))
        col.add_widget(lbl("Цвет: Черный", 14, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(20)))
        if size != "—":
            col.add_widget(lbl(f"Размер: {size}", 14, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(20)))
        pr = BoxLayout(size_hint_y=None, height=dp(48))
        pc = BoxLayout(orientation="vertical")
        pc.add_widget(lbl(f"[s]{T.price(p['old_price'] * qty)}[/s]" if p["old_price"] else "", 13, color=T.MUTED,
                          markup=True, weight="reg"))
        pc.add_widget(lbl(T.price(p["price"] * qty), 17, weight="semi", color=T.BLUE if p["old_price"] else T.TEXT))
        pr.add_widget(pc)
        pr.add_widget(QtyBox(qty, lambda q: store.set_qty(key, q), pos_hint={"center_y": .5}))
        col.add_widget(pr)
        ex = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(6))
        ex.add_widget(Icon(name="alert-circle-filled", color=T.TEXT, size_hint_x=None, width=dp(18)))
        ex.add_widget(lbl("Доступен для экспресс-доставки", 13, weight="reg"))
        col.add_widget(ex)
        rec = PressBox(size_hint_y=None, height=dp(34))
        rec.add_widget(lbl("Также рекомендуем", 16, color=T.BLUE))
        rec.bind(on_release=lambda *_: self.recommend(p))
        col.add_widget(rec)
        self.add_widget(col)

    def _sel(self, _w, on):
        (store.selected.add if on else store.selected.discard)(self.key)
        store.save()
        self.screen.refresh_totals()

    def menu(self, p):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(16)))
        sheet = None
        for icon, text, fn in (("heart", "Перенести в избранное", lambda: (store.toggle_fav(p["id"]) if p["id"] not in store.favorites else None,
                                                                         self.remove(), app.toast("Товар перенесён в избранное"))),
                               ("share", "Поделиться", lambda: app.toast("Ссылка скопирована")),
                               ("trash", "Удалить", lambda: self.remove())):
            r = PressBox(size_hint_y=None, height=dp(54), spacing=dp(14))
            r.add_widget(Icon(name=icon, color=T.RED if icon == "trash" else T.TEXT, size_hint_x=None, width=dp(24)))
            r.add_widget(lbl(text, 16, color=T.RED if icon == "trash" else T.TEXT))
            r.bind(on_release=lambda *_, fn=fn: (sheet.close(), fn()))
            content.add_widget(r)
        sheet = BottomSheet(content, height=dp(54) * 3 + dp(40))
        sheet.open(app.root_layout)

    def recommend(self, p):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=(0, 0, 0, dp(20)), spacing=dp(10))
        content.add_widget(lbl("Также рекомендуем", 21, weight="semi", size_hint_y=None, height=dp(40), padding=(PAD, 0)))
        content.add_widget(product_strip([x for x in PRODUCTS if x["cat"] == p["cat"] and x["id"] != p["id"]][:8], width=dp(160)))
        sheet = BottomSheet(content, height=dp(160) * 1.2 + dp(230))
        sheet.open(app.root_layout)

    def remove(self):
        a = Animation(opacity=0, d=0.18) + Animation(height=0, d=0.22, t="in_cubic")
        a.bind(on_complete=lambda *_: (store.selected.discard(self.key), store.set_qty(self.key, 0)))
        a.start(self)


class Coupon(PressBox):
    """Купон-«билет» с вертикальной надписью «ПРИМЕНИТЬ»."""

    def __init__(self, text, dates, color, **kw):
        super().__init__(size_hint=(None, None), size=(dp(190), dp(78)), padding=(dp(14), dp(8), dp(4), dp(8)), **kw)
        with self.canvas.before:
            Color(*color)
            self._r = RoundedRectangle(radius=[dp(8)])
            Color(1, 1, 1, 1)
            self._c1 = Ellipse()
            self._c2 = Ellipse()
            Color(1, 1, 1, 0.5)
            self._dash = Line(dash_length=4, dash_offset=4, width=1)
        self.bind(pos=self._upd, size=self._upd)
        col = BoxLayout(orientation="vertical")
        col.add_widget(lbl(text, 13, color=T.WHITE, max_lines=2, valign="top"))
        col.add_widget(lbl(dates, 10, color=T.rgba(T.WHITE, 0.8), weight="reg", size_hint_y=None, height=dp(14)))
        self.add_widget(col)
        v = fit_w(lbl("ПРИМЕНИТЬ", 9, weight="bold", color=T.WHITE, halign="center"))
        holder = Widget(size_hint_x=None, width=dp(22))
        from kivy.graphics import PushMatrix, PopMatrix, Rotate
        with v.canvas.before:
            PushMatrix()
            rot = Rotate(angle=90)
        with v.canvas.after:
            PopMatrix()
        holder.add_widget(v)
        holder.bind(pos=lambda *_: (setattr(v, "center", holder.center), setattr(rot, "origin", holder.center)),
                    size=lambda *_: (setattr(v, "center", holder.center), setattr(rot, "origin", holder.center)))
        v.bind(size=lambda *_: setattr(v, "center", holder.center))
        self.add_widget(holder)
        self.applied = False
        self.bind(on_release=lambda *_: self.apply(v))

    def _upd(self, *_):
        self._r.pos, self._r.size = self.pos, self.size
        r = dp(8)
        self._c1.pos, self._c1.size = (self.x - r, self.center_y - r), (2 * r, 2 * r)
        self._c2.pos, self._c2.size = (self.right - r, self.center_y - r), (2 * r, 2 * r)
        x = self.right - dp(30)
        self._dash.points = [x, self.y + dp(4), x, self.top - dp(4)]

    def apply(self, v):
        self.applied = not self.applied
        v.text = "ОТМЕНИТЬ" if self.applied else "ПРИМЕНИТЬ"
        App.get_running_app().toast("Промокод применён" if self.applied else "Промокод отменён")


class CartScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="cart", **kw)
        self.layer = FloatLayout()
        self.add_widget(self.layer)
        self.root_box = BoxLayout(orientation="vertical", pos_hint={"x": 0, "y": 0})
        paint(self.root_box, T.BG)
        self.layer.add_widget(self.root_box)
        self.bar = TopBar("Корзина", back=False, actions=[("share", lambda: App.get_running_app().toast("Ссылка на корзину скопирована"))])
        self.loaded = False
        self.float = None
        store.bind(cart=self._on_cart)

    def on_pre_enter(self):
        if not self.loaded:
            self.loaded = True
            self._fetch()
        elif not getattr(self, "failed", False):
            self.build()

    def _fetch(self):
        self.failed = False
        self.root_box.clear_widgets()
        self.root_box.add_widget(self.bar)
        self.root_box.add_widget(city_row(chat=False))
        fl = FloatLayout()
        fl.add_widget(LoadRing(pos_hint={"center_x": .5, "center_y": .55}))
        self.root_box.add_widget(fl)

        def failed(kind):
            self.failed = True
            fl.clear_widgets()
            fl.add_widget(ErrorView(kind, self._fetch))
        net.request(lambda: self.build(animate=True), failed, delay=0.9)

    def _on_cart(self, *_):
        if self.manager and self.manager.current == self.name and self.loaded and not getattr(self, "failed", False):
            Clock.schedule_once(lambda *_: self.build(), 0)

    def build(self, animate=False):
        r = self.root_box
        r.clear_widgets()
        r.add_widget(self.bar)
        if self.float:
            self.layer.remove_widget(self.float)
            self.float = None
        if not store.cart:
            r.add_widget(empty_state("shopping-cart", "В корзине пока пусто", "Добавьте товары из каталога или избранного",
                                     "Перейти в каталог", lambda: App.get_running_app().go_tab("catalog")))
            return
        sv, box = vscroll(bottom=NAV_SPACE + dp(20))
        box.spacing = 0
        self.sv = sv
        box.add_widget(city_row(chat=False))
        rows = []
        for i, (k, p, size, q) in enumerate(store.items()):
            if i:
                sep = BoxLayout(size_hint_y=None, height=1, padding=(PAD, 0))
                ln = Widget()
                paint(ln, T.LINE)
                sep.add_widget(ln)
                box.add_widget(sep)
            it = CartItem(k, p, size, q, self)
            rows.append(it)
            box.add_widget(it)
        body = BoxLayout(orientation="vertical", size_hint_y=None, padding=(PAD, dp(10)), spacing=dp(14))
        body.bind(minimum_height=body.setter("height"))
        promo = BoxLayout(size_hint_y=None, height=dp(56), padding=(dp(16), 0))
        paint(promo, T.GRAY_BG, dp(4))
        self.promo = TextInput(hint_text="Введите промокод", multiline=False, font_name="AppReg", font_size="16sp",
                               background_normal="", background_active="", background_color=(0, 0, 0, 0),
                               foreground_color=T.TEXT, cursor_color=T.BLUE, hint_text_color=T.MUTED, padding=(0, dp(17), 0, 0))
        self.promo.bind(on_text_validate=lambda *_: App.get_running_app().toast(
            "Промокод не найден" if self.promo.text.strip() else "Введите промокод"))
        promo.add_widget(self.promo)
        body.add_widget(promo)
        csv, crow = hscroll(dp(78))
        crow.padding = (0, 0)
        for t, d, c in (("Скидка 10% по промокоду на одежду", "с 02.11 до 08.11", (0.35, 0.42, 0.55, 1)),
                        ("До −20% на обувь для туризма", "с 01.04 до 31.08", (0.27, 0.35, 0.5, 1)),
                        ("−500 ₽ на первый заказ", "до 31.12", (0.19, 0.3, 0.62, 1))):
            crow.add_widget(Coupon(t, d, c))
        body.add_widget(csv)
        br = BoxLayout(size_hint_y=None, height=dp(34))
        br.add_widget(lbl("Списать 0 бонусов", 16, color=T.rgba(T.MUTED, 0.8)))
        tg = Toggle(disabled_look=True, pos_hint={"center_y": .5})
        br.add_widget(tg)
        body.add_widget(br)
        wr = BoxLayout(size_hint_y=None, height=dp(22))
        wr.add_widget(lbl("Для этого заказа нельзя списать бонусы", 12, color=T.ORANGE))
        wr.add_widget(Icon(name="info-circle", color=T.MUTED, size_hint_x=None, width=dp(22)))
        body.add_widget(wr)
        info = BoxLayout(size_hint_y=None, height=dp(72), padding=(dp(14), dp(10)), spacing=dp(8))
        paint(info, T.GRAY_BG, dp(8))
        info.add_widget(Icon(name="alert-circle-filled", color=T.TEXT, size_hint=(None, 1), width=dp(18)))
        info.add_widget(lbl("Если в заказе несколько товаров, бонусы распределяются между ними. Поэтому цена в корзине "
                            "может отличаться от цены в карточке товара", 12, weight="reg", valign="top"))
        body.add_widget(info)
        # итоги
        sm = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(160), padding=(dp(16), dp(12)), spacing=dp(2))
        paint(sm, T.GRAY_BG, dp(8))
        self.n_cnt = lbl("", 16, color=T.MUTED, weight="reg")
        self.n_full = CountLabel(font_size="16sp", halign="right", valign="middle", font_name="AppReg")
        self.n_disc = lbl("", 16, color=T.MUTED, halign="right", weight="reg")
        self.n_total = CountLabel(font_size="17sp", halign="right", valign="middle", font_name="AppSemi")
        for w in (self.n_full, self.n_total):
            w.bind(size=lambda o, v: setattr(o, "text_size", v))
        self.n_full.color = T.MUTED
        r1 = BoxLayout()
        r1.add_widget(self.n_cnt)
        r1.add_widget(self.n_full)
        sm.add_widget(r1)
        r2 = PressBox()
        r2.add_widget(fit_w(lbl("Скидки и акции", 16, color=T.MUTED, weight="reg")))
        r2.add_widget(Icon(name="chevron", color=T.MUTED, size_hint_x=None, width=dp(18)))
        r2.add_widget(self.n_disc)
        r2.bind(on_release=lambda *_: App.get_running_app().toast("Скидка по акции «Выгодная скидка»"))
        sm.add_widget(r2)
        r3 = BoxLayout()
        r3.add_widget(lbl("Итого", 17, weight="semi"))
        r3.add_widget(self.n_total)
        sm.add_widget(r3)
        r4 = BoxLayout(spacing=dp(6))
        r4.add_widget(fit_w(lbl("Бонусы за покупку", 16, color=T.MUTED, weight="reg")))
        q = BoxLayout(size_hint=(None, None), size=(dp(18), dp(18)), pos_hint={"center_y": .5})
        paint(q, T.rgba(T.MUTED, 0.6), dp(9))
        q.add_widget(lbl("?", 11, color=T.WHITE, halign="center", weight="bold"))
        r4.add_widget(q)
        r4.add_widget(Widget())
        self.n_bon = fit_w(lbl("", 16))
        r4.add_widget(self.n_bon)
        cw = BoxLayout(size_hint_x=None, width=dp(20), padding=(dp(2), dp(9)))
        coin = Widget()
        with coin.canvas:
            Color(*T.YELLOW)
            ce = Ellipse()
        coin.bind(pos=lambda *_: (setattr(ce, "pos", coin.pos), setattr(ce, "size", coin.size)),
                  size=lambda *_: (setattr(ce, "pos", coin.pos), setattr(ce, "size", coin.size)))
        cw.add_widget(coin)
        r4.add_widget(cw)
        sm.add_widget(r4)
        body.add_widget(sm)
        # способы оплаты частями
        for title, sub, icon in (("Оплатить частями", "Покупайте сразу, а оплату делите на части", "clock-dollar"),
                                 ("Оплата в 4 платежа", "Без переплат и комиссий", "credit-card"),
                                 ("В рассрочку от банка", "При оформлении заказа укажите способ оплаты «Рассрочка»", "calendar-dollar")):
            row = PressBox(size_hint_y=None, height=dp(82), spacing=dp(14))
            ib = BoxLayout(size_hint=(None, None), size=(dp(52), dp(52)), padding=dp(13), pos_hint={"top": 1})
            paint(ib, T.BLUE_LIGHT, dp(10))
            ib.add_widget(Icon(name=icon, color=T.BLUE))
            ibw = BoxLayout(size_hint_x=None, width=dp(52), orientation="vertical")
            ibw.add_widget(ib)
            ibw.add_widget(Widget())
            row.add_widget(ibw)
            c = BoxLayout(orientation="vertical", spacing=dp(2))
            h = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(8))
            h.add_widget(fit_w(lbl(title, 16)))
            badge = BoxLayout(size_hint=(None, None), size=(dp(76), dp(22)), pos_hint={"center_y": .5})
            paint(badge, T.GREEN_BADGE, dp(4))
            badge.add_widget(lbl("Доступно", 11, color=T.WHITE, halign="center"))
            h.add_widget(badge)
            h.add_widget(Widget())
            h.add_widget(Icon(name="info-circle", color=T.MUTED, size_hint_x=None, width=dp(22)))
            c.add_widget(h)
            c.add_widget(lbl(sub, 13, color=T.MUTED, weight="reg", valign="top", max_lines=2))
            row.add_widget(c)
            row.bind(on_release=lambda *_, t=title: App.get_running_app().toast(f"«{t}» можно выбрать при оформлении"))
            body.add_widget(row)
        # кнопка «Перейти к оформлению»
        go = RelativeLayout(size_hint_y=None, height=dp(66))
        self.go_btn = AppButton(text="Перейти к оформлению", height=dp(54), radius=dp(6), pos=(0, 0), size_hint=(1, None))
        self.go_btn.bind(on_release=lambda *_: App.get_running_app().open_checkout())
        go.add_widget(self.go_btn)
        self.go_chip = bonus_chip(650)
        go.add_widget(self.go_chip)
        go.bind(size=lambda *_: setattr(self.go_chip, "pos", (go.width - self.go_chip.width - dp(4), dp(40))))
        body.add_widget(go)
        self.go_wrap = go
        box.add_widget(body)
        r.add_widget(sv)

        # плавающая тёмная панель (видна, пока кнопка «Перейти к оформлению» за экраном)
        fb = RelativeLayout(size_hint=(None, None), size=(Window.width - PAD * 2, dp(78)))
        bar = BoxLayout(size_hint=(1, None), height=dp(64), pos=(0, 0), padding=(dp(14), dp(6), dp(8), dp(6)), spacing=dp(8))
        shadow(bar, radius=dp(8), alpha=0.25)
        paint(bar, T.NAVY, dp(8))
        col = BoxLayout(orientation="vertical")
        self.f_old = lbl("", 13, color=T.rgba(T.WHITE, 0.6), markup=True, weight="reg")
        col.add_widget(self.f_old)
        self.f_total = CountLabel(font_name="AppSemi", font_size="20sp", halign="left", valign="middle")
        self.f_total.color = T.WHITE
        self.f_total.bind(size=lambda o, v: setattr(o, "text_size", v))
        col.add_widget(self.f_total)
        bar.add_widget(col)
        fbtn = AppButton(text="К оформлению", height=dp(46), radius=dp(6), size_hint_x=None, width=dp(158))
        fbtn.pos_hint = {"center_y": .5}
        fbtn.bind(on_release=lambda *_: App.get_running_app().open_checkout())
        bar.add_widget(fbtn)
        fb.add_widget(bar)
        self.f_chip = bonus_chip(650)
        fb.add_widget(self.f_chip)
        self.f_chip.pos = (fb.width - self.f_chip.width - dp(2), dp(52))
        fb.pos = (PAD, dp(84))
        self.float = fb
        self.layer.add_widget(fb)
        sv.bind(scroll_y=lambda *_: Clock.schedule_once(lambda *_: self._float_vis(), 0))
        Clock.schedule_once(lambda *_: self._float_vis(), 0.1)
        self.refresh_totals(start=animate)
        if animate:
            stagger_in(rows, 0.06)

    def _float_vis(self):
        if not self.float or not self.go_wrap.get_root_window():
            return
        _, y = self.go_wrap.parent.to_window(*self.go_wrap.pos)
        visible = y > dp(70) and y < Window.height
        target = 0 if visible else 1
        if getattr(self, "_fv", None) != target:
            self._fv = target
            Animation.cancel_all(self.float)
            Animation(opacity=target, y=dp(84) if target else dp(60), d=0.2).start(self.float)
            self.float.disabled = not target

    def refresh_totals(self, start=False):
        full, disc, total, earn = store.totals()
        n = sum(q for *_, q in store.selected_items())
        self.n_cnt.text = f"{n} {T.plural(n, 'товар', 'товара', 'товаров')}"
        self.n_disc.text = f"-{T.price(disc)}" if disc else "0 ₽"
        self.n_bon.text = f"+{earn}"
        for w in (self.n_full, self.n_total, self.f_total):
            if start:
                w.value = 0
        self.n_full.animate_to(full)
        self.n_total.animate_to(total)
        self.f_total.animate_to(total)
        self.f_old.text = f"[s]{T.price(full)}[/s]" if disc else ""
        for ch in (self.go_chip, self.f_chip):
            ch.num.text = str(earn)
        self.go_btn.opacity = 1 if n else 0.5

    def on_leave(self):
        pass


class FavoritesScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.root_box = BoxLayout(orientation="vertical")
        paint(self.root_box, T.BG)
        self.add_widget(self.root_box)
        self.bar = TopBar("Избранное")
        store.bind(favorites=self._changed)
        self.build(animate=True)

    def _changed(self, *_):
        if self.manager and self.manager.current == self.name:
            Clock.schedule_once(lambda *_: self.build(), 0.35)

    def build(self, animate=False):
        r = self.root_box
        r.clear_widgets()
        r.add_widget(self.bar)
        if not store.favorites:
            r.add_widget(empty_state("heart", "Здесь будут избранные товары", "Нажимайте на сердечко, чтобы сохранить товар",
                                     "За покупками", lambda: App.get_running_app().go_tab("home")))
            return
        sv, box = vscroll()
        box.padding = (0, dp(8), 0, box.padding[3])
        g = product_grid([BY_ID[i] for i in store.favorites])
        box.add_widget(g)
        r.add_widget(sv)
        if animate:
            stagger_in(g.cards, 0.04)
