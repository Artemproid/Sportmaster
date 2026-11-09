"""Оформление заказа по ролику ДЗ1:
загрузка → «Оформление заказа» → «Выбрать пункт самовывоза» → запрос геолокации → карта пунктов →
«Забрать в магазине» → «Заберу отсюда» → способ оплаты → «Контактная информация» → «Оформить».
Дальше — детали заказа и фиктивная оплата (checkout.py)."""
import os

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle, Line, Ellipse, Triangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scatter import ScatterPlane
from kivy.uix.stencilview import StencilView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from .. import theme as T
from ..common import (lbl, paint, vscroll, hscroll, TopBar, PAD, fit_w, band, FloatField, OutlineChip, phone_fmt,
                      ErrorView, net_call)
from ..net import net
from ..data import PICKUP_POINTS, PAY_METHODS, APP, photo
from ..icons import Icon
from ..store import store
from ..widgets import AppButton, PressBox, IconButton, LoadRing, WaitDialog, BottomSheet
from .cart import bonus_chip
from .checkout import OrderScreen


def thumbs(items, h=dp(86)):
    """Миниатюры товаров с плашкой «1 шт»."""
    sv, row = hscroll(h)
    row.padding = (PAD, 0)
    row.spacing = dp(10)
    for _, p, size, q in items:
        t = RelativeLayout(size_hint_x=None, width=dp(66))
        with t.canvas.before:
            Color(*T.GRAY_BG)
            RoundedRectangle(pos=(0, 0), size=(dp(66), h), radius=[dp(8)])
        t.add_widget(Image(source=photo(p["image"]), fit_mode="contain", size_hint=(.95, .8), pos_hint={"center_x": .5, "top": .95}))
        tg = BoxLayout(size_hint=(None, None), size=(dp(36), dp(18)), pos_hint={"right": .96, "y": .05})
        paint(tg, T.rgba((0.35, 0.35, 0.38), 0.85), dp(3))
        tg.add_widget(lbl(f"{q} шт", 10, color=T.WHITE, halign="center"))
        t.add_widget(tg)
        row.add_widget(t)
    return sv


class TabsLine(BoxLayout):
    """Две вкладки с переезжающей синей линией (Самовывоз / Доставка)."""
    ux = NumericProperty(0)

    def __init__(self, names, on_change, dark_title=False, **kw):
        super().__init__(size_hint_y=None, height=dp(50), **kw)
        self.cb, self.idx, self.labels = on_change, 0, []
        for i, n in enumerate(names):
            b = PressBox()
            l = lbl(n, 17, halign="center", color=T.TEXT if i == 0 else T.MUTED)
            b.add_widget(l)
            b.bind(on_release=lambda *_, i=i: self.select(i))
            self.labels.append(l)
            self.add_widget(b)
        with self.canvas.after:
            Color(*T.BLUE)
            self._u = Rectangle()
        self.bind(pos=self._draw, size=self._draw, ux=self._draw)

    def _draw(self, *_):
        w = self.width / len(self.labels)
        self._u.pos, self._u.size = (self.x + self.ux * w, self.y), (w, dp(2.5))

    def select(self, i):
        if i == self.idx:
            return
        self.idx = i
        for j, l in enumerate(self.labels):
            Animation(color=T.TEXT if j == i else T.MUTED, d=0.2).start(l)
        Animation(ux=i, d=0.3, t="out_cubic").start(self)
        self.cb(i)


# ============================================================================ загрузка
class LoadingScreen(Screen):
    """Белый экран с крестиком и кольцом загрузки, затем подменяется целевым экраном."""

    def __init__(self, target_factory, delay=1.1, **kw):
        super().__init__(**kw)
        root = FloatLayout()
        paint(root, T.BG)
        x = IconButton(icon="close", icon_size=dp(30), pos_hint={"x": 0.01, "top": 0.99})
        x.bind(on_release=lambda *_: App.get_running_app().back())
        root.add_widget(x)
        root.add_widget(LoadRing(pos_hint={"center_x": .5, "center_y": .55}))
        self.add_widget(root)
        self.factory, self.delay = target_factory, delay

    def on_enter(self):
        self._fetch()

    def _fetch(self):
        def ok():
            if self.manager and self.manager.current_screen is self:
                App.get_running_app().replace(self.factory())

        def failed(kind):
            self.err = ErrorView(kind, retry)
            self.err.padding = (dp(32), dp(70), dp(32), dp(20))
            self.children[0].add_widget(self.err)

        def retry():
            self.children[0].remove_widget(self.err)
            self._fetch()
        net.request(ok, failed, delay=self.delay)


