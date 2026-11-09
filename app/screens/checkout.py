"""Оформление заказа → детали заказа → фиктивная оплата.

ВАЖНО: оплата демонстрационная. Данные карты никуда не отправляются и нигде не сохраняются
(запоминаются только последние 4 цифры для отображения в заказе).
"""
import math
import os

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Ellipse, RoundedRectangle, PushMatrix, PopMatrix, Scale
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from .. import theme as T
from ..common import (lbl, paint, vscroll, hscroll, TopBar, PAD, fit_w, band, Field, phone_fmt, ShakeBox, CountLabel)
from ..data import BY_ID, STORES, photo
from ..icons import Icon
from ..store import store, STATUSES
from ..net import net
from ..common import ErrorDialog
from ..widgets import AppButton, PressBox, IconButton, BottomSheet, Chip, shadow


def bottom_bar(left_top, left_main, button_text, on_press, extra=None):
    """Нижняя белая панель: сумма слева, кнопка справа."""
    bar = BoxLayout(size_hint_y=None, height=dp(84), padding=(PAD, dp(12)), spacing=dp(12))
    paint(bar, T.BG)
    with bar.canvas.before:
        Color(*T.LINE)
        from kivy.graphics import Rectangle
        ln = Rectangle(size=(0, 1))
    bar.bind(pos=lambda *_: setattr(ln, "pos", (bar.x, bar.top - 1)), size=lambda *_: setattr(ln, "size", (bar.width, 1)))
    col = BoxLayout(orientation="vertical", size_hint_x=0.58)
    col.add_widget(lbl(left_top, 13, color=T.MUTED, weight="reg"))
    row = BoxLayout(spacing=dp(6))
    main = fit_w(lbl(left_main, 19, weight="bold"))
    row.add_widget(main)
    if extra:
        row.add_widget(extra)
    row.add_widget(Widget())
    col.add_widget(row)
    bar.add_widget(col)
    btn = AppButton(text=button_text, height=dp(54))
    btn.pos_hint = {"center_y": .5}
    btn.bind(on_release=lambda *_: on_press())
    bar.add_widget(btn)
    bar.main_lbl, bar.btn = main, btn
    return bar


def bonus_chip(n):
    b = BoxLayout(size_hint=(None, None), height=dp(28), padding=(dp(4), 0, dp(10), 0), spacing=dp(4),
                  pos_hint={"center_y": .5})
    with b.canvas.before:
        Color(*T.YELLOW)
        r = RoundedRectangle(radius=[dp(14)])
    b.bind(pos=lambda *_: setattr(r, "pos", b.pos), size=lambda *_: setattr(r, "size", b.size))
    coin = BoxLayout(size_hint_x=None, width=dp(22), padding=(0, dp(3)))
    coin.add_widget(Icon(name="gift", color=T.NAVY))
    b.add_widget(coin)
    t = fit_w(lbl(f"+{n}", 13, weight="bold", color=T.NAVY))
    b.add_widget(t)
    b.width = t.width + dp(40)
    return b


class Tabs(BoxLayout):
    """Две вкладки с переезжающим подчёркиванием."""
    ux = NumericProperty(0)

    def __init__(self, names, on_change, **kw):
        super().__init__(size_hint_y=None, height=dp(52), **kw)
        self.labels = []
        self.cb = on_change
        self.idx = 0
        for i, n in enumerate(names):
            b = PressBox()
            l = lbl(n, 17, halign="center", color=T.TEXT if i == 0 else T.MUTED)
            b.add_widget(l)
            b.bind(on_release=lambda *_, i=i: self.select(i))
            self.labels.append(l)
            self.add_widget(b)
        with self.canvas.after:
            Color(*T.LINE)
            self._base = RoundedRectangle()
            Color(*T.BLUE)
            self._u = RoundedRectangle(radius=[dp(1.5)])
        self.bind(pos=self._draw, size=self._draw, ux=self._draw)

    def _draw(self, *_):
        w = self.width / len(self.labels)
        self._base.pos, self._base.size = self.pos, (self.width, 1)
        self._u.pos = (self.x + self.ux * w, self.y)
        self._u.size = (w, dp(3))

    def select(self, i):
        if i == self.idx:
            return
        self.idx = i
        for j, l in enumerate(self.labels):
            Animation(color=T.TEXT if j == i else T.MUTED, d=0.2).start(l)
        Animation(ux=i, d=0.3, t="out_cubic").start(self)
        self.cb(i)


class Collapsible(BoxLayout):
    """Блок, высота которого анимируется при смене содержимого."""

    def set(self, widget, animate=True):
        self.clear_widgets()
        self.add_widget(widget)
        h = widget.height
        if animate:
            widget.opacity = 0
            Animation(height=h, d=0.3, t="out_cubic").start(self)
            Animation(opacity=1, d=0.35).start(widget)
        else:
            self.height = h


