"""급식 위젯: 나이스 개방 API(mealServiceDietInfo)."""

from __future__ import annotations

import datetime
import re
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.data_remote import http_get_json, read_cache, write_cache
from teacher_widgets.core.responsive import resolve_breakpoint, scale_factor, scaled_font_pt

MEAL_TIERS = [(0, "today"), (420, "week")]

_ALLERGY_RE = re.compile(r"\s*\(([\d\.]+)\)\s*$")


def build_meal_url(edu_code: str, school_code: str, from_ymd: str,
                   to_ymd: str, api_key: str = "") -> str:
    url = ("https://open.neis.go.kr/hub/mealServiceDietInfo?Type=json"
           f"&ATPT_OFCDC_SC_CODE={edu_code}&SD_SCHUL_CODE={school_code}"
           f"&MLSV_FROM_YMD={from_ymd}&MLSV_TO_YMD={to_ymd}")
    if api_key:
        url += f"&KEY={api_key}"
    return url


def split_allergy(item: str) -> tuple[str, str]:
    item = item.strip()
    m = _ALLERGY_RE.search(item)
    if m:
        return item[: m.start()].strip(), m.group(1)
    return item, ""


def parse_meal_response(payload: dict) -> list[dict]:
    info = payload.get("mealServiceDietInfo")
    if not isinstance(info, list) or len(info) < 2:
        return []  # INFO-200(데이터 없음) 또는 형식 이상
    rows = info[1].get("row", [])
    meals = []
    for r in rows:
        menu = []
        for item in r.get("DDISH_NM", "").split("<br/>"):
            name, allergy = split_allergy(item)
            if name:
                menu.append({"name": name, "allergy": allergy})
        meals.append({
            "date": r.get("MLSV_YMD", ""),
            "cal": r.get("CAL_INFO", ""),
            "menu": menu,
        })
    return meals


class MealFetchWorker(QtCore.QThread):
    finished_ok = QtCore.Signal(dict)
    failed = QtCore.Signal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)

    def run(self) -> None:
        try:
            s = self._settings
            today = datetime.date.today()
            monday = today - datetime.timedelta(days=today.weekday())
            friday = monday + datetime.timedelta(days=4)
            url = build_meal_url(
                s["edu_code"], s["school_code"],
                monday.strftime("%Y%m%d"), friday.strftime("%Y%m%d"),
                s.get("api_key", ""),
            )
            meals = parse_meal_response(http_get_json(url))
            self.finished_ok.emit({
                "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "meals": meals,
            })
        except Exception as exc:
            self.failed.emit(str(exc))


class MealWidget(BaseWidget):
    BASE_SIZE = (240, 300)

    def __init__(self, store: ConfigStore):
        super().__init__("meal", store)
        self.cache_path = Path(store.path).parent / "cache" / "meal.json"
        self._data: dict | None = None
        self._worker: MealFetchWorker | None = None
        self._tier = ""

        self.header_label = QtWidgets.QLabel("🍽 오늘 급식", alignment=QtCore.Qt.AlignCenter)
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
        self.render_meal()

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
        minutes = int(self.store.data["meal"].get("refresh_minutes", 360))
        self._refresh_timer.start(minutes * 60 * 1000)
        if not self.store.data["meal"].get("_skip_initial_fetch", False):
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
        self._worker = MealFetchWorker(self.store.data["meal"], self)
        self._worker.finished_ok.connect(self._on_fetch_ok)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_ok(self, data: dict) -> None:
        self._data = data
        write_cache(self.cache_path, data)
        self.status_label.setText(f"갱신: {data.get('fetched_at', '')[:16]}")
        self.render_meal()

    def _on_fetch_failed(self, msg: str) -> None:
        self.status_label.setText("갱신 실패 — 캐시 표시 중")
        self.setToolTip(msg)

    # --- 렌더 ---
    def current_tier(self) -> str:
        return resolve_breakpoint(self.height(), MEAL_TIERS)

    def menu_text(self) -> str:
        parts = []
        for i in range(self.body_layout.count()):
            wdg = self.body_layout.itemAt(i).widget()
            if isinstance(wdg, QtWidgets.QLabel):
                parts.append(wdg.text())
        return "\n".join(parts)

    def _add_menu_lines(self, meal: dict, compact: bool) -> None:
        for m in meal["menu"]:
            suffix = f"  ({m['allergy']})" if m["allergy"] else ""
            lbl = QtWidgets.QLabel(f"· {m['name']}{suffix}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color:#2b2b2b;")
            self.body_layout.addWidget(lbl)
            if compact and self.body_layout.count() > 12:
                break
        if meal.get("cal"):
            cal = QtWidgets.QLabel(meal["cal"])
            cal.setStyleSheet("color:#999;")
            self.body_layout.addWidget(cal)

    def render_meal(self) -> None:
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tier = self.current_tier()
        meals = (self._data or {}).get("meals", [])
        today_ymd = datetime.date.today().strftime("%Y%m%d")
        weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

        if self._tier == "today":
            todays = [m for m in meals if m["date"] == today_ymd]
            if not todays:
                lbl = QtWidgets.QLabel("오늘은 급식 정보가 없습니다")
                lbl.setStyleSheet("color:#bbb;")
                self.body_layout.addWidget(lbl)
            else:
                self._add_menu_lines(todays[0], compact=True)
        else:
            shown = False
            for m in meals:
                try:
                    d = datetime.datetime.strptime(m["date"], "%Y%m%d").date()
                except ValueError:
                    continue
                head = QtWidgets.QLabel(
                    f"{d.month}/{d.day} ({weekday_names[d.weekday()]})"
                    + ("  ← 오늘" if m["date"] == today_ymd else "")
                )
                head.setStyleSheet("font-weight:600; color:#666;")
                self.body_layout.addWidget(head)
                self._add_menu_lines(m, compact=True)
                shown = True
            if not shown:
                lbl = QtWidgets.QLabel("이번 주 급식 정보가 없습니다")
                lbl.setStyleSheet("color:#bbb;")
                self.body_layout.addWidget(lbl)
        self._apply_responsive()

    def _custom_menu_actions(self, menu) -> dict:
        refresh_action = menu.addAction("새로고침")
        return {refresh_action: self.refresh}

    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.header_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(12, factor)}pt;"
        )
        self.status_label.setStyleSheet(
            f"color:#999; font-size:{scaled_font_pt(8, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        new_tier = self.current_tier()
        if new_tier != self._tier:
            self.render_meal()
        else:
            self._apply_responsive()
