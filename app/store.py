"""Состояние приложения текущего пользователя (или гостя): корзина, избранное, заказы, бонусы.

Всё автоматически сохраняется в локальную базу, поэтому не пропадает после перезапуска.
"""
import random
from datetime import datetime, timedelta

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, ListProperty, DictProperty, ObjectProperty
from .catalog_db import apply_saved
from .data import BY_ID, START_CART
from .db import db

STATUSES = ["Создан", "Оплачен", "Собран", "Получен"]


class Store(EventDispatcher):
    cart = DictProperty({})          # "pid|size" -> qty
    favorites = ListProperty([])
    compare = ListProperty([])
    cart_count = NumericProperty(0)
    bonus = NumericProperty(0)
    orders = ListProperty([])
    contacts = DictProperty({})      # name, phone, email
    user = ObjectProperty(None, allownone=True)   # None — гость

    def __init__(self, **kw):
        super().__init__(**kw)
        self.selected = set()
        self.addresses = []
        self._loading = False
        self._save_trig = Clock.create_trigger(lambda *_: self.save(), 0.2)
        self.bind(cart=self._changed, favorites=self._changed, compare=self._changed, bonus=self._changed,
                  contacts=self._changed)

    def _changed(self, *_):
        if not self._loading:
            self._save_trig()

    # ---------- загрузка и сохранение
    def start(self, folder):
        """Открыть базу и восстановить сессию."""
        db.open(folder, {"cart": dict(START_CART), "selected": list(START_CART)})
        apply_saved(db.data["products"])
        user = db.get_user(db.data["session"])
        if user is not None and user["blocked"]:
            user = None
        self._activate(user)

    def _state_ref(self):
        return self.user["state"] if self.user else db.data["guest"]

    def _activate(self, user):
        self._loading = True
        self.user = user
        db.data["session"] = user["id"] if user else None
        st = self._state_ref()
        self.cart = {k: v for k, v in st["cart"].items() if self._valid(k)}
        self.selected = {k for k in st["selected"] if k in self.cart}
        self.favorites = [i for i in st["favorites"] if i in BY_ID]
        self.compare = [i for i in st["compare"] if i in BY_ID]
        self.bonus = st["bonus"]
        self.contacts = dict(st["contacts"])
        self.addresses = st["addresses"]
        self.refresh_orders()
        self._recount()
        self._loading = False
        db.save()

    @staticmethod
    def _valid(k):
        p = BY_ID.get(int(k.split("|")[0]))
        return p is not None and not p.get("hidden")

    def save(self):
        if db.data is None:
            return
        self._state_ref().update(cart=dict(self.cart), selected=sorted(self.selected), favorites=list(self.favorites),
                                 compare=list(self.compare), bonus=self.bonus, contacts=dict(self.contacts),
                                 addresses=self.addresses)
        db.save()

    def refresh_orders(self):
        self.orders = db.orders_of(self.user["id"] if self.user else None)

    # ---------- вход и выход
    @property
    def is_admin(self):
        return bool(self.user) and self.user["role"] == "admin"

    def login(self, user):
        """Войти: корзина и избранное гостя переносятся в учётную запись."""
        self.save()
        guest = db.data["guest"]
        st = user["state"]
        for k, v in guest["cart"].items():
            st["cart"][k] = min(10, st["cart"].get(k, 0) + v)
        st["selected"] = sorted(set(st["selected"]) | set(guest["selected"]))
        st["favorites"] = list(dict.fromkeys(list(st["favorites"]) + list(guest["favorites"])))
        st["compare"] = list(dict.fromkeys(list(st["compare"]) + list(guest["compare"])))
        for o in db.orders_of(None):      # заказы, оформленные гостем на этом устройстве
            o["uid"] = user["id"]
        guest.update(cart={}, selected=[], favorites=[], compare=[])
        self._activate(user)

    def logout(self):
        self.save()
        self._activate(None)

    def _recount(self):
        self.cart_count = sum(self.cart.values())

    @staticmethod
    def key(pid, size):
        return f"{pid}|{size}"

    def add(self, pid, size):
        k = self.key(pid, size)
        c = dict(self.cart)
        c[k] = min(c.get(k, 0) + 1, 10)
        self.selected.add(k)
        self.cart = c
        self._recount()

    def set_qty(self, k, qty):
        c = dict(self.cart)
        if qty <= 0:
            c.pop(k, None)
            self.selected.discard(k)
        else:
            c[k] = min(qty, 10)
        self.cart = c
        self._recount()

    def prune(self):
        """Убрать из корзины товары, которые администратор скрыл."""
        self.set_cart({k: v for k, v in self.cart.items() if self._valid(k)})

    def set_cart(self, c):
        self.cart = c
        self.selected &= set(c)
        self._recount()

    def in_cart(self, pid):
        return any(k.split("|")[0] == str(pid) for k in self.cart)

    def items(self):
        out = []
        for k, q in self.cart.items():
            pid, size = k.split("|")
            out.append((k, BY_ID[int(pid)], size, q))
        return out

    def selected_items(self):
        return [it for it in self.items() if it[0] in self.selected]

    def totals(self, items=None):
        items = self.selected_items() if items is None else items
        full = sum((p["old_price"] or p["price"]) * q for _, p, _, q in items)
        total = sum(p["price"] * q for _, p, _, q in items)
        return full, full - total, total, int(total * 0.05)

    # ---------- заказы
    def create_order(self, method, place):
        """Создаёт заказ из отмеченных товаров (статус «Создан», ждёт оплаты)."""
        items = self.selected_items()
        full, disc, total, earn = self.totals(items)
        delivery = 0 if method == "pickup" or total >= 3000 else 299
        now = datetime.now()
        order = {
            "n": f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            "uid": self.user["id"] if self.user else None,
            "created": now.strftime("%d.%m.%Y, %H:%M"),
            "ready": (now + timedelta(days=1)).strftime("%d.%m"),
            "items": [[p["id"], size, q] for _, p, size, q in items],
            "full": full, "disc": disc, "delivery": delivery, "total": total + delivery, "earn": earn,
            "method": method, "place": place, "contacts": dict(self.contacts),
            "status": 0, "paid_card": None, "cancelled": False,
        }
        db.add_order(order)
        self.set_cart({k: v for k, v in self.cart.items() if k not in self.selected})
        self.selected = set(self.cart)
        self.refresh_orders()
        return order

    def _add_bonus(self, order, amount):
        """Изменить бонусы владельца заказа (он может быть не текущим пользователем — действие из админки)."""
        cur = self.user["id"] if self.user else None
        if order.get("uid") == cur:
            self.bonus = max(0, self.bonus + amount)
        else:
            owner = db.get_user(order.get("uid"))
            if owner:
                owner["state"]["bonus"] = max(0, owner["state"]["bonus"] + amount)

    def pay(self, order, card_last4):
        order["status"] = max(1, order["status"])
        order["paid_card"] = card_last4
        order["bonus_given"] = True
        self._add_bonus(order, order["earn"])
        db.save()
        self.refresh_orders()

    def set_order_status(self, order, status=None, cancelled=None):
        """Смена статуса администратором. Бонусы начисляются один раз и снимаются при отмене."""
        if cancelled is not None:
            order["cancelled"] = cancelled
        if status is not None:
            order["status"] = status
        should_have = order["status"] >= 1 and not order["cancelled"]
        if should_have != bool(order.get("bonus_given")):
            self._add_bonus(order, order["earn"] if should_have else -order["earn"])
            order["bonus_given"] = should_have
        db.save()
        self.refresh_orders()

    # ---------- списки
    def toggle_fav(self, pid):
        f = list(self.favorites)
        f.remove(pid) if pid in f else f.insert(0, pid)
        self.favorites = f
        return pid in f

    def toggle_compare(self, pid):
        f = list(self.compare)
        f.remove(pid) if pid in f else f.insert(0, pid)
        self.compare = f
        return pid in f


store = Store()
