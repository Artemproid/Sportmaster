"""Локальная база приложения (JSON-файл на устройстве): пользователи, роли, заказы, правки каталога.

Сервера пока нет, поэтому всё хранится локально. Пароли хранятся только в виде соли и хеша PBKDF2.
"""
import hashlib
import json
import os
import secrets
import time
from datetime import datetime

# демо-учётные записи создаются при первом запуске
DEMO_ADMIN = ("admin@sportly.local", "admin12345")
DEMO_USER = ("user@sportly.local", "user12345")
PBKDF2_ROUNDS = 120_000
MAX_FAILS, LOCK_SECONDS = 5, 30


class AuthError(Exception):
    """Ошибка входа/регистрации с понятным пользователю текстом."""


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return salt, digest.hex()


def phone_digits(phone):
    d = "".join(c for c in (phone or "") if c.isdigit())
    if len(d) == 11 and d[0] == "8":
        d = "7" + d[1:]
    return d


def valid_email(email):
    if email.count("@") != 1 or " " in email:
        return False
    name, domain = email.split("@")
    return bool(name) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def empty_state(bonus=0):
    return {"cart": {}, "selected": [], "favorites": [], "compare": [], "bonus": bonus, "contacts": {}, "addresses": []}


class DB:
    def __init__(self):
        self.path = None
        self.data = None
        self._fails = {}

    # ---------- файл
    def open(self, folder, first_guest_state=None):
        os.makedirs(folder, exist_ok=True)
        self.path = os.path.join(folder, "sportly_db.json")
        self.data = self._read()
        if self.data is None:
            guest = empty_state()
            guest.update(first_guest_state or {})
            self.data = {"users": [], "next_uid": 1, "session": None, "guest": guest, "orders": [],
                         "products": {"overrides": {}, "custom": []}}
            self._seed()
            self.save()
        return self

    def _read(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except (ValueError, OSError):
            # повреждённый файл не должен ломать запуск: сохраняем копию и начинаем заново
            try:
                os.replace(self.path, self.path + ".broken")
            except OSError:
                pass
            return None

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False)
        os.replace(tmp, self.path)   # атомарная замена: файл не повредится при сбое записи

    def _seed(self):
        self._create("Администратор", DEMO_ADMIN[0], "+7 900 000-00-01", DEMO_ADMIN[1], role="admin", bonus=0)
        self._create("Анна Иванова", DEMO_USER[0], "+7 900 000-00-02", DEMO_USER[1], bonus=1250)

    # ---------- пользователи
    @property
    def users(self):
        return self.data["users"]

    def get_user(self, uid):
        return next((u for u in self.users if u["id"] == uid), None)

    def find_user(self, login):
        login = login.strip().lower()
        digits = phone_digits(login)
        for u in self.users:
            if u["email"].lower() == login or (len(digits) == 11 and phone_digits(u["phone"]) == digits):
                return u
        return None

    def _create(self, name, email, phone, password, role="user", bonus=500):
        salt, digest = hash_password(password)
        user = {"id": self.data["next_uid"], "name": name, "email": email.strip().lower(), "phone": phone, "salt": salt,
                "hash": digest, "role": role, "blocked": False, "created": datetime.now().strftime("%d.%m.%Y"),
                "state": empty_state(bonus)}
        user["state"]["contacts"] = {"name": name, "email": user["email"], "phone": phone}
        self.data["next_uid"] += 1
        self.users.append(user)
        return user

    def register(self, name, email, phone, password):
        name, email = name.strip(), email.strip().lower()
        if len(name) < 2:
            raise AuthError("Укажите имя")
        if not valid_email(email):
            raise AuthError("Проверьте адрес почты")
        if len(phone_digits(phone)) != 11:
            raise AuthError("Введите номер телефона полностью")
        if len(password) < 8:
            raise AuthError("Пароль должен быть не короче 8 символов")
        if self.find_user(email):
            raise AuthError("Такая почта уже зарегистрирована")
        if self.find_user(phone):
            raise AuthError("Такой телефон уже зарегистрирован")
        user = self._create(name, email, phone, password)
        self.save()
        return user

    def check_login(self, login, password):
        key = login.strip().lower()
        fails, until = self._fails.get(key, (0, 0))
        left = int(until - time.time())
        if left > 0:
            raise AuthError(f"Слишком много попыток. Повторите через {left} с")
        user = self.find_user(login)
        ok = bool(user) and secrets.compare_digest(hash_password(password, user["salt"])[1], user["hash"])
        if not ok:
            fails += 1
            self._fails[key] = (0, time.time() + LOCK_SECONDS) if fails >= MAX_FAILS else (fails, 0)
            raise AuthError("Неверная почта, телефон или пароль")
        self._fails.pop(key, None)
        if user["blocked"]:
            raise AuthError("Учётная запись заблокирована. Обратитесь в поддержку")
        return user

    def set_password(self, user, password):
        if len(password) < 8:
            raise AuthError("Пароль должен быть не короче 8 символов")
        user["salt"], user["hash"] = hash_password(password)
        self.save()

    def update_profile(self, user, name, email, phone):
        name, email = name.strip(), email.strip().lower()
        if len(name) < 2:
            raise AuthError("Укажите имя")
        if not valid_email(email):
            raise AuthError("Проверьте адрес почты")
        if len(phone_digits(phone)) != 11:
            raise AuthError("Введите номер телефона полностью")
        for other in (self.find_user(email), self.find_user(phone)):
            if other and other is not user:
                raise AuthError("Эта почта или телефон уже заняты")
        user.update(name=name, email=email, phone=phone)
        self.save()

    def admins_count(self):
        return sum(1 for u in self.users if u["role"] == "admin" and not u["blocked"])

    def _guard_last_admin(self, user):
        if user["role"] == "admin" and not user["blocked"] and self.admins_count() <= 1:
            raise AuthError("Нельзя: это последний администратор")

    def set_role(self, user, role):
        if role != "admin":
            self._guard_last_admin(user)
        user["role"] = role
        self.save()

    def set_blocked(self, user, blocked):
        if blocked:
            self._guard_last_admin(user)
        user["blocked"] = blocked
        self.save()

    def delete_user(self, user):
        self._guard_last_admin(user)
        self.users.remove(user)
        self.save()

    # ---------- заказы
    @property
    def orders(self):
        return self.data["orders"]

    def orders_of(self, uid):
        return [o for o in self.orders if o.get("uid") == uid]

    def add_order(self, order):
        self.orders.insert(0, order)
        self.save()


db = DB()
