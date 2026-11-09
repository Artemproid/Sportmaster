"""Общие части экранов: шапки, сетки, ленты, поля ввода, счётчики."""
import math

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle, PushMatrix, PopMatrix, Translate
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from . import theme as T
from .icons import Icon
from .widgets import IconButton, ProductCard, PressBox, AppButton

PAD = dp(16)
GAP = dp(10)
NAV_SPACE = dp(104)   # место под плавающее нижнее меню

FONTS = {"reg": "AppReg", "med": "App", "semi": "AppSemi", "bold": "AppBold"}


def lbl(text, size=14, bold=False, color=None, halign="left", wrap=False, weight=None, **kw):
    kw.setdefault("valign", "middle")
    font = FONTS[weight] if weight else ("AppSemi" if bold else "App")
    w = Label(text=text, font_size=sp(size), font_name=font, halign=halign, **kw)
    w.color = color or T.TEXT
    if wrap:
        w.size_hint_y = None
        w.bind(width=lambda o, v: setattr(o, "text_size", (v, None)),
               texture_size=lambda o, v: setattr(o, "height", v[1]))
    else:
        w.bind(size=lambda o, v: None if getattr(o, "_fit", False) else setattr(o, "text_size", v))
    return w


def fit_w(label, extra=0):
    """Ширина метки = ширине текста."""
    label.size_hint_x = None
    label._fit = True
    label.text_size = (None, label.text_size[1] if label.text_size else None)
    label.text_size = (None, None)
    label.bind(texture_size=lambda o, v: setattr(o, "width", v[0] + extra))
    label.texture_update()
    label.width = label.texture_size[0] + extra
    return label


def paint(widget, color, radius=0):
    with widget.canvas.before:
        c = Color(*color)
        r = RoundedRectangle(pos=widget.pos, size=widget.size, radius=[radius] if not isinstance(radius, (list, tuple)) else radius) \
            if radius else Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda *_: setattr(r, "pos", widget.pos), size=lambda *_: setattr(r, "size", widget.size))
    return c


def vscroll(bottom=NAV_SPACE):
    sv = ScrollView(do_scroll_x=False, bar_width=dp(3), bar_color=T.rgba(T.MUTED, 0.5),
                    bar_inactive_color=(0, 0, 0, 0), effect_cls="ScrollEffect")
    box = GridLayout(cols=1, size_hint_y=None, spacing=dp(8), padding=(0, 0, 0, bottom))
    box.bind(minimum_height=box.setter("height"))
    sv.add_widget(box)
    return sv, box


def hscroll(height):
    sv = ScrollView(do_scroll_y=False, size_hint_y=None, height=height, bar_width=0, effect_cls="ScrollEffect")
    row = BoxLayout(size_hint_x=None, spacing=GAP, padding=(PAD, 0))
    row.bind(minimum_width=row.setter("width"))
    sv.add_widget(row)
    return sv, row


def card_width():
    return (Window.width - PAD * 2 - GAP) / 2


def product_grid(products):
    grid = GridLayout(cols=2, spacing=(GAP, dp(18)), padding=(PAD, dp(4)), size_hint_y=None)
    grid.bind(minimum_height=grid.setter("height"))
    cw = card_width()
    cards = [ProductCard(p, width=cw) for p in products]
    for c in cards:
        grid.add_widget(c)

    def resize(*_):
        for c in cards:
            c.set_width(card_width())
    Window.bind(width=resize)
    grid.cards = cards
    return grid


def product_strip(products, width=dp(164)):
    sv, row = hscroll(width * 1.2 + dp(120))
    for p in products:
        row.add_widget(ProductCard(p, width=width))
    return sv


def section(text, action="", cb=None):
    row = BoxLayout(size_hint_y=None, height=dp(52), padding=(PAD, dp(14), PAD, 0))
    row.add_widget(lbl(text, 22, bold=True))
    if action:
        a = PressBox(size_hint_x=None, width=dp(60))
        a.add_widget(lbl(action, 16, color=T.BLUE, halign="right"))
        a.bind(on_release=lambda *_: cb())
        row.add_widget(a)
    return row


