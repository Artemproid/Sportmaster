"""Админ-панель: сводка, товары, заказы, пользователи и режимы сети. Доступна только роли admin."""
import secrets

from kivy.animation import Animation
from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from .. import theme as T
from ..catalog_db import ALL_PRODUCTS, TEMPLATES, add_product, edit_product
from ..common import (lbl, paint, vscroll, hscroll, TopBar, PAD, fit_w, FloatField, OutlineChip, ErrorDialog, net_call)
from ..data import BY_ID, photo
from ..db import db, AuthError
from ..icons import Icon
from ..net import net, MODES
from ..store import store, STATUSES
from ..widgets import AppButton, PressBox, BottomSheet, SquareCheck, Toggle, stagger_in


def app():
    return App.get_running_app()


def _sep(box):
    w = Widget(size_hint_y=None, height=1)
    paint(w, T.LINE)
    box.add_widget(w)


def search_field(hint, on_text):
    f = BoxLayout(size_hint_y=None, height=dp(46), padding=(dp(14), 0), spacing=dp(8))
    paint(f, T.GRAY_BG, dp(23))
    f.add_widget(Icon(name="search", color=T.MUTED, size_hint_x=None, width=dp(22)))
    inp = TextInput(hint_text=hint, multiline=False, font_name="AppReg", font_size="15sp", background_normal="",
                    background_active="", background_color=(0, 0, 0, 0), foreground_color=T.TEXT, cursor_color=T.BLUE,
                    hint_text_color=T.MUTED, padding=(0, dp(12), 0, 0))
    inp.bind(text=lambda i, t: on_text(t.strip().lower()))
    f.add_widget(inp)
    return f


def confirm(title, text, button, on_yes):
    content = BoxLayout(orientation="vertical", padding=(PAD, 0, PAD, dp(16)), spacing=dp(10))
    content.add_widget(lbl(title, 20, weight="semi", size_hint_y=None, height=dp(40)))
    content.add_widget(lbl(text, 15, color=T.MUTED, weight="reg", wrap=True))
    content.add_widget(Widget())
    sheet = None
    yes = AppButton(text=button, bg=T.RED, radius=dp(8))
    no = AppButton(text="Отмена", bg=T.BLUE_LIGHT, fg=T.BLUE, radius=dp(8))
    content.add_widget(yes)
    content.add_widget(no)
    sheet = BottomSheet(content, height=dp(280))
    yes.bind(on_release=lambda *_: (sheet.close(), on_yes()))
    no.bind(on_release=lambda *_: sheet.close())
    sheet.open(app().root_layout)


class AdminBase(Screen):
    hide_nav = True

    def __init__(self, title, **kw):
        super().__init__(**kw)
        self.root_box = BoxLayout(orientation="vertical")
        paint(self.root_box, T.BG)
        self.root_box.add_widget(TopBar(title))
        self.add_widget(self.root_box)


# ============================================================================ сводка
class AdminScreen(AdminBase):
    def __init__(self, **kw):
        super().__init__("Админ-панель", **kw)
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, dp(6), PAD, dp(30))
        box.spacing = dp(12)
        self.grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(190))
        box.add_widget(self.grid)
        for icon, text, sub, make in (("package", "Товары", "Цены, скидки, скрытие, новые товары", AdminProductsScreen),
                                      ("receipt", "Заказы", "Статусы и отмена", AdminOrdersScreen),
                                      ("users", "Пользователи", "Роли, блокировка, бонусы, пароли", AdminUsersScreen),
                                      ("wifi", "Сеть и ошибки", "Проверка экранов ошибок", AdminNetworkScreen)):
            r = PressBox(size_hint_y=None, height=dp(72), spacing=dp(14))
            ic = BoxLayout(size_hint=(None, None), size=(dp(46), dp(46)), padding=dp(11), pos_hint={"center_y": .5})
            paint(ic, T.BLUE_LIGHT, dp(12))
            ic.add_widget(Icon(name=icon, color=T.BLUE))
            r.add_widget(ic)
            c = BoxLayout(orientation="vertical", padding=(0, dp(14)))
            c.add_widget(lbl(text, 16))
            c.add_widget(lbl(sub, 13, color=T.MUTED, weight="reg"))
            r.add_widget(c)
            r.add_widget(Icon(name="chevron", color=T.MUTED, size_hint_x=None, width=dp(20)))
            r.bind(on_release=lambda *_, m=make: app().push(m()))
            box.add_widget(r)
            _sep(box)
        self.root_box.add_widget(sv)

    def on_pre_enter(self):
        paid = [o for o in db.orders if o["status"] >= 1 and not o.get("cancelled")]
        self.grid.clear_widgets()
        visible = sum(1 for p in ALL_PRODUCTS if not p.get("hidden"))
        for title, value in (("Товаров в продаже", str(visible)), ("Пользователей", str(len(db.users))),
                             ("Заказов", str(len(db.orders))), ("Выручка", T.price(sum(o["total"] for o in paid)))):
            c = BoxLayout(orientation="vertical", padding=dp(14))
            paint(c, T.GRAY_BG, dp(12))
            c.add_widget(lbl(value, 22, weight="bold"))
            c.add_widget(lbl(title, 13, color=T.MUTED, weight="reg"))
            self.grid.add_widget(c)


