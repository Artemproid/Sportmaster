"""Экраны сервисов и профиля: тренировки, тренеры, трекер, афиша, маршруты, медиа, трансляции,
магазины, адреса доставки, сравнение товаров, таблица размеров."""
import math

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from .. import theme as T
from ..common import lbl, paint, vscroll, hscroll, TopBar, PAD, fit_w, FloatField, product_strip, empty_state
from ..data import STORES, PICKUP_POINTS, BY_ID, MEDIA, tile, photo, section_items
from ..icons import Icon
from ..store import store
from ..widgets import AppButton, PressBox, IconButton, BottomSheet, stagger_in


def _sep(box):
    w = Widget(size_hint_y=None, height=1)
    paint(w, T.LINE)
    box.add_widget(w)


class ListScreen(Screen):
    """Шаблон: заголовок + вступление + строки (иконка, текст, подпись, кнопка-переключатель)."""

    def __init__(self, title, intro, rows, icon="info-circle", action=None, done_text=None, cta=None, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar(title))
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, dp(6), PAD, dp(30))
        box.spacing = dp(2)
        if intro:
            box.add_widget(lbl(intro, 15, color=T.MUTED, weight="reg", wrap=True))
            box.add_widget(Widget(size_hint_y=None, height=dp(10)))
        items = []
        for r in rows:
            name, sub = r[0], r[1]
            ic = r[2] if len(r) > 2 else icon
            row = BoxLayout(size_hint_y=None, height=dp(72), spacing=dp(12))
            ib = BoxLayout(size_hint=(None, None), size=(dp(46), dp(46)), padding=dp(11), pos_hint={"center_y": .5})
            paint(ib, T.BLUE_LIGHT, dp(12))
            ib.add_widget(Icon(name=ic, color=T.BLUE))
            row.add_widget(ib)
            c = BoxLayout(orientation="vertical", padding=(0, dp(12)))
            c.add_widget(lbl(name, 16, shorten=True))
            c.add_widget(lbl(sub, 13, color=T.MUTED, weight="reg", shorten=True))
            row.add_widget(c)
            if action:
                b = AppButton(text=action, bg=T.BLUE_LIGHT, fg=T.BLUE, height=dp(36), radius=dp(18), font_size="13sp",
                              size_hint=(None, None), width=dp(112), pos_hint={"center_y": .5})

                def tap(w, name=name):
                    on = w.text == action
                    w.text = done_text if on else action
                    Animation(bg=T.BLUE if on else T.BLUE_LIGHT, fg=T.WHITE if on else T.BLUE, d=0.2).start(w)
                    App.get_running_app().toast(f"«{name}»: {'готово' if on else 'отменено'}")
                b.bind(on_release=tap)
                row.add_widget(b)
            box.add_widget(row)
            _sep(box)
            items.append(row)
        if cta:
            text, section = cta
            box.add_widget(Widget(size_hint_y=None, height=dp(14)))
            b = AppButton(text=text, radius=dp(8))
            from .catalog import open_section
            b.bind(on_release=lambda *_: open_section(section))
            box.add_widget(b)
        root.add_widget(sv)
        self.add_widget(root)
        stagger_in(items, 0.03)


class Ring(Widget):
    """Кольцо прогресса шагов (анимируется при открытии)."""
    k = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(size_hint=(None, None), size=(dp(200), dp(200)), **kw)
        self.bind(pos=self.draw, size=self.draw, k=self.draw)

    def draw(self, *_):
        self.canvas.clear()
        cx, cy, r = self.center_x, self.center_y, dp(86)
        with self.canvas:
            Color(*T.BLUE_LIGHT)
            Line(circle=(cx, cy, r), width=dp(12))
            Color(*T.BLUE)
            if self.k > 0:
                Line(circle=(cx, cy, r, 0, 360 * self.k), width=dp(12), cap="round")


