"""SPORTLY — учебное мобильное приложение спортивного магазина (Python + Kivy)."""
import os
import sys

from kivy.config import Config

if not any(p in sys.platform for p in ("android", "ios")):
    Config.set("graphics", "width", "400")
    Config.set("graphics", "height", "860")
    Config.set("graphics", "resizable", "1")
    Config.set("input", "mouse", "mouse,multitouch_on_demand")

from app import theme as T  # noqa: E402

T.register_fonts()

from kivy.animation import Animation  # noqa: E402
from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line  # noqa: E402
from kivy.metrics import dp  # noqa: E402
from kivy.properties import NumericProperty  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.floatlayout import FloatLayout  # noqa: E402
from kivy.uix.image import Image  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from kivy.uix.relativelayout import RelativeLayout  # noqa: E402
from kivy.uix.screenmanager import ScreenManager, FadeTransition, SlideTransition, NoTransition  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402

from app.common import lbl, paint  # noqa: E402
from app.icons import Icon  # noqa: E402
from app.net import net  # noqa: E402
from app.store import store  # noqa: E402
from app.widgets import Badge, Pressable, show_toast, shadow  # noqa: E402
from app.screens.home import HomeScreen  # noqa: E402
from app.screens.catalog import CatalogScreen, SearchScreen, ResultsScreen, FilterScreen, MessagesScreen  # noqa: E402
from app.screens.product import ProductScreen  # noqa: E402
from app.screens.cart import CartScreen, FavoritesScreen  # noqa: E402
from app.screens.checkout import OrdersScreen, OrderScreen, PaymentScreen  # noqa: E402
from app.screens.checkout_flow import (CheckoutScreen, LoadingScreen, PickupMapScreen, StoreScreen,  # noqa: E402
                                       ContactsScreen)
from app.screens.profile import ProfileScreen  # noqa: E402
from app.screens.services import ServicesScreen  # noqa: E402

TABS = [("home", "home", "Главная"), ("catalog", "catalog", "Каталог"), ("services", "services", "Сервисы"),
        ("cart", "cart", "Корзина"), ("profile", "user", "Профиль")]


class NavTab(Pressable, BoxLayout):
    isize = NumericProperty(dp(28))

    def __init__(self, name, icon, title, **kw):
        super().__init__(orientation="vertical", padding=(0, dp(9), 0, dp(7)), spacing=dp(1), **kw)
        self.tab = name
        self.box = RelativeLayout(size_hint_y=None, height=dp(30))
        self.icon = Icon(name=icon, size_hint=(None, None), size=(dp(28), dp(28)))
        self.box.add_widget(self.icon)
        self.box.bind(size=self._center)
        self.bind(isize=self._center)
        self.add_widget(self.box)
        self.title = lbl(title, 11, halign="center")
        self.add_widget(self.title)
        self.badge = None
        if name == "cart":
            self.badge = Badge()
            self.box.add_widget(self.badge)
        self.set_active(False, animate=False)

    def _center(self, *_):
        self.icon.size = (self.isize, self.isize)
        self.icon.center = (self.box.width / 2, self.box.height / 2)
        if self.badge:
            self.badge.pos = (self.box.width / 2 + dp(4), self.box.height - dp(12))

    def set_active(self, on, animate=True):
        c = T.BLUE if on else T.MUTED
        if animate:
            Animation(color=c, d=0.2).start(self.icon)
            Animation(color=c, d=0.2).start(self.title)
            if on:
                (Animation(isize=dp(33), d=0.1) + Animation(isize=dp(28), d=0.35, t="out_back")).start(self)
        else:
            self.icon.color = c
            self.title.color = c


class BottomNav(FloatLayout):
    """Плавающее меню-«таблетка» с тенью."""

    def __init__(self, on_tab, **kw):
        super().__init__(size_hint=(None, None), **kw)
        shadow(self, radius=dp(34), blur=dp(24), alpha=0.18)
        paint(self, T.BG, dp(34))
        self.row = BoxLayout(pos_hint={"x": 0, "y": 0}, padding=(dp(6), 0))
        self.tabs = {}
        for name, icon, title in TABS:
            t = NavTab(name, icon, title)
            t.bind(on_release=lambda w: on_tab(w.tab))
            self.tabs[name] = t
            self.row.add_widget(t)
        self.add_widget(self.row)
        self.current = None
        store.bind(cart_count=self._cart)
        self._cart()
        Window.bind(size=self.place)
        self.place()

    def place(self, *_):
        self.size = (Window.width - dp(28), dp(66))
        self.pos = (dp(14), dp(12))

    def select(self, name):
        if name not in self.tabs:
            return
        for n, t in self.tabs.items():
            if (n == name) != (n == self.current):
                t.set_active(n == name)
        self.current = name

    def _cart(self, *_):
        b = self.tabs["cart"].badge
        b.text = str(store.cart_count) if store.cart_count else ""

    def cart_center(self):
        t = self.tabs["cart"]
        return t.icon.to_window(*t.icon.center)

    def show(self, on):
        Animation.cancel_all(self, "y", "opacity")
        Animation(y=dp(12) if on else -dp(90), opacity=1 if on else 0, d=0.25, t="out_cubic").start(self)