def band(h=dp(10)):
    w = Widget(size_hint_y=None, height=h)
    paint(w, T.GRAY_BAND)
    return w


class TopBar(BoxLayout):
    """Белая шапка: стрелка «назад», заголовок, иконки справа."""
    title = StringProperty("")

    def __init__(self, title="", back=True, actions=(), line=False, **kw):
        super().__init__(size_hint_y=None, height=dp(60), padding=(dp(6), 0, dp(8), 0), spacing=dp(6), **kw)
        self.title = title
        paint(self, T.BG)
        if line:
            with self.canvas.after:
                Color(*T.LINE)
                ln = Rectangle(size=(0, 1))
            self.bind(pos=lambda *_: setattr(ln, "pos", self.pos), size=lambda *_: setattr(ln, "size", (self.width, 1)))
        if back:
            b = IconButton(icon="back", icon_size=dp(28))
            b.pos_hint = {"center_y": .5}
            b.bind(on_release=lambda *_: App.get_running_app().back())
            self.add_widget(b)
        else:
            self.add_widget(Widget(size_hint_x=None, width=dp(10)))
        t = lbl(title, 20, bold=True, shorten=True, shorten_from="right")
        self.title_lbl = t
        self.bind(title=lambda o, v: setattr(t, "text", v))
        self.add_widget(t)
        self.action_buttons = []
        for icon, cb in actions:
            ib = IconButton(icon=icon, icon_size=dp(28))
            ib.pos_hint = {"center_y": .5}
            ib.bind(on_release=lambda *_, cb=cb: cb())
            self.add_widget(ib)
            self.action_buttons.append(ib)


class SearchPill(PressBox):
    """Поле поиска-кнопка. dark=True — для тёмной шапки главной."""

    def __init__(self, text="Искать в SPORTLY", dark=False, **kw):
        super().__init__(size_hint_y=None, height=dp(50), padding=(dp(14), 0), spacing=dp(10), **kw)
        paint(self, T.NAVY_2 if dark else T.GRAY_BG, dp(14))
        c = T.rgba(T.WHITE, 0.55) if dark else T.MUTED
        self.add_widget(Icon(name="search", color=c, size_hint_x=None, width=dp(24)))
        self.add_widget(lbl(text, 16, color=c, weight="reg"))
        self.add_widget(Icon(name="barcode", color=c, size_hint_x=None, width=dp(26)))
        self.bind(on_release=lambda *_: App.get_running_app().open_search())


class ShakeBox(BoxLayout):
    """Контейнер, который умеет «трястись» (ошибка ввода)."""
    tx = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            PushMatrix()
            self._t = Translate(0, 0)
        with self.canvas.after:
            PopMatrix()
        self.bind(tx=lambda *_: setattr(self._t, "x", self.tx))

    def shake(self):
        a = Animation(tx=dp(10), d=0.05)
        for v in (-dp(9), dp(7), -dp(5), dp(3), 0):
            a += Animation(tx=v, d=0.06)
        a.start(self)


class CountLabel(Label):
    """Число, которое плавно «досчитывает» до нового значения."""
    value = NumericProperty(0)
    fmt = StringProperty("price")

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(value=self._upd)
        self._upd()

    def _upd(self, *_):
        self.text = T.price(self.value) if self.fmt == "price" else f"{int(self.value):,}".replace(",", " ")

    def animate_to(self, v, d=0.6):
        Animation.cancel_all(self, "value")
        Animation(value=v, d=d, t="out_cubic").start(self)