# ============================================================================ оформление
class CheckoutScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.method = "pickup"
        self.point = None
        self.pay = None
        self.items = store.selected_items()
        self.full, self.disc, self.total, self.earn = store.totals(self.items)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Оформление заказа"))
        self.sv, box = vscroll(bottom=dp(20))
        box.spacing = 0
        box.add_widget(lbl("Контактная информация", 19, size_hint_y=None, height=dp(52), padding=(PAD, 0)))
        self.contacts_box = BoxLayout(size_hint_y=None, height=dp(52), padding=(PAD, 0))
        box.add_widget(self.contacts_box)
        box.add_widget(Widget(size_hint_y=None, height=dp(22)))
        box.add_widget(band(dp(14)))
        box.add_widget(lbl("Способ получения", 19, size_hint_y=None, height=dp(66), padding=(PAD, dp(4))))
        box.add_widget(TabsLine(["Самовывоз", "Доставка"], self._method))
        box.add_widget(Widget(size_hint_y=None, height=dp(12)))
        self.method_box = BoxLayout(orientation="vertical", size_hint_y=None)
        self.method_box.bind(minimum_height=self.method_box.setter("height"))
        box.add_widget(self.method_box)
        self.pay_box = BoxLayout(orientation="vertical", size_hint_y=None)
        self.pay_box.bind(minimum_height=self.pay_box.setter("height"))
        box.add_widget(self.pay_box)
        sr = PressBox(size_hint_y=None, height=dp(62), padding=(PAD, 0), spacing=dp(10))
        sr.add_widget(lbl("Сумма заказа", 17))
        sr.add_widget(fit_w(lbl(T.price(self.total), 17)))
        circ = BoxLayout(size_hint=(None, None), size=(dp(28), dp(28)), padding=dp(5), pos_hint={"center_y": .5})
        paint(circ, T.GRAY_BG, dp(14))
        self.sum_ic = Icon(name="chevron_down", color=T.TEXT)
        circ.add_widget(self.sum_ic)
        sr.add_widget(circ)
        sr.bind(on_release=lambda *_: self._toggle_sum())
        box.add_widget(sr)
        self.sum_details = BoxLayout(orientation="vertical", size_hint_y=None, height=0, padding=(PAD, 0), opacity=0)
        box.add_widget(self.sum_details)
        root.add_widget(self.sv)

        self.bottom = BoxLayout(size_hint_y=None, height=dp(78), padding=(PAD, dp(10)), spacing=dp(12))
        paint(self.bottom, T.BG)
        with self.bottom.canvas.before:
            Color(*T.LINE)
            ln = Rectangle(size=(0, 1))
        self.bottom.bind(pos=lambda *_: setattr(ln, "pos", (self.bottom.x, self.bottom.top - 1)),
                         size=lambda *_: setattr(ln, "size", (self.bottom.width, 1)))
        col = BoxLayout(orientation="vertical")
        n = sum(q for *_, q in self.items)
        self.cnt_lbl = lbl(f"{n} {T.plural(n, 'товар', 'товара', 'товаров')}", 12, color=T.MUTED, weight="reg")
        col.add_widget(self.cnt_lbl)
        pr = BoxLayout(spacing=dp(8))
        pr.add_widget(fit_w(lbl(T.price(self.total), 20, weight="semi")))
        self.chip = bonus_chip(self.earn)
        self.chip.pos_hint = {"center_y": .5}
        pr.add_widget(self.chip)
        pr.add_widget(Widget())
        col.add_widget(pr)
        self.bottom.add_widget(col)
        self.btn = AppButton(text="Оформить", height=dp(50), radius=dp(6), size_hint_x=None, width=dp(160))
        self.btn.pos_hint = {"center_y": .5}
        self.btn.bind(on_release=lambda *_: self.submit())
        self.bottom.add_widget(self.btn)
        root.add_widget(self.bottom)
        self.add_widget(root)
        self._contacts()
        self._method(0)

    # ---- контакты
    def _contacts(self):
        b = self.contacts_box
        b.clear_widgets()
        c = store.contacts
        if c.get("name"):
            card = PressBox(spacing=dp(12), padding=(dp(14), 0))
            paint(card, T.GRAY_BG, dp(8))
            col = BoxLayout(orientation="vertical", padding=(0, dp(6)))
            col.add_widget(lbl(c["name"], 15))
            col.add_widget(lbl("  ·  ".join(x for x in (c.get("phone"), c.get("email")) if x), 12, color=T.MUTED,
                               weight="reg", shorten=True))
            card.add_widget(col)
            card.add_widget(fit_w(lbl("Изменить", 14, color=T.BLUE)))
            card.bind(on_release=lambda *_: self.open_contacts())
            b.height = dp(60)
            b.add_widget(card)
        else:
            btn = AppButton(text="Заполните данные", bg=T.BLUE_LIGHT, fg=T.BLUE, height=dp(52), radius=dp(6))
            btn.bind(on_release=lambda *_: self.open_contacts())
            b.height = dp(52)
            b.add_widget(btn)

    def open_contacts(self):
        App.get_running_app().push(ContactsScreen(self))

    # ---- получение
    def _method(self, i):
        self.method = "pickup" if i == 0 else "delivery"
        mb = self.method_box
        mb.clear_widgets()
        if self.method == "pickup" and not self.point:
            mp = RelativeLayout(size_hint_y=None, height=dp(96))
            wrap = BoxLayout(size_hint_y=None, height=dp(96), padding=(PAD, 0))
            with mp.canvas.before:
                Color(1, 1, 1, 1)
                self._map_r = RoundedRectangle(source=os.path.join(T.IMG, "map.jpg"), radius=[dp(8)], pos=(0, 0))
            mp.bind(size=lambda *_: setattr(self._map_r, "size", mp.size))
            bt = AppButton(text="Выбрать пункт самовывоза", bg=T.rgba(T.BLUE_LIGHT, 0.95), fg=T.BLUE, height=dp(46),
                           radius=dp(6), size_hint=(0.9, None), pos_hint={"center_x": .5, "center_y": .5})
            bt.bind(on_release=lambda *_: self.choose_point())
            mp.add_widget(bt)
            wrap.add_widget(mp)
            mb.add_widget(wrap)
            n = sum(q for *_, q in self.items)
            mb.add_widget(lbl(f"Товары, {n} шт", 16, size_hint_y=None, height=dp(54), padding=(PAD, 0)))
            mb.add_widget(thumbs(self.items))
            self.pay_box.clear_widgets()
        elif self.method == "pickup":
            p = self.point
            card = BoxLayout(size_hint_y=None, height=dp(64), padding=(PAD, 0), spacing=dp(12))
            ic = BoxLayout(size_hint=(None, None), size=(dp(46), dp(46)), padding=dp(11), pos_hint={"top": 1})
            paint(ic, T.BLUE_LIGHT, dp(8))
            ic.add_widget(Icon(name="map-pin-filled", color=T.BLUE))
            card.add_widget(ic)
            col = BoxLayout(orientation="vertical")
            col.add_widget(lbl("Магазин" if p["kind"] != "Пункт выдачи" else "Пункт выдачи", 15, size_hint_y=None, height=dp(20)))
            col.add_widget(lbl(p["addr"], 14, color=T.MUTED, weight="reg", max_lines=2, valign="top"))
            card.add_widget(col)
            ch = PressBox(size_hint=(None, None), size=(dp(76), dp(22)), pos_hint={"top": 1})
            ch.add_widget(lbl("Изменить", 13, color=T.BLUE, halign="right"))
            ch.bind(on_release=lambda *_: self.choose_point())
            card.add_widget(ch)
            mb.add_widget(card)
            mb.add_widget(lbl(f"Можно получить {p['when'].lower()}", 17, size_hint_y=None, height=dp(52), padding=(PAD, 0)))
            mb.add_widget(thumbs(self.items))
            self._pay_section()
        else:
            box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(200), padding=(PAD, 0), spacing=dp(10))
            self.addr = FloatField("Адрес доставки", getattr(self, "_addr", ""))
            self.addr.inp.bind(text=lambda i, t: setattr(self, "_addr", t))
            box.add_widget(self.addr)
            box.add_widget(lbl("Курьер привезёт заказ завтра с 10:00 до 22:00 · бесплатно", 14, color=T.SUCCESS,
                               size_hint_y=None, height=dp(24)))
            n = sum(q for *_, q in self.items)
            box.add_widget(lbl(f"Товары, {n} шт", 16, size_hint_y=None, height=dp(30)))
            mb.add_widget(box)
            mb.add_widget(thumbs(self.items))
            self._pay_section()
        self._refresh_button()

    def _pay_section(self):
        pb = self.pay_box
        pb.clear_widgets()
        h = BoxLayout(size_hint_y=None, height=dp(56), padding=(PAD, dp(14), PAD, 0))
        h.add_widget(lbl("Способ оплаты", 17))
        al = PressBox(size_hint_x=None, width=dp(40))
        al.add_widget(lbl("Все", 14, color=T.BLUE, halign="right"))
        al.bind(on_release=lambda *_: self._all_pay())
        h.add_widget(al)
        pb.add_widget(h)
        sv, row = hscroll(dp(64))
        row.padding = (PAD, dp(4))
        row.spacing = dp(10)
        self.pay_chips = []
        for name, icon in PAY_METHODS:
            c = PayChip(name, icon, info=name not in ("Онлайн", "При получении"))
            c.active = name == self.pay
            c.bind(on_release=lambda w: self.select_pay(w))
            row.add_widget(c)
            self.pay_chips.append(c)
        pb.add_widget(sv)

    def _all_pay(self):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(16)))
        content.add_widget(lbl("Способ оплаты", 21, weight="semi", size_hint_y=None, height=dp(46)))
        sheet = None
        for (name, icon), chip in zip(PAY_METHODS, self.pay_chips):
            r = PressBox(size_hint_y=None, height=dp(54), spacing=dp(14))
            r.add_widget(Icon(name=icon, color=T.TEXT, size_hint_x=None, width=dp(26)))
            r.add_widget(lbl(name, 16))
            r.add_widget(Icon(name="check", color=T.BLUE if self.pay == name else (0, 0, 0, 0), size_hint_x=None, width=dp(24)))
            r.bind(on_release=lambda *_, c=chip: (sheet.close(), self.select_pay(c)))
            content.add_widget(r)
        sheet = BottomSheet(content, height=dp(54) * len(PAY_METHODS) + dp(80))
        sheet.open(app.root_layout)

    def select_pay(self, chip):
        def done():
            self.pay = chip.name
            for c in self.pay_chips:
                c.active = c is chip
        net_call(done, delay=0.9)

    def choose_point(self):
        app = App.get_running_app()
        ask = not getattr(app, "geo_asked", False)
        net_call(lambda: app.push(PickupMapScreen(self, ask=ask)), delay=0.3)   # карте нужна сеть

    def set_point(self, p):
        self.point = p
        self._method(0)

    # ---- сумма
    def _toggle_sum(self):
        d = self.sum_details
        opening = d.height == 0
        self.sum_ic.name = "chevron_up" if opening else "chevron_down"
        d.clear_widgets()
        if opening:
            for a, b, c in (("Товары", T.price(self.full), T.TEXT), ("Скидки и акции", "−" + T.price(self.disc), T.RED),
                            ("Получение", "Бесплатно", T.TEXT), ("Бонусы за покупку", f"+{self.earn}", T.TEXT)):
                r = BoxLayout(size_hint_y=None, height=dp(30))
                r.add_widget(lbl(a, 15, color=T.MUTED, weight="reg"))
                r.add_widget(lbl(b, 15, color=c, halign="right"))
                d.add_widget(r)
        Animation(height=dp(124) if opening else 0, opacity=1 if opening else 0, d=0.25, t="out_cubic").start(d)

    def _refresh_button(self):
        ready = self.method == "delivery" or self.point is not None
        Animation(bg=T.BLUE if ready else T.rgba(T.BLUE, 0.45), d=0.2).start(self.btn)
        self.cnt_lbl.text = ("1 заказ" if ready else
                             f"{sum(q for *_, q in self.items)} {T.plural(sum(q for *_, q in self.items), 'товар', 'товара', 'товаров')}")

    def submit(self):
        app = App.get_running_app()
        if self.method == "pickup" and not self.point:
            return app.toast("Выберите пункт самовывоза", y=dp(92))
        if self.method == "delivery" and len(getattr(self, "_addr", "")) < 6:
            self.addr.error()
            return app.toast("Укажите адрес доставки", y=dp(92))
        if not store.contacts.get("name"):
            return app.toast("Заполните контактную информацию", y=dp(92))
        if not self.pay:
            return app.toast("Выберите способ оплаты", y=dp(92))
        place = f"{self.point['name']}, {self.point['addr']}" if self.method == "pickup" else self._addr

        def go():
            order = store.create_order(self.method, place)
            order["pay_method"] = self.pay
            app.replace(OrderScreen(order, fresh=True))
        net_call(go, delay=1.0)


