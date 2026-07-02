"""주간학습계획 위젯: 순수 함수부(Task 2) + Worker·Widget(Task 3)."""

from __future__ import annotations

import datetime
import subprocess
import urllib.error
import webbrowser
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.data_remote import (
    anon_sign_in,
    firestore_get_document,
    firestore_run_query,
    read_cache,
    write_cache,
)
from teacher_widgets.core.responsive import resolve_breakpoint, scale_factor, scaled_font_pt
from teacher_widgets.widgets.timetable import build_app_command

PLAN_TIERS = [(0, "compact"), (300, "two_days"), (480, "week")]

_SPECIAL_DEPT = "학사일정"


def week_monday(today: datetime.date) -> datetime.date:
    """표시 기준 월요일. 주말이면 다음 주 월요일."""
    if today.weekday() >= 5:
        return today + datetime.timedelta(days=7 - today.weekday())
    return today - datetime.timedelta(days=today.weekday())


def build_schedules_query(start_iso: str, end_iso: str) -> dict:
    def _f(op: str, value: str) -> dict:
        return {"fieldFilter": {"field": {"fieldPath": "date"}, "op": op,
                                "value": {"stringValue": value}}}

    return {
        "from": [{"collectionId": "schedules"}],
        "where": {"compositeFilter": {"op": "AND", "filters": [
            _f("GREATER_THAN_OR_EQUAL", start_iso),
            _f("LESS_THAN_OR_EQUAL", end_iso),
        ]}},
        "orderBy": [{"field": {"fieldPath": "date"}, "direction": "ASCENDING"}],
        "limit": 200,
    }


def _sv(fields: dict, key: str) -> str:
    return fields.get(key, {}).get("stringValue", "")


def parse_schedule_docs(docs: list[dict]) -> list[dict]:
    out = []
    for d in docs:
        f = d.get("fields", {})
        order_raw = f.get("order", {}).get("integerValue")
        out.append({
            "date": _sv(f, "date"),
            "department": _sv(f, "department"),
            "content": _sv(f, "content"),
            "order": int(order_raw) if order_raw is not None else 0,
        })
    return out


def parse_messages_doc(fs_doc: dict | None) -> dict:
    fields = (fs_doc or {}).get("fields", {})
    return {
        "principal": _sv(fields, "principal"),
        "vicePrincipal": _sv(fields, "vicePrincipal"),
    }


def group_entries(entries: list) -> dict:
    grouped: dict = {}
    for e in entries:
        grouped.setdefault(e["date"], []).append(e)
    for items in grouped.values():
        items.sort(key=lambda e: (0 if e["department"] == _SPECIAL_DEPT else 1,
                                  e.get("order", 0)))
    return grouped


def pick_days(tier: str, base_monday: datetime.date,
              today: datetime.date) -> list[datetime.date]:
    base = today if base_monday <= today <= base_monday + datetime.timedelta(days=4) \
        else base_monday
    if tier == "compact":
        return [base]
    if tier == "two_days":
        return [base, base + datetime.timedelta(days=1)]
    days = [base_monday + datetime.timedelta(days=i) for i in range(5)]
    days.append(base_monday + datetime.timedelta(days=7))
    return days


class PlanFetchWorker(QtCore.QThread):
    """백그라운드에서 익명 인증→runQuery→(있으면) 이번 주 말씀 GET. GUI 블로킹 금지."""

    finished_ok = QtCore.Signal(dict)
    failed = QtCore.Signal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)

    def run(self) -> None:
        try:
            s = self._settings
            token = anon_sign_in(s["api_key"])
            monday = week_monday(datetime.date.today())
            end = monday + datetime.timedelta(days=7)
            parent_path = f"artifacts/{s['artifact_app_id']}/public/data"
            docs = firestore_run_query(
                s["project_id"], parent_path,
                build_schedules_query(monday.isoformat(), end.isoformat()),
                token,
            )
            entries = parse_schedule_docs(docs)
            try:
                msg_doc = firestore_get_document(
                    s["project_id"],
                    f"{parent_path}/weekly_messages/{monday.isoformat()}",
                    token,
                )
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    msg_doc = None  # 이번 주 말씀 미작성 — 정상
                else:
                    raise
            data = {
                "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "week_monday": monday.isoformat(),
                "entries": entries,
                "messages": parse_messages_doc(msg_doc),
            }
            self.finished_ok.emit(data)
        except Exception as exc:
            self.failed.emit(str(exc))