class Field(ShakeBox):
    """Поле ввода с подписью, подсветкой фокуса и текстом ошибки."""

    def __init__(self, title, hint="", password=False, input_filter=None, maxlen=None, fmt=None, **kw):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(86), spacing=dp(4), **kw)
        self.fmt = fmt
        self.maxlen = maxlen
        self.title = lbl(title, 13, color=T.MUTED, size_hint_y=None, height=dp(18))
        self.add_widget(self.title)
        box = BoxLayout(size_hint_y=None, height=dp(48), padding=(dp(14), 0))
        with box.canvas.before:
            Color(*T.GRAY_BG)
            bg = RoundedRectangle(radius=[dp(12)])
            self._ring_c = Color(0, 0, 0, 0)
            from kivy.graphics import Line
            self._ring = Line(width=1.3)
        box.bind(pos=lambda *_: self._box(box, bg), size=lambda *_: self._box(box, bg))
        self.inp = TextInput(hint_text=hint, multiline=False, password=password, input_filter=input_filter,
                             font_name="App", font_size="16sp", background_normal="", background_active="",
                             background_color=(0, 0, 0, 0), foreground_color=T.TEXT, cursor_color=T.BLUE,
                             hint_text_color=T.MUTED, padding=(0, dp(14), 0, 0), write_tab=False)
        self.inp.bind(focus=self._focus, text=self._text)
        box.add_widget(self.inp)
        self.add_widget(box)
        self.err = lbl("", 12, color=T.RED, size_hint_y=None, height=dp(14))
        self.add_widget(self.err)
        self._busy = False

    def _box(self, box, bg):
        bg.pos, bg.size = box.pos, box.size
        self._ring.rounded_rectangle = (box.x, box.y, box.width, box.height, dp(12))

    def _focus(self, _i, f):
        Animation(a=1 if f else 0, d=0.18).start(self._ring_c)
        self._ring_c.rgb = T.BLUE[:3]

    def _text(self, inp, text):
        if self._busy:
            return
        self.err.text = ""
        new = text
        if self.fmt:
            new = self.fmt(text)
        if self.maxlen:
            new = new[:self.maxlen]
        if new != text:
            self._busy = True
            inp.text = new
            Clock.schedule_once(lambda *_: setattr(inp, "cursor", (len(new), 0)), 0)
            self._busy = False

    @property
    def text(self):
        return self.inp.text.strip()

    @text.setter
    def text(self, v):
        self.inp.text = v

    def error(self, msg):
        self.err.text = msg
        self._ring_c.rgb = T.RED[:3]
        self._ring_c.a = 1
        self.shake()


def phone_fmt(t):
    d = "".join(ch for ch in t if ch.isdigit())
    if not d:
        return ""
    if d[0] in "78":
        d = d[1:]
    d = d[:10]
    out = "+7"
    if d:
        out += " " + d[:3]
    if len(d) > 3:
        out += " " + d[3:6]
    if len(d) > 6:
        out += "-" + d[6:8]
    if len(d) > 8:
        out += "-" + d[8:10]
    return out


def empty_state(icon, title, sub, button, on_button):
    box = BoxLayout(orientation="vertical", padding=(dp(32), dp(30), dp(32), NAV_SPACE), spacing=dp(14))
    box.add_widget(Widget())
    holder = Widget(size_hint_y=None, height=dp(120))
    circle = Widget(size_hint=(None, None), size=(dp(110), dp(110)))
    with circle.canvas:
        Color(*T.BLUE_LIGHT)
        e = RoundedRectangle(radius=[dp(55)])
    ic = Icon(name=icon, color=T.BLUE, size_hint=(None, None), size=(dp(54), dp(54)))
    holder.add_widget(circle)
    holder.add_widget(ic)
    t0 = [0.0]

    def place(*_):
        circle.center = holder.center
        e.pos, e.size = circle.pos, circle.size
        ic.center = (holder.center_x, holder.center_y + math.sin(t0[0] * 2.4) * dp(6))
    holder.bind(pos=place, size=place)

    def tick(dt):
        t0[0] += dt
        place()
    ev = Clock.schedule_interval(tick, 1 / 60)
    box.bind(parent=lambda o, p: ev.cancel() if p is None else None)
    box.add_widget(holder)
    box.add_widget(lbl(title, 20, bold=True, halign="center", wrap=True))
    box.add_widget(lbl(sub, 15, color=T.MUTED, halign="center", wrap=True, weight="reg"))
    btn = AppButton(text=button)
    btn.bind(on_release=lambda *_: on_button())
    box.add_widget(btn)
    box.add_widget(Widget())
    return box