class PayChip(PressBox):
    """Карточка способа оплаты (обводка; выбранная — тёмно-синяя)."""
    from kivy.properties import BooleanProperty as _B
    active = _B(False)

    def __init__(self, name, icon, info=False, **kw):
        super().__init__(size_hint_x=None, padding=(dp(14), 0), spacing=dp(10), **kw)
        self.name = name
        with self.canvas.before:
            Color(*T.BG)
            self._r = RoundedRectangle(radius=[dp(6)])
            self._lc = Color(*T.LINE)
            self._ln = Line(width=1.1)
        self.bind(pos=self._upd, size=self._upd, active=lambda *_: Animation(rgba=T.BLUE if self.active else T.LINE,
                                                                             d=0.15).start(self._lc))
        self.add_widget(Icon(name=icon, color=T.BLUE, size_hint_x=None, width=dp(24)))
        l = fit_w(lbl(name, 15))
        self.add_widget(l)
        w = dp(28) + dp(24) + dp(10) + l.width
        if info:
            self.add_widget(Icon(name="info-circle", color=T.MUTED, size_hint_x=None, width=dp(22)))
            w += dp(32)
        self.width = w

    def _upd(self, *_):
        self._r.pos, self._r.size = self.pos, self.size
        self._ln.rounded_rectangle = (self.x + .5, self.y + .5, self.width - 1, self.height - 1, dp(6))
        self._ln.width = 1.5 if self.active else 1.1


