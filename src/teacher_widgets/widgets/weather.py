"""날씨 위젯: Open-Meteo forecast + air-quality (키 불필요)."""

from __future__ import annotations

import datetime
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.data_remote import http_get_json, read_cache, write_cache
from teacher_widgets.core.responsive import resolve_breakpoint, scale_factor, scaled_font_pt

WEATHER_TIERS = [(0, "now"), (300, "two_days")]

_WMO = [
    ((0, 0), "맑음 ☀️"),
    ((1, 2), "구름 조금 🌤️"),
    ((3, 3), "흐림 ☁️"),
    ((45, 48), "안개 🌫️"),
    ((51, 57), "이슬비 🌦️"),
    ((61, 67), "비 🌧️"),
    ((71, 77), "눈 🌨️"),
    ((80, 82), "소나기 🌧️"),
    ((85, 86), "소낙눈 🌨️"),
    ((95, 99), "뇌우 ⛈️"),
]


def build_forecast_url(lat: float, lon: float) -> str:
    return ("https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,weather_code"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max"
            "&timezone=Asia%2FSeoul&forecast_days=2")


def build_air_url(lat: float, lon: float) -> str:
    return ("https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}"
            "&current=pm10,pm2_5&timezone=Asia%2FSeoul")


def wmo_to_text(code: int) -> str:
    for (lo, hi), text in _WMO:
        if lo <= code <= hi:
            return text
    return "-"


def _grade(value, bounds: tuple[int, int, int]) -> str:
    if value is None:
        return "-"
    good, normal, bad = bounds
    if value <= good:
        return "좋음"
    if value <= normal:
        return "보통"
    if value <= bad:
        return "나쁨"
    return "매우나쁨"


def pm10_grade(value) -> str:
    return _grade(value, (30, 80, 150))


def pm25_grade(value) -> str:
    return _grade(value, (15, 35, 75))


def _daily(forecast: dict, key: str, idx: int):
    values = forecast.get("daily", {}).get(key, [])
    return values[idx] if len(values) > idx else None


def parse_weather(forecast: dict, air: dict) -> dict:
    current = forecast.get("current", {})
    air_now = air.get("current", {})
    return {
        "temp": current.get("temperature_2m"),
        "code": current.get("weather_code"),
        "today_max": _daily(forecast, "temperature_2m_max", 0),
        "today_min": _daily(forecast, "temperature_2m_min", 0),
        "tomorrow_max": _daily(forecast, "temperature_2m_max", 1),
        "tomorrow_min": _daily(forecast, "temperature_2m_min", 1),
        "tomorrow_rain": _daily(forecast, "precipitation_probability_max", 1),
        "pm10": air_now.get("pm10"),
        "pm25": air_now.get("pm2_5"),
    }


class WeatherFetchWorker(QtCore.QThread):
    finished_ok = QtCore.Signal(dict)
    failed = QtCore.Signal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)

    def run(self) -> None:
        lat = self._settings.get("lat", 37.617)
        lon = self._settings.get("lon", 126.921)
        forecast, air = {}, {}
        errors = []
        try:
            forecast = http_get_json(build_forecast_url(lat, lon))
        except Exception as exc:
            errors.append(f"forecast: {exc}")
        try:
            air = http_get_json(build_air_url(lat, lon))
        except Exception as exc:
            errors.append(f"air: {exc}")
        if not forecast and not air:
            self.failed.emit("; ".join(errors))
            return
        self.finished_ok.emit({
            "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "weather": parse_weather(forecast, air),
        })


