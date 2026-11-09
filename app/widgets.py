"""Переиспользуемые виджеты и анимации."""
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle, BoxShadow, Ellipse, Line
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (NumericProperty, StringProperty, BooleanProperty, ListProperty, ObjectProperty)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget

from . import theme as T
from .data import discount, photo
from .icons import Icon  # noqa: F401
from .store import store

KV = """
#:import T app.theme
#:import dp kivy.metrics.dp

<Label>:
    font_name: "App"
    color: T.TEXT

<Icon>:
    font_name: "Icons"

<Pressable>:
    canvas.before:
        PushMatrix
        Scale:
            origin: self.center
            x: self.pscale
            y: self.pscale
    canvas.after:
        PopMatrix

<AppButton>:
    size_hint_y: None
    height: dp(52)
    canvas.before:
        Color:
            rgba: self.bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]
    BoxLayout:
        pos: root.pos
        size: root.size
        spacing: dp(8)
        Widget:
        Icon:
            name: root.icon or "check"
            color: root.fg
            size_hint_x: None
            width: dp(22) if root.icon else 0
            opacity: 1 if root.icon else 0
        Label:
            text: root.text
            font_name: "AppSemi"
            font_size: root.font_size
            color: root.fg
            size_hint_x: None
            width: self.texture_size[0]
        Widget:

<IconButton>:
    size_hint: None, None
    size: dp(44), dp(44)
    canvas.before:
        Color:
            rgba: self.bg
        Ellipse:
            pos: self.pos
            size: self.size
    Icon:
        name: root.icon
        color: root.icon_color
        size: root.icon_size, root.icon_size
        pos: root.center_x - self.width / 2, root.center_y - self.height / 2

<Chip>:
    size_hint: None, None
    height: dp(36)
    width: lbl.texture_size[0] + dp(30)
    canvas.before:
        Color:
            rgba: T.NAVY if self.active else T.GRAY_BG
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(18)]
    Label:
        id: lbl
        text: root.text
        font_size: "13sp"
        color: T.WHITE if root.active else T.TEXT
        size: self.texture_size
        pos: root.center_x - self.width / 2, root.center_y - self.height / 2

<SizeChip>:
    size_hint: None, None
    size: max(dp(70), lbl.texture_size[0] + dp(28)), dp(58) if self.sub else dp(46)
    canvas.before:
        Color:
            rgba: T.BG
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
        Color:
            rgba: T.BLUE if self.active else T.LINE
        Line:
            rounded_rectangle: (self.x + .5, self.y + .5, self.width - 1, self.height - 1, dp(10))
            width: 1.4 if self.active else 1
    Label:
        id: lbl
        text: root.text
        font_name: "AppSemi"
        font_size: "16sp"
        size: self.texture_size
        pos: root.center_x - self.width / 2, root.center_y - self.height / 2 + (dp(8) if root.sub else 0)
    Label:
        text: root.sub
        font_name: "AppReg"
        font_size: "12sp"
        color: T.MUTED
        size: self.texture_size
        pos: root.center_x - self.width / 2, root.center_y - self.height / 2 - dp(10)
        opacity: 1 if root.sub else 0

<Badge>:
    size_hint: None, None
    size: max(dp(18), lbl.texture_size[0] + dp(10)), dp(18)
    opacity: 1 if self.text not in ("", "0") else 0
    canvas.before:
        PushMatrix
        Scale:
            origin: self.center
            x: self.bscale
            y: self.bscale
        Color:
            rgba: T.RED
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(9)]
        Color:
            rgba: 1, 1, 1, 1
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, dp(9))
            width: 1.3
    canvas.after:
        PopMatrix
    Label:
        id: lbl
        text: root.text
        font_name: "AppBold"
        font_size: "10sp"
        color: T.WHITE
        size: self.texture_size
        pos: root.center_x - self.width / 2, root.center_y - self.height / 2

<RoundToggle>:
    size_hint: None, None
    size: dp(36), dp(36)
    canvas.before:
        Color:
            rgba: 1, 1, 1, .95
        Ellipse:
            pos: self.pos
            size: self.size
        Color:
            rgba: T.RED[0], T.RED[1], T.RED[2], ((1 - self.ring) if 0 < self.ring < 1 else 0)
        Line:
            circle: self.center_x, self.center_y, dp(14) + dp(14) * self.ring
            width: dp(2) * (1 - self.ring) + 0.5
    Icon:
        name: root.icon_on if root.active else root.icon_off
        color: root.color_on if root.active else T.TEXT
        size: dp(22) * root.hscale, dp(22) * root.hscale
        pos: root.center_x - self.width / 2, root.center_y - self.height / 2

<CartMini>:
    size_hint: None, None
    size: dp(38), dp(38)
    canvas.before:
        Color:
            rgba: T.SUCCESS if self.done else (T.BLUE if self.filled else (0, 0, 0, 0))
        Ellipse:
            pos: self.pos
            size: self.size
    Icon:
        name: "check" if root.done else "shopping-cart"
        color: T.WHITE if (root.done or root.filled) else T.BLUE
        size: dp(24), dp(24)
        pos: root.center_x - self.width / 2, root.center_y - self.height / 2

<ProductCard>:
    orientation: "vertical"
    size_hint: None, None
    spacing: dp(2)
    RelativeLayout:
        id: pic
        size_hint_y: None
        height: root.width * 1.2
        canvas.before:
            Color:
                rgba: T.GRAY_BG
            RoundedRectangle:
                pos: 0, 0
                size: self.size
                radius: [dp(12)]
        Image:
            id: img
            source: root.image
            fit_mode: "contain"
            size_hint: .92, .92
            pos_hint: {"center_x": .5, "center_y": .5}
        RoundToggle:
            kind: "fav"
            pid: root.pid
            pos: self.parent.width - self.width - dp(8), self.parent.height - self.height - dp(8)
        RoundToggle:
            kind: "compare"
            pid: root.pid
            pos: self.parent.width - self.width - dp(8), self.parent.height - 2 * self.height - dp(14)
    PhotoDots:
        size_hint_y: None
        height: dp(10)
        n: root.n_photos
    BoxLayout:
        size_hint_y: None
        height: dp(42)
        padding: 0, 0, 0, 0
        BoxLayout:
            orientation: "vertical"
            Label:
                text: root.price_text
                font_name: "AppBold"
                font_size: "17sp"
                color: T.BLUE if root.discount else T.TEXT
                text_size: self.size
                halign: "left"
                valign: "bottom"
            Label:
                text: root.old_text
                markup: True
                font_name: "AppReg"
                font_size: "12sp"
                color: T.MUTED
                text_size: self.size
                halign: "left"
                valign: "top"
                opacity: 1 if root.old_text else 0
        CartMini:
            product: root.product
            pos_hint: {"center_y": .5}
    Label:
        text: root.title
        font_name: "AppReg"
        font_size: "15sp"
        text_size: self.width, None
        size_hint_y: None
        height: dp(40)
        valign: "top"
        max_lines: 2
        line_height: .92
    BoxLayout:
        size_hint_y: None
        height: dp(24) if root.tag else 0
        opacity: 1 if root.tag else 0
        BoxLayout:
            size_hint_x: None
            width: tg.texture_size[0] + dp(14)
            padding: dp(7), dp(2)
            canvas.before:
                Color:
                    rgba: T.PINK_TAG
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(5)]
            Label:
                id: tg
                text: root.tag
                font_size: "12sp"
                color: T.PINK_TEXT
        Widget:
    BoxLayout:
        size_hint_y: None
        height: dp(22)
        spacing: dp(3)
        Icon:
            name: "star"
            color: T.BLUE
            size_hint_x: None
            width: dp(16)
        Label:
            text: "%.1f [color=8a8a8e](%d)[/color]" % (root.rating, root.reviews)
            markup: True
            font_size: "13sp"
            text_size: self.size
            halign: "left"
            valign: "middle"

<SkeletonBox>:
    canvas.before:
        Color:
            rgba: T.SKELETON
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]
"""


