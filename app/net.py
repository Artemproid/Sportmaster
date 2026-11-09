"""Сетевой слой: проверка интернета и ошибки сети.

Сервера пока нет, но все «запросы» экранов идут через Net.request, поэтому позже его можно заменить
настоящим API. В режиме "auto" проверяется реальное соединение. Остальные режимы включаются в админ-панели
для демонстрации ошибок и не сохраняются между запусками.
"""
import socket
import threading

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, StringProperty

MODES = [("auto", "Реальная сеть", "Проверяется настоящее подключение устройства"),
         ("offline", "Нет сети", "Как будто интернет отключён"),
         ("timeout", "Таймаут", "Сервер не отвечает, запрос обрывается через 4 секунды"),
         ("server", "Ошибка сервера", "Сервер возвращает ошибку 500"),
         ("slow", "Медленная сеть", "Каждый запрос выполняется на 3 секунды дольше")]

ERRORS = {
    "offline": ("wifi-off", "Нет подключения к интернету", "Проверьте Wi-Fi или мобильную сеть и попробуйте снова"),
    "timeout": ("clock-exclamation", "Сервер не отвечает", "Запрос выполнялся слишком долго. Попробуйте ещё раз"),
    "server": ("server-off", "Что-то пошло не так", "На сервере произошла ошибка (код 500). Мы уже разбираемся"),
}

# проверяем несколько адресов, чтобы блокировка одного не выглядела как отсутствие сети
PROBES = [("1.1.1.1", 443), ("8.8.8.8", 53), ("77.88.8.8", 53), ("connectivitycheck.gstatic.com", 80)]
PROBE_TIMEOUT = 2.5
MONITOR_INTERVAL = 5


def has_internet(timeout=PROBE_TIMEOUT):
    """True, если отвечает хотя бы один адрес. Вызывать не из главного потока."""
    done = threading.Event()
    found = []
    left = [len(PROBES)]
    lock = threading.Lock()

    def attempt(addr):
        try:
            socket.create_connection(addr, timeout=timeout).close()
            found.append(addr)
            done.set()
        except OSError:
            pass
        finally:
            with lock:
                left[0] -= 1
                if left[0] == 0:
                    done.set()
    for addr in PROBES:
        threading.Thread(target=attempt, args=(addr,), daemon=True).start()
    done.wait(timeout + 0.5)
    return bool(found)


class Net(EventDispatcher):
    mode = StringProperty("auto")
    online = BooleanProperty(True)

    def start(self):
        self._tick()
        Clock.schedule_interval(self._tick, MONITOR_INTERVAL)

    def on_mode(self, *_):
        self._tick()

    def _tick(self, *_):
        if self.mode != "auto":
            self.online = self.mode != "offline"
            return
        self.probe(lambda ok: setattr(self, "online", ok) if self.mode == "auto" else None)

    def probe(self, cb):
        def work():
            ok = has_internet()
            Clock.schedule_once(lambda *_: cb(ok), 0)
        threading.Thread(target=work, daemon=True).start()

    def request(self, on_ok, on_fail=None, delay=0.8):
        """Имитация запроса к серверу: on_ok() при успехе, on_fail(вид_ошибки) при ошибке."""
        on_fail = on_fail or (lambda kind: None)
        mode = self.mode
        if mode == "offline":
            Clock.schedule_once(lambda *_: on_fail("offline"), min(delay, 0.5))
        elif mode == "timeout":
            Clock.schedule_once(lambda *_: on_fail("timeout"), 4)
        elif mode == "server":
            Clock.schedule_once(lambda *_: on_fail("server"), delay)
        elif mode == "slow":
            Clock.schedule_once(lambda *_: on_ok(), delay + 3)
        else:
            def checked(ok):
                self.online = ok
                if ok:
                    Clock.schedule_once(lambda *_: on_ok(), delay)
                else:
                    on_fail("offline")
            self.probe(checked)


net = Net()