# ------------------------------------------------------------------ элементы по ролику ДЗ1
def chat_button(color=None, cb=None):
    """Иконка чата в шапке (открывает «Сообщения»)."""
    b = IconButton(icon="message-circle-filled", icon_color=color or T.NAVY, icon_size=dp(30))
    b.pos_hint = {"center_y": .5}
    b.bind(on_release=lambda *_: (cb or App.get_running_app().open_messages)())
    return b


def search_header(dark=False, back=False, query="", on_search=None):
    """Строка «поиск + чат». back=True — со стрелкой назад (экран результатов)."""
    row = BoxLayout(size_hint_y=None, height=dp(62), padding=(dp(6) if back else PAD, dp(7), dp(6), dp(7)),
                    spacing=dp(4))
    if back:
        b = IconButton(icon="back", icon_size=dp(28), icon_color=T.WHITE if dark else T.TEXT)
        b.pos_hint = {"center_y": .5}
        b.bind(on_release=lambda *_: App.get_running_app().back())
        row.add_widget(b)
    pill = PressBox(padding=(dp(14), 0), spacing=dp(8))
    paint(pill, T.NAVY_2 if dark else T.GRAY_BG, dp(24))
    c = T.rgba(T.WHITE, 0.55) if dark else T.MUTED
    pill.add_widget(Icon(name="search", color=c, size_hint_x=None, width=dp(22)))
    pill.add_widget(lbl(query or f"Искать в {_app_name()}", 16, color=(T.TEXT if query else c), weight="reg"))
    if not query:
        pill.add_widget(Icon(name="barcode", color=c, size_hint_x=None, width=dp(24)))
    pill.bind(on_release=lambda *_: (on_search or App.get_running_app().open_search)())
    row.add_widget(pill)
    row.add_widget(chat_button(T.rgba(T.WHITE, 0.85) if dark else T.NAVY))
    return row


def _app_name():
    from .data import APP
    return APP


def section_all(text, cb=None, size=22, action="Все"):
    """Заголовок раздела с синей ссылкой «Все» справа."""
    row = BoxLayout(size_hint_y=None, height=dp(56), padding=(PAD, dp(16), PAD, dp(4)))
    row.add_widget(lbl(text, size, weight="semi"))
    if cb:
        a = PressBox(size_hint_x=None, width=dp(50))
        a.add_widget(lbl(action, 16, color=T.BLUE, halign="right"))
        a.bind(on_release=lambda *_: cb())
        row.add_widget(a)
    return row


def title2(text, size=21):
    """Двухстрочный заголовок подборки."""
    box = BoxLayout(size_hint_y=None, padding=(PAD, dp(20), PAD, dp(10)))
    l = lbl(text, size, weight="semi", wrap=True)
    box.add_widget(l)
    l.bind(height=lambda o, h: setattr(box, "height", h + dp(30)))
    box.height = dp(80)
    return box


def city_row(cb=None, chat=True):
    row = BoxLayout(size_hint_y=None, height=dp(66), padding=(PAD, dp(9), dp(6), dp(9)), spacing=dp(4))
    pill = PressBox(padding=(dp(14), 0), spacing=dp(8))
    paint(pill, T.GRAY_BG, dp(10))
    pill.add_widget(Icon(name="map-pin-filled", color=T.BLUE, size_hint_x=None, width=dp(22)))
    from .data import CITY
    pill.add_widget(lbl(CITY, 16))
    pill.add_widget(Icon(name="chevron", color=T.MUTED, size_hint_x=None, width=dp(20)))
    pill.bind(on_release=lambda *_: (cb or (lambda: App.get_running_app().toast("Выбор города доступен в профиле")))())
    row.add_widget(pill)
    if chat:
        row.add_widget(chat_button())
    else:
        row.padding = (PAD, dp(9), PAD, dp(9))
    return row