class Pressable(ButtonBehavior, Widget):
    """Элемент слегка «проседает» при нажатии и пружинит обратно."""
    pscale = NumericProperty(1)

    def on_press(self):
        Animation.cancel_all(self, "pscale")
        Animation(pscale=0.95, d=0.08, t="out_quad").start(self)

    def on_release(self):
        Animation.cancel_all(self, "pscale")
        Animation(pscale=1, d=0.35, t="out_back").start(self)

    def on_touch_up(self, touch):
        r = super().on_touch_up(touch)
        if self.pscale < 1 and self.state == "normal":
            Animation(pscale=1, d=0.2).start(self)
        return r


class PressBox(Pressable, BoxLayout):
    pass


class AppButton(Pressable):
    text = StringProperty("")
    icon = StringProperty("")
    bg = ListProperty(T.BLUE)
    fg = ListProperty(T.WHITE)
    radius = NumericProperty(dp(12))
    font_size = StringProperty("16sp")

    @classmethod
    def light(cls, **kw):
        return cls(bg=T.BLUE_LIGHT, fg=T.BLUE, **kw)


class IconButton(Pressable):
    icon = StringProperty("back")
    icon_color = ListProperty(T.TEXT)
    icon_size = NumericProperty(dp(26))
    bg = ListProperty([0, 0, 0, 0])