# =====================================================================================
class CheckoutScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.method = "pickup"
        self.store_sel = None
        self.items = store.items()
        full, disc, total, earn = store.totals(self.items)
        self.total, self.earn, self.full, self.disc = total, earn, full, disc

        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Оформление заказа"))
        sv, box = vscroll(bottom=dp(20))
        box.spacing = 0
        self.sv = sv

        # контакты
        box.add_widget(lbl("Контактная информация", 20, bold=True, size_hint_y=None, height=dp(52), padding=(PAD, 0)))
        self.contacts_box = Collapsible(size_hint_y=None, padding=(PAD, 0))
        box.add_widget(self.contacts_box)
        box.add_widget(Widget(size_hint_y=None, height=dp(18)))
        box.add_widget(band(dp(12)))

        # способ получения
        box.add_widget(lbl("Способ получения", 20, bold=True, size_hint_y=None, height=dp(62), padding=(PAD, 0)))
        box.add_widget(Tabs(["Самовывоз", "Доставка"], self._method))
        box.add_widget(Widget(size_hint_y=None, height=dp(14)))
        self.method_box = Collapsible(size_hint_y=None, padding=(PAD, 0))
        box.add_widget(self.method_box)

        # товары
        n = sum(q for *_, q in self.items)
        box.add_widget(lbl(f"Товары, {n} шт", 17, size_hint_y=None, height=dp(54), padding=(PAD, 0)))
        th_sv, th = hscroll(dp(116))
        for _, p, size, q in self.items:
            t = RelativeLayout(size_hint_x=None, width=dp(92))
            with t.canvas.before:
                Color(*T.GRAY_BG)
                RoundedRectangle(pos=(0, 0), size=(dp(92), dp(116)), radius=[dp(14)])
            t.add_widget(Image(source=photo(p["image"]), fit_mode="contain", size_hint=(.92, .8), pos_hint={"center_x": .5, "top": .98}))
            q_tag = BoxLayout(size_hint=(None, None), size=(dp(44), dp(22)), pos_hint={"right": .95, "y": .05})
            paint(q_tag, T.rgba(T.NAVY, 0.55), dp(6))
            q_tag.add_widget(lbl(f"{q} шт", 11, color=T.WHITE, halign="center"))
            t.add_widget(q_tag)
            th.add_widget(t)
        box.add_widget(th_sv)

        # сумма
        sum_row = PressBox(size_hint_y=None, height=dp(66), padding=(PAD, 0), spacing=dp(10))
        sum_row.add_widget(lbl("Сумма заказа", 17))
        self.sum_lbl = fit_w(lbl(T.price(total), 17))
        sum_row.add_widget(self.sum_lbl)
        circ = BoxLayout(size_hint=(None, None), size=(dp(30), dp(30)), pos_hint={"center_y": .5}, padding=dp(5))
        paint(circ, T.GRAY_BG, dp(15))
        self.sum_ic = Icon(name="chevron_down", color=T.TEXT)
        circ.add_widget(self.sum_ic)
        sum_row.add_widget(circ)
        sum_row.bind(on_release=lambda *_: self._toggle_sum())
        box.add_widget(sum_row)
        self.sum_details = Collapsible(size_hint_y=None, height=0, padding=(PAD, 0))
        box.add_widget(self.sum_details)
        self.sum_open = False
        root.add_widget(sv)

        self.bar = bottom_bar(f"{n} {T.plural(n, 'товар', 'товара', 'товаров')}", T.price(total), "Оформить",
                              self.submit, extra=bonus_chip(earn))
        root.add_widget(self.bar)
        self.add_widget(root)
        self._contacts_view(animate=False)
        self._method(0, animate=False)

    # ----- контакты
    def _contacts_view(self, animate=True):
        c = store.contacts
        if c.get("name"):
            card = PressBox(size_hint_y=None, height=dp(76), padding=(dp(16), dp(10)), spacing=dp(12))
            paint(card, T.GRAY_BG, dp(14))
            card.add_widget(Icon(name="user", color=T.BLUE, size_hint_x=None, width=dp(26)))
            col = BoxLayout(orientation="vertical")
            col.add_widget(lbl(c["name"], 16, bold=True))
            col.add_widget(lbl(f"{c['phone']}  ·  {c.get('email') or 'без e-mail'}", 13, color=T.MUTED, weight="reg",
                               shorten=True))
            card.add_widget(col)
            card.add_widget(fit_w(lbl("Изменить", 14, color=T.BLUE)))
            card.bind(on_release=lambda *_: self._contacts_form())
            self.contacts_box.set(card, animate)
        else:
            btn = AppButton.light(text="Заполните данные", height=dp(56))
            btn.bind(on_release=lambda *_: self._contacts_form())
            self.contacts_ask = btn
            w = ShakeBox(size_hint_y=None, height=dp(56))
            w.add_widget(btn)
            self.contacts_widget = w
            self.contacts_box.set(w, animate)

    def _contacts_form(self):
        c = store.contacts
        form = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        self.f_name = Field("Имя и фамилия", "Например, Алексей Иванов")
        self.f_phone = Field("Телефон", "+7 900 000-00-00", fmt=phone_fmt)
        self.f_mail = Field("E-mail (необязательно)", "mail@example.ru")
        for f, k in ((self.f_name, "name"), (self.f_phone, "phone"), (self.f_mail, "email")):
            f.text = c.get(k, "")
            form.add_widget(f)
        save = AppButton(text="Сохранить")
        save.bind(on_release=lambda *_: self._save_contacts())
        form.add_widget(save)
        form.height = dp(86) * 3 + dp(56)
        self.contacts_box.set(form)
        Clock.schedule_once(lambda *_: setattr(self.f_name.inp, "focus", True), 0.3)

    def _save_contacts(self):
        ok = True
        if len(self.f_name.text) < 2:
            self.f_name.error("Укажите имя")
            ok = False
        if len("".join(ch for ch in self.f_phone.text if ch.isdigit())) != 11:
            self.f_phone.error("Введите номер полностью")
            ok = False
        mail = self.f_mail.text
        if mail and ("@" not in mail or "." not in mail.split("@")[-1]):
            self.f_mail.error("Проверьте адрес почты")
            ok = False
        if not ok:
            return
        store.contacts = {"name": self.f_name.text, "phone": self.f_phone.text, "email": mail}
        self._contacts_view()

    # ----- способ получения
    def _method(self, i, animate=True):
        self.method = "pickup" if i == 0 else "delivery"
        if self.method == "pickup":
            self.method_box.set(self._pickup_view(), animate)
        else:
            self.method_box.set(self._delivery_view(), animate)
        self._update_total()

    def _pickup_view(self):
        if self.store_sel:
            s = self.store_sel
            card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(130), padding=(dp(16), dp(12)), spacing=dp(4))
            paint(card, T.GRAY_BG, dp(14))
            top = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(8))
            top.add_widget(Icon(name="store", color=T.BLUE, size_hint_x=None, width=dp(24)))
            top.add_widget(lbl(s["name"], 16, bold=True))
            card.add_widget(top)
            card.add_widget(lbl(f"{s['addr']}, м. {s['metro']}", 14, weight="reg"))
            card.add_widget(lbl(f"{s['when']} · бесплатно", 14, color=T.SUCCESS))
            ch = PressBox(size_hint_y=None, height=dp(28))
            ch.add_widget(lbl("Выбрать другой пункт", 14, color=T.BLUE))
            ch.bind(on_release=lambda *_: self._choose_store())
            card.add_widget(ch)
            return card
        m = FloatLayout(size_hint_y=None, height=dp(150))
        with m.canvas.before:
            Color(1, 1, 1, 1)
            r = RoundedRectangle(source=os.path.join(T.IMG, "map.jpg"), radius=[dp(16)])
        m.bind(pos=lambda *_: setattr(r, "pos", m.pos), size=lambda *_: setattr(r, "size", m.size))
        btn = AppButton.light(text="Выбрать пункт самовывоза", size_hint=(0.9, None), height=dp(56),
                              pos_hint={"center_x": .5, "center_y": .5})
        btn.bind(on_release=lambda *_: self._choose_store())
        m.add_widget(btn)
        w = ShakeBox(size_hint_y=None, height=dp(150))
        w.add_widget(m)
        self.place_widget = w
        return w

    def _choose_store(self):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=(PAD, dp(4), PAD, dp(20)), spacing=dp(8))
        content.add_widget(lbl("Пункты самовывоза", 21, bold=True, size_hint_y=None, height=dp(36)))
        sheet = None
        for s in STORES:
            row = PressBox(size_hint_y=None, height=dp(76), padding=(dp(14), dp(8)), spacing=dp(12))
            paint(row, T.GRAY_BG, dp(14))
            row.add_widget(Icon(name="pin", color=T.BLUE, size_hint_x=None, width=dp(26)))
            col = BoxLayout(orientation="vertical")
            col.add_widget(lbl(s["name"], 15, bold=True))
            col.add_widget(lbl(f"{s['addr']} · {s['when']}", 13, color=T.MUTED, weight="reg", shorten=True))
            row.add_widget(col)
            row.add_widget(Icon(name="chevron", color=T.MUTED, size_hint_x=None, width=dp(20)))

            def pick(_w, s=s):
                self.store_sel = s
                sheet.close()
                self.method_box.set(self._pickup_view())
            row.bind(on_release=pick)
            content.add_widget(row)
        sheet = BottomSheet(content, height=dp(76) * len(STORES) + dp(8) * len(STORES) + dp(100))
        sheet.open(app.root_layout)

    def _delivery_view(self):
        box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        self.f_addr = Field("Адрес доставки", "Город, улица, дом, квартира")
        self.f_addr.text = getattr(self, "_addr", "")
        self.f_addr.inp.bind(text=lambda i, t: setattr(self, "_addr", t))
        box.add_widget(self.f_addr)
        box.add_widget(lbl("Дата доставки", 14, color=T.MUTED, size_hint_y=None, height=dp(22)))
        sv, row = hscroll(dp(44))
        row.padding = (0, 0)
        row.spacing = dp(8)
        self.day_chips = []
        from datetime import datetime, timedelta
        names = ["Завтра", "Послезавтра"]
        for i in range(5):
            d = datetime.now() + timedelta(days=i + 1)
            t = names[i] if i < 2 else d.strftime("%d.%m")
            c = Chip(text=t, active=i == getattr(self, "_day", 0))
            c.bind(on_release=lambda w, i=i: self._pick_day(i))
            row.add_widget(c)
            self.day_chips.append(c)
        box.add_widget(sv)
        free = self.total >= 3000
        box.add_widget(lbl("Курьером с 10:00 до 22:00 · " + ("бесплатно" if free else "299 ₽"), 14,
                           color=T.SUCCESS if free else T.TEXT, size_hint_y=None, height=dp(36)))
        box.height = dp(86) + dp(22) + dp(44) + dp(36) + dp(12)
        return box

    def _pick_day(self, i):
        self._day = i
        for j, c in enumerate(self.day_chips):
            c.active = j == i

    def _update_total(self):
        delivery = 0 if self.method == "pickup" or self.total >= 3000 else 299
        self.delivery = delivery
        v = self.total + delivery
        self.bar.main_lbl.text = T.price(v)
        self.sum_lbl.text = T.price(v)
        if self.sum_open:
            self.sum_details.set(self._sum_view(), animate=False)

    def _sum_view(self):
        rows = [("Товары", T.price(self.full), T.TEXT), ("Скидка", "−" + T.price(self.disc), T.RED),
                ("Доставка", "Бесплатно" if not self.delivery else T.price(self.delivery), T.TEXT),
                ("Бонусов будет начислено", f"+{self.earn}", T.BLUE)]
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(30) * len(rows) + dp(10))
        for a, b, c in rows:
            r = BoxLayout()
            r.add_widget(lbl(a, 15, color=T.MUTED, weight="reg"))
            r.add_widget(lbl(b, 15, color=c, halign="right"))
            box.add_widget(r)
        return box

    def _toggle_sum(self):
        self.sum_open = not self.sum_open
        self.sum_ic.name = "chevron_up" if self.sum_open else "chevron_down"
        if self.sum_open:
            self.sum_details.set(self._sum_view())
        else:
            Animation(height=0, d=0.25, t="out_cubic").start(self.sum_details)

    # ----- оформление
    def submit(self):
        app = App.get_running_app()
        if not store.contacts.get("name"):
            app.toast("Заполните контактные данные")
            self.sv.scroll_to(self.contacts_box, padding=dp(40))
            if hasattr(self, "contacts_widget") and self.contacts_widget.parent:
                self.contacts_widget.shake()
            return
        if self.method == "pickup" and not self.store_sel:
            app.toast("Выберите пункт самовывоза")
            self.place_widget.shake()
            return
        if self.method == "delivery" and len(self.f_addr.text) < 6:
            self.f_addr.error("Укажите адрес полностью")
            app.toast("Укажите адрес доставки")
            return
        if self.method == "pickup":
            place = f"{self.store_sel['name']}, {self.store_sel['addr']}"
        else:
            place = self.f_addr.text
        order = store.create_order(self.method, place)
        app.replace(OrderScreen(order, fresh=True))


