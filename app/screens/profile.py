"""Профиль (бонусная карта с переворотом) и «Сервисы»."""
import os
from kivy.animation import Animation
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, PushMatrix, PopMatrix, Scale, Ellipse
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen
from kivy.uix.switch import Switch
from kivy.uix.widget import Widget

from .. import theme as T
from ..common import lbl, paint, vscroll, CountLabel, PAD, GAP, fit_w
from ..icons import Icon
from ..store import store
from ..widgets import PressBox, stagger_in

def _x():
    from . import extra
    return extra


def _chat():
    from .catalog import ChatScreen
    return ChatScreen()


LEVELS = [("Базовый", 0), ("Серебряный", 1000), ("Золотой", 3000), ("Платиновый", 8000)]


def gradient(c1, c2, horizontal=False):
    tex = Texture.create(size=(64, 64), colorfmt="rgba")
    buf = bytearray()
    for y in range(64):
        for x in range(64):
            t = x / 63 if horizontal else (x + (63 - y)) / 126
            buf += bytes(int(255 * (c1[i] + (c2[i] - c1[i]) * t)) for i in range(3)) + b"\xff"
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    return tex


class FlipCard(ButtonBehavior, FloatLayout):
    """Бонусная карта: по нажатию переворачивается и показывает QR-код."""
    sx = NumericProperty(1)
    progress = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(size_hint_y=None, **kw)
        self.front_side = True
        with self.canvas.before:
            PushMatrix()
            self._sc = Scale(origin=(0, 0))
            Color(1, 1, 1, 1)
            self._bg = RoundedRectangle(radius=[dp(20)], texture=gradient(T.BLUE, (0.1, 0.17, 0.45)))
            Color(1, 1, 1, 0.08)
            self._deco1 = Ellipse()
            self._deco2 = Ellipse()
        with self.canvas.after:
            PopMatrix()
        self.bind(pos=self._upd, size=self._upd, sx=self._upd)

        self.front = BoxLayout(orientation="vertical", padding=(dp(20), dp(18)), spacing=dp(4), pos_hint={"x": 0, "y": 0})
        top = BoxLayout(size_hint_y=None, height=dp(24))
        top.add_widget(lbl("SPORTLY CLUB", 14, weight="bold", color=T.WHITE))
        self.level_lbl = lbl("", 13, weight="bold", color=T.YELLOW, halign="right")
        top.add_widget(self.level_lbl)
        self.front.add_widget(top)
        self.front.add_widget(Widget())
        self.front.add_widget(lbl("Бонусный баланс", 13, color=T.rgba(T.WHITE, 0.75), size_hint_y=None, height=dp(18)))
        self.balance = CountLabel(fmt="num", font_name="AppBold", font_size="36sp", halign="left", valign="middle",
                                  size_hint_y=None, height=dp(48))
        self.balance.color = T.WHITE
        self.balance.bind(size=lambda o, v: setattr(o, "text_size", v))
        self.front.add_widget(self.balance)
        self.prog_bg = Widget(size_hint_y=None, height=dp(6))
        with self.prog_bg.canvas:
            Color(1, 1, 1, 0.25)
            self._pb = RoundedRectangle(radius=[dp(3)])
            Color(*T.YELLOW)
            self._pf = RoundedRectangle(radius=[dp(3)])
        self.prog_bg.bind(pos=self._prog, size=self._prog)
        self.bind(progress=self._prog)
        self.front.add_widget(self.prog_bg)
        self.next_lbl = lbl("", 12, color=T.rgba(T.WHITE, 0.85), size_hint_y=None, height=dp(24))
        self.front.add_widget(self.next_lbl)
        hint = BoxLayout(size_hint_y=None, height=dp(22), spacing=dp(6))
        hint.add_widget(Icon(name="qr", color=T.WHITE, size_hint_x=None, width=dp(18)))
        hint.add_widget(lbl("Нажмите, чтобы показать карту на кассе", 12, color=T.rgba(T.WHITE, 0.85)))
        self.front.add_widget(hint)
        self.add_widget(self.front)

        self.back_side = BoxLayout(orientation="vertical", padding=(dp(20), dp(16)), spacing=dp(6), pos_hint={"x": 0, "y": 0})
        qr_row = BoxLayout()
        qr_row.add_widget(Widget())
        qr_box = BoxLayout(size_hint_x=None, padding=dp(8))
        paint(qr_box, T.WHITE, dp(12))
        qr_box.add_widget(Image(source=os.path.join(T.IMG, "qr.png"), fit_mode="contain"))
        qr_row.bind(height=lambda o, h: setattr(qr_box, "width", h))
        qr_row.add_widget(qr_box)
        qr_row.add_widget(Widget())
        self.back_side.add_widget(qr_row)
        self.back_side.add_widget(lbl("2990 4471 0035", 17, weight="bold", color=T.WHITE, halign="center",
                                      size_hint_y=None, height=dp(26)))
        Window.bind(width=self._h)
        self._h()

    def _h(self, *_):
        self.height = (Window.width - PAD * 2) * 0.6

    def _upd(self, *_):
        self._sc.origin = self.center
        self._sc.x = self.sx
        self._bg.pos, self._bg.size = self.pos, self.size
        r = self.height * 0.9
        self._deco1.pos, self._deco1.size = (self.right - r * 0.6, self.top - r * 0.55), (r, r)
        self._deco2.pos, self._deco2.size = (self.right - r * 0.35, self.y - r * 0.5), (r * 0.8, r * 0.8)

    def _prog(self, *_):
        w = self.prog_bg
        self._pb.pos, self._pb.size = w.pos, w.size
        self._pf.pos, self._pf.size = w.pos, (w.width * self.progress, w.height)

    def set_progress(self, v):
        self.progress = 0
        Animation(progress=v, d=1.1, t="out_cubic").start(self)

    def on_release(self):
        a = Animation(sx=0, d=0.16, t="in_quad")
        a.bind(on_complete=lambda *_: self._swap())
        a.start(self)

    def _swap(self):
        self.front_side = not self.front_side
        if self.front_side:
            self.remove_widget(self.back_side)
            self.add_widget(self.front)
        else:
            self.remove_widget(self.front)
            self.add_widget(self.back_side)
        Animation(sx=1, d=0.28, t="out_back").start(self)