# ============================================================================ товары
LIST_LIMIT = 40


class AdminProductsScreen(AdminBase):
    def __init__(self, **kw):
        super().__init__("Товары", **kw)
        self.q, self.flt = "", "Все"
        head = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(176), padding=(PAD, 0, PAD, dp(6)), spacing=dp(8))
        add = AppButton(text="Добавить товар", icon="plus", height=dp(50), radius=dp(8))
        add.bind(on_release=lambda *_: app().push(AdminProductEdit()))
        head.add_widget(add)
        head.add_widget(search_field("Название или бренд", self._search))
        csv, chips = hscroll(dp(44))
        chips.padding = (0, dp(2))
        chips.spacing = dp(8)
        self.chips = {}
        for name in ("Все", "Скрытые", "Со скидкой", "Новые"):
            c = OutlineChip(name, height=dp(38))
            c.active = name == "Все"
            c.bind(on_release=lambda *_, n=name: self._filter(n))
            chips.add_widget(c)
            self.chips[name] = c
        head.add_widget(csv)
        self.root_box.add_widget(head)
        self.sv, self.box = vscroll(bottom=dp(20))
        self.box.padding = (PAD, 0, PAD, dp(20))
        self.box.spacing = 0
        self.root_box.add_widget(self.sv)

    def on_pre_enter(self):
        self.refresh()

    def _search(self, q):
        self.q = q
        self.refresh()

    def _filter(self, name):
        self.flt = name
        for n, c in self.chips.items():
            c.active = n == name
        self.refresh()

    def refresh(self):
        tests = {"Все": lambda p: True, "Скрытые": lambda p: p.get("hidden"), "Со скидкой": lambda p: p["old_price"],
                 "Новые": lambda p: p.get("custom")}
        items = [p for p in reversed(ALL_PRODUCTS) if tests[self.flt](p) and
                 (self.q in p["name"].lower() or self.q in p["brand"].lower())]
        self.box.clear_widgets()
        self.box.add_widget(lbl(f"Найдено: {len(items)}" + (f", показаны первые {LIST_LIMIT}" if len(items) > LIST_LIMIT else ""),
                                13, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(28)))
        for p in items[:LIST_LIMIT]:
            r = PressBox(size_hint_y=None, height=dp(80), spacing=dp(12), padding=(0, dp(6)))
            th = BoxLayout(size_hint_x=None, width=dp(60))
            paint(th, T.GRAY_BG, dp(8))
            th.add_widget(Image(source=photo(p["image"]), fit_mode="contain"))
            r.add_widget(th)
            c = BoxLayout(orientation="vertical", padding=(0, dp(6)))
            c.add_widget(lbl(p["name"], 14, shorten=True, shorten_from="right", color=T.MUTED if p.get("hidden") else T.TEXT))
            sub = T.price(p["price"]) + (f"  (было {T.price(p['old_price'])})" if p["old_price"] else "")
            c.add_widget(lbl(("Скрыт · " if p.get("hidden") else "") + sub, 13, weight="reg",
                             color=T.RED if p.get("hidden") else T.MUTED))
            r.add_widget(c)
            r.add_widget(Icon(name="chevron", color=T.MUTED, size_hint_x=None, width=dp(20)))
            r.bind(on_release=lambda *_, p=p: app().push(AdminProductEdit(p)))
            self.box.add_widget(r)
            _sep(self.box)