# =====================================================================================
class Timeline(Widget):
    """Шкала статусов заказа с анимированным заполнением."""
    progress = NumericProperty(0)

    def __init__(self, step, **kw):
        super().__init__(size_hint_y=None, height=dp(64), **kw)
        self.step = step
        self.labels = []
        for s in STATUSES:
            l = lbl(s, 12, halign="center", size_hint=(None, None))
            l.size = (dp(80), dp(20))
            self.labels.append(l)
            self.add_widget(l)
        self._trig = Clock.create_trigger(self.draw, -1)
        self.bind(pos=self._trig, size=self._trig, progress=self._trig)

    def animate_to(self, step):
        self.step = step
        Animation(progress=step, d=0.8, t="out_cubic").start(self)

    def draw(self, *_):
        n = len(STATUSES)
        x0, x1 = self.x + dp(30), self.right - dp(30)
        y = self.top - dp(16)
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*T.LINE)
            Line(points=[x0, y, x1, y], width=dp(1.5))
            Color(*T.BLUE)
            xp = x0 + (x1 - x0) * (self.progress / (n - 1))
            Line(points=[x0, y, xp, y], width=dp(2))
            for i in range(n):
                cx = x0 + (x1 - x0) * i / (n - 1)
                done = self.progress >= i - 0.01
                Color(*(T.BLUE if done else T.LINE))
                r = dp(9) if i == round(self.progress) else dp(7)
                Ellipse(pos=(cx - r, y - r), size=(2 * r, 2 * r))
                if done:
                    Color(1, 1, 1, 1)
                    Ellipse(pos=(cx - dp(3), y - dp(3)), size=(dp(6), dp(6)))
        for i, l in enumerate(self.labels):
            cx = x0 + (x1 - x0) * i / (n - 1)
            l.center_x = cx
            l.y = self.y + dp(4)
            l.color = T.TEXT if self.progress >= i - 0.01 else T.MUTED