class Splash(FloatLayout):
    """Заставка: знак пружинит, линия-«рывок» прорисовывается, экран растворяется."""
    k = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        paint(self, T.NAVY)
        self.mark = Widget(size_hint=(None, None), size=(dp(84), dp(84)))
        with self.mark.canvas:
            Color(*T.BLUE)
            self._bg = RoundedRectangle(radius=[dp(24)])
            Color(1, 1, 1, 1)
            self._ln = Line(width=dp(5), cap="round", joint="round")
        self.mark.bind(pos=self._draw, size=self._draw)
        self.add_widget(self.mark)
        self.title = lbl("SPORTLY", 34, weight="bold", color=T.WHITE, halign="center", size_hint=(1, None), height=dp(50))
        self.sub = lbl("Всё для спорта и отдыха", 15, color=T.rgba(T.WHITE, 0.7), halign="center", weight="reg",
                       size_hint=(1, None), height=dp(24))
        self.add_widget(self.title)
        self.add_widget(self.sub)
        self.bind(size=self._layout)
        self.title.opacity = self.sub.opacity = self.mark.opacity = 0

    def _layout(self, *_):
        self.mark.center = (self.center_x, self.center_y + dp(50))
        self.title.center_y = self.center_y - dp(30)
        self.sub.center_y = self.center_y - dp(64)

    def _draw(self, *_):
        m = self.mark
        self._bg.pos, self._bg.size = m.pos, m.size
        x, y, s = m.x, m.y, m.width
        full = [(.26, .32), (.46, .56), (.57, .44), (.76, .7)]
        n = len(full) - 1
        reach = self.k * n
        pts = []
        for i, (px, py) in enumerate(full):
            if i <= reach:
                pts += [x + s * px, y + s * py]
            else:
                a = full[i - 1]
                f = reach - (i - 1)
                pts += [x + s * (a[0] + (px - a[0]) * f), y + s * (a[1] + (py - a[1]) * f)]
                break
        self._ln.points = pts if len(pts) >= 4 else []

    def play(self, done):
        self._layout()
        m = self.mark
        m.size = (dp(20), dp(20))
        m.center = (self.center_x, self.center_y + dp(50))
        m.opacity = 1
        a = Animation(size=(dp(84), dp(84)), d=0.6, t="out_elastic")
        a.bind(on_progress=lambda *_: setattr(m, "center", (self.center_x, self.center_y + dp(50))))
        a.start(m)

        def draw_line(*_):
            an = Animation(k=1, d=0.45, t="out_cubic")
            an.bind(on_progress=lambda *_: self._draw())
            an.start(self)
        Clock.schedule_once(draw_line, 0.35)
        for i, w in enumerate((self.title, self.sub)):
            y0 = w.y
            w.y = y0 - dp(16)
            Clock.schedule_once(lambda _dt, w=w, y0=y0: Animation(opacity=1, y=y0, d=0.45, t="out_cubic").start(w),
                                0.5 + i * 0.12)

        def out(*_):
            an = Animation(opacity=0, d=0.35)
            an.bind(on_complete=lambda *_: done())
            an.start(self)
        Clock.schedule_once(out, 1.7)


# экраны, на которых нижнее меню скрыто (как в оригинале)
NO_NAV = (CheckoutScreen, LoadingScreen, PickupMapScreen, StoreScreen, ContactsScreen, OrderScreen, PaymentScreen,
          FilterScreen)


def disable_android_focus_highlight():
    """Android рисует серую подсветку фокуса на всю поверхность приложения после нажатия клавиши
    (например, Enter с физической клавиатуры). Отключаем её у всех view окна."""
    try:
        from android.runnable import run_on_ui_thread
        from jnius import autoclass
    except ImportError:
        return     # не Android

    @run_on_ui_thread
    def apply():
        try:
            from jnius import cast
            group_cls = autoclass("java.lang.Class").forName("android.view.ViewGroup")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            stack = [activity.getWindow().getDecorView()]
            n = 0
            while stack:
                view = stack.pop()
                view.setDefaultFocusHighlightEnabled(False)
                n += 1
                if group_cls.isInstance(view):
                    group = cast("android.view.ViewGroup", view)
                    stack.extend(group.getChildAt(i) for i in range(group.getChildCount()))
            print("focus highlight: off for", n, "views")
        except Exception as e:     # подсветка — косметика, запуск из-за неё не должен падать
            print("focus highlight:", e)
    apply()