class TrackerScreen(Screen):
    """Трекер активности: шаги за день (имитация шагомера), цель, неделя."""
    grow = NumericProperty(0)

    def __init__(self, **kw):
        super().__init__(**kw)
        import random
        self.steps = 6000 + random.randint(0, 3500)
        self.goal = 10000
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Трекер активности"))
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, dp(10), PAD, dp(30))
        box.spacing = dp(10)
        holder = RelativeLayout(size_hint_y=None, height=dp(220))
        self.ring = Ring(pos_hint={"center_x": .5, "center_y": .5})
        holder.add_widget(self.ring)
        self.num = lbl("0", 34, weight="bold", halign="center", pos_hint={"center_x": .5, "center_y": .55})
        holder.add_widget(self.num)
        holder.add_widget(lbl(f"из {self.goal:,} шагов".replace(",", " "), 14, color=T.MUTED, halign="center",
                              pos_hint={"center_x": .5, "center_y": .4}))
        box.add_widget(holder)
        stats = BoxLayout(size_hint_y=None, height=dp(76), spacing=dp(10))
        for title, val in (("Километры", f"{self.steps * 0.00075:.1f}"), ("Калории", str(int(self.steps * 0.04))),
                           ("Минуты", str(self.steps // 110))):
            c = BoxLayout(orientation="vertical", padding=dp(10))
            paint(c, T.GRAY_BG, dp(12))
            c.add_widget(lbl(val, 20, weight="semi", halign="center"))
            c.add_widget(lbl(title, 12, color=T.MUTED, halign="center", weight="reg"))
            stats.add_widget(c)
        box.add_widget(stats)
        box.add_widget(lbl("Неделя", 19, weight="semi", size_hint_y=None, height=dp(40)))
        week = BoxLayout(size_hint_y=None, height=dp(150), spacing=dp(8))
        self.bars = []
        for i, d in enumerate("Пн Вт Ср Чт Пт Сб Вс".split()):
            col = BoxLayout(orientation="vertical", spacing=dp(4))
            area = Widget()
            val = [0.55, 0.8, 0.4, 0.95, 0.7, 1.0, self.steps / self.goal][i]
            with area.canvas:
                Color(*(T.BLUE if i == 6 else T.BLUE_LIGHT))
                rr = RoundedRectangle(radius=[dp(6)])
            area.val, area.rr = val, rr
            area.bind(pos=self._bar, size=self._bar)
            self.bars.append(area)
            col.add_widget(area)
            col.add_widget(lbl(d, 12, color=T.MUTED, halign="center", size_hint_y=None, height=dp(18)))
            week.add_widget(col)
        box.add_widget(week)
        self.grow = 0.0
        goal = AppButton(text="Изменить цель", bg=T.BLUE_LIGHT, fg=T.BLUE, radius=dp(8))
        goal.bind(on_release=lambda *_: self._goal())
        box.add_widget(goal)
        root.add_widget(sv)
        self.add_widget(root)

    def _bar(self, area, *_):
        h = area.height * area.val * self.grow
        area.rr.pos, area.rr.size = (area.x + dp(6), area.y), (area.width - dp(12), h)

    def on_enter(self):
        Animation(k=min(1, self.steps / self.goal), d=1.2, t="out_cubic").start(self.ring)
        a = Animation(grow=1, d=0.9, t="out_cubic")
        a.bind(on_progress=lambda *_: [self._bar(b) for b in self.bars])
        a.start(self)
        t0 = [0.0]

        def tick(dt):
            t0[0] += dt
            k = min(1, t0[0] / 1.2)
            self.num.text = f"{int(self.steps * (1 - (1 - k) ** 3)):,}".replace(",", " ")
            return k < 1
        Clock.schedule_interval(tick, 1 / 60)

    def _goal(self):
        app = App.get_running_app()
        content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(16)), spacing=dp(8))
        content.add_widget(lbl("Цель на день", 21, weight="semi", size_hint_y=None, height=dp(44)))
        sheet = None
        for g in (6000, 8000, 10000, 12000, 15000):
            r = PressBox(size_hint_y=None, height=dp(50))
            r.add_widget(lbl(f"{g:,} шагов".replace(",", " "), 16, weight="reg"))
            r.add_widget(Icon(name="check", color=T.BLUE if g == self.goal else (0, 0, 0, 0), size_hint_x=None, width=dp(24)))

            def pick(_w, g=g):
                self.goal = g
                sheet.close()
                app.toast("Цель сохранена")
                Animation(k=min(1, self.steps / g), d=0.6, t="out_cubic").start(self.ring)
            r.bind(on_release=pick)
            content.add_widget(r)
        sheet = BottomSheet(content, height=dp(50) * 5 + dp(90))
        sheet.open(app.root_layout)



class ArticleScreen(Screen):
    """Статья из раздела «Медиа» (или карточка трансляции)."""

    def __init__(self, title, date, key, live=False, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Трансляция" if live else "Медиа"))
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, dp(4), PAD, dp(30))
        box.spacing = dp(10)
        pic = RelativeLayout(size_hint_y=None, height=(Window.width - PAD * 2) * 0.6)
        with pic.canvas.before:
            Color(1, 1, 1, 1)
            rr = RoundedRectangle(radius=[dp(14)], source=tile(key), pos=(0, 0))
        pic.bind(size=lambda *_: setattr(rr, "size", pic.size))
        if live:
            self.play = AppButton(text="", icon="player-play-filled", size_hint=(None, None), size=(dp(64), dp(64)),
                                  radius=dp(32), pos_hint={"center_x": .5, "center_y": .5})
            self.play.bind(on_release=lambda *_: self._toggle())
            pic.add_widget(self.play)
            self.live_tag = BoxLayout(size_hint=(None, None), size=(dp(74), dp(26)), pos_hint={"x": .03, "top": .95})
            paint(self.live_tag, T.RED, dp(6))
            self.live_tag.add_widget(lbl("● LIVE", 12, weight="bold", color=T.WHITE, halign="center"))
            pic.add_widget(self.live_tag)
        box.add_widget(pic)
        box.add_widget(lbl(title, 22, weight="semi", wrap=True))
        box.add_widget(lbl(date, 13, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(20)))
        text = ("Рассказываем, как подготовиться, что взять с собой и на что обратить внимание. Начинайте с коротких "
                "тренировок, постепенно увеличивая нагрузку, и не забывайте про разминку и восстановление.\n\n"
                "Правильная экипировка помогает тренироваться дольше и без травм: подбирайте обувь по размеру стопы, "
                "одежду — по погоде, а инвентарь — по уровню подготовки.")
        box.add_widget(lbl(text, 15, weight="reg", wrap=True, line_height=1.25))
        box.add_widget(lbl("Товары из статьи", 19, weight="semi", size_hint_y=None, height=dp(44)))
        strip = product_strip(section_items(key if key in ("run", "tennis", "nutrition") else "run")[:8], width=dp(150))
        strip.children[0].padding = (0, 0)
        box.add_widget(strip)
        root.add_widget(sv)
        self.add_widget(root)
        self.playing = False

    def _toggle(self):
        self.playing = not self.playing
        self.play.icon = "player-pause-filled" if self.playing else "player-play-filled"
        App.get_running_app().toast("Трансляция запущена" if self.playing else "Пауза")
        if self.playing:
            a = Animation(opacity=0.4, d=0.6) + Animation(opacity=1, d=0.6)
            a.repeat = True
            a.start(self.live_tag)
        else:
            Animation.cancel_all(self.live_tag)
            self.live_tag.opacity = 1


class MediaListScreen(Screen):
    def __init__(self, live=False, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Live-трансляции" if live else "Медиа"))
        sv, box = vscroll()
        box.padding = (PAD, dp(4), PAD, box.padding[3])
        box.spacing = dp(16)
        items = MEDIA + [("Разминка перед бегом за 10 минут", "20 октября", "fitness"),
                         ("Как выбрать мяч для футбола", "15 октября", "football")]
        cards = []
        for name, date, key in items:
            c = PressBox(orientation="vertical", size_hint_y=None, height=dp(250), spacing=dp(6))
            pic = RelativeLayout(size_hint_y=None, height=dp(180))
            with pic.canvas.before:
                Color(1, 1, 1, 1)
                rr = RoundedRectangle(radius=[dp(12)], source=tile(key), pos=(0, 0))
            pic.bind(size=lambda o, *_, rr=rr: setattr(rr, "size", o.size))
            c.add_widget(pic)
            c.add_widget(lbl(name, 16, size_hint_y=None, height=dp(24), shorten=True))
            c.add_widget(lbl(date, 13, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(18)))
            c.bind(on_release=lambda *_, n=name, d=date, k=key: App.get_running_app().push(ArticleScreen(n, d, k, live=live)))
            box.add_widget(c)
            cards.append(c)
        root.add_widget(sv)
        self.add_widget(root)
        stagger_in(cards, 0.05)


def service_action(name):
    """Что открывает плитка сервиса."""
    app = App.get_running_app()
    n = name.replace("\n", " ").replace("- ", "-")
    from .catalog import open_section
    simple = {
        "Беговые тренировки": ("run", None), "Питание": ("nutrition", None),
        "Бра, топы": ("clothes", {"gender": {"Женский"}}), "Стильные легинсы": ("style", {"gender": {"Женский"}}),
    }
    if n in simple:
        return open_section(*simple[n])
    if n.startswith("Онлайн"):
        return app.push(ListScreen("Онлайн-тренировки", "Занимайтесь дома с тренерами SPORTLY — бесплатно.", [
            ("Утренняя зарядка", "15 мин · новичкам", "sun"), ("Функциональная тренировка", "30 мин · средний", "barbell"),
            ("Йога для спины", "25 мин · все уровни", "stretching"), ("Интервальный бег", "40 мин · продвинутым", "run"),
            ("Растяжка после бега", "12 мин · все уровни", "stretching-2")], action="Начать", done_text="Идёт ✓"))
    if n.startswith("Биржа"):
        return app.push(ListScreen("Биржа тренеров", "Персональные тренеры рядом с вами.", [
            ("Ирина К.", "Бег, ОФП · ★ 4.9 · от 1 500 ₽", "user"), ("Максим Д.", "Футбол · ★ 4.8 · от 1 200 ₽", "user"),
            ("Ольга С.", "Йога, растяжка · ★ 5.0 · от 1 800 ₽", "user"), ("Артём В.", "Теннис · ★ 4.7 · от 2 000 ₽", "user")],
            action="Записаться", done_text="Записаны"))
    if n.startswith("Трекер"):
        return app.push(TrackerScreen())
    if n.startswith("Live"):
        return app.push(MediaListScreen(live=True))
    if n == "Медиа":
        return app.push(MediaListScreen())
    if n == "Афиша":
        return app.push(ListScreen("Афиша", "Спортивные события вашего города.", [
            ("Городской забег 10 км", "16 ноября · Набережная", "calendar-event"),
            ("Турнир по мини-футболу", "23 ноября · Стадион «Труд»", "ball-football"),
            ("Открытая тренировка по йоге", "30 ноября · ТРЦ «Лето»", "stretching"),
            ("Лыжный марафон", "14 декабря · Лесопарк", "ski-jumping")], action="Пойду", done_text="Иду ✓"))
    if n == "Маршруты":
        return app.push(ListScreen("Маршруты", "Популярные маршруты для бега, прогулок и велосипеда.", [
            ("Вдоль набережной", "5,2 км · бег · лёгкий", "route"), ("Лесопарковая петля", "8,7 км · бег · средний", "trees"),
            ("Вело-кольцо", "21 км · велосипед · средний", "bike"), ("Горка и обратно", "3,4 км · ходьба · лёгкий", "mountain")],
            action="В избранное", done_text="Сохранён", cta=("Товары для походов", "hiking")))
    app.toast(n)


class StoresScreen(Screen):
    """Мои магазины: список с раскрывающимися подробностями. pick — для брони товара."""

    def __init__(self, product=None, **kw):
        super().__init__(**kw)
        self.product = product
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Забронировать в магазине" if product else "Мои магазины"))
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, 0, PAD, dp(30))
        box.spacing = 0
        rows = []
        for p in PICKUP_POINTS:
            wrap = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(74))
            head = PressBox(size_hint_y=None, height=dp(74), spacing=dp(12))
            head.add_widget(Icon(name="map-pin-filled", color=T.NAVY, size_hint_x=None, width=dp(24)))
            c = BoxLayout(orientation="vertical", padding=(0, dp(14)))
            c.add_widget(lbl(p["name"], 16))
            c.add_widget(lbl(p["addr"], 13, color=T.MUTED, weight="reg", shorten=True))
            head.add_widget(c)
            arrow = Icon(name="chevron_down", color=T.MUTED, size_hint_x=None, width=dp(22))
            head.add_widget(arrow)
            det = BoxLayout(orientation="vertical", size_hint_y=None, height=0, opacity=0, padding=(dp(36), 0, 0, dp(8)),
                            spacing=dp(6))
            for t in ("Ежедневно 10:00–22:00", "+7 (3822) 00-00-00", f"Товары {p['when'].lower()}"):
                det.add_widget(lbl(t, 14, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(20)))
            btn = AppButton(text="Забронировать здесь" if product else "Построить маршрут", bg=T.BLUE_LIGHT, fg=T.BLUE,
                            height=dp(40), radius=dp(8))
            btn.bind(on_release=lambda *_, p=p: self._act(p))
            det.add_widget(btn)

            def toggle(_w, det=det, wrap=wrap, arrow=arrow):
                open_ = det.height == 0
                arrow.name = "chevron_up" if open_ else "chevron_down"
                Animation(height=dp(130) if open_ else 0, opacity=1 if open_ else 0, d=0.25, t="out_cubic").start(det)
                Animation(height=dp(74) + (dp(130) if open_ else 0), d=0.25, t="out_cubic").start(wrap)
            head.bind(on_release=toggle)
            wrap.add_widget(head)
            wrap.add_widget(det)
            box.add_widget(wrap)
            _sep(box)
            rows.append(wrap)
        root.add_widget(sv)
        self.add_widget(root)
        stagger_in(rows, 0.04)

    def _act(self, p):
        app = App.get_running_app()
        if self.product:
            app.toast(f"Товар забронирован в «{p['name']}» на 24 часа")
            app.back()
        else:
            app.toast(f"Маршрут до «{p['name']}»: 12 минут пешком")