# ============================================================================ запрос геолокации
class GeoDialog(FloatLayout):
    """Имитация системного запроса доступа к геолокации (тёмная панель снизу)."""

    def __init__(self, on_done, **kw):
        super().__init__(**kw)
        self.on_done = on_done
        with self.canvas.before:
            self._c = Color(0, 0, 0, 0)
            self._r = Rectangle()
        self.bind(pos=lambda *_: setattr(self._r, "pos", self.pos), size=lambda *_: setattr(self._r, "size", self.size))
        w = Window.width - dp(16)
        p = BoxLayout(orientation="vertical", size_hint=(None, None), size=(w, dp(410)), padding=(dp(20), dp(18), dp(20), dp(10)),
                      spacing=dp(8), pos=(dp(8), -dp(420)))
        paint(p, (0.16, 0.16, 0.18, 1), dp(26))
        p.add_widget(Icon(name="map-pin", color=(0.6, 0.7, 1, 1), size_hint_y=None, height=dp(34)))
        p.add_widget(lbl(f"Разрешить приложению [b]{APP}[/b] доступ к данным о местоположении устройства?", 15,
                         color=T.WHITE, halign="center", markup=True, wrap=True))
        opts = BoxLayout(size_hint_y=None, height=dp(150), spacing=dp(10))
        self.opt = []
        for i, name in enumerate(("Точно", "Приблизительно")):
            o = PressBox(orientation="vertical", padding=dp(8), spacing=dp(6))
            with o.canvas.before:
                bc = Color(*((0.18, 0.27, 0.55, 1) if i == 0 else (0.25, 0.25, 0.28, 1)))
                br = RoundedRectangle(radius=[dp(18)])
                lc = Color(*((0.55, 0.65, 1, 1) if i == 0 else (0, 0, 0, 0)))
                ln = Line(width=1.6)
            o.bind(pos=lambda w, *_, br=br, ln=ln: (setattr(br, "pos", w.pos), setattr(br, "size", w.size),
                                                    setattr(ln, "rounded_rectangle", (w.x, w.y, w.width, w.height, dp(18)))),
                   size=lambda w, *_, br=br, ln=ln: (setattr(br, "pos", w.pos), setattr(br, "size", w.size),
                                                     setattr(ln, "rounded_rectangle", (w.x, w.y, w.width, w.height, dp(18)))))
            hdr = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
            ic = Icon(name="circle-check-filled" if i == 0 else "circle", color=T.WHITE, size_hint_x=None, width=dp(20))
            hdr.add_widget(ic)
            hdr.add_widget(lbl(name, 13, color=T.WHITE))
            o.add_widget(hdr)
            m = RelativeLayout()
            with m.canvas.before:
                Color(1, 1, 1, 0.85)
                RoundedRectangle(pos=(0, 0), size=(w / 2 - dp(40), dp(100)), radius=[dp(10)],
                                 source=os.path.join(T.IMG, "map.jpg"))
            m.add_widget(Icon(name="map-pin-filled" if i == 0 else "circle-filled", color=(0.35, 0.55, 1, 1 if i == 0 else 0.5),
                              size_hint=(None, None), size=(dp(36), dp(36)), pos_hint={"center_x": .5, "center_y": .5}))
            o.add_widget(m)
            o.bind(on_release=lambda *_, i=i: self._opt(i))
            self.opt.append((bc, lc, ic))
            opts.add_widget(o)
        p.add_widget(opts)
        for t in ("При использовании приложения", "Только в этот раз", "Запретить"):
            b = PressBox(size_hint_y=None, height=dp(44))
            b.add_widget(lbl(t, 16, color=T.WHITE, halign="center"))
            b.bind(on_release=lambda *_, t=t: self.close(t != "Запретить"))
            p.add_widget(b)
        self.panel = p
        self.add_widget(p)

    def _opt(self, i):
        for j, (bc, lc, ic) in enumerate(self.opt):
            bc.rgba = (0.18, 0.27, 0.55, 1) if j == i else (0.25, 0.25, 0.28, 1)
            lc.rgba = (0.55, 0.65, 1, 1) if j == i else (0, 0, 0, 0)
            ic.name = "circle-check-filled" if j == i else "circle"

    def open(self, parent):
        parent.add_widget(self)
        Animation(a=0.55, d=0.25).start(self._c)
        Animation(y=dp(8), d=0.35, t="out_cubic").start(self.panel)

    def close(self, allowed):
        Animation(a=0, d=0.2).start(self._c)
        a = Animation(y=-dp(430), d=0.25, t="in_cubic")
        a.bind(on_complete=lambda *_: (self.parent and self.parent.remove_widget(self), self.on_done(allowed)))
        a.start(self.panel)

    def on_touch_down(self, touch):
        super().on_touch_down(touch)
        return True