class OrderScreen(Screen):
    """Детали заказа: статус, получение, состав, суммы и кнопка оплаты."""

    def __init__(self, order, fresh=False, **kw):
        super().__init__(**kw)
        self.order = order
        self.fresh = fresh
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar(f"Заказ № {order['n']}"))
        self.sv, box = vscroll(bottom=dp(20))
        box.spacing = 0
        o = order

        # статус
        st = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(176), padding=(PAD, dp(16)), spacing=dp(10))
        head = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(14))
        self.st_icon_box = BoxLayout(size_hint_x=None, width=dp(56), padding=dp(12))
        self.st_icon_c = paint(self.st_icon_box, T.BLUE_LIGHT, dp(28))
        self.st_icon = Icon(name="clock", color=T.BLUE)
        self.st_icon_box.add_widget(self.st_icon)
        head.add_widget(self.st_icon_box)
        col = BoxLayout(orientation="vertical")
        self.st_title = lbl("", 18, bold=True)
        self.st_sub = lbl("", 13, color=T.MUTED, weight="reg")
        col.add_widget(self.st_title)
        col.add_widget(self.st_sub)
        head.add_widget(col)
        st.add_widget(head)
        self.timeline = Timeline(o["status"])
        st.add_widget(self.timeline)
        box.add_widget(st)
        box.add_widget(band())

        # получение и получатель
        info = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(232), padding=(PAD, dp(10)))
        for icon, a, b in (
            ("store" if o["method"] == "pickup" else "delivery",
             "Самовывоз" if o["method"] == "pickup" else "Доставка курьером", o["place"]),
            ("calendar", "Дата получения", f"с {o['ready']}, хранение 7 дней" if o["method"] == "pickup" else f"{o['ready']}, 10:00–22:00"),
            ("user", o["contacts"].get("name", ""), o["contacts"].get("phone", "")),
        ):
            r = BoxLayout(spacing=dp(14))
            ic = BoxLayout(size_hint_x=None, width=dp(28), padding=(0, dp(20)))
            ic.add_widget(Icon(name=icon, color=T.BLUE))
            r.add_widget(ic)
            c = BoxLayout(orientation="vertical", padding=(0, dp(12)))
            c.add_widget(lbl(a, 15, bold=True))
            c.add_widget(lbl(b, 13, color=T.MUTED, weight="reg", shorten=True))
            r.add_widget(c)
            info.add_widget(r)
        box.add_widget(info)
        box.add_widget(band())

        # состав
        n = sum(q for *_, q in o["items"])
        box.add_widget(lbl(f"Состав заказа, {n} шт", 19, bold=True, size_hint_y=None, height=dp(56), padding=(PAD, 0)))
        for pid, size, q in o["items"]:
            p = BY_ID[pid]
            r = BoxLayout(size_hint_y=None, height=dp(92), padding=(PAD, dp(6)), spacing=dp(12))
            th = BoxLayout(size_hint_x=None, width=dp(80))
            paint(th, T.GRAY_BG, dp(12))
            th.add_widget(Image(source=photo(p["image"]), fit_mode="contain"))
            r.add_widget(th)
            c = BoxLayout(orientation="vertical", padding=(0, dp(4)))
            c.add_widget(lbl(p["name"], 14, weight="reg", shorten=True))
            c.add_widget(lbl((f"Размер {size} · " if size != "—" else "") + f"{q} шт", 13, color=T.MUTED, weight="reg"))
            c.add_widget(lbl(T.price(p["price"] * q), 16, weight="bold"))
            r.add_widget(c)
            box.add_widget(r)
        box.add_widget(band())

        # суммы
        sums = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(200), padding=(PAD, dp(12)))
        for a, b, c in (("Товары", T.price(o["full"]), T.TEXT), ("Скидка", "−" + T.price(o["disc"]), T.RED),
                        ("Доставка", "Бесплатно" if not o["delivery"] else T.price(o["delivery"]), T.TEXT),
                        ("Бонусы за заказ", f"+{o['earn']}", T.BLUE)):
            r = BoxLayout()
            r.add_widget(lbl(a, 15, color=T.MUTED, weight="reg"))
            r.add_widget(lbl(b, 15, color=c, halign="right"))
            sums.add_widget(r)
        r = BoxLayout()
        r.add_widget(lbl("Итого", 20, bold=True))
        r.add_widget(lbl(T.price(o["total"]), 20, weight="bold", halign="right"))
        sums.add_widget(r)
        self.paid_lbl = lbl("", 13, color=T.SUCCESS, halign="right")
        sums.add_widget(self.paid_lbl)
        box.add_widget(sums)
        root.add_widget(self.sv)

        self.bottom = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(150), padding=(PAD, dp(12)), spacing=dp(10))
        paint(self.bottom, T.BG)
        root.add_widget(self.bottom)
        self.add_widget(root)
        self.refresh(animate=False)

    def refresh(self, animate=True):
        o = self.order
        paid = o["status"] >= 1
        if o.get("cancelled"):
            self.st_title.text = "Заказ отменён"
            self.st_sub.text = "Если вы его оплатили, деньги вернутся на карту"
            self.st_icon.name, self.st_icon.color = "close", T.RED
            self.st_icon_c.rgba = T.rgba(T.RED, 0.12)
        elif paid:
            self.st_title.text = {1: "Заказ оплачен", 2: "Заказ собран", 3: "Заказ получен"}[o["status"]]
            self.st_sub.text = {1: "Мы начали собирать ваш заказ", 2: "Заказ готов к выдаче",
                                3: "Спасибо за покупку!"}[o["status"]]
            self.st_icon.name, self.st_icon.color = "ok", T.SUCCESS
            self.st_icon_c.rgba = T.rgba(T.SUCCESS, 0.12)
            self.paid_lbl.text = f"Оплачено картой •••• {o['paid_card']}" if o.get("paid_card") else ""
        else:
            self.st_title.text = "Заказ создан"
            self.st_sub.text = f"Ожидает оплаты · {o['created']}"
            self.st_icon.name, self.st_icon.color = "clock", T.BLUE
        if animate:
            self.timeline.progress = 0
            self.timeline.animate_to(o["status"])
        else:
            self.timeline.progress = o["status"]
        b = self.bottom
        b.clear_widgets()
        if paid or o.get("cancelled"):
            b.height = dp(80)
            done = AppButton(text="Вернуться к покупкам")
            done.bind(on_release=lambda *_: App.get_running_app().go_tab("home"))
            b.add_widget(done)
        else:
            b.height = dp(150)
            pay = AppButton(text=f"Оплатить {T.price(o['total'])}", icon="card")
            pay.bind(on_release=lambda *_: App.get_running_app().push(PaymentScreen(o, self)))
            b.add_widget(pay)
            later = AppButton.light(text="Оплачу при получении" if o["method"] == "pickup" else "Оплачу курьеру")
            later.bind(on_release=lambda *_: App.get_running_app().toast("Хорошо! Заказ будет ждать вас"))
            b.add_widget(later)

    def on_enter(self):
        if self.fresh:
            self.fresh = False
            self.timeline.progress = 0
            self.timeline.animate_to(self.order["status"])
            self.st_icon_box.opacity = 0
            Animation(opacity=1, d=0.4).start(self.st_icon_box)
            App.get_running_app().toast(f"Заказ № {self.order['n']} создан")