def template_samples():
    """По одному товару на каждую фотографию — основа для нового товара."""
    seen, out = set(), []
    for p in ALL_PRODUCTS:
        if p["image"] not in seen and not p.get("custom") and p["cat"] != "gift":
            seen.add(p["image"])
            out.append(p)
    return out


class AdminProductEdit(AdminBase):
    def __init__(self, product=None, **kw):
        super().__init__("Новый товар" if product is None else "Редактирование", **kw)
        self.p = product
        self.base = None
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, dp(6), PAD, dp(30))
        box.spacing = dp(12)
        if product is None:
            box.add_widget(lbl("Основа товара: фото, категория и характеристики", 15, wrap=True))
            ssv, row = hscroll(dp(92))
            row.padding = (0, 0)
            row.spacing = dp(8)
            self.tiles = []
            for s in template_samples():
                t = PressBox(size_hint_x=None, width=dp(84))
                t.col = paint(t, T.GRAY_BG, dp(10))
                t.add_widget(Image(source=photo(s["image"]), fit_mode="contain"))
                t.bind(on_release=lambda w, s=s: self._base(w, s))
                row.add_widget(t)
                self.tiles.append(t)
            box.add_widget(ssv)
            self.base_lbl = lbl("Выберите основу", 13, color=T.MUTED, weight="reg", size_hint_y=None, height=dp(20))
            box.add_widget(self.base_lbl)
        else:
            th = BoxLayout(size_hint_y=None, height=dp(150))
            paint(th, T.GRAY_BG, dp(12))
            th.add_widget(Image(source=photo(product["image"]), fit_mode="contain"))
            box.add_widget(th)
        p = product or {}
        self.f_name = FloatField("Название", p.get("name", ""))
        self.f_brand = FloatField("Бренд", p.get("brand", ""))
        self.f_price = FloatField("Цена, ₽", str(p.get("price", "")))
        self.f_old = FloatField("Старая цена, ₽ (если есть скидка)", str(p.get("old_price") or ""))
        self.f_price.inp.input_filter = self.f_old.inp.input_filter = "int"
        for f in (self.f_name, self.f_brand, self.f_price, self.f_old):
            box.add_widget(f)
        vis = BoxLayout(size_hint_y=None, height=dp(52))
        vis.add_widget(lbl("Показывать покупателям", 16))
        self.vis = Toggle(active=not p.get("hidden"), pos_hint={"center_y": .5})
        self.vis.k = 1 if self.vis.active else 0
        vis.add_widget(self.vis)
        box.add_widget(vis)
        self.err = lbl("", 14, color=T.RED, wrap=True)
        box.add_widget(self.err)
        b = AppButton(text="Сохранить", height=dp(54), radius=dp(8))
        b.bind(on_release=lambda *_: self.save())
        box.add_widget(b)
        self.root_box.add_widget(sv)

    def _base(self, tile, sample):
        self.base = sample
        for t in self.tiles:
            t.col.rgba = T.BLUE_LIGHT if t is tile else T.GRAY_BG
        self.base_lbl.text = f"Основа: {sample['kind']}, цвет {sample['color'].lower()}"
        self.f_brand.inp.text = self.f_brand.inp.text or sample["brand"]

    def save(self):
        name, brand = self.f_name.text, self.f_brand.text
        price = int(self.f_price.text or 0)
        old = int(self.f_old.text or 0) or None
        if self.p is None and self.base is None:
            self.err.text = "Выберите основу товара"
        elif len(name) < 3:
            self.err.text = "Укажите название"
            self.f_name.error()
        elif not brand:
            self.err.text = "Укажите бренд"
            self.f_brand.error()
        elif price <= 0:
            self.err.text = "Цена должна быть больше нуля"
            self.f_price.error()
        elif old is not None and old <= price:
            self.err.text = "Старая цена должна быть больше новой"
            self.f_old.error()
        else:
            fields = dict(name=name, brand=brand, price=price, old_price=old, hidden=not self.vis.active)

            def go():
                saved = db.data["products"]
                if self.p is None:
                    add_product(self.base["id"], fields, saved)
                else:
                    edit_product(self.p["id"], fields, saved)
                db.save()
                store.prune()
                app().back()
                app().toast("Товар сохранён")
            net_call(go, delay=0.5)