# ============================================================================ карта пунктов
class MapView(StencilView):
    """Карта: её можно двигать пальцем; на ней метки пунктов выдачи и «я»."""

    def __init__(self, points, on_pick, **kw):
        super().__init__(**kw)
        self.plane = ScatterPlane(do_rotation=False, do_scale=True, scale_min=1, scale_max=2.5, auto_bring_to_front=False)
        self.img = Image(source=os.path.join(T.IMG, "city_map.jpg"), fit_mode="fill", size_hint=(None, None),
                         size=(Window.width * 1.25, Window.width * 1.25 * 1500 / 1080))
        self.plane.add_widget(self.img)
        self.pins = []
        for p in points:
            pin = MapPin(p, on_pick)
            self.plane.add_widget(pin)
            self.pins.append(pin)
        self.me = Widget(size_hint=(None, None), size=(dp(44), dp(52)))
        with self.me.canvas:
            Color(*T.NAVY)
            self._me_c = Ellipse()
            self._me_t = Triangle()
        self.me.bind(pos=self._me, size=self._me)
        me_icon = Icon(name="user", color=T.WHITE, size_hint=(None, None), size=(dp(24), dp(24)))
        self.me_icon = me_icon
        self.plane.add_widget(self.me)
        self.plane.add_widget(me_icon)
        self.add_widget(self.plane)
        self.bind(size=self._place)

    def _me(self, *_):
        m = self.me
        self._me_c.pos, self._me_c.size = (m.x, m.y + dp(8)), (dp(44), dp(44))
        self._me_t.points = [m.center_x - dp(8), m.y + dp(12), m.center_x + dp(8), m.y + dp(12), m.center_x, m.y]
        self.me_icon.center = (m.center_x, m.y + dp(30))

    def _place(self, *_):
        W, H = self.img.size
        for pin in self.pins:
            pin.center_x = W * pin.p["x"]
            pin.y = H * (1 - pin.p["y"]) - dp(10)
        self.me.center_x, self.me.y = W * 0.49, H * 0.55
        self.plane.pos = (self.x - (W - self.width) / 2, self.y - (H - self.height) / 2 + dp(60))


class MapPin(PressBox):
    """Метка магазина: тёмно-синий кружок с логотипом и зелёная плашка «Сегодня · 2 из 2»."""

    def __init__(self, p, on_pick, **kw):
        super().__init__(orientation="vertical", size_hint=(None, None), size=(dp(110), dp(70)), **kw)
        self.p = p
        holder = RelativeLayout(size_hint_y=None, height=dp(44))
        c = BoxLayout(size_hint=(None, None), size=(dp(40), dp(40)), padding=dp(8), pos_hint={"center_x": .5, "center_y": .5})
        paint(c, T.NAVY if p["full"] else T.MUTED, dp(20))
        c.add_widget(Icon(name="run", color=T.WHITE))
        holder.add_widget(c)
        self.add_widget(holder)
        tagw = BoxLayout(size_hint_y=None, height=dp(20))
        tg = BoxLayout(size_hint_x=None, padding=(dp(6), 0))
        paint(tg, (0.18, 0.64, 0.3, 1) if p["full"] else T.MUTED, dp(4))
        l = fit_w(lbl(f"{p['when']} · {'2 из 2' if p['full'] else '1 из 2'}", 10, color=T.WHITE, italic=True))
        tg.add_widget(l)
        tg.width = l.width + dp(12)
        tagw.add_widget(Widget())
        tagw.add_widget(tg)
        tagw.add_widget(Widget())
        self.add_widget(tagw)
        self.bind(on_release=lambda *_: on_pick(p))