# =====================================================================================
DECLINED_CARD = "4000000000000002"   # тестовая карта, по которой банк «отказывает»


def luhn_ok(num):
    d = [int(c) for c in num if c.isdigit()]
    if len(d) < 13:
        return False
    s = 0
    for i, v in enumerate(reversed(d)):
        if i % 2:
            v *= 2
            v -= 9 if v > 9 else 0
        s += v
    return s % 10 == 0


def card_fmt(t):
    d = "".join(ch for ch in t if ch.isdigit())[:16]
    return " ".join(d[i:i + 4] for i in range(0, len(d), 4))


def exp_fmt(t):
    d = "".join(ch for ch in t if ch.isdigit())[:4]
    return d if len(d) <= 2 else d[:2] + "/" + d[2:]


class CardPreview(FloatLayout):
    """Превью банковской карты: обновляется при вводе, переворачивается при вводе CVC."""
    sx = NumericProperty(1)

    def __init__(self, **kw):
        super().__init__(size_hint_y=None, **kw)
        from .profile import gradient
        self.front = True
        with self.canvas.before:
            PushMatrix()
            self._sc = Scale(origin=(0, 0))
            Color(1, 1, 1, 1)
            self._bg = RoundedRectangle(radius=[dp(18)], texture=gradient(T.NAVY, (0.25, 0.32, 0.55)))
            Color(1, 1, 1, 0.06)
            self._d1 = Ellipse()
            self._strip_c = Color(0, 0, 0, 0)
            from kivy.graphics import Rectangle
            self._strip = Rectangle()
        with self.canvas.after:
            PopMatrix()
        self.bind(pos=self._upd, size=self._upd, sx=self._upd)
        self.f = BoxLayout(orientation="vertical", padding=(dp(20), dp(18)), pos_hint={"x": 0, "y": 0})
        top = BoxLayout(size_hint_y=None, height=dp(28))
        top.add_widget(lbl("DEMO BANK", 14, weight="bold", color=T.WHITE))
        top.add_widget(Icon(name="card", color=T.WHITE, size_hint_x=None, width=dp(30)))
        self.f.add_widget(top)
        chip = Widget(size_hint=(None, None), size=(dp(42), dp(30)))
        paint(chip, (0.95, 0.8, 0.4, 1), dp(6))
        self.f.add_widget(Widget(size_hint_y=None, height=dp(10)))
        self.f.add_widget(chip)
        self.f.add_widget(Widget())
        self.num = lbl("•••• •••• •••• ••••", 21, weight="semi", color=T.WHITE, size_hint_y=None, height=dp(34))
        self.f.add_widget(self.num)
        bot = BoxLayout(size_hint_y=None, height=dp(24))
        self.holder = lbl("ИМЯ ВЛАДЕЛЬЦА", 13, color=T.rgba(T.WHITE, 0.8))
        self.exp = fit_w(lbl("ММ/ГГ", 13, color=T.rgba(T.WHITE, 0.8)))
        bot.add_widget(self.holder)
        bot.add_widget(self.exp)
        self.f.add_widget(bot)
        self.add_widget(self.f)
        self.b = BoxLayout(orientation="vertical", padding=(dp(20), dp(18)), pos_hint={"x": 0, "y": 0})
        self.b.add_widget(Widget())
        cv = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        cv.add_widget(Widget())
        cvb = BoxLayout(size_hint_x=None, width=dp(70), padding=(dp(10), 0))
        paint(cvb, T.WHITE, dp(6))
        self.cvc = lbl("•••", 17, weight="bold", halign="center")
        cvb.add_widget(self.cvc)
        cv.add_widget(cvb)
        self.b.add_widget(cv)
        self.b.add_widget(lbl("CVC — три цифры на обороте", 12, color=T.rgba(T.WHITE, 0.7), halign="right",
                              size_hint_y=None, height=dp(30)))
        Window.bind(width=self._h)
        self._h()

    def _h(self, *_):
        self.height = (Window.width - PAD * 2) * 0.6

    def _upd(self, *_):
        self._sc.origin = self.center
        self._sc.x = self.sx
        self._bg.pos, self._bg.size = self.pos, self.size
        r = self.height * 1.1
        self._d1.pos, self._d1.size = (self.right - r * 0.55, self.y - r * 0.35), (r, r)
        self._strip.pos = (self.x, self.top - dp(70))
        self._strip.size = (self.width, dp(42))

    def flip(self, to_back):
        if to_back == (not self.front):
            return
        a = Animation(sx=0, d=0.15, t="in_quad")

        def swap(*_):
            self.front = not to_back
            if to_back:
                self.remove_widget(self.f)
                self.add_widget(self.b)
                self._strip_c.a = 0.85
            else:
                self.remove_widget(self.b)
                self.add_widget(self.f)
                self._strip_c.a = 0
            Animation(sx=1, d=0.25, t="out_back").start(self)
        a.bind(on_complete=swap)
        a.start(self)