class WeatherWidget(BaseWidget):
    BASE_SIZE = (220, 240)

    def __init__(self, store: ConfigStore):
        super().__init__("weather", store)
        self.cache_path = Path(store.path).parent / "cache" / "weather.json"
        self._data: dict | None = None
        self._worker: WeatherFetchWorker | None = None
        self._tier = ""

        self.header_label = QtWidgets.QLabel("🌈 날씨", alignment=QtCore.Qt.AlignCenter)
        self.header_label.setStyleSheet("font-weight:700; color:#2b2b2b;")
        self.status_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#999;")
        self.content_layout.addWidget(self.header_label)
        self.content_layout.addWidget(self.status_label)

        body = QtWidgets.QWidget()
        self.body_layout = QtWidgets.QVBoxLayout(body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(2)
        self.content_layout.addWidget(body, stretch=1)

        cached = read_cache(self.cache_path)
        if cached is not None:
            self._data = cached
            self.status_label.setText(f"갱신: {cached.get('fetched_at', '')[:16]}")
        else:
            self.status_label.setText("데이터 없음 — 우클릭 → 새로고침")
        self.render_weather()

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown_worker)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        minutes = int(self.store.data["weather"].get("refresh_minutes", 30))
        self._refresh_timer.start(minutes * 60 * 1000)
        if not self.store.data["weather"].get("_skip_initial_fetch", False):
            self.refresh()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._refresh_timer.stop()

    def _shutdown_worker(self) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait(2000)

    def refresh(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._worker = WeatherFetchWorker(self.store.data["weather"], self)
        self._worker.finished_ok.connect(self._on_fetch_ok)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_ok(self, data: dict) -> None:
        self._data = data
        write_cache(self.cache_path, data)
        self.status_label.setText(f"갱신: {data.get('fetched_at', '')[:16]}")
        self.render_weather()

    def _on_fetch_failed(self, msg: str) -> None:
        self.status_label.setText("갱신 실패 — 캐시 표시 중")
        self.setToolTip(msg)

    # --- 렌더 ---
    def current_tier(self) -> str:
        return resolve_breakpoint(self.height(), WEATHER_TIERS)

    def body_text(self) -> str:
        parts = []
        for i in range(self.body_layout.count()):
            wdg = self.body_layout.itemAt(i).widget()
            if isinstance(wdg, QtWidgets.QLabel):
                parts.append(wdg.text())
        return "\n".join(parts)

    def render_weather(self) -> None:
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tier = self.current_tier()
        wx = (self._data or {}).get("weather", {})

        temp = wx.get("temp")
        code = wx.get("code")
        big = QtWidgets.QLabel(
            (f"{temp}°C" if temp is not None else "-")
            + ("  " + wmo_to_text(int(code)) if code is not None else "")
        )
        big.setAlignment(QtCore.Qt.AlignCenter)
        big.setStyleSheet("font-size:20pt; font-weight:700; color:#2b2b2b;")
        self.body_layout.addWidget(big)

        tmax, tmin = wx.get("today_max"), wx.get("today_min")
        hilo = QtWidgets.QLabel(
            f"오늘 {tmax if tmax is not None else '-'}° / {tmin if tmin is not None else '-'}°"
        )
        hilo.setAlignment(QtCore.Qt.AlignCenter)
        hilo.setStyleSheet("color:#666;")
        self.body_layout.addWidget(hilo)

        pm = QtWidgets.QLabel(
            f"미세 {pm10_grade(wx.get('pm10'))} · 초미세 {pm25_grade(wx.get('pm25'))}"
        )
        pm.setAlignment(QtCore.Qt.AlignCenter)
        pm.setStyleSheet("color:#2b6e4f;")
        self.body_layout.addWidget(pm)

        if self._tier == "two_days":
            rain = wx.get("tomorrow_rain")
            tomorrow = QtWidgets.QLabel(
                f"내일 {wx.get('tomorrow_max', '-')}° / {wx.get('tomorrow_min', '-')}°"
                + (f" · 강수 {rain}%" if rain is not None else "")
            )
            tomorrow.setAlignment(QtCore.Qt.AlignCenter)
            tomorrow.setStyleSheet("color:#666;")
            self.body_layout.addWidget(tomorrow)
        self._apply_responsive()

    def _custom_menu_actions(self, menu) -> dict:
        refresh_action = menu.addAction("새로고침")
        return {refresh_action: self.refresh}

    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.header_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(11, factor)}pt;"
        )
        self.status_label.setStyleSheet(
            f"color:#999; font-size:{scaled_font_pt(8, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        new_tier = self.current_tier()
        if new_tier != self._tier:
            self.render_weather()
        else:
            self._apply_responsive()