class Chip(Pressable):
    text = StringProperty("")
    active = BooleanProperty(False)


class SizeChip(Pressable):
    text = StringProperty("")
    sub = StringProperty("")
    value = StringProperty("")
    active = BooleanProperty(False)


class Badge(Widget):
    text = StringProperty("")
    bscale = NumericProperty(1)

    def bounce(self):
        Animation.cancel_all(self, "bscale")
        (Animation(bscale=1.6, d=0.12, t="out_quad") + Animation(bscale=1, d=0.45, t="out_elastic")).start(self)


class RoundToggle(ButtonBehavior, Widget):
    """Круглая кнопка на фото: «в избранное» (сердце) или «сравнить» (весы)."""
    kind = StringProperty("fav")
    pid = NumericProperty(0)
    active = BooleanProperty(False)
    hscale = NumericProperty(1)
    ring = NumericProperty(0)
    icon_on = StringProperty("heart_fill")
    icon_off = StringProperty("heart")
    color_on = ListProperty(T.RED)

    def __init__(self, **kw):
        super().__init__(**kw)
        store.bind(favorites=self._sync, compare=self._sync)
        self.bind(pid=self._sync, kind=self._kind)
        self._kind()

    def _kind(self, *_):
        if self.kind == "compare":
            self.icon_on = self.icon_off = "compare"
            self.color_on = T.BLUE
        else:
            self.icon_on, self.icon_off, self.color_on = "heart_fill", "heart", T.RED
        self._sync()

    def _sync(self, *_):
        lst = store.favorites if self.kind == "fav" else store.compare
        self.active = self.pid in lst

    def on_release(self):
        app = App.get_running_app()
        Animation.cancel_all(self)
        if self.kind == "fav":
            now = store.toggle_fav(self.pid)
            msg = "Добавлено в избранное" if now else "Удалено из избранного"
        else:
            now = store.toggle_compare(self.pid)
            msg = "Добавлено к сравнению" if now else "Удалено из сравнения"
        if now:
            self.ring = 0.01
            Animation(ring=1, d=0.45, t="out_quad").start(self)
            (Animation(hscale=1.45, d=0.12, t="out_quad") + Animation(hscale=1, d=0.5, t="out_elastic")).start(self)
        else:
            (Animation(hscale=0.7, d=0.1) + Animation(hscale=1, d=0.3, t="out_back")).start(self)
        app.toast(msg)