class NetBanner(Label):
    """Полоса сверху: «Нет подключения к интернету» / «Соединение восстановлено»."""

    def __init__(self, on_visible=None, **kw):
        super().__init__(size_hint=(1, None), height=dp(34), font_size="13sp", halign="center", valign="middle", **kw)
        self.on_visible = on_visible
        self.color = T.WHITE
        self.bind(size=lambda o, v: setattr(o, "text_size", v))
        with self.canvas.before:
            self._c = Color(*T.NAVY)
            self._r = Rectangle()
        self.bind(pos=lambda *_: setattr(self._r, "pos", self.pos), size=lambda *_: setattr(self._r, "size", self.size))
        self.y = Window.height
        net.bind(online=self._changed)
        self._ev = None

    def _changed(self, _n, online):
        if self._ev:
            self._ev.cancel()
        Animation.cancel_all(self)
        if online:
            self.text, self._c.rgba = "Соединение восстановлено", T.SUCCESS
            self._ev = Clock.schedule_once(lambda *_: self._hide(), 2)
        else:
            self.text, self._c.rgba = "Нет подключения к интернету", T.NAVY
        Animation(y=Window.height - self.height, d=0.25, t="out_cubic").start(self)
        self.on_visible(self.height)

    def _hide(self):
        Animation(y=Window.height, d=0.25).start(self)
        self.on_visible(0)


