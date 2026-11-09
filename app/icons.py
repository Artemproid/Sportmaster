"""Иконки из открытого набора Tabler Icons (MIT), отрисованные шрифтом."""
import json
import os

from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.uix.label import Label

_MAP = json.load(open(os.path.join(os.path.dirname(__file__), "icon_map.json")))

# короткие имена, которыми пользуются экраны -> имена Tabler
ALIAS = {
    "catalog": "list-search", "services": "layout-grid", "heart_fill": "heart-filled", "bag": "shopping-cart",
    "cart": "shopping-cart", "back": "arrow-left", "chevron": "chevron-right", "chevron_down": "chevron-down",
    "chevron_up": "chevron-up", "close": "x", "star": "star-filled", "filter": "adjustments-horizontal",
    "pin": "map-pin", "qr": "qrcode", "box": "package", "help": "help-circle", "info": "info-circle",
    "percent": "discount", "compare": "scale", "chat": "message-circle", "card": "credit-card",
    "store": "building-store", "play": "player-play", "ok": "circle-check-filled", "location": "current-location",
    "shield": "shield-check", "delivery": "truck-delivery",
}


def glyph(name):
    return chr(_MAP.get(ALIAS.get(name, name), _MAP["help-circle"]))


Builder.load_string("""
<Icon>:
    font_name: "Icons"
    text: self.glyph_of(self.name)
    font_size: min(self.width, self.height) * self.scale
    halign: "center"
    valign: "middle"
    text_size: self.size
""")


class Icon(Label):
    name = StringProperty("home")
    color = ListProperty([0, 0, 0, 1])
    stroke = NumericProperty(1.7)   # не используется, оставлено для совместимости
    scale = NumericProperty(0.96)

    def __init__(self, **kw):
        super().__init__(**kw)
        # правило <Label> из widgets.py загружается позже и ставит обычный шрифт — возвращаем иконочный
        self.font_name = "Icons"

    @staticmethod
    def glyph_of(name):
        return glyph(name)