# старое имя
class HeartButton(RoundToggle):
    pass


class CartMini(Pressable):
    """Кнопка «в корзину» на карточке: синий круг (или контур, если товара нет в наличии онлайн)."""
    product = ObjectProperty(None, allownone=True)
    done = BooleanProperty(False)
    filled = BooleanProperty(True)

    def on_product(self, *_):
        p = self.product
        self.filled = not (p and p.get("id", 0) % 4 == 0)

    def on_release(self):
        super().on_release()
        p = self.product
        app = App.get_running_app()
        if p["sizes"]:
            app.open_product(p["id"], pick_size=True)
            return
        store.add(p["id"], "—")
        self.done = True
        Clock.schedule_once(lambda *_: setattr(self, "done", False), 1.6)
        card = self.parent.parent
        app.fly_to_cart(card.ids.img)


class ProductCard(Pressable, BoxLayout):
    pid = NumericProperty(0)
    image = StringProperty("")
    title = StringProperty("")
    price_text = StringProperty("")
    old_text = StringProperty("")
    discount = NumericProperty(0)
    rating = NumericProperty(0)
    reviews = NumericProperty(0)
    product = ObjectProperty(None, allownone=True)
    n_photos = NumericProperty(1)
    tag = StringProperty("")

    def __init__(self, product, width=None, **kw):
        super().__init__(**kw)
        self.product = product
        p = product
        self.n_photos = len(p.get("photos", [1]))
        self.tag = "Выгодная скидка" if p.get("promo") or (p.get("old_price") and p["id"] % 2) else (
            "Только у нас" if p.get("only_here") else "")
        self.pid = p["id"]
        self.image = photo(p["image"])
        self.title = p["name"]
        self.price_text = T.price(p["price"])
        d = discount(p)
        self.old_text = f"[s]{T.price(p['old_price'])}[/s] [color=e8262c]-{d}%[/color]" if p["old_price"] else ""
        self.discount = d
        self.rating = p["rating"]
        self.reviews = p["reviews"]
        if width:
            self.set_width(width)

    def set_width(self, w):
        self.width = w
        self.height = w * 1.2 + dp(146)

    def on_release(self):
        super().on_release()
        App.get_running_app().open_product(self.pid)


def _shimmer_texture():
    tex = Texture.create(size=(64, 1), colorfmt="rgba")
    buf = bytearray()
    for i in range(64):
        a = int(255 * max(0.0, 1 - abs(i - 32) / 32) * 0.7)
        buf += bytes([255, 255, 255, a])
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    return tex


_SHIMMER = None


class PhotoDots(Widget):
    """Точки-индикатор фото под картинкой карточки (активная — тёмная)."""
    n = NumericProperty(1)
    active = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw, n=self._draw, active=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        n = int(min(self.n, 6))
        if n <= 1:
            return
        gap = dp(6)
        x0 = self.center_x - (n - 1) * gap / 2
        with self.canvas:
            for i in range(n):
                on = i == self.active
                Color(*(T.TEXT if on else T.rgba(T.MUTED, 0.45)))
                r = dp(2.2) if on else dp(1.8) * (1 - 0.12 * max(0, i - 3))
                Ellipse(pos=(x0 + i * gap - r, self.center_y - r), size=(2 * r, 2 * r))


class LoadRing(Widget):
    """Синяя вращающаяся дуга-загрузка (как в оригинале)."""
    angle = NumericProperty(0)
    radius = NumericProperty(dp(18))

    def __init__(self, **kw):
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("size", (dp(48), dp(48)))
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw, angle=self._draw)
        self.anim = Animation(angle=-360, d=0.9) + Animation(angle=0, d=0)
        self.anim.repeat = True
        self.anim.start(self)
        self.bind(parent=lambda o, p: None if p else self.anim.cancel(self))

    def _draw(self, *_):
        self.canvas.clear()
        a = self.angle
        span = 100 + 60 * abs(((a % 360) / 180.0) - 1)
        with self.canvas:
            Color(*T.BLUE)
            Line(circle=(self.center_x, self.center_y, self.radius, -a, -a + span), width=dp(2.6), cap="round")