class AddressesScreen(Screen):
    """Адреса доставки: список, добавление, удаление."""

    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Адреса доставки"))
        self.list = BoxLayout(orientation="vertical", size_hint_y=None, padding=(PAD, 0), spacing=0)
        self.list.bind(minimum_height=self.list.setter("height"))
        sv, box = vscroll(bottom=dp(20))
        box.add_widget(self.list)
        form = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(140), padding=(PAD, dp(14)), spacing=dp(12))
        self.f = FloatField("Новый адрес: город, улица, дом")
        form.add_widget(self.f)
        add = AppButton(text="Добавить адрес", radius=dp(8))
        add.bind(on_release=lambda *_: self.add())
        form.add_widget(add)
        box.add_widget(form)
        root.add_widget(sv)
        self.add_widget(root)
        self.refresh()

    def refresh(self):
        self.list.clear_widgets()
        if not store.addresses:
            self.list.add_widget(lbl("Пока нет сохранённых адресов", 15, color=T.MUTED, weight="reg", size_hint_y=None,
                                     height=dp(60)))
        for a in store.addresses:
            r = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(12))
            r.add_widget(Icon(name="home", color=T.BLUE, size_hint_x=None, width=dp(24)))
            r.add_widget(lbl(a, 15, shorten=True))
            rm = IconButton(icon="trash", icon_color=T.MUTED, icon_size=dp(22), pos_hint={"center_y": .5})
            rm.bind(on_release=lambda *_, a=a: (store.addresses.remove(a), store.save(), self.refresh()))
            r.add_widget(rm)
            self.list.add_widget(r)

    def add(self):
        t = self.f.text
        if len(t) < 6:
            self.f.error()
            return App.get_running_app().toast("Укажите адрес полностью")
        store.addresses.append(t)
        store.save()
        self.f.inp.text = ""
        self.refresh()
        App.get_running_app().toast("Адрес сохранён")