class PickupMapScreen(Screen):
    """Самовывоз / Доставка, фильтры-чипы, карта, подсказка и список пунктов внизу."""

    def __init__(self, checkout, ask=False, **kw):
        super().__init__(**kw)
        self.checkout = checkout
        self.ask = ask
        self.only_full = True
        root = FloatLayout()
        paint(root, T.BG)
        self.root_fl = root
        top = BoxLayout(orientation="vertical", size_hint=(1, None), height=dp(116), pos_hint={"x": 0, "top": 1})
        paint(top, T.BG)
        bar = BoxLayout(size_hint_y=None, height=dp(58), padding=(dp(6), 0, dp(10), 0))
        x = IconButton(icon="close", icon_size=dp(30), pos_hint={"center_y": .5})
        x.bind(on_release=lambda *_: App.get_running_app().back())
        bar.add_widget(x)
        self.tabs = TabsLine(["Самовывоз", "Доставка"], self._tab)
        self.tabs.size_hint_y = 1
        bar.add_widget(self.tabs)
        fw = RelativeLayout(size_hint_x=None, width=dp(46))
        fb = IconButton(icon="adjustments-horizontal", icon_size=dp(28), pos=(0, dp(7)))
        fb.bind(on_release=lambda *_: self._filter_sheet())
        fw.add_widget(fb)
        from ..widgets import Badge
        self.badge = Badge(text="1", pos=(dp(26), dp(34)))
        fw.add_widget(self.badge)
        bar.add_widget(fw)
        top.add_widget(bar)
        sv, row = hscroll(dp(54))
        row.padding = (PAD, dp(8))
        row.spacing = dp(8)
        self.c_all = OutlineChip("Все товары", icon=None, height=dp(38))
        self.c_all.active = True
        self.c_all.bind(on_release=lambda *_: self._toggle_full())
        row.add_widget(self.c_all)
        for t in ("Через 15 минут", "Магазины", "Пункты выдачи", "Постаматы"):
            c = OutlineChip(t, height=dp(38))
            c.bind(on_release=lambda w: (setattr(w, "active", not w.active), self._refresh_list()))
            row.add_widget(c)
        top.add_widget(sv)

        self.map = MapView(PICKUP_POINTS, self.pick, size_hint=(1, None), pos_hint={"x": 0})
        root.add_widget(self.map)
        root.add_widget(top)

        # нижняя панель со списком
        self.sheet = BoxLayout(orientation="vertical", size_hint=(1, None), height=Window.height * 0.36, pos=(0, 0),
                               padding=(PAD, dp(12), PAD, 0), spacing=dp(8))
        with self.sheet.canvas.before:
            Color(0, 0, 0, 0.08)
            from kivy.graphics import BoxShadow
            sh = BoxShadow(blur_radius=dp(16), border_radius=(dp(18),) * 4)
            Color(*T.BG)
            sr = RoundedRectangle(radius=[dp(18), dp(18), 0, 0])
        self.sheet.bind(pos=lambda *_: (setattr(sr, "pos", self.sheet.pos), setattr(sr, "size", self.sheet.size),
                                        setattr(sh, "pos", self.sheet.pos), setattr(sh, "size", self.sheet.size)),
                        size=lambda *_: (setattr(sr, "pos", self.sheet.pos), setattr(sr, "size", self.sheet.size),
                                         setattr(sh, "pos", self.sheet.pos), setattr(sh, "size", self.sheet.size)))
        sf = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(14), 0), spacing=dp(8))
        paint(sf, T.GRAY_BG, dp(22))
        sf.add_widget(Icon(name="search", color=T.MUTED, size_hint_x=None, width=dp(22)))
        self.q = TextInput(hint_text="Поиск", multiline=False, font_name="AppReg", font_size="16sp", background_normal="",
                           background_active="", background_color=(0, 0, 0, 0), foreground_color=T.TEXT,
                           cursor_color=T.BLUE, hint_text_color=T.MUTED, padding=(0, dp(11), 0, 0))
        self.q.bind(text=lambda *_: self._refresh_list())
        sf.add_widget(self.q)
        self.sheet.add_widget(sf)
        self.list_sv, self.list_box = vscroll(bottom=dp(10))
        self.list_box.spacing = 0
        self.sheet.add_widget(self.list_sv)
        root.add_widget(self.sheet)
        self.add_widget(root)
        self.bind(size=self._layout)
        self._refresh_list()

    def _layout(self, *_):
        self.map.height = self.height - dp(116) - self.sheet.height + dp(20)
        self.map.y = self.sheet.height - dp(20)

    def on_enter(self):
        app = App.get_running_app()
        if self.ask:
            self.ask = False
            app.geo_asked = True
            GeoDialog(self._geo_done).open(app.root_layout)
        else:
            self._hint()

    def _geo_done(self, allowed):
        if allowed:
            App.get_running_app().toast("Определили ваше местоположение")
        self._hint()

    def _hint(self):
        """Подсказка поверх карты про фильтр «Все товары»."""
        ov = FloatLayout()
        with ov.canvas.before:
            c = Color(0, 0, 0, 0)
            r = Rectangle(pos=(0, 0), size=Window.size)
        col = BoxLayout(orientation="vertical", size_hint=(0.85, None), height=dp(120), pos_hint={"x": .06, "top": .86}, spacing=dp(6))
        col.add_widget(Icon(name="arrow-up", color=T.WHITE, size_hint=(None, None), size=(dp(30), dp(30))))
        col.add_widget(lbl("Показываем только те пункты выдачи, где можно забрать заказ целиком. "
                           "Если хотите увидеть все — снимите фильтр", 15, color=T.WHITE, wrap=True))
        col.opacity = 0
        ov.add_widget(col)
        self.root_fl.add_widget(ov)
        Animation(a=0.55, d=0.25).start(c)
        Animation(opacity=1, d=0.3).start(col)

        def hide(*_):
            Animation(a=0, d=0.25).start(c)
            a = Animation(opacity=0, d=0.25)
            a.bind(on_complete=lambda *_: ov.parent and self.root_fl.remove_widget(ov))
            a.start(col)
        Clock.schedule_once(hide, 2.4)
        ov.bind(on_touch_down=lambda *_: (hide(), True)[1])

    def _tab(self, i):
        if i == 1:
            self.checkout._method(1)
            Clock.schedule_once(lambda *_: App.get_running_app().back(), 0.25)

    def _toggle_full(self):
        self.only_full = not self.only_full
        self.c_all.active = self.only_full
        self.badge.text = "1" if self.only_full else ""
        for pin in self.map.pins:
            Animation(opacity=1 if (pin.p["full"] or not self.only_full) else 0, d=0.2).start(pin)
        self._refresh_list()

    def _filter_sheet(self):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(16)), spacing=dp(6))
        content.add_widget(lbl("Фильтры", 21, weight="semi", size_hint_y=None, height=dp(44)))
        from ..widgets import SquareCheck
        r = BoxLayout(size_hint_y=None, height=dp(52))
        r.add_widget(lbl("Только пункты, где заказ целиком", 16))
        cb = SquareCheck(active=self.only_full, pos_hint={"center_y": .5})
        cb.bind(active=lambda *_: self._toggle_full())
        r.add_widget(cb)
        content.add_widget(r)
        BottomSheet(content, height=dp(150)).open(app.root_layout)

    def _refresh_list(self):
        b = self.list_box
        b.clear_widgets()
        q = self.q.text.strip().lower() if hasattr(self, "q") else ""
        for p in PICKUP_POINTS:
            if self.only_full and not p["full"]:
                continue
            if q and q not in (p["name"] + p["addr"]).lower():
                continue
            r = PressBox(orientation="vertical", size_hint_y=None, height=dp(72), padding=(0, dp(10)))
            top = BoxLayout(spacing=dp(10))
            top.add_widget(Icon(name="map-pin-filled", color=T.NAVY, size_hint_x=None, width=dp(22)))
            top.add_widget(lbl(p["name"], 16))
            top.add_widget(fit_w(lbl(p["price"], 14, color=T.MUTED, weight="reg")))
            r.add_widget(top)
            sub = BoxLayout(padding=(dp(32), 0, 0, 0))
            sub.add_widget(lbl(f"{p['kind']} · {p['when']}", 13, color=T.MUTED, weight="reg"))
            r.add_widget(sub)
            r.bind(on_release=lambda *_, p=p: self.pick(p))
            b.add_widget(r)
            sep = Widget(size_hint_y=None, height=1)
            paint(sep, T.LINE)
            b.add_widget(sep)

    def pick(self, p):
        App.get_running_app().push(StoreScreen(p, self.checkout))