class SquareCheck(ButtonBehavior, Widget):
    """Квадратный чекбокс: пустой серый контур / синий с галочкой."""
    active = BooleanProperty(False)
    k = NumericProperty(0)

    def __init__(self, **kw):
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("size", (dp(24), dp(24)))
        super().__init__(**kw)
        self.k = 1 if self.active else 0
        self.bind(pos=self._draw, size=self._draw, k=self._draw)
        self.bind(active=lambda *_: Animation(k=1 if self.active else 0, d=0.18).start(self))
        self._draw()

    def on_release(self):
        self.active = not self.active

    def _draw(self, *_):
        self.canvas.clear()
        x, y = self.center_x - dp(10), self.center_y - dp(10)
        with self.canvas:
            Color(*T.rgba(T.MUTED, 0.7 * (1 - self.k)))
            Line(rounded_rectangle=(x, y, dp(20), dp(20), dp(3)), width=1.2)
            Color(*T.rgba(T.BLUE, self.k))
            RoundedRectangle(pos=(x, y), size=(dp(20), dp(20)), radius=[dp(3)])
            Color(1, 1, 1, self.k)
            Line(points=[x + dp(5), y + dp(10), x + dp(8.5), y + dp(6.5), x + dp(15), y + dp(13.5)], width=dp(1.6),
                 cap="round", joint="round")


class Toggle(ButtonBehavior, Widget):
    """Переключатель-ползунок (серый/синий), можно сделать неактивным."""
    active = BooleanProperty(False)
    disabled_look = BooleanProperty(False)
    k = NumericProperty(0)

    def __init__(self, **kw):
        kw.setdefault("size_hint", (None, None))
        kw.setdefault("size", (dp(44), dp(26)))
        super().__init__(**kw)
        self.bind(pos=self._draw, size=self._draw, k=self._draw, disabled_look=self._draw)
        self.bind(active=lambda *_: Animation(k=1 if self.active else 0, d=0.2, t="out_cubic").start(self))
        self._draw()

    def on_release(self):
        if not self.disabled_look:
            self.active = not self.active

    def _draw(self, *_):
        self.canvas.clear()
        x, y, w, h = self.x, self.center_y - dp(9), dp(40), dp(18)
        a = 0.45 if self.disabled_look else 1
        with self.canvas:
            Color(*T.rgba([.82 + (T.BLUE[0] - .82) * self.k, .82 + (T.BLUE[1] - .82) * self.k,
                           .84 + (T.BLUE[2] - .84) * self.k], a))
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[h / 2])
            Color(1, 1, 1, 1)
            cx = x + dp(9) + (w - dp(18)) * self.k
            Ellipse(pos=(cx - dp(11), self.center_y - dp(11)), size=(dp(22), dp(22)))
            Color(0, 0, 0, 0.12)
            Line(circle=(cx, self.center_y, dp(11)), width=1)