class OutlineChip(PressBox):
    """Чип с серой обводкой (фильтры, «Способ получения»). active — синяя обводка и фон."""
    from kivy.properties import BooleanProperty as _B
    active = _B(False)

    def __init__(self, text, dot=None, icon=None, height=dp(40), **kw):
        super().__init__(size_hint=(None, None), height=height, padding=(dp(14), 0), spacing=dp(8), **kw)
        from kivy.graphics import Line
        with self.canvas.before:
            self._bg = Color(*T.BG)
            self._r = RoundedRectangle(radius=[height / 2])
            self._lc = Color(*T.LINE)
            self._ln = Line(width=1.1)
        self.bind(pos=self._upd, size=self._upd, active=self._paint)
        w = dp(28)
        if dot:
            from kivy.utils import get_color_from_hex as hx
            d = Widget(size_hint=(None, None), size=(dp(18), dp(18)), pos_hint={"center_y": .5})
            with d.canvas:
                Color(*hx(dot))
                e = RoundedRectangle(radius=[dp(9)])
                Color(*T.LINE)
                el = Line(width=1)
            d.bind(pos=lambda *_: (setattr(e, "pos", d.pos), setattr(e, "size", d.size),
                                   setattr(el, "circle", (d.center_x, d.center_y, dp(9)))))
            self.add_widget(d)
            w += dp(26)
        if icon:
            self.add_widget(Icon(name=icon, color=T.TEXT, size_hint_x=None, width=dp(22)))
            w += dp(22) + (dp(8) if text else 0)
        if text:
            self.label = fit_w(lbl(text, 14))
            self.add_widget(self.label)
            w += self.label.width
        else:
            self.padding = (dp(10), 0)
            w = dp(44)
        self.width = w

    def _upd(self, *_):
        self._r.pos, self._r.size = self.pos, self.size
        self._ln.rounded_rectangle = (self.x + .5, self.y + .5, self.width - 1, self.height - 1, self.height / 2)

    def _paint(self, *_):
        Animation(rgba=T.BLUE_LIGHT if self.active else T.BG, d=0.15).start(self._bg)
        Animation(rgba=T.BLUE if self.active else T.LINE, d=0.15).start(self._lc)

    def on_release(self):
        super().on_release()


from kivy.uix.floatlayout import FloatLayout as _FL


class FloatField(_FL):
    """Поле как в оригинале: серый блок, подпись сверху (плавает), синяя линия при фокусе."""
    from kivy.properties import NumericProperty as _N
    k = _N(0)   # 0 — подпись внутри, 1 — сверху

    def __init__(self, title, text="", fmt=None, password=False, **kw):
        super().__init__(size_hint_y=None, height=dp(58), **kw)
        from kivy.graphics import Rectangle as R
        self.fmt = fmt
        with self.canvas.before:
            Color(*T.GRAY_BG)
            self._bg = R()
            self._lc = Color(*T.rgba(T.BLUE, 0))
            self._ln = R()
        self.bind(pos=self._upd, size=self._upd, k=self._upd)
        self.title = Label(text=title, font_name="AppReg", font_size=sp(16), color=T.MUTED, size_hint=(None, None),
                           halign="left", valign="middle")
        self.inp = TextInput(text=text, multiline=False, font_name="App", font_size="16sp", background_normal="",
                             background_active="", background_color=(0, 0, 0, 0), foreground_color=T.TEXT,
                             cursor_color=T.BLUE, cursor_width=dp(1.6), padding=(dp(16), dp(24), dp(16), 0),
                             write_tab=False, pos_hint={"x": 0, "y": 0}, password=password)
        self.add_widget(self.inp)
        self.add_widget(self.title)
        if password:
            eye = IconButton(icon="eye", icon_color=T.MUTED, icon_size=dp(22), pos_hint={"right": 1, "center_y": .5})

            def toggle(*_):
                self.inp.password = not self.inp.password
                eye.icon = "eye" if self.inp.password else "eye-off"
            eye.bind(on_release=toggle)
            self.add_widget(eye)
        self.k = 1 if text else 0
        self.inp.bind(focus=self._focus, text=self._text)
        self.err = None

    def _upd(self, *_):
        self._bg.pos, self._bg.size = self.pos, self.size
        self._ln.pos, self._ln.size = self.pos, (self.width, dp(1.6))
        t = self.title
        t.font_size = sp(16 - 4 * self.k)
        t.texture_update()
        t.size = t.texture_size
        t.x = self.x + dp(16)
        t.center_y = self.center_y + (self.height * 0.25) * self.k

    def _focus(self, _i, f):
        Animation(a=1 if f else 0, d=0.18).start(self._lc)
        Animation(k=1 if (f or self.inp.text) else 0, d=0.18, t="out_cubic").start(self)
        if f:
            self._lc.rgb = T.BLUE[:3]

    def _text(self, inp, t):
        if self.fmt:
            n = self.fmt(t)
            if n != t:
                inp.text = n
                Clock.schedule_once(lambda *_: setattr(inp, "cursor", (len(n), 0)), 0)
        if t and self.k < 1:
            self.k = 1

    @property
    def text(self):
        return self.inp.text.strip()

    def error(self):
        self._lc.rgb = T.RED[:3]
        self._lc.a = 1