class LoadRing(Widget):
    """Вращающаяся дуга-загрузка."""
    angle = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(size_hint=(None, None), size=(dp(64), dp(64)), **kw)
        self.bind(pos=self.draw, size=self.draw, angle=self.draw)
        self.anim = Animation(angle=360, d=0.9) + Animation(angle=0, d=0)
        self.anim.repeat = True
        self.anim.start(self)

    def draw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(*T.LINE)
            Line(circle=(self.center_x, self.center_y, dp(26)), width=dp(4))
            Color(*T.BLUE)
            Line(circle=(self.center_x, self.center_y, dp(26), self.angle, self.angle + 100), width=dp(4), cap="round")


class CheckMark(Widget):
    """Круг рисуется по дуге, затем «прописывается» галочка."""
    p1 = NumericProperty(0)
    p2 = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(size_hint=(None, None), size=(dp(110), dp(110)), **kw)
        self.bind(pos=self.draw, size=self.draw, p1=self.draw, p2=self.draw)

    def start(self):
        (Animation(p1=1, d=0.5, t="out_cubic") + Animation(p2=1, d=0.35, t="out_cubic")).start(self)

    def draw(self, *_):
        self.canvas.clear()
        cx, cy = self.center
        r = dp(46)
        with self.canvas:
            Color(*T.rgba(T.SUCCESS, 0.12 * self.p1))
            Ellipse(pos=(cx - r - dp(8), cy - r - dp(8)), size=(2 * r + dp(16), 2 * r + dp(16)))
            Color(*T.SUCCESS)
            if self.p1 > 0:
                Line(circle=(cx, cy, r, 0, 360 * self.p1), width=dp(3.5), cap="round")
            if self.p2 > 0:
                a, b, c = (cx - r * .42, cy + r * .02), (cx - r * .1, cy - r * .3), (cx + r * .45, cy + r * .3)
                t = self.p2
                pts = [*a]
                if t < 0.4:
                    k = t / 0.4
                    pts += [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k]
                else:
                    k = (t - 0.4) / 0.6
                    pts += [*b, b[0] + (c[0] - b[0]) * k, b[1] + (c[1] - b[1]) * k]
                Line(points=pts, width=dp(4), cap="round", joint="round")