# ============================================================================ заказы
def user_name(uid):
    u = db.get_user(uid)
    return u["name"] if u else ("Гость" if uid is None else "Удалённый пользователь")


def order_status(o):
    if o.get("cancelled"):
        return "Отменён", T.RED
    return (STATUSES[o["status"]], T.SUCCESS) if o["status"] >= 1 else ("Ожидает оплаты", T.BLUE)


class AdminOrdersScreen(AdminBase):
    def __init__(self, **kw):
        super().__init__("Заказы", **kw)
        self.sv, self.box = vscroll(bottom=dp(20))
        self.box.padding = (PAD, 0, PAD, dp(20))
        self.box.spacing = 0
        self.root_box.add_widget(self.sv)

    def on_pre_enter(self):
        self.box.clear_widgets()
        if not db.orders:
            self.box.add_widget(lbl("Заказов пока нет", 16, color=T.MUTED, halign="center", size_hint_y=None, height=dp(120)))
        for o in db.orders:
            r = PressBox(orientation="vertical", size_hint_y=None, height=dp(82), padding=(0, dp(10)))
            top = BoxLayout()
            top.add_widget(lbl(f"№ {o['n']}", 16))
            text, color = order_status(o)
            top.add_widget(fit_w(lbl(text, 13, color=color)))
            r.add_widget(top)
            bot = BoxLayout()
            bot.add_widget(lbl(f"{user_name(o.get('uid'))} · {o['created']}", 13, color=T.MUTED, weight="reg", shorten=True))
            bot.add_widget(fit_w(lbl(T.price(o["total"]), 14)))
            r.add_widget(bot)
            r.bind(on_release=lambda *_, o=o: app().push(AdminOrderScreen(o)))
            self.box.add_widget(r)
            _sep(self.box)


class AdminOrderScreen(AdminBase):
    def __init__(self, order, **kw):
        super().__init__(f"Заказ № {order['n']}", **kw)
        self.o = order
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, dp(4), PAD, dp(30))
        box.spacing = dp(8)
        c = order.get("contacts", {})
        for a, b in (("Покупатель", user_name(order.get("uid"))), ("Контакты", " · ".join(x for x in (c.get("name"), c.get("phone")) if x) or "—"),
                     ("Создан", order["created"]), ("Получение", order["place"]), ("Сумма", T.price(order["total"])),
                     ("Оплата", f"карта •••• {order['paid_card']}" if order.get("paid_card") else "не оплачен картой")):
            r = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
            r.add_widget(lbl(a, 14, color=T.MUTED, weight="reg", size_hint_x=0.34))
            r.add_widget(lbl(b, 14, halign="right", max_lines=2))
            box.add_widget(r)
        _sep(box)
        box.add_widget(lbl("Состав", 18, weight="semi", size_hint_y=None, height=dp(38)))
        for pid, size, q in order["items"]:
            p = BY_ID[pid]
            size_text = "" if size == "—" else f"размер {size}, "
            box.add_widget(lbl(f"{p['name']} · {size_text}{q} шт", 14, weight="reg", wrap=True))
        _sep(box)
        box.add_widget(lbl("Статус", 18, weight="semi", size_hint_y=None, height=dp(38)))
        self.state_lbl = lbl("", 15, size_hint_y=None, height=dp(26))
        box.add_widget(self.state_lbl)
        csv, chips = hscroll(dp(48))
        chips.padding = (0, dp(4))
        chips.spacing = dp(8)
        self.chips = []
        for i, name in enumerate(STATUSES):
            c = OutlineChip(name, height=dp(40))
            c.bind(on_release=lambda *_, i=i: self.set_status(i))
            chips.add_widget(c)
            self.chips.append(c)
        box.add_widget(csv)
        self.cancel = AppButton(text="", bg=T.RED_SOFT, fg=T.RED, height=dp(50), radius=dp(8))
        self.cancel.bind(on_release=lambda *_: self.toggle_cancel())
        box.add_widget(self.cancel)
        self.root_box.add_widget(sv)
        self.sync()

    def sync(self):
        text, color = order_status(self.o)
        self.state_lbl.text, self.state_lbl.color = text, color
        for i, c in enumerate(self.chips):
            c.active = i == self.o["status"] and not self.o.get("cancelled")
        self.cancel.text = "Вернуть в работу" if self.o.get("cancelled") else "Отменить заказ"

    def set_status(self, i):
        net_call(lambda: (store.set_order_status(self.o, status=i, cancelled=False), self.sync(),
                          app().toast(f"Статус изменён: {STATUSES[i]}")), delay=0.4)

    def toggle_cancel(self):
        if self.o.get("cancelled"):
            store.set_order_status(self.o, cancelled=False)
            self.sync()
        else:
            confirm("Отменить заказ?", "Покупатель увидит отмену, начисленные за заказ бонусы будут списаны.", "Отменить заказ",
                    lambda: (store.set_order_status(self.o, cancelled=True), self.sync()))