class CompareScreen(Screen):
    """Сравнение товаров: таблица характеристик с горизонтальной прокруткой."""

    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Сравнение"))
        items = [BY_ID[i] for i in store.compare if i in BY_ID]
        if not items:
            root.add_widget(empty_state("scale", "Нет товаров для сравнения", "Нажмите на весы на карточке товара",
                                        "В каталог", lambda: App.get_running_app().go_tab("catalog")))
            self.add_widget(root)
            return
        rows = [("Цена", lambda p: T.price(p["price"])), ("Бренд", lambda p: p["brand"]), ("Вид", lambda p: p["kind"]),
                ("Пол", lambda p: p["gender"]), ("Цвет", lambda p: p["color"]), ("Сезон", lambda p: p["season"] or "—"),
                ("Рейтинг", lambda p: f"★ {p['rating']}"), ("Размеры", lambda p: ", ".join(s for s, _ in p["sizes"]) or "—")]
        sv = ScrollView(do_scroll_y=True, do_scroll_x=True, bar_width=0, effect_cls="ScrollEffect")
        cw = dp(160)
        grid = GridLayout(cols=len(items) + 1, size_hint=(None, None), padding=(PAD, dp(8)), spacing=(dp(10), 0))
        grid.bind(minimum_height=grid.setter("height"), minimum_width=grid.setter("width"))
        grid.add_widget(Widget(size_hint=(None, None), size=(dp(80), dp(200))))
        for p in items:
            c = PressBox(orientation="vertical", size_hint=(None, None), size=(cw, dp(200)))
            pic = BoxLayout(size_hint_y=None, height=dp(130))
            paint(pic, T.GRAY_BG, dp(10))
            pic.add_widget(Image(source=photo(p["image"]), fit_mode="contain"))
            c.add_widget(pic)
            c.add_widget(lbl(p["name"], 13, max_lines=2, valign="top"))
            c.bind(on_release=lambda *_, p=p: App.get_running_app().open_product(p["id"]))
            grid.add_widget(c)
        def cell(text, w, **kw):
            c = lbl(text, kw.pop("fs", 14), size_hint=(None, None), **kw)
            c.size = (w, dp(44))
            return c
        for title, fn in rows:
            grid.add_widget(cell(title, dp(80), fs=13, color=T.MUTED, weight="reg"))
            for p in items:
                grid.add_widget(cell(fn(p), cw, shorten=True))
        sv.add_widget(grid)
        root.add_widget(sv)
        self.add_widget(root)