class MenuRow(PressBox):
    def __init__(self, icon, text, sub="", right=None, cb=None, **kw):
        super().__init__(size_hint_y=None, height=dp(62), padding=(PAD, 0), spacing=dp(14), **kw)
        self.add_widget(Icon(name=icon, color=T.TEXT, size_hint_x=None, width=dp(26)))
        col = BoxLayout(orientation="vertical", padding=(0, dp(11) if sub else 0))
        col.add_widget(lbl(text, 16))
        if sub:
            col.add_widget(lbl(sub, 12, color=T.MUTED, weight="reg"))
        self.add_widget(col)
        self.add_widget(right if right is not None else Icon(name="chevron", color=T.MUTED, size_hint_x=None, width=dp(20)))
        if cb:
            self.bind(on_release=lambda *_: cb())


class ProfileScreen(Screen):
    """Гость видит предложение войти, пользователь — карту и меню, администратор — ещё и админ-панель."""

    def __init__(self, **kw):
        super().__init__(name="profile", **kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        sv, box = vscroll()
        box.spacing = dp(4)
        head = BoxLayout(size_hint_y=None, height=dp(84), padding=(PAD, dp(14)), spacing=dp(14))
        avl = BoxLayout(size_hint=(None, None), size=(dp(56), dp(56)), pos_hint={"center_y": .5})
        paint(avl, T.BLUE_LIGHT, dp(28))
        self.initials = lbl("", 20, weight="bold", color=T.BLUE, halign="center")
        avl.add_widget(self.initials)
        head.add_widget(avl)
        nm = BoxLayout(orientation="vertical", padding=(0, dp(6)))
        self.name_lbl = lbl("", 20, bold=True, shorten=True)
        self.phone_lbl = lbl("", 13, color=T.MUTED, weight="reg", shorten=True)
        nm.add_widget(self.name_lbl)
        nm.add_widget(self.phone_lbl)
        head.add_widget(nm)
        box.add_widget(head)

        self.card_wrap = BoxLayout(size_hint_y=None, padding=(PAD, 0))
        self.card = FlipCard()
        self.card_wrap.add_widget(self.card)
        self.card_wrap.height = self.card.height
        self.card.bind(height=lambda *_: setattr(self.card_wrap, "height", self.card.height))
        self.login_wrap = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(130), padding=(PAD, 0), spacing=dp(10))
        self.login_wrap.add_widget(lbl("Войдите, чтобы копить бонусы и видеть заказы на любом устройстве", 15, color=T.MUTED,
                                       weight="reg", wrap=True))
        from ..widgets import AppButton
        btn = AppButton(text="Войти или зарегистрироваться", height=dp(54), radius=dp(8))
        btn.bind(on_release=lambda *_: self.open_login())
        self.login_wrap.add_widget(btn)
        self.holder = BoxLayout(size_hint_y=None)
        box.add_widget(self.holder)
        box.add_widget(Widget(size_hint_y=None, height=dp(10)))
        self.menu = BoxLayout(orientation="vertical", size_hint_y=None)
        self.menu.bind(minimum_height=self.menu.setter("height"))
        box.add_widget(self.menu)
        root.add_widget(sv)
        self.add_widget(root)
        store.bind(bonus=lambda *_: self._level())

    def open_login(self):
        from .auth import LoginScreen
        App.get_running_app().push(LoginScreen())

    def _build_menu(self):
        from .admin import AdminScreen
        from .auth import ProfileEditScreen
        app = lambda: App.get_running_app()  # noqa: E731
        self.menu.clear_widgets()
        rows = []
        if store.is_admin:
            rows.append(MenuRow("shield-lock", "Админ-панель", "Товары, заказы, пользователи, сеть",
                                cb=lambda: app().push(AdminScreen())))
        if store.user:
            rows.append(MenuRow("user", "Мои данные", "Имя, почта, телефон, пароль", cb=lambda: app().push(ProfileEditScreen())))
        sw = Switch(active=True, size_hint_x=None, width=dp(64))
        rows += [MenuRow("box", "Мои заказы", "Статусы и история", cb=lambda: app().open_orders()),
                 MenuRow("heart", "Избранное", cb=lambda: app().open_favorites()),
                 MenuRow("percent", "Мои скидки", "Товары со скидкой", cb=lambda: app().open_category("deals")),
                 MenuRow("scale", "Сравнение товаров", cb=lambda: app().push(_x().CompareScreen())),
                 MenuRow("store", "Мои магазины", cb=lambda: app().push(_x().StoresScreen())),
                 MenuRow("pin", "Адреса доставки", cb=lambda: app().push(_x().AddressesScreen())),
                 MenuRow("bell", "Уведомления", right=sw),
                 MenuRow("help", "Помощь", "Чат поддержки", cb=lambda: app().push(_chat())),
                 MenuRow("info", "О приложении", "SPORTLY 2.0 · учебный проект", cb=lambda: app().toast("SPORTLY 2.0"))]
        if store.user:
            rows.append(MenuRow("logout", "Выйти", cb=self.logout))
        for r in rows:
            self.menu.add_widget(r)

    def logout(self):
        store.logout()
        self.on_pre_enter()
        App.get_running_app().toast("Вы вышли из учётной записи")

    def _level(self):
        b = store.bonus
        cur = [l for l in LEVELS if b >= l[1]][-1]
        nxt = next((l for l in LEVELS if l[1] > b), None)
        self.card.level_lbl.text = cur[0].upper()
        if nxt:
            prog = (b - cur[1]) / (nxt[1] - cur[1])
            self.card.next_lbl.text = f"До уровня «{nxt[0]}» — {int(nxt[1] - b)} бонусов"
        else:
            prog = 1
            self.card.next_lbl.text = "Максимальный уровень"
        self.card.set_progress(prog)

    def on_pre_enter(self):
        u = store.user
        self.holder.clear_widgets()
        self._build_menu()
        if u:
            self.name_lbl.text = u["name"]
            self.phone_lbl.text = u["phone"]
            self.initials.text = "".join(w[0] for w in u["name"].split()[:2]).upper()
            self.holder.height = self.card_wrap.height
            self.holder.add_widget(self.card_wrap)
            self.card.balance.value = 0
            self.card.balance.animate_to(store.bonus, d=1.2)
            self._level()
        else:
            self.name_lbl.text = "Гость"
            self.phone_lbl.text = "Вы не вошли в учётную запись"
            self.initials.text = "Г"
            self.holder.height = self.login_wrap.height
            self.holder.add_widget(self.login_wrap)