# ============================================================================ пользователи
class AdminUsersScreen(AdminBase):
    def __init__(self, **kw):
        super().__init__("Пользователи", **kw)
        self.q = ""
        head = BoxLayout(size_hint_y=None, height=dp(56), padding=(PAD, 0, PAD, dp(10)))
        head.add_widget(search_field("Имя, почта или телефон", self._search))
        self.root_box.add_widget(head)
        self.sv, self.box = vscroll(bottom=dp(20))
        self.box.padding = (PAD, 0, PAD, dp(20))
        self.box.spacing = 0
        self.root_box.add_widget(self.sv)

    def on_pre_enter(self):
        self.refresh()

    def _search(self, q):
        self.q = q
        self.refresh()

    def refresh(self):
        self.box.clear_widgets()
        for u in db.users:
            if self.q not in f"{u['name']} {u['email']} {u['phone']}".lower():
                continue
            r = PressBox(size_hint_y=None, height=dp(72), spacing=dp(12))
            av = BoxLayout(size_hint=(None, None), size=(dp(44), dp(44)), pos_hint={"center_y": .5})
            paint(av, T.BLUE_LIGHT, dp(22))
            av.add_widget(lbl(u["name"][:1].upper(), 17, weight="bold", color=T.BLUE, halign="center"))
            r.add_widget(av)
            c = BoxLayout(orientation="vertical", padding=(0, dp(14)))
            c.add_widget(lbl(u["name"], 16, shorten=True))
            c.add_widget(lbl(u["email"], 13, color=T.MUTED, weight="reg", shorten=True))
            r.add_widget(c)
            if u["blocked"]:
                r.add_widget(fit_w(lbl("Заблокирован", 12, color=T.RED)))
            elif u["role"] == "admin":
                r.add_widget(fit_w(lbl("Админ", 12, color=T.BLUE)))
            r.bind(on_release=lambda *_, u=u: app().push(AdminUserScreen(u)))
            self.box.add_widget(r)
            _sep(self.box)