# ============================================================================ «Забрать в магазине»
class StoreScreen(Screen):
    def __init__(self, point, checkout, **kw):
        super().__init__(**kw)
        self.point, self.checkout = point, checkout
        root = FloatLayout()
        paint(root, T.BG)
        col = BoxLayout(orientation="vertical", pos_hint={"x": 0, "y": 0})
        col.add_widget(TopBar("Забрать в магазине"))
        mp = RelativeLayout(size_hint_y=None, height=dp(200))
        with mp.canvas.before:
            Color(1, 1, 1, 1)
            mr = Rectangle(source=os.path.join(T.IMG, "store_map.jpg"), pos=(0, 0))
        mp.bind(size=lambda *_: setattr(mr, "size", mp.size))
        pin = MapPin(point, lambda p: None, pos_hint={"center_x": .5, "center_y": .55})
        mp.add_widget(pin)
        pin.opacity = 0
        pin.y_off = 0
        Clock.schedule_once(lambda *_: Animation(opacity=1, d=0.35, t="out_back").start(pin), 0.25)
        col.add_widget(mp)
        sv, box = vscroll(bottom=dp(100))
        box.padding = (PAD, dp(14), PAD, dp(100))
        box.spacing = dp(6)
        r = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        r.add_widget(Icon(name="map-pin-filled", color=T.NAVY, size_hint=(None, None), size=(dp(22), dp(22)), pos_hint={"top": 1}))
        c = BoxLayout(orientation="vertical")
        c.add_widget(lbl(point["name"], 17, weight="semi"))
        c.add_widget(lbl(point["kind"], 15, weight="reg"))
        r.add_widget(c)
        r.add_widget(fit_w(lbl(point["price"], 15, color=T.MUTED, weight="reg", valign="top")))
        box.add_widget(r)
        more = PressBox(size_hint_y=None, height=dp(42), spacing=dp(10))
        more.add_widget(Icon(name="home-filled", color=T.BLUE, size_hint_x=None, width=dp(22)))
        more.add_widget(lbl("Подробнее о магазине", 15))
        circ = BoxLayout(size_hint=(None, None), size=(dp(28), dp(28)), padding=dp(5), pos_hint={"center_y": .5})
        paint(circ, T.GRAY_BG, dp(14))
        self.more_ic = Icon(name="chevron_down", color=T.TEXT)
        circ.add_widget(self.more_ic)
        more.add_widget(circ)
        more.bind(on_release=lambda *_: self.toggle())
        box.add_widget(more)
        self.details = BoxLayout(orientation="vertical", size_hint_y=None, height=0, opacity=0, padding=(dp(32), 0, 0, 0))
        for t in (point["addr"], "Ежедневно 10:00–22:00", "+7 (3822) 00-00-00", "Примерочные, оплата картой и наличными"):
            self.details.add_widget(lbl(t, 14, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(24), shorten=True))
        box.add_widget(self.details)
        box.add_widget(lbl(f"Можно получить {point['when'].lower()}", 18, weight="semi", size_hint_y=None, height=dp(44)))
        th = thumbs(checkout.items, h=dp(80))
        th.children[0].padding = (0, 0)
        box.add_widget(th)
        box.add_widget(lbl("Срок хранения 3 дня", 14, weight="reg", size_hint_y=None, height=dp(30)))
        col.add_widget(sv)
        root.add_widget(col)
        bw = BoxLayout(size_hint=(1, None), height=dp(84), padding=(PAD, dp(12), PAD, dp(18)), pos_hint={"x": 0, "y": 0})
        paint(bw, T.BG)
        b = AppButton(text="Заберу отсюда", height=dp(54), radius=dp(6))
        b.bind(on_release=lambda *_: self.take())
        bw.add_widget(b)
        root.add_widget(bw)
        self.add_widget(root)

    def toggle(self):
        open_ = self.details.height == 0
        self.more_ic.name = "chevron_up" if open_ else "chevron_down"
        Animation(height=dp(100) if open_ else 0, opacity=1 if open_ else 0, d=0.28, t="out_cubic").start(self.details)

    def take(self):
        app = App.get_running_app()

        def done():
            self.checkout.set_point(self.point)
            app.back_to(self.checkout)
        net_call(done, delay=1.0)