class SportlyApp(App):
    title = "SPORTLY"

    def on_start(self):
        Clock.schedule_once(lambda *_: disable_android_focus_highlight(), 0.5)

    def build(self):
        Window.clearcolor = T.BG
        Window.softinput_mode = "below_target"   # клавиатура не перекрывает поле ввода
        self.ready = False
        store.start(os.environ.get("SPORTLY_DATA_DIR") or self.user_data_dir)
        self.root_layout = FloatLayout()
        self.sm = ScreenManager(transition=NoTransition(), pos_hint={"x": 0, "y": 0})
        self.tabs = {"home": HomeScreen(), "catalog": CatalogScreen(), "services": ServicesScreen(),
                     "cart": CartScreen(), "profile": ProfileScreen()}
        for s in self.tabs.values():
            self.sm.add_widget(s)
        self.stack = []
        self.tab = "home"
        self._uid = 0
        self.root_layout.add_widget(self.sm)
        self.nav = BottomNav(self.go_tab)
        self.root_layout.add_widget(self.nav)
        Clock.schedule_once(lambda *_: self.nav.select("home"), 0)
        self.splash = Splash()
        self.root_layout.add_widget(self.splash)
        Clock.schedule_once(lambda *_: self.splash.play(self._splash_done), 0.1)
        self.sm.size_hint_y = None
        self.top_gap = 0
        self.sm.height = Window.height
        Window.bind(height=lambda *_: self._set_top_gap(self.top_gap))
        self.root_layout.add_widget(NetBanner(on_visible=self._set_top_gap))
        net.start()
        Window.bind(on_keyboard=self._key)
        self.sm.bind(current_screen=self._nav_visibility)
        return self.root_layout

    def _set_top_gap(self, gap):
        """Освободить место под полосу состояния сети, чтобы она не закрывала шапку экрана."""
        self.top_gap = gap
        Animation.cancel_all(self.sm, "height")
        Animation(height=Window.height - gap, d=0.25, t="out_cubic").start(self.sm)

    def _splash_done(self):
        self.root_layout.remove_widget(self.splash)
        self.ready = True
        self.sm.current_screen.dispatch("on_enter")

    def _nav_visibility(self, *_):
        hide = isinstance(self.sm.current_screen, NO_NAV) or getattr(self.sm.current_screen, "hide_nav", False)
        self.nav.show(not hide)

    # ---------- навигация
    def _busy(self):
        return self.sm.transition.is_active

    def go_tab(self, name):
        if self._busy():
            return
        self.nav.select(name)
        if self.tab == name and not self.stack:
            return
        self.sm.transition = FadeTransition(duration=0.18)
        self.sm.current = name
        self.tab = name
        for s in self.stack:
            self.sm.remove_widget(s)
        self.stack = []

    def push(self, screen):
        if self._busy():
            # идёт анимация перехода — откроем экран сразу после неё
            Clock.schedule_once(lambda *_: self.push(screen), 0.08)
            return
        self._uid += 1
        screen.name = f"pushed{self._uid}"
        self.sm.add_widget(screen)
        self.stack.append(screen)
        self.sm.transition = SlideTransition(direction="left", duration=0.28)
        self.sm.current = screen.name

    def replace(self, screen):
        """Открыть экран вместо текущего (например, детали заказа вместо оформления)."""
        old = self.stack.pop() if self.stack else None
        self._uid += 1
        screen.name = f"pushed{self._uid}"
        self.sm.add_widget(screen)
        self.stack.append(screen)
        self.sm.transition = SlideTransition(direction="left", duration=0.28)
        self.sm.current = screen.name
        if old:
            Clock.schedule_once(lambda *_: old.parent and self.sm.remove_widget(old), 0.4)

    def back(self):
        if self._busy():
            return True
        if not self.stack:
            if self.tab != "home":
                self.go_tab("home")
                return True
            return False
        cur = self.stack.pop()
        target = self.stack[-1].name if self.stack else self.tab
        self.sm.transition = SlideTransition(direction="right", duration=0.25)
        self.sm.current = target
        Clock.schedule_once(lambda *_: cur.parent and self.sm.remove_widget(cur), 0.35)
        return True

    def _key(self, _w, key, *_a):
        if key == 27:  # Esc / «назад» на Android
            for w in list(self.root_layout.children):
                if w.__class__.__name__ == "BottomSheet":
                    w.close()
                    return True
                if w.__class__.__name__ == "ErrorDialog":
                    w.dismiss()
                    return True
            return self.back()
        return False

    def open_product(self, pid, pick_size=False):
        self.push(ProductScreen(pid, pick_size=pick_size))

    def open_category(self, key, preset=None):
        from app.screens.catalog import open_section
        open_section(key, preset)

    def open_results(self, query="кроссовки мужские"):
        from app.data import search, search_title
        items = search(query)
        self.push(ResultsScreen(title=search_title(query, items), items=items, query=query))

    def open_messages(self):
        self.push(MessagesScreen())

    def back_to(self, screen):
        """Вернуться к экрану из стека, закрыв всё, что открыто поверх него."""
        if screen not in self.stack or self._busy():
            return self.back()
        cur = self.stack.pop()
        while self.stack and self.stack[-1] is not screen:
            self.sm.remove_widget(self.stack.pop())
        self.sm.transition = SlideTransition(direction="right", duration=0.25)
        self.sm.current = screen.name
        Clock.schedule_once(lambda *_: cur.parent and self.sm.remove_widget(cur), 0.35)

    def open_search(self):
        self.push(SearchScreen())

    def open_checkout(self):
        if not store.selected_items():
            return self.toast("Отметьте товары для оформления")
        self.push(LoadingScreen(lambda: CheckoutScreen()))

    def open_orders(self):
        self.push(OrdersScreen())

    def show_card(self):
        """«Я в магазине»: профиль с перевёрнутой бонусной картой (QR для кассы)."""
        self.go_tab("profile")
        if not store.user:
            return self.toast("Войдите, чтобы показать бонусную карту")
        card = self.tabs["profile"].card
        Clock.schedule_once(lambda *_: card.front_side and card.on_release(), 0.5)

    def open_favorites(self):
        self.push(FavoritesScreen())

    # ---------- эффекты
    def toast(self, text, y=None):
        if y is None:
            y = dp(96) if self.nav.opacity < 0.5 else dp(150)
        show_toast(self.root_layout, text, y=y)

    def fly_to_cart(self, img_widget, toast=True):
        """Фото товара летит по дуге в иконку корзины в нижнем меню."""
        x, y = img_widget.to_window(*img_widget.pos)
        w, h = img_widget.size
        s = min(w, h) * 0.55
        fly = Image(source=img_widget.source, size_hint=(None, None), size=(s, s),
                    pos=(x + (w - s) / 2, y + (h - s) / 2), fit_mode="contain")
        self.root_layout.add_widget(fly)
        tx, ty = self.nav.cart_center()
        mid_x = (fly.center_x + tx) / 2
        a = Animation(center_x=mid_x, y=fly.y + dp(60), size=(s * 0.55, s * 0.55), d=0.3, t="out_quad") + \
            Animation(center_x=tx, center_y=ty, size=(dp(24), dp(24)), opacity=0.4, d=0.4, t="in_quad")

        def done(*_):
            self.root_layout.remove_widget(fly)
            self.nav.tabs["cart"].badge.bounce()
            if toast:
                self.toast("Товар добавлен в корзину")
        a.bind(on_complete=done)
        a.start(fly)


if __name__ == "__main__":
    SportlyApp().run()