class PaymentScreen(Screen):
    """Фиктивная оплата: проверяет поля, «обрабатывает» платёж и отмечает заказ оплаченным."""

    def __init__(self, order, order_screen, **kw):
        super().__init__(**kw)
        self.order, self.order_screen = order, order_screen
        self.layer = FloatLayout()
        root = BoxLayout(orientation="vertical", pos_hint={"x": 0, "y": 0})
        paint(root, T.BG)
        root.add_widget(TopBar("Оплата заказа"))
        sv, box = vscroll(bottom=dp(20))
        box.padding = (PAD, dp(4), PAD, dp(20))
        box.spacing = dp(14)

        demo = BoxLayout(size_hint_y=None, height=dp(62), padding=(dp(14), dp(8)), spacing=dp(10))
        paint(demo, T.rgba(T.YELLOW, 0.25), dp(12))
        demo.add_widget(Icon(name="info", color=(0.6, 0.45, 0, 1), size_hint_x=None, width=dp(24)))
        demo.add_widget(lbl("Демо-оплата. Деньги не списываются, данные карты никуда не отправляются.",
                            13, color=(0.45, 0.33, 0, 1), weight="reg"))
        box.add_widget(demo)

        sumrow = BoxLayout(size_hint_y=None, height=dp(40))
        sumrow.add_widget(lbl(f"Заказ № {order['n']}", 16, color=T.MUTED, weight="reg"))
        sumrow.add_widget(lbl(T.price(order["total"]), 22, weight="bold", halign="right"))
        box.add_widget(sumrow)

        self.card = CardPreview()
        box.add_widget(self.card)

        self.f_num = Field("Номер карты", "0000 0000 0000 0000", input_filter="int", fmt=card_fmt, maxlen=19)
        self.f_num.inp.input_filter = None
        row = BoxLayout(size_hint_y=None, height=dp(86), spacing=dp(12))
        self.f_exp = Field("Срок действия", "ММ/ГГ", fmt=exp_fmt, maxlen=5)
        self.f_cvc = Field("CVC", "•••", password=True, fmt=lambda t: "".join(c for c in t if c.isdigit())[:3])
        row.add_widget(self.f_exp)
        row.add_widget(self.f_cvc)
        self.f_name = Field("Имя на карте", "IVAN IVANOV", fmt=lambda t: t.upper())
        for w in (self.f_num, row, self.f_name):
            box.add_widget(w)
        self.f_num.inp.bind(text=self._num)
        self.f_exp.inp.bind(text=lambda i, t: setattr(self.card.exp, "text", t or "ММ/ГГ"))
        self.f_name.inp.bind(text=lambda i, t: setattr(self.card.holder, "text", t or "ИМЯ ВЛАДЕЛЬЦА"))
        self.f_cvc.inp.bind(focus=lambda i, f: self.card.flip(f),
                            text=lambda i, t: setattr(self.card.cvc, "text", "•" * len(t) or "•••"))

        test = PressBox(size_hint_y=None, height=dp(30), spacing=dp(6))
        test.add_widget(Icon(name="sparkles", color=T.BLUE, size_hint_x=None, width=dp(20)))
        test.add_widget(lbl("Заполнить тестовой картой", 15, color=T.BLUE))
        test.bind(on_release=lambda *_: self.fill_test())
        box.add_widget(test)
        sec = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
        sec.add_widget(Icon(name="lock", color=T.MUTED, size_hint_x=None, width=dp(18)))
        sec.add_widget(lbl("Соединение защищено (имитация)", 12, color=T.MUTED, weight="reg"))
        box.add_widget(sec)
        root.add_widget(sv)
        bottom = BoxLayout(size_hint_y=None, height=dp(80), padding=(PAD, dp(12)))
        paint(bottom, T.BG)
        self.pay_btn = AppButton(text=f"Оплатить {T.price(order['total'])}", icon="lock")
        self.pay_btn.bind(on_release=lambda *_: self.pay())
        bottom.add_widget(self.pay_btn)
        root.add_widget(bottom)
        self.layer.add_widget(root)
        self.add_widget(self.layer)

    def _num(self, _i, t):
        digits = "".join(c for c in t if c.isdigit())
        shown = (digits + "•" * (16 - len(digits)))[:16]
        self.card.num.text = " ".join(shown[i:i + 4] for i in range(0, 16, 4))

    def fill_test(self):
        self.f_num.text = "4242 4242 4242 4242"
        self.f_exp.text = "12/30"
        self.f_cvc.text = "123"
        self.f_name.text = "DEMO USER"

    def pay(self):
        ok = True
        if not luhn_ok(self.f_num.text):
            self.f_num.error("Неверный номер карты")
            ok = False
        e = self.f_exp.text
        try:
            mm, yy = int(e[:2]), int(e[3:5])
            from datetime import datetime
            now = datetime.now()
            if not (1 <= mm <= 12) or (2000 + yy, mm) < (now.year, now.month):
                raise ValueError
        except (ValueError, IndexError):
            self.f_exp.error("Проверьте срок")
            ok = False
        if len(self.f_cvc.text) != 3:
            self.f_cvc.error("3 цифры")
            ok = False
        if len(self.f_name.text) < 3:
            self.f_name.error("Как на карте")
            ok = False
        if not ok:
            App.get_running_app().toast("Проверьте данные карты")
            return
        for f in (self.f_num, self.f_exp, self.f_cvc, self.f_name):
            f.inp.focus = False
        self._processing()

    def _processing(self):
        ov = FloatLayout()
        paint(ov, T.rgba(T.BG, 0.97))
        col = BoxLayout(orientation="vertical", size_hint=(0.86, None), height=dp(260),
                        pos_hint={"center_x": .5, "center_y": .55}, spacing=dp(16))
        holder = BoxLayout(size_hint_y=None, height=dp(120))
        holder.add_widget(Widget())
        sp = LoadRing()
        sp_box = BoxLayout(size_hint_x=None, width=dp(110), padding=(dp(23), dp(28)))
        sp_box.add_widget(sp)
        holder.add_widget(sp_box)
        holder.add_widget(Widget())
        col.add_widget(holder)
        title = lbl("Обрабатываем платёж…", 20, bold=True, halign="center", size_hint_y=None, height=dp(30))
        sub = lbl("Это демо: банк не участвует", 14, color=T.MUTED, halign="center", weight="reg",
                  size_hint_y=None, height=dp(22))
        col.add_widget(title)
        col.add_widget(sub)
        ov.add_widget(col)
        ov.opacity = 0
        self.layer.add_widget(ov)
        Animation(opacity=1, d=0.2).start(ov)

        def success(*_):
            sp.anim.cancel(sp)
            sp_box.clear_widgets()
            cm = CheckMark()
            sp_box.padding = (0, dp(5))
            sp_box.add_widget(cm)
            cm.start()
            title.text = "Оплата прошла успешно"
            sub.text = f"Списано {T.price(self.order['total'])} (понарошку)"
            last4 = "".join(c for c in self.f_num.text if c.isdigit())[-4:]
            store.pay(self.order, last4)
            Clock.schedule_once(done, 1.6)

        def done(*_):
            app = App.get_running_app()
            app.back()
            Clock.schedule_once(lambda *_: self.order_screen.refresh(animate=True), 0.3)

        def failed(kind=None, title=None, sub=None):
            self.layer.remove_widget(ov)
            ErrorDialog(kind, on_retry=self._processing, title=title, sub=sub).open()

        if "".join(c for c in self.f_num.text if c.isdigit()) == DECLINED_CARD:
            Clock.schedule_once(lambda *_: failed("declined", "Банк отклонил платёж",
                                                  "Недостаточно средств на карте. Попробуйте другую карту"), 2.0)
        else:
            net.request(success, failed, delay=2.0)


