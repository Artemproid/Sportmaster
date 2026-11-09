"""Сервисы (по ролику ДЗ1): город, загрузка, группы сервисов, «Медиа», «Live-трансляции»."""
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget

from .. import theme as T
from ..common import lbl, paint, vscroll, hscroll, city_row, section_all, PAD, ErrorView
from ..net import net
from ..data import SERVICE_GROUPS, MEDIA, tile
from ..icons import Icon
from ..widgets import PressBox, LoadRing, stagger_in
from .home import service_icon


class ServicesScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="services", **kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(city_row())
        self.body = FloatLayout()
        root.add_widget(self.body)
        self.add_widget(root)
        self.loaded = False

    def on_pre_enter(self):
        if self.loaded:
            return
        self.loaded = True
        self._fetch()

    def _fetch(self):
        self.body.clear_widgets()
        self.body.add_widget(LoadRing(pos_hint={"center_x": .5, "center_y": .55}))

        def failed(kind):
            self.body.clear_widgets()
            self.body.add_widget(ErrorView(kind, self._fetch))
        net.request(self._load, failed, delay=0.9)

    def _load(self):
        self.body.clear_widgets()
        sv, box = vscroll()
        sv.pos_hint = {"x": 0, "y": 0}
        box.padding = (PAD, dp(4), PAD, box.padding[3])
        box.spacing = dp(10)
        cards = []
        for title, items in SERVICE_GROUPS:
            c = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(160), padding=(dp(14), dp(12)), spacing=dp(6))
            paint(c, T.GRAY_BG, dp(14))
            c.add_widget(lbl(title, 17, size_hint_y=None, height=dp(26)))
            row = BoxLayout(spacing=dp(6))
            for name, icon, c1, c2 in items:
                row.add_widget(service_icon(name, icon, c1, c2))
            row.add_widget(Widget())
            c.add_widget(row)
            box.add_widget(c)
            cards.append(c)
        for title, play in (("Медиа", False), ("Live-трансляции", True)):
            from .extra import MediaListScreen, ArticleScreen
            hdr = section_all(title, lambda p=play: App.get_running_app().push(MediaListScreen(live=p)))
            hdr.padding = (0, dp(16), 0, dp(4))
            box.add_widget(hdr)
            sv2, row = hscroll(dp(250))
            row.padding = (0, 0)
            row.spacing = dp(12)
            for name, date, key in MEDIA:
                card = PressBox(orientation="vertical", size_hint_x=None, width=dp(250), spacing=dp(6))
                pic = RelativeLayout(size_hint_y=None, height=dp(150))
                with pic.canvas.before:
                    Color(1, 1, 1, 1)
                    RoundedRectangle(pos=(0, 0), size=(dp(250), dp(150)), radius=[dp(12)], source=tile(key))
                if play:
                    pb = BoxLayout(size_hint=(None, None), size=(dp(56), dp(56)), padding=dp(14),
                                   pos_hint={"center_x": .5, "center_y": .5})
                    paint(pb, T.BLUE, dp(28))
                    pb.add_widget(Icon(name="player-play-filled", color=T.WHITE))
                    pic.add_widget(pb)
                card.add_widget(pic)
                card.add_widget(lbl(name, 15, max_lines=2, valign="top", size_hint_y=None, height=dp(42)))
                card.add_widget(lbl(date, 13, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(20)))
                card.bind(on_release=lambda *_, n=name, d=date, k=key, p=play:
                          App.get_running_app().push(ArticleScreen(n, d, k, live=p)))
                row.add_widget(card)
            box.add_widget(sv2)
        self.body.add_widget(sv)
        stagger_in(cards, 0.05)
