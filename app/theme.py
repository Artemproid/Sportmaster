"""Цвета, шрифты и форматирование — единый стиль приложения."""
import os
from kivy.core.text import LabelBase
from kivy.utils import get_color_from_hex as hx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
IMG = os.path.join(ASSETS, "img")
PHOTOS = os.path.join(ASSETS, "photos")

NAVY = hx("#181D30")          # тёмные блоки: шапка главной, плавающая панель покупки
NAVY_2 = hx("#31374F")        # поле поиска на тёмном фоне
BLUE = hx("#1D4ED8")          # основные кнопки, активная вкладка, цены со скидкой
BLUE_2 = hx("#3B6FF0")
BLUE_LIGHT = hx("#E9ECFB")    # светлые кнопки и плашки
RED = hx("#E8262C")
RED_SOFT = hx("#FDE1E6")
YELLOW = hx("#FFCF26")
BG = hx("#FFFFFF")
GRAY_BG = hx("#F4F4F4")       # подложка фото и полей
GRAY_BAND = hx("#EEEEEE")
TEXT = hx("#121212")
MUTED = hx("#8A8A8E")
LINE = hx("#E4E4E7")
SKELETON = hx("#ECEEF1")
SUCCESS = hx("#1AA35B")
GREEN_BADGE = hx("#5BD94A")
TILE = hx("#E2E7FD")
ORANGE = hx("#E58A00")
PINK_TAG = hx("#FDE1E6")
PINK_TEXT = hx("#E2264D")
WHITE = [1, 1, 1, 1]

# совместимость со старыми именами
PRIMARY = BLUE
PRIMARY_DARK = NAVY
PRIMARY_LIGHT = BLUE_LIGHT
ACCENT = RED
ACCENT_SOFT = RED_SOFT
CARD = BG


def rgba(c, a):
    return [c[0], c[1], c[2], a]


def register_fonts():
    f = os.path.join(ASSETS, "fonts")
    LabelBase.register(name="App", fn_regular=os.path.join(f, "Montserrat-Medium.ttf"),
                       fn_bold=os.path.join(f, "Montserrat-Bold.ttf"))
    LabelBase.register(name="AppReg", fn_regular=os.path.join(f, "Montserrat-Regular.ttf"))
    LabelBase.register(name="AppSemi", fn_regular=os.path.join(f, "Montserrat-SemiBold.ttf"))
    LabelBase.register(name="AppBold", fn_regular=os.path.join(f, "Montserrat-Bold.ttf"))
    LabelBase.register(name="Icons", fn_regular=os.path.join(f, "tabler-icons.ttf"))


def price(v):
    """12990 -> '12 990 ₽'"""
    return f"{int(round(v)):,}".replace(",", " ") + " ₽"


def plural(n, one, few, many):
    n = abs(n) % 100
    if 10 < n < 20:
        return many
    n %= 10
    return one if n == 1 else few if 2 <= n <= 4 else many
