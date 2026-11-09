"""Проверка пользователей, админ-панели и сетевых ошибок. Работает на временной базе.

Запуск: .venv/bin/python tools/test_accounts.py [папка_для_скриншотов]
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
OUT = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
os.makedirs(OUT, exist_ok=True)
DATA = tempfile.mkdtemp()
os.environ["SPORTLY_DATA_DIR"] = DATA

import main  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from app.catalog_db import BY_ID, PRODUCTS, ALL_PRODUCTS, search  # noqa: E402
from app.common import ErrorView, ErrorDialog  # noqa: E402
from app.db import db, DB, AuthError, DEMO_ADMIN, DEMO_USER  # noqa: E402
from app.net import net  # noqa: E402
from app.screens import admin as A  # noqa: E402
from app.screens.auth import LoginScreen  # noqa: E402
from app.store import store  # noqa: E402

app = main.SportlyApp()
steps, T0, errors = [], [0.0], []


def at(dt, fn):
    steps.append((dt, fn))


def shot(name):
    return lambda: Window.screenshot(os.path.join(OUT, name + ".png"))


def check(name, cond):
    print(("OK   " if cond else "FAIL ") + name)
    if not cond:
        errors.append(name)


def raises(fn):
    try:
        fn()
    except AuthError:
        return True
    return False


cur = lambda: app.sm.current_screen  # noqa: E731


def has(widget_cls, root=None):
    return any(isinstance(w, widget_cls) for w in (root or app.root_layout).walk())


def login_via_screen(login, password):
    s = cur()
    s.f_login.inp.text, s.f_pass.inp.text = login, password
    s.do_login()


def logic_checks():
    check("Гость при запуске, в корзине 2 товара", store.user is None and store.cart_count == 2)
    check("В базе нет паролей в открытом виде", DEMO_ADMIN[1] not in open(db.path, encoding="utf-8").read())
    check("Регистрация: короткий пароль отклонён", raises(lambda: db.register("Иван", "i@a.ru", "+7 911 111-11-11", "123")))
    check("Регистрация: занятая почта отклонена", raises(lambda: db.register("Иван", DEMO_USER[0], "+7 911 111-11-11", "password1")))
    check("Регистрация: плохая почта отклонена", raises(lambda: db.register("Иван", "почта", "+7 911 111-11-11", "password1")))
    u = db.register("Пётр Новый", "new@sportly.local", "+7 911 111-11-11", "password1")
    check("Вход по телефону", db.check_login("8 911 111 11 11", "password1") is u)
    check("Неверный пароль отклонён", raises(lambda: db.check_login("new@sportly.local", "wrong")))
    for _ in range(4):
        raises(lambda: db.check_login("new@sportly.local", "wrong"))
    try:
        db.check_login("new@sportly.local", "password1")
        check("Блокировка после 5 ошибок", False)
    except AuthError as e:
        check("Блокировка после 5 ошибок", "попыток" in str(e))
    db._fails.clear()
    db.set_blocked(u, True)
    check("Заблокированный не входит", raises(lambda: db.check_login("new@sportly.local", "password1")))
    db.set_blocked(u, False)
    adm = db.find_user(DEMO_ADMIN[0])
    check("Последнего админа нельзя заблокировать", raises(lambda: db.set_blocked(adm, True)))
    check("Последнего админа нельзя разжаловать", raises(lambda: db.set_role(adm, "user")))
    check("Последнего админа нельзя удалить", raises(lambda: db.delete_user(adm)))


# --- гость и вход
at(3.5, logic_checks)
at(0.2, lambda: app.go_tab("profile"))
at(0.7, lambda: check("Гость видит кнопку входа", app.tabs["profile"].login_wrap.parent is not None))
at(0.0, shot("01_guest_profile"))
at(0.2, lambda: app.tabs["profile"].open_login())
at(0.6, lambda: login_via_screen(DEMO_USER[0], "неверный"))
at(1.2, lambda: check("Экран входа показывает ошибку", "Неверная" in cur().err.text))
at(0.0, shot("02_login_error"))
at(0.2, lambda: cur().tabs if False else None)
at(0.1, lambda: login_via_screen(DEMO_ADMIN[0], DEMO_ADMIN[1]))
at(1.6, lambda: check("Вход админа, корзина гостя перенесена", store.is_admin and store.cart_count == 2))
at(0.0, lambda: check("Сессия сохранена", json.load(open(db.path))["session"] == store.user["id"]))
at(0.5, shot("03_admin_profile"))
at(0.1, lambda: check("У админа есть пункт админ-панели", any("Админ-панель" in getattr(w, "text", "") for w in app.tabs["profile"].menu.walk())))
# --- админка: товар
at(0.1, lambda: app.push(A.AdminScreen()))
at(0.6, shot("04_admin"))
at(0.1, lambda: app.push(A.AdminProductsScreen()))
at(0.8, shot("05_admin_products"))
at(0.1, lambda: app.push(A.AdminProductEdit(BY_ID[1])))
at(0.6, lambda: (setattr(cur().f_price.inp, "text", "1"), setattr(cur().f_old.inp, "text", "1"), cur().save()))
at(0.2, lambda: check("Товар: старая цена не меньше новой", "Старая" in cur().err.text))
at(0.1, lambda: (setattr(cur().f_price.inp, "text", "1234"), setattr(cur().f_old.inp, "text", ""),
                 setattr(cur().f_name.inp, "text", "Кроссовки тестовые Зебра"), cur().save()))
at(1.2, lambda: check("Цена и название изменились", BY_ID[1]["price"] == 1234 and BY_ID[1]["name"].endswith("Зебра")))
at(0.0, lambda: check("Поиск находит новое название", any(p["id"] == 1 for p in search("зебра"))))
at(0.0, lambda: check("Без старой цены нет в разделе скидок", "sale" not in BY_ID[1]["sections"]))
at(0.1, lambda: app.push(A.AdminProductEdit(BY_ID[2])))
at(0.6, lambda: (setattr(cur().vis, "active", False), cur().save()))
at(1.2, lambda: check("Скрытого товара нет на витрине и в поиске", BY_ID[2] not in PRODUCTS and BY_ID[2] in ALL_PRODUCTS))
at(0.1, lambda: app.push(A.AdminProductEdit()))
at(0.7, shot("06_admin_new_product"))


def new_product():
    s = cur()
    s._base(s.tiles[0], A.template_samples()[0])
    s.f_name.inp.text, s.f_price.inp.text = "Новинка Единорог", "777"
    s.save()


at(0.1, new_product)
at(1.2, lambda: check("Новый товар появился в поиске", any(p["price"] == 777 for p in search("единорог"))))
at(0.1, lambda: app.back())
at(0.5, lambda: app.back())
# --- админка: пользователи
at(0.5, lambda: app.push(A.AdminUsersScreen()))
at(0.7, shot("07_admin_users"))
at(0.1, lambda: app.push(A.AdminUserScreen(store.user)))


def block_self():
    s = cur()
    s.t_block.active = True
    s.set_block(s.t_block)


at(0.6, block_self)
at(0.2, lambda: check("Себя заблокировать нельзя", store.user["blocked"] is False and cur().t_block.active is False))
at(0.2, lambda: app.back())
at(0.5, lambda: app.push(A.AdminUserScreen(db.find_user(DEMO_USER[0]))))
at(0.7, shot("08_admin_user"))
at(0.1, lambda: cur().reset_password())
at(0.4, shot("09_new_password"))
at(0.0, lambda: check("Новый пароль заменил старый", raises(lambda: db.check_login(DEMO_USER[0], DEMO_USER[1]))))
at(0.0, lambda: db._fails.clear())
at(0.1, lambda: [w.dismiss() for w in list(app.root_layout.children) if isinstance(w, ErrorDialog)])
at(0.1, lambda: app.back())
at(0.5, lambda: app.back())
# --- заказ и бонусы
order = {}


def make_order():
    store.selected = set(store.cart)
    before = store.bonus
    o = store.create_order("pickup", "тест")
    order.update(o=o, before=before)
    store.pay(o, "4242")
    check("Оплата начисляет бонусы", store.bonus == before + o["earn"])


at(0.5, make_order)
at(0.1, lambda: app.push(A.AdminOrdersScreen()))
at(0.7, shot("10_admin_orders"))
at(0.1, lambda: app.push(A.AdminOrderScreen(order["o"])))
at(0.6, shot("11_admin_order"))
at(0.1, lambda: cur().set_status(2))
at(1.0, lambda: check("Статус «Собран», бонусы не задвоились", order["o"]["status"] == 2 and store.bonus == order["before"] + order["o"]["earn"]))
at(0.1, lambda: store.set_order_status(order["o"], cancelled=True))
at(0.1, lambda: check("Отмена списала бонусы", store.bonus == order["before"]))
at(0.1, lambda: app.back())
at(0.5, lambda: app.back())
at(0.5, lambda: app.back())
# --- сеть
at(0.5, lambda: setattr(net, "mode", "offline"))
at(0.4, lambda: check("Полоса «нет интернета» появилась", not net.online))
at(0.4, shot("12_banner_offline"))
at(0.1, lambda: app.open_results("мяч"))
at(1.6, lambda: check("Выдача: экран ошибки без сети", has(ErrorView, cur())))
at(0.1, shot("13_results_offline"))
at(0.1, lambda: setattr(net, "mode", "server"))
at(0.1, lambda: [w.children[1].dispatch("on_release") for w in cur().walk() if isinstance(w, ErrorView)])
at(1.6, lambda: check("Выдача: ошибка сервера после «Повторить»", any(isinstance(w, ErrorView) and w.kind == "server" for w in cur().walk())))
at(0.1, shot("14_results_server"))
at(0.1, lambda: setattr(net, "mode", "auto"))
at(0.1, lambda: [w.children[1].dispatch("on_release") for w in cur().walk() if isinstance(w, ErrorView)])
at(2.8, lambda: check("После «Повторить» товары загрузились", hasattr(cur(), "grid_box") and not has(ErrorView, cur())))
at(0.1, shot("15_results_ok"))
at(0.1, lambda: app.go_tab("profile"))
at(0.6, lambda: setattr(net, "mode", "timeout"))
at(0.1, lambda: app.tabs["profile"].logout())
at(0.5, lambda: app.tabs["profile"].open_login())
at(0.6, lambda: login_via_screen(DEMO_ADMIN[0], DEMO_ADMIN[1]))
at(4.6, lambda: check("Вход при таймауте: окно с ошибкой", has(ErrorDialog) and store.user is None))
at(0.1, shot("16_login_timeout"))
at(0.1, lambda: setattr(net, "mode", "auto"))
at(0.1, lambda: [w.dismiss() for w in list(app.root_layout.children) if isinstance(w, ErrorDialog)])
# --- данные сохраняются
at(0.3, lambda: check("База читается заново, правки на месте",
                      DB().open(DATA).data["products"]["overrides"]["1"]["price"] == 1234))
at(0.5, lambda: (print("ИТОГО ошибок:", len(errors)), app.stop()))



def run(i):
    """Шаги идут строго по очереди: следующий ждёт паузу и конец анимации перехода."""
    if i >= len(steps):
        return

    def go(_dt):
        if app.sm.transition.is_active:
            return Clock.schedule_once(go, 0.05)
        steps[i][1]()
        run(i + 1)
    Clock.schedule_once(go, steps[i][0])


run(0)
app.run()
