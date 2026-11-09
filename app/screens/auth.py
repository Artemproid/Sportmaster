"""Вход, регистрация и редактирование профиля."""
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from .. import theme as T
from ..common import lbl, paint, vscroll, TopBar, PAD, FloatField, phone_fmt, net_call
from ..db import db, AuthError, hash_password
from ..store import store
from ..widgets import AppButton, PressBox
from .checkout_flow import TabsLine


class LoginScreen(Screen):
    """Две вкладки: «Вход» и «Регистрация»."""
    hide_nav = True

    def __init__(self, **kw):
        super().__init__(**kw)
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Личный кабинет"))
        root.add_widget(TabsLine(["Вход", "Регистрация"], self._tab))
        self.sv, self.box = vscroll(bottom=dp(30))
        self.box.padding = (PAD, dp(18), PAD, dp(30))
        self.box.spacing = dp(12)
        root.add_widget(self.sv)
        self.add_widget(root)
        self._tab(0)

    def _tab(self, i):
        self.box.clear_widgets()
        self.err = lbl("", 14, color=T.RED, wrap=True)
        self._login_form() if i == 0 else self._register_form()

    def _login_form(self):
        self.f_login = FloatField("Почта или телефон")
        self.f_pass = FloatField("Пароль", password=True)
        self.box.add_widget(self.f_login)
        self.box.add_widget(self.f_pass)
        self.box.add_widget(self.err)
        b = AppButton(text="Войти", height=dp(54), radius=dp(8))
        b.bind(on_release=lambda *_: self.do_login())
        self.box.add_widget(b)
        forgot = PressBox(size_hint_y=None, height=dp(40))
        forgot.add_widget(lbl("Забыли пароль?", 15, color=T.BLUE, halign="center"))
        forgot.bind(on_release=lambda *_: App.get_running_app().toast("Новый пароль может выдать администратор"))
        self.box.add_widget(forgot)

    def _register_form(self):
        self.f_name = FloatField("Имя и фамилия")
        self.f_mail = FloatField("Почта")
        self.f_phone = FloatField("Телефон", fmt=phone_fmt)
        self.f_new = FloatField("Пароль, не короче 8 символов", password=True)
        self.f_again = FloatField("Повторите пароль", password=True)
        for f in (self.f_name, self.f_mail, self.f_phone, self.f_new, self.f_again):
            self.box.add_widget(f)
        self.box.add_widget(self.err)
        b = AppButton(text="Зарегистрироваться", height=dp(54), radius=dp(8))
        b.bind(on_release=lambda *_: self.do_register())
        self.box.add_widget(b)

    def _enter(self, user, text):
        store.login(user)
        app = App.get_running_app()
        app.back()
        Clock.schedule_once(lambda *_: app.toast(text), 0.3)

    def do_login(self):
        self.err.text = ""
        login, password = self.f_login.text, self.f_pass.inp.text
        if not login or not password:
            self.err.text = "Введите почту или телефон и пароль"
            return

        def go():
            try:
                user = db.check_login(login, password)
            except AuthError as e:
                self.err.text = str(e)
                self.f_pass.error()
                return
            self._enter(user, f"Здравствуйте, {user['name'].split()[0]}!")
        net_call(go, delay=0.5)

    def do_register(self):
        self.err.text = ""
        if self.f_new.inp.text != self.f_again.inp.text:
            self.err.text = "Пароли не совпадают"
            self.f_again.error()
            return

        def go():
            try:
                user = db.register(self.f_name.text, self.f_mail.text, self.f_phone.text, self.f_new.inp.text)
            except AuthError as e:
                self.err.text = str(e)
                return
            self._enter(user, "Вы зарегистрированы! Начислили 500 бонусов")
        net_call(go, delay=0.7)


class ProfileEditScreen(Screen):
    """Данные профиля и смена пароля."""
    hide_nav = True

    def __init__(self, **kw):
        super().__init__(**kw)
        u = store.user
        root = BoxLayout(orientation="vertical")
        paint(root, T.BG)
        root.add_widget(TopBar("Мои данные"))
        sv, box = vscroll(bottom=dp(30))
        box.padding = (PAD, dp(10), PAD, dp(30))
        box.spacing = dp(12)
        self.f_name = FloatField("Имя и фамилия", u["name"])
        self.f_mail = FloatField("Почта", u["email"])
        self.f_phone = FloatField("Телефон", u["phone"], fmt=phone_fmt)
        for f in (self.f_name, self.f_mail, self.f_phone):
            box.add_widget(f)
        self.err = lbl("", 14, color=T.RED, wrap=True)
        box.add_widget(self.err)
        b = AppButton(text="Сохранить", height=dp(54), radius=dp(8))
        b.bind(on_release=lambda *_: self.save())
        box.add_widget(b)
        box.add_widget(Widget(size_hint_y=None, height=dp(12)))
        box.add_widget(lbl("Смена пароля", 19, weight="semi", size_hint_y=None, height=dp(34)))
        self.f_old = FloatField("Текущий пароль", password=True)
        self.f_new = FloatField("Новый пароль, не короче 8 символов", password=True)
        box.add_widget(self.f_old)
        box.add_widget(self.f_new)
        self.err2 = lbl("", 14, color=T.RED, wrap=True)
        box.add_widget(self.err2)
        b2 = AppButton(text="Изменить пароль", bg=T.BLUE_LIGHT, fg=T.BLUE, height=dp(54), radius=dp(8))
        b2.bind(on_release=lambda *_: self.change_password())
        box.add_widget(b2)
        root.add_widget(sv)
        self.add_widget(root)

    def save(self):
        self.err.text = ""

        def go():
            u = store.user
            try:
                db.update_profile(u, self.f_name.text, self.f_mail.text, self.f_phone.text)
            except AuthError as e:
                self.err.text = str(e)
                return
            store.contacts = {"name": u["name"], "email": u["email"], "phone": u["phone"]}
            app = App.get_running_app()
            app.back()
            Clock.schedule_once(lambda *_: app.toast("Данные сохранены"), 0.3)
        net_call(go, delay=0.5)

    def change_password(self):
        self.err2.text = ""
        u = store.user
        if hash_password(self.f_old.inp.text, u["salt"])[1] != u["hash"]:
            self.err2.text = "Текущий пароль указан неверно"
            self.f_old.error()
            return

        def go():
            try:
                db.set_password(u, self.f_new.inp.text)
            except AuthError as e:
                self.err2.text = str(e)
                return
            self.f_old.inp.text = self.f_new.inp.text = ""
            App.get_running_app().toast("Пароль изменён")
        net_call(go, delay=0.5)