class WeeklyPlanWidget(BaseWidget):
    BASE_SIZE = (320, 360)

    def __init__(self, store: ConfigStore):
        super().__init__("weekly_plan", store)
        self.cache_path = Path(store.path).parent / "cache" / "weekly_plan.json"
        self._data: dict | None = None
        self._worker: PlanFetchWorker | None = None
        self._web_proc = None
        self._tier = ""

        self.header_label = QtWidgets.QLabel("주간학습계획", alignment=QtCore.Qt.AlignCenter)
        self.header_label.setStyleSheet("font-weight:700; color:#2b2b2b;")
        self.status_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#999;")
        self.content_layout.addWidget(self.header_label)
        self.content_layout.addWidget(self.status_label)

        days_widget = QtWidgets.QWidget()
        self.days_layout = QtWidgets.QVBoxLayout(days_widget)
        self.days_layout.setContentsMargins(0, 0, 0, 0)
        self.days_layout.setSpacing(4)
        self.content_layout.addWidget(days_widget, stretch=1)

        cached = read_cache(self.cache_path)
        if cached is not None:
            self._data = cached
            self.status_label.setText(f"갱신: {cached.get('fetched_at', '')[:16]}")
        else:
            self.status_label.setText("데이터 없음 — 우클릭 → 새로고침")
        self.render_plan()

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

    # --- 수명주기 (시간표 패턴) ---
    def showEvent(self, event) -> None:
        super().showEvent(event)
        minutes = int(self.store.data["weekly_plan"].get("refresh_minutes", 30))
        self._refresh_timer.start(minutes * 60 * 1000)
        if not self.store.data["weekly_plan"].get("_skip_initial_fetch", False):
            self.refresh()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._refresh_timer.stop()

    def _shutdown_worker(self) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait(2000)

    # --- 데이터 ---
    def refresh(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._worker = PlanFetchWorker(self.store.data["weekly_plan"], self)
        self._worker.finished_ok.connect(self._on_fetch_ok)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_ok(self, data: dict) -> None:
        self.apply_data(data)
        self.status_label.setText(f"갱신: {data.get('fetched_at', '')[:16]}")

    def _on_fetch_failed(self, msg: str) -> None:
        self.status_label.setText("갱신 실패 — 캐시 표시 중")
        self.setToolTip(msg)

    def apply_data(self, data: dict) -> None:
        self._data = data
        write_cache(self.cache_path, data)
        self.render_plan()

    # --- 렌더 ---
    def current_tier(self) -> str:
        return resolve_breakpoint(self.height(), PLAN_TIERS)

    def days_text(self) -> str:
        """테스트/디버그용: 렌더된 일자 섹션 텍스트를 이어붙여 반환."""
        parts = []
        for i in range(self.days_layout.count()):
            wdg = self.days_layout.itemAt(i).widget()
            if isinstance(wdg, QtWidgets.QLabel):
                parts.append(wdg.text())
        return "\n".join(parts)

    def render_plan(self) -> None:
        while self.days_layout.count():
            item = self.days_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tier = self.current_tier()

        entries = (self._data or {}).get("entries", [])
        grouped = group_entries(entries)
        monday_iso = (self._data or {}).get("week_monday")
        today = datetime.date.today()
        monday = (datetime.date.fromisoformat(monday_iso)
                  if monday_iso else week_monday(today))
        weekday_names = ["월", "화", "수", "목", "금", "토", "일"]

        for day in pick_days(self._tier, monday, today):
            iso = day.isoformat()
            head = QtWidgets.QLabel(
                f"{day.month}/{day.day} ({weekday_names[day.weekday()]})"
                + ("  ← 오늘" if day == today else "")
            )
            head.setStyleSheet(
                "font-weight:600; color:#2b6e4f;" if day == today
                else "font-weight:600; color:#666;"
            )
            self.days_layout.addWidget(head)
            items = grouped.get(iso, [])
            if not items:
                empty = QtWidgets.QLabel("  일정 없음")
                empty.setStyleSheet("color:#bbb;")
                self.days_layout.addWidget(empty)
                continue
            for e in items:
                badge = "🟠" if e["department"] == "학사일정" else "▪"
                lbl = QtWidgets.QLabel(f"  {badge} [{e['department']}] {e['content']}")
                lbl.setWordWrap(True)
                lbl.setStyleSheet("color:#2b2b2b;")
                self.days_layout.addWidget(lbl)

        if self._tier == "week":
            messages = (self._data or {}).get("messages", {})
            for key, title in (("principal", "교장선생님"), ("vicePrincipal", "교감선생님")):
                text = (messages.get(key) or "").strip()
                if text:
                    lbl = QtWidgets.QLabel(f"💬 {title}: {text}")
                    lbl.setWordWrap(True)
                    lbl.setStyleSheet("color:#2b6e4f;")
                    self.days_layout.addWidget(lbl)
        self._apply_responsive()

    # --- 메뉴/웹앱 ---
    def _custom_menu_actions(self, menu) -> dict:
        refresh_action = menu.addAction("새로고침")
        return {refresh_action: self.refresh}

    def open_webapp(self) -> None:
        url = self.store.data["weekly_plan"].get("webapp_url", "")
        if not url:
            return
        if self._web_proc is not None and self._web_proc.poll() is None:
            return  # 이미 실행 중 (bring-to-front는 timetable 위젯과 달리 생략 — 단순화)
        cmd = build_app_command(url)
        if cmd:
            self._web_proc = subprocess.Popen(cmd)
        else:
            webbrowser.open(url)

    def mouseDoubleClickEvent(self, event) -> None:
        self.open_webapp()
        event.accept()

    # --- 반응형 ---
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
            self.render_plan()
        else:
            self._apply_responsive()