class AdminUserScreen(AdminBase):
    def __init__(self, user, **kw):
        super().__init__(user["name"], **kw)
        self.u = user
        self.me = store.user is user
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, dp(4), PAD, dp(30))
        box.spacing = dp(8)
        orders = db.orders_of(user["id"])
        for a, b in (("Почта", user["email"]), ("Телефон", user["phone"]), ("Регистрация", user["created"]),
                     ("Заказов", str(len(orders))),
                     ("Покупок на", T.price(sum(o["total"] for o in orders if o["status"] >= 1 and not o.get("cancelled"))))):
            r = BoxLayout(size_hint_y=None, height=dp(34))
            r.add_widget(lbl(a, 14, color=T.MUTED, weight="reg", size_hint_x=0.4))
            r.add_widget(lbl(b, 14, halign="right", shorten=True))
            box.add_widget(r)
        _sep(box)
        self.err = lbl("", 14, color=T.RED, wrap=True)
        self.t_admin = self._toggle(box, "Администратор", user["role"] == "admin", self.set_admin)
        self.t_block = self._toggle(box, "Заблокирован", user["blocked"], self.set_block)
        box.add_widget(self.err)
        _sep(box)
        row = BoxLayout(size_hint_y=None, height=dp(58), spacing=dp(10))
        bonus = store.bonus if self.me else user["state"]["bonus"]
        self.f_bonus = FloatField("Бонусы", str(int(bonus)))
        self.f_bonus.inp.input_filter = "int"
        row.add_widget(self.f_bonus)
        b = AppButton(text="Сохранить", height=dp(58), radius=dp(8), size_hint_x=None, width=dp(130))
        b.bind(on_release=lambda *_: self.save_bonus())
        row.add_widget(b)
        box.add_widget(row)
        reset = AppButton(text="Выдать новый пароль", bg=T.BLUE_LIGHT, fg=T.BLUE, height=dp(50), radius=dp(8))
        reset.bind(on_release=lambda *_: self.reset_password())
        box.add_widget(reset)
        if not self.me:
            rm = AppButton(text="Удалить пользователя", bg=T.RED_SOFT, fg=T.RED, height=dp(50), radius=dp(8))
            rm.bind(on_release=lambda *_: self.delete())
            box.add_widget(rm)
        self.root_box.add_widget(sv)

    def _toggle(self, box, text, value, on_change):
        r = BoxLayout(size_hint_y=None, height=dp(50))
        r.add_widget(lbl(text, 16))
        t = Toggle(active=value, pos_hint={"center_y": .5})
        t.k = 1 if value else 0
        t.bind(on_release=lambda w: on_change(w))
        r.add_widget(t)
        box.add_widget(r)
        return t

    def _apply(self, toggle, fn):
        """Выполнить действие; при запрете вернуть переключатель и показать причину."""
        self.err.text = ""
        if self.me:
            toggle.active = not toggle.active
            self.err.text = "Нельзя менять роль и блокировку у самого себя"
            return
        try:
            fn()
        except AuthError as e:
            toggle.active = not toggle.active
            self.err.text = str(e)

    def set_admin(self, t):
        self._apply(t, lambda: db.set_role(self.u, "admin" if t.active else "user"))

    def set_block(self, t):
        self._apply(t, lambda: db.set_blocked(self.u, t.active))

    def save_bonus(self):
        value = int(self.f_bonus.text or 0)
        if self.me:
            store.bonus = value
        else:
            self.u["state"]["bonus"] = value
            db.save()
        app().toast("Бонусы сохранены")

    def reset_password(self):
        temp = secrets.token_urlsafe(6)
        db.set_password(self.u, temp)
        ErrorDialog(None, title="Новый пароль", sub=f"Передайте пользователю: {temp}\nБольше он показан не будет").open()

    def delete(self):
        def go():
            try:
                db.delete_user(self.u)
            except AuthError as e:
                self.err.text = str(e)
                return
            app().back()
            app().toast("Пользователь удалён")
        confirm("Удалить пользователя?", f"{self.u['name']} больше не сможет войти. Заказы останутся в истории.", "Удалить", go)


# ============================================================================ сеть
class AdminNetworkScreen(AdminBase):
    def __init__(self, **kw):
        super().__init__("Сеть и ошибки", **kw)
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, dp(4), PAD, dp(30))
        box.spacing = 0
        box.add_widget(lbl("Режим действует до перезапуска приложения и влияет на все экраны с загрузкой: главную, "
                           "сервисы, корзину, выдачу, оформление, вход и оплату.", 14, color=T.MUTED, weight="reg", wrap=True))
        box.add_widget(Widget(size_hint_y=None, height=dp(8)))
        self.checks = {}
        for key, name, sub in MODES:
            r = PressBox(size_hint_y=None, height=dp(70), spacing=dp(12))
            c = BoxLayout(orientation="vertical", padding=(0, dp(12)))
            c.add_widget(lbl(name, 16))
            c.add_widget(lbl(sub, 12, color=T.MUTED, weight="reg", max_lines=2))
            r.add_widget(c)
            cb = SquareCheck(active=net.mode == key, pos_hint={"center_y": .5})
            cb.bind(on_release=lambda *_, k=key: self.select(k))
            r.add_widget(cb)
            r.bind(on_release=lambda *_, k=key: self.select(k))
            self.checks[key] = cb
            box.add_widget(r)
            _sep(box)
        box.add_widget(Widget(size_hint_y=None, height=dp(14)))
        t = AppButton(text="Проверить запрос", height=dp(50), radius=dp(8))
        t.bind(on_release=lambda *_: net_call(lambda: app().toast("Запрос выполнен успешно"), delay=0.6))
        box.add_widget(t)
        self.root_box.add_widget(sv)

    def select(self, key):
        net.mode = key
        for k, cb in self.checks.items():
            cb.active = k == key
        app().toast(f"Режим: {dict((m[0], m[1]) for m in MODES)[key]}")