def size_table_sheet(product):
    """Таблица размеров (шторка)."""
    app = App.get_running_app()
    content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(16)), spacing=dp(2))
    content.add_widget(lbl("Таблица размеров", 21, weight="semi", size_hint_y=None, height=dp(46)))
    shoes = product["cat"] == "shoes"
    head = ("RUS", "EUR", "US", "Стопа") if shoes else ("RUS", "INT", "Грудь", "Талия")
    from ..data import size_in
    rows = []
    for rus, hint in product["sizes"]:
        if shoes:
            rows.append((rus, size_in("EUR", "shoes", rus), size_in("US", "shoes", rus), hint))
        else:
            n = int(rus) if rus.isdigit() else 48
            rows.append((rus, hint, f"{n * 2} см", f"{n * 2 - 12} см"))
    g = GridLayout(cols=4, size_hint_y=None, row_default_height=dp(38), row_force_default=True)
    g.bind(minimum_height=g.setter("height"))
    for h in head:
        g.add_widget(lbl(h, 14, color=T.MUTED, halign="center"))
    for r in rows:
        for v in r:
            g.add_widget(lbl(v, 15, weight="reg", halign="center"))
    content.add_widget(g)
    if shoes:
        content.add_widget(lbl("Как узнать длину стопы: встаньте на лист бумаги, обведите стопу и измерьте расстояние от "
                               "пятки до кончика самого длинного пальца.", 13, color=T.MUTED, weight="reg", wrap=True))
    BottomSheet(content, height=dp(38) * (len(rows) + 1) + dp(180)).open(app.root_layout)