# =====================================================================================
class OrdersScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Мои заказы"))
        self.sv, self.box = vscroll()
        root.add_widget(self.sv)
        self.add_widget(root)

    def on_pre_enter(self):
        b = self.box
        b.clear_widgets()
        b.padding = (PAD, dp(6), PAD, b.padding[3])
        b.spacing = dp(10)
        if not store.orders:
            b.add_widget(lbl("Заказов пока нет", 18, bold=True, halign="center", size_hint_y=None, height=dp(120)))
            return
        for o in store.orders:
            r = PressBox(orientation="vertical", size_hint_y=None, height=dp(130), padding=(dp(16), dp(12)), spacing=dp(6))
            paint(r, T.GRAY_BG, dp(16))
            top = BoxLayout(size_hint_y=None, height=dp(24))
            top.add_widget(lbl(f"№ {o['n']}", 16, bold=True))
            paid = o["status"] >= 1
            st = fit_w(lbl("Отменён" if o.get("cancelled") else STATUSES[o["status"]] if paid else "Ожидает оплаты", 13,
                           bold=True, color=T.RED if o.get("cancelled") else T.SUCCESS if paid else T.BLUE))
            top.add_widget(st)
            r.add_widget(top)
            r.add_widget(lbl(o["created"] + " · " + ("самовывоз" if o["method"] == "pickup" else "доставка"),
                             13, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(20)))
            th = BoxLayout(spacing=dp(6))
            for pid, *_ in o["items"][:4]:
                t = BoxLayout(size_hint_x=None, width=dp(48))
                paint(t, T.BG, dp(8))
                t.add_widget(Image(source=photo(BY_ID[pid]["image"]), fit_mode="contain"))
                th.add_widget(t)
            th.add_widget(Widget())
            th.add_widget(fit_w(lbl(T.price(o["total"]), 17, weight="bold")))
            r.add_widget(th)
            r.bind(on_release=lambda *_, o=o: App.get_running_app().push(OrderScreen(o)))
            b.add_widget(r)