class RangeSlider(Widget):
    """Ползунок цены с двумя «бегунками»."""
    from kivy.properties import NumericProperty as _N
    lo = _N(0)
    hi = _N(1)

    def __init__(self, on_change=None, **kw):
        super().__init__(size_hint_y=None, height=dp(36), **kw)
        self.cb = on_change
        self._drag = None
        self.bind(pos=self._draw, size=self._draw, lo=self._draw, hi=self._draw)

    def _x(self, v):
        return self.x + dp(12) + (self.width - dp(24)) * v

    def _draw(self, *_):
        self.canvas.clear()
        y = self.center_y
        from kivy.graphics import Line, Ellipse as E
        with self.canvas:
            Color(*T.LINE)
            Line(points=[self._x(0), y, self._x(1), y], width=dp(1.6))
            Color(*T.BLUE)
            Line(points=[self._x(self.lo), y, self._x(self.hi), y], width=dp(2))
            for v in (self.lo, self.hi):
                r = dp(12) if self._drag is not None and abs(getattr(self, self._drag) - v) < 1e-9 else dp(11)
                E(pos=(self._x(v) - r, y - r), size=(2 * r, 2 * r))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        v = (touch.x - self.x - dp(12)) / max(1, self.width - dp(24))
        self._drag = "lo" if abs(v - self.lo) < abs(v - self.hi) else "hi"
        touch.grab(self)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        v = max(0.0, min(1.0, (touch.x - self.x - dp(12)) / max(1, self.width - dp(24))))
        if self._drag == "lo":
            self.lo = min(v, self.hi - 0.02)
        else:
            self.hi = max(v, self.lo + 0.02)
        if self.cb:
            self.cb(self.lo, self.hi)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._drag = None
            self._draw()
            if self.cb:
                self.cb(self.lo, self.hi, True)
            return True
        return False


def fade_image(source, delay=0.0, **kw):
    """Картинка, которая плавно проявляется (как подгрузка фото в оригинале)."""
    from kivy.uix.image import Image
    im = Image(source=source, fit_mode=kw.pop("fit_mode", "contain"), **kw)
    im.opacity = 0
    Clock.schedule_once(lambda *_: Animation(opacity=1, d=0.35).start(im), 0.15 + delay)
    return im