# ============================================================================ контакты
class ContactsScreen(Screen):
    def __init__(self, checkout, **kw):
        super().__init__(**kw)
        self.checkout = checkout
        c = store.contacts
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        bar = BoxLayout(size_hint_y=None, height=dp(60), padding=(dp(6), 0), spacing=dp(6))
        x = IconButton(icon="close", icon_size=dp(30), pos_hint={"center_y": .5})
        x.bind(on_release=lambda *_: App.get_running_app().back())
        bar.add_widget(x)
        bar.add_widget(lbl("Контактная информация", 20))
        root.add_widget(bar)
        box = BoxLayout(orientation="vertical", padding=(PAD, dp(4)), spacing=dp(12))
        self.f_name = FloatField("ФИО", c.get("name", ""))
        self.f_mail = FloatField("E-mail", c.get("email", ""))
        self.f_phone = FloatField("Номер телефона", c.get("phone", ""), fmt=phone_fmt)
        for f in (self.f_name, self.f_mail, self.f_phone):
            box.add_widget(f)
        box.add_widget(Widget(size_hint_y=None, height=dp(6)))
        save = AppButton(text="Сохранить", height=dp(54), radius=dp(6))
        save.bind(on_release=lambda *_: self.save())
        box.add_widget(save)
        self.err = lbl("", 13, color=T.RED, size_hint_y=None, height=dp(20))
        box.add_widget(self.err)
        box.add_widget(Widget())
        root.add_widget(box)
        self.add_widget(root)

    def on_enter(self):
        f = next((f for f in (self.f_name, self.f_mail, self.f_phone) if not f.text), None)
        if f:
            Clock.schedule_once(lambda *_: setattr(f.inp, "focus", True), 0.1)

    def save(self):
        errs = []
        if len(self.f_name.text.split()) < 2:
            self.f_name.error()
            errs.append("укажите имя и фамилию")
        mail = self.f_mail.text
        if mail and ("@" not in mail or "." not in mail.split("@")[-1]):
            self.f_mail.error()
            errs.append("проверьте e-mail")
        if len("".join(ch for ch in self.f_phone.text if ch.isdigit())) != 11:
            self.f_phone.error()
            errs.append("введите телефон полностью")
        if errs:
            self.err.text = "Проверьте данные: " + ", ".join(errs)
            return
        store.contacts = {"name": self.f_name.text, "email": mail, "phone": self.f_phone.text}
        self.checkout._contacts()
        App.get_running_app().back()