class WaitDialog(FloatLayout):
    """Модальное «Подождите, пожалуйста...» поверх затемнения."""

    def __init__(self, text="Подождите, пожалуйста...", **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(0, 0, 0, 0)
            self._r = Rectangle()
        self.bind(pos=lambda *_: setattr(self._r, "pos", self.pos), size=lambda *_: setattr(self._r, "size", self.size))
        box = BoxLayout(size_hint=(None, None), size=(min(Window.width * 0.88, dp(380)), dp(80)),
                        pos_hint={"center_x": .5, "center_y": .55}, padding=(dp(18), 0), spacing=dp(16))
        with box.canvas.before:
            Color(1, 1, 1, 1)
            rr = RoundedRectangle(radius=[dp(2)])
        box.bind(pos=lambda *_: setattr(rr, "pos", box.pos), size=lambda *_: setattr(rr, "size", box.size))
        rr.size = box.size
        holder = BoxLayout(size_hint_x=None, width=dp(44), padding=(0, dp(16)))
        holder.add_widget(LoadRing(size=(dp(44), dp(44)), radius=dp(16)))
        box.add_widget(holder)
        l = Label(text=text, font_size="15sp", halign="left", valign="middle")
        l.bind(size=lambda o, v: setattr(o, "text_size", v))
        box.add_widget(l)
        self.box = box
        self.add_widget(box)

    def open(self, parent, duration=None, then=None):
        parent.add_widget(self)
        self.box.opacity = 0
        Animation(a=0.4, d=0.2).start(self._c)
        Animation(opacity=1, d=0.2).start(self.box)
        if duration:
            def fin(*_):
                self.dismiss()
                if then:
                    then()
            Clock.schedule_once(fin, duration)

    def dismiss(self, *_):
        Animation(a=0, d=0.18).start(self._c)
        a = Animation(opacity=0, d=0.18)
        a.bind(on_complete=lambda *_: self.parent and self.parent.remove_widget(self))
        a.start(self.box)

    def on_touch_down(self, touch):
        return True


class SkeletonBox(StencilView):
    """Серый блок-заглушка с бегущим бликом (пока «грузятся» данные)."""
    radius = NumericProperty(dp(10))
    phase = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        global _SHIMMER
        if _SHIMMER is None:
            _SHIMMER = _shimmer_texture()
        with self.canvas:
            self._band = Rectangle(texture=_SHIMMER)
        self.bind(pos=self._upd, size=self._upd, phase=self._upd)
        self._anim = Animation(phase=1, d=1.1) + Animation(phase=0, d=0)
        self._anim.repeat = True
        self._anim.start(self)

    def _upd(self, *_):
        bw = max(dp(80), self.width * 0.6)
        x = self.x - bw + (self.width + bw) * self.phase
        self._band.pos = (x, self.y)
        self._band.size = (bw, self.height)

    def stop(self):
        self._anim.cancel(self)


def shadow(widget, radius=dp(16), blur=dp(18), offset=(0, -dp(3)), alpha=0.16):
    """Мягкая тень под виджетом (BoxShadow)."""
    with widget.canvas.before:
        Color(0, 0, 0, alpha)
        s = BoxShadow(pos=widget.pos, size=widget.size, offset=offset, blur_radius=blur,
                      border_radius=(radius,) * 4)
    widget.bind(pos=lambda *_: setattr(s, "pos", widget.pos), size=lambda *_: setattr(s, "size", widget.size))
    return s


def show_toast(parent, text, y=None):
    """Тёмная плашка-уведомление над нижней панелью (как Snackbar)."""
    lbl = Label(text=text, font_size="15sp", size_hint=(None, None), halign="left", valign="middle",
                padding=(dp(14), dp(12)))
    lbl.color = T.WHITE
    w = min(Window.width - dp(28), dp(420))
    lbl.text_size = (w, None)
    lbl.texture_update()
    lbl.size = (w, lbl.texture_size[1])
    with lbl.canvas.before:
        Color(*T.NAVY)
        bg = RoundedRectangle(radius=[dp(6)])
    lbl.bind(pos=lambda *_: setattr(bg, "pos", lbl.pos), size=lambda *_: setattr(bg, "size", lbl.size))
    bg.pos, bg.size = lbl.pos, lbl.size
    lbl.center_x = parent.center_x
    y0 = y if y is not None else dp(110)
    lbl.y = y0 - dp(16)
    lbl.opacity = 0
    for w_ in list(parent.children):
        if getattr(w_, "is_toast", False):
            parent.remove_widget(w_)
    lbl.is_toast = True
    parent.add_widget(lbl)
    a = Animation(y=y0, opacity=1, d=0.25, t="out_cubic") + Animation(d=1.8) + Animation(opacity=0, d=0.25)
    a.bind(on_complete=lambda *_: lbl.parent and parent.remove_widget(lbl))
    a.start(lbl)


def stagger_in(widgets, delay=0.04):
    """Элементы появляются по очереди с лёгким «пружинящим» увеличением."""
    for i, w in enumerate(widgets):
        w.opacity = 0

        def go(_dt, w=w):
            Animation(opacity=1, d=0.35, t="out_cubic").start(w)
            if hasattr(w, "pscale"):
                w.pscale = 0.92
                Animation(pscale=1, d=0.45, t="out_back").start(w)
        Clock.schedule_once(go, 0.05 + i * delay)


class BottomSheet(FloatLayout):
    """Шторка снизу с затемнением. Закрывается тапом по фону или свайпом вниз."""
    dim = NumericProperty(0)

    def __init__(self, content, height, on_close=None, color=None, radius=None, margin=0, **kw):
        super().__init__(**kw)
        self.on_close_cb = on_close
        self._color = color or T.BG
        self._radius = dp(22) if radius is None else radius
        self._margin = margin
        with self.canvas.before:
            self._dim_c = Color(0, 0, 0, 0)
            self._dim_r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd, dim=lambda *_: setattr(self._dim_c, "a", self.dim))
        self.sheet = BoxLayout(orientation="vertical", size_hint=(1, None), height=height,
                               padding=(margin, dp(10), margin, margin))
        with self.sheet.canvas.before:
            Color(*self._color)
            r = self._radius
            self._sr = RoundedRectangle(radius=[r, r, r, r] if self._margin else [r, r, 0, 0])
            Color(*T.LINE)
            self._grip = RoundedRectangle(radius=[dp(2)])
        self.sheet.bind(pos=self._upd_sheet, size=self._upd_sheet)
        self.sheet.add_widget(Widget(size_hint_y=None, height=dp(8)))
        self.sheet.add_widget(content)
        self.add_widget(self.sheet)
        self.sheet.y = -height

    def _upd(self, *_):
        self._dim_r.pos, self._dim_r.size = self.pos, self.size

    def _upd_sheet(self, *_):
        s = self.sheet
        m = self._margin
        if m:
            self._sr.pos, self._sr.size = (s.x + m, s.y + m), (s.width - 2 * m, s.height - m)
        else:
            self._sr.pos, self._sr.size = s.pos, (s.width, s.height + dp(30))
        self._grip.pos = (s.center_x - dp(18), s.top - dp(10))
        self._grip.size = (dp(36), dp(4))

    def open(self, parent):
        parent.add_widget(self)
        Animation(dim=0.45, d=0.25).start(self)
        Animation(y=0, d=0.38, t="out_cubic").start(self.sheet)

    def close(self, *_):
        Animation(dim=0, d=0.22).start(self)
        a = Animation(y=-self.sheet.height, d=0.25, t="in_cubic")
        a.bind(on_complete=lambda *_: self.parent and self.parent.remove_widget(self))
        a.start(self.sheet)
        if self.on_close_cb:
            self.on_close_cb()

    def on_touch_down(self, touch):
        if self.sheet.collide_point(*touch.pos):
            touch.ud["sheet_y"] = touch.y
            super().on_touch_down(touch)
            return True
        self.close()
        return True

    def on_touch_move(self, touch):
        super().on_touch_move(touch)
        return True

    def on_touch_up(self, touch):
        sy = touch.ud.get("sheet_y")
        if sy is not None and sy - touch.y > dp(80) and abs(touch.x - touch.ox) < dp(60):
            self.close()
        super().on_touch_up(touch)
        return True


Builder.load_string(KV)