# ------------------------------------------------------------------ ошибки сети
class ErrorView(BoxLayout):
    """Экран ошибки вместо содержимого: значок, текст и кнопка «Повторить»."""

    def __init__(self, kind, on_retry, **kw):
        from .net import ERRORS
        super().__init__(orientation="vertical", padding=(dp(32), dp(20), dp(32), NAV_SPACE), spacing=dp(12),
                         pos_hint={"x": 0, "y": 0}, **kw)
        icon, title, sub = ERRORS[kind]
        self.kind = kind
        self.add_widget(Widget())
        holder = BoxLayout(size_hint_y=None, height=dp(96))
        holder.add_widget(Widget())
        c = BoxLayout(size_hint_x=None, width=dp(96), padding=dp(24))
        paint(c, T.GRAY_BG, dp(48))
        c.add_widget(Icon(name=icon, color=T.MUTED))
        holder.add_widget(c)
        holder.add_widget(Widget())
        self.add_widget(holder)
        self.add_widget(lbl(title, 20, weight="semi", halign="center", wrap=True))
        self.add_widget(lbl(sub, 15, color=T.MUTED, weight="reg", halign="center", wrap=True))
        btn = AppButton(text="Повторить", radius=dp(8))
        btn.bind(on_release=lambda *_: on_retry())
        self.add_widget(btn)
        self.add_widget(Widget())
        self.opacity = 0
        Animation(opacity=1, d=0.25).start(self)


class ErrorDialog(_FL):
    """Модальное окно ошибки для действий («Оформить», «Войти», оплата)."""

    def __init__(self, kind, on_retry=None, title=None, sub=None, **kw):
        from .net import ERRORS
        super().__init__(**kw)
        icon, t, s = ERRORS.get(kind, ("alert-circle", title, sub))
        with self.canvas.before:
            self._c = Color(0, 0, 0, 0)
            self._r = Rectangle()
        self.bind(pos=lambda *_: setattr(self._r, "pos", self.pos), size=lambda *_: setattr(self._r, "size", self.size))
        box = BoxLayout(orientation="vertical", size_hint=(None, None), size=(min(Window.width * 0.88, dp(380)), dp(280)),
                        pos_hint={"center_x": .5, "center_y": .55}, padding=dp(20), spacing=dp(10))
        paint(box, T.BG, dp(14))
        box.add_widget(Icon(name=icon, color=T.RED, size_hint_y=None, height=dp(44)))
        box.add_widget(lbl(title or t, 18, weight="semi", halign="center", wrap=True))
        box.add_widget(lbl(sub or s, 14, color=T.MUTED, weight="reg", halign="center", wrap=True))
        box.add_widget(Widget())
        if on_retry:
            r = AppButton(text="Повторить", height=dp(46), radius=dp(8))
            r.bind(on_release=lambda *_: (self.dismiss(), on_retry()))
            box.add_widget(r)
        c = AppButton(text="Закрыть", bg=T.BLUE_LIGHT, fg=T.BLUE, height=dp(46), radius=dp(8))
        c.bind(on_release=lambda *_: self.dismiss())
        box.add_widget(c)
        self.box = box
        self.add_widget(box)

    def open(self, parent=None):
        (parent or App.get_running_app().root_layout).add_widget(self)
        self.box.opacity = 0
        Animation(a=0.45, d=0.2).start(self._c)
        Animation(opacity=1, d=0.2).start(self.box)

    def dismiss(self):
        if self.parent:
            self.parent.remove_widget(self)

    def on_touch_down(self, touch):
        super().on_touch_down(touch)
        return True

    def on_touch_move(self, touch):
        super().on_touch_move(touch)
        return True

    def on_touch_up(self, touch):
        super().on_touch_up(touch)
        return True


def net_call(on_ok, delay=0.9, text="Подождите, пожалуйста..."):
    """Действие через сеть: окно ожидания, при ошибке — окно с кнопкой «Повторить»."""
    from .net import net
    from .widgets import WaitDialog
    app = App.get_running_app()
    wait = WaitDialog(text)
    wait.open(app.root_layout)

    def ok():
        wait.dismiss()
        on_ok()

    def fail(kind):
        wait.dismiss()
        ErrorDialog(kind, on_retry=lambda: net_call(on_ok, delay, text)).open()
    net.request(ok, fail, delay=delay)