class ServicesScreen(Screen):
    """Плитки сервисов."""

    def __init__(self, **kw):
        super().__init__(name="services", **kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(lbl("Сервисы", 26, bold=True, size_hint_y=None, height=dp(72), padding=(PAD, dp(10))))
        sv, box = vscroll()
        grid = GridLayout(cols=2, spacing=GAP, padding=(PAD, 0), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        app = lambda: App.get_running_app()  # noqa: E731
        items = [("heart", "Избранное", lambda: app().open_favorites(), T.RED),
                 ("box", "Мои заказы", lambda: app().open_orders(), T.BLUE),
                 ("compare", "Сравнение", lambda: app().toast(f"К сравнению: {len(store.compare)} товара"), T.BLUE),
                 ("qr", "Бонусная карта", lambda: app().go_tab("profile"), T.NAVY),
                 ("store", "Магазины", lambda: app().toast("4 магазина в вашем городе"), T.SUCCESS),
                 ("gift", "Подарочные карты", lambda: app().toast("Номиналы от 1 000 до 30 000 ₽"), T.RED),
                 ("delivery", "Доставка и оплата", lambda: app().toast("Бесплатно от 3 000 ₽"), T.BLUE),
                 ("shield", "Возврат и гарантия", lambda: app().toast("Возврат в течение 30 дней"), T.SUCCESS),
                 ("help", "Помощь", lambda: app().toast("Поддержка: 8 800 000-00-00"), T.NAVY)]
        self.tiles = []
        for icon, text, cb, color in items:
            t = PressBox(orientation="vertical", size_hint_y=None, height=dp(124), padding=(dp(16), dp(14)), spacing=dp(4))
            paint(t, T.GRAY_BG, dp(18))
            ib = BoxLayout(size_hint=(None, None), size=(dp(44), dp(44)), padding=dp(9))
            paint(ib, T.rgba(color, 0.12), dp(14))
            ib.add_widget(Icon(name=icon, color=color))
            t.add_widget(ib)
            t.add_widget(Widget())
            t.add_widget(lbl(text, 15, bold=True, size_hint_y=None, height=dp(40), valign="bottom"))
            t.bind(on_release=lambda *_, cb=cb: cb())
            grid.add_widget(t)
            self.tiles.append(t)
        box.add_widget(grid)
        root.add_widget(sv)
        self.add_widget(root)

    def on_pre_enter(self):
        stagger_in(self.tiles, 0.03)
