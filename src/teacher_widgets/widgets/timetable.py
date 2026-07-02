"""시간표 위젯: Firestore 문서 파싱/필터 순수 함수 + 다이얼로그 + GUI.

이 파일의 상단부(순수 함수)는 Task 2, TargetDialog는 Task 3,
FetchWorker·TimetableWidget은 Task 4~5에서 추가된다.
"""

from __future__ import annotations

import datetime
import shutil
import subprocess
import webbrowser
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.data_remote import (
    anon_sign_in,
    firestore_get_document,
    read_cache,
    write_cache,
)
from teacher_widgets.core.responsive import scale_factor, scaled_font_pt

DAYS = ["월", "화", "수", "목", "금"]
PERIODS = [1, 2, 3, 4, 5, 6, 7]

_VIEW_KEY = {"class": "classId", "room": "room", "teacher": "teacher"}


def _sv(fields: dict, key: str, default: str = "") -> str:
    return fields.get(key, {}).get("stringValue", default)


def parse_global_state(fs_doc: dict) -> dict:
    """Firestore 문서에서 활성 시간표의 경량 lessons를 추출."""
    fields = fs_doc.get("fields", {})
    active_id = _sv(fields, "activeTableId")
    tables = fields.get("timetables", {}).get("arrayValue", {}).get("values", [])

    chosen = None
    for t in tables:
        tf = t.get("mapValue", {}).get("fields", {})
        if _sv(tf, "id") == active_id:
            chosen = tf
            break
    if chosen is None and tables:
        chosen = tables[0].get("mapValue", {}).get("fields", {})
    if chosen is None:
        return {"table_name": "", "lessons": []}

    lessons = []
    for lv in chosen.get("lessons", {}).get("arrayValue", {}).get("values", []):
        lf = lv.get("mapValue", {}).get("fields", {})
        day = _sv(lf, "day")
        period_raw = lf.get("period", {}).get("integerValue")
        if not day or period_raw is None:
            continue
        lessons.append({
            "name": _sv(lf, "name"),
            "teacher": _sv(lf, "teacher"),
            "room": _sv(lf, "room"),
            "classId": _sv(lf, "classId"),
            "day": day,
            "period": int(period_raw),
        })
    return {"table_name": _sv(chosen, "name"), "lessons": lessons}


def filter_lessons(lessons: list, view_type: str, target: str) -> dict:
    """뷰 유형·대상으로 필터해 {(day, period): [lesson...]} 반환."""
    key = _VIEW_KEY[view_type]
    grid: dict = {}
    for lesson in lessons:
        if lesson.get(key) == target:
            grid.setdefault((lesson["day"], lesson["period"]), []).append(lesson)
    return grid


def cell_text(entries: list, view_type: str) -> str:
    """한 칸의 표시 문자열. 웹앱 표시 규칙 계승."""
    if not entries:
        return ""
    parts = []
    for e in entries[:3]:
        if view_type == "class":
            room = e.get("room", "")
            name = e.get("name", "")
            parts.append(f"{name}📍{room}" if room and room != "교실" else name)
        else:
            parts.append(e.get("classId") or e.get("name", ""))
    text = "/".join(parts)
    if len(entries) > 3:
        text += f" 외 {len(entries) - 3}"
    return text


def derive_targets(lessons: list) -> dict:
    """캐시된 lessons에서 뷰별 대상 목록을 유도(정렬·중복 제거·빈값 제외)."""
    out = {"class": set(), "room": set(), "teacher": set()}
    for lesson in lessons:
        if lesson.get("classId"):
            out["class"].add(lesson["classId"])
        if lesson.get("room"):
            out["room"].add(lesson["room"])
        if lesson.get("teacher"):
            out["teacher"].add(lesson["teacher"])
    return {k: sorted(v) for k, v in out.items()}


def build_app_command(url: str) -> list[str] | None:
    """앱 모드(--app) 실행 명령. Edge 우선, Chrome 차선, 없으면 None."""
    for exe in ("msedge", "chrome"):
        path = shutil.which(exe)
        if path:
            return [path, f"--app={url}"]
    return None


class TargetDialog(QtWidgets.QDialog):
    """시간표 대상 선택: 유형(학급/특별실/전담) + 대상 콤보."""

    def __init__(self, targets: dict, view_type: str, target: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("대상 변경")
        self._targets = targets

        layout = QtWidgets.QVBoxLayout(self)

        radios = QtWidgets.QHBoxLayout()
        self.class_radio = QtWidgets.QRadioButton("학급")
        self.room_radio = QtWidgets.QRadioButton("특별실")
        self.teacher_radio = QtWidgets.QRadioButton("전담")
        for r in (self.class_radio, self.room_radio, self.teacher_radio):
            radios.addWidget(r)
            r.toggled.connect(self._repopulate)
        layout.addLayout(radios)

        self.target_combo = QtWidgets.QComboBox()
        layout.addWidget(self.target_combo)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        {"class": self.class_radio, "room": self.room_radio,
         "teacher": self.teacher_radio}.get(view_type, self.class_radio).setChecked(True)
        idx = self.target_combo.findText(target)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)

    def _current_type(self) -> str:
        if self.room_radio.isChecked():
            return "room"
        if self.teacher_radio.isChecked():
            return "teacher"
        return "class"

    def _repopulate(self, checked: bool) -> None:
        if not checked:
            return  # 해제 시그널은 무시(전환 시 두 번 호출 방지)
        self.target_combo.clear()
        self.target_combo.addItems(self._targets.get(self._current_type(), []))

    def values(self) -> tuple[str, str]:
        return self._current_type(), self.target_combo.currentText()


class FetchWorker(QtCore.QThread):
    """백그라운드에서 익명 인증→문서 GET→경량 파싱. GUI 블로킹 금지."""

    finished_ok = QtCore.Signal(dict)
    failed = QtCore.Signal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = dict(settings)

    def run(self) -> None:
        try:
            token = anon_sign_in(self._settings["api_key"])
            doc_path = (
                f"artifacts/{self._settings['artifact_app_id']}"
                "/public/data/timetables_state/global_state"
            )
            doc = firestore_get_document(self._settings["project_id"], doc_path, token)
            data = parse_global_state(doc)
            data["fetched_at"] = datetime.datetime.now().isoformat(timespec="seconds")
            self.finished_ok.emit(data)
        except Exception as exc:  # 네트워크·파싱 어떤 실패든 위젯을 죽이지 않는다
            self.failed.emit(str(exc))


class TimetableWidget(BaseWidget):
    BASE_SIZE = (340, 330)

    def __init__(self, store: ConfigStore):
        super().__init__("timetable", store)
        self.cache_path = Path(store.path).parent / "cache" / "timetable.json"
        self._data: dict | None = None
        self._worker: FetchWorker | None = None
        self._web_proc = None
        self._cells: dict[tuple[str, int], QtWidgets.QLabel] = {}

        self.header_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.header_label.setStyleSheet("font-weight:700; color:#2b2b2b;")
        self.status_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#999;")
        self.content_layout.addWidget(self.header_label)
        self.content_layout.addWidget(self.status_label)

        grid_container = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(2)
        for col, day in enumerate(DAYS):
            head = QtWidgets.QLabel(day, alignment=QtCore.Qt.AlignCenter)
            head.setStyleSheet("color:#666; font-weight:600;")
            self.grid_layout.addWidget(head, 0, col + 1)
        for row, period in enumerate(PERIODS):
            num = QtWidgets.QLabel(str(period), alignment=QtCore.Qt.AlignCenter)
            num.setStyleSheet("color:#999;")
            self.grid_layout.addWidget(num, row + 1, 0)
            for col, day in enumerate(DAYS):
                cell = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
                cell.setWordWrap(True)
                self._cells[(day, period)] = cell
                self.grid_layout.addWidget(cell, row + 1, col + 1)
        self.content_layout.addWidget(grid_container, stretch=1)

        cached = read_cache(self.cache_path)
        if cached is not None:
            self._data = cached
            self.render_grid()
            self.status_label.setText(f"갱신: {cached.get('fetched_at', '')[:16]}")
        else:
            self.status_label.setText("데이터 없음 — 우클릭 → 새로고침")

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)

        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown_worker)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        minutes = int(self.store.data["timetable"].get("refresh_minutes", 60))
        self._refresh_timer.start(minutes * 60 * 1000)
        if not self.store.data["timetable"].get("_skip_initial_fetch", False):
            self.refresh()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._refresh_timer.stop()

    def _shutdown_worker(self) -> None:
        """앱 종료 시 진행 중인 fetch를 제한 시간 내에서 기다린다."""
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait(2000)  # 무한 대기 금지 — 네트워크 타임아웃보다 짧게

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    # --- 데이터 ---
    def refresh(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self._worker = FetchWorker(self.store.data["timetable"], self)
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
        self.render_grid()

    # --- 렌더 ---
    def render_grid(self) -> None:
        settings = self.store.data["timetable"]
        view_type = settings.get("view_type", "class")
        target = settings.get("target", "")
        self.header_label.setText(f"{target} 시간표")

        lessons = (self._data or {}).get("lessons", [])
        grid = filter_lessons(lessons, view_type, target)
        today = DAYS[datetime.date.today().weekday()] if datetime.date.today().weekday() < 5 else None
        for (day, period), cell in self._cells.items():
            cell.setText(cell_text(grid.get((day, period), []), view_type))
            base = "background:rgba(124,198,166,0.18); border-radius:4px;" if day == today else ""
            cell.setStyleSheet(f"color:#2b2b2b; {base}")
        self._apply_responsive()

    def _set_target(self, view_type: str, target: str) -> None:
        self.store.data["timetable"]["view_type"] = view_type
        self.store.data["timetable"]["target"] = target
        self.store.save()
        self.render_grid()

    # --- 메뉴 ---
    def _custom_menu_actions(self, menu) -> dict:
        target_action = menu.addAction("대상 변경")
        refresh_action = menu.addAction("새로고침")
        return {target_action: self.change_target, refresh_action: self.refresh}

    def change_target(self) -> None:
        lessons = (self._data or {}).get("lessons", [])
        targets = derive_targets(lessons)
        settings = self.store.data["timetable"]
        dlg = TargetDialog(targets, settings.get("view_type", "class"),
                           settings.get("target", ""), self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            view_type, target = dlg.values()
            if target:
                self._set_target(view_type, target)

    # --- 웹앱 ---
    def open_webapp(self) -> None:
        url = self.store.data["timetable"].get("webapp_url", "")
        if not url:
            return
        # 이전에 띄운 앱 창이 살아있으면 맨 앞으로 (best-effort)
        if self._web_proc is not None and self._web_proc.poll() is None:
            self._bring_web_to_front()
            return
        cmd = build_app_command(url)
        if cmd:
            self._web_proc = subprocess.Popen(cmd)
        else:
            webbrowser.open(url)

    def _bring_web_to_front(self) -> None:
        """자식 프로세스의 최상위 창을 앞으로. 실패해도 무해(best-effort)."""
        try:
            import ctypes

            user32 = ctypes.windll.user32
            pid = self._web_proc.pid

            @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            def enum_handler(hwnd, _lparam):
                found_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(found_pid))
                if found_pid.value == pid and user32.IsWindowVisible(hwnd):
                    user32.SetForegroundWindow(hwnd)
                    return False  # 중단
                return True

            user32.EnumWindows(enum_handler, 0)
        except Exception:
            pass  # 브라우저가 기존 프로세스에 위임한 경우 등 — 조용히 무시

    def mouseDoubleClickEvent(self, event) -> None:
        self.open_webapp()
        event.accept()

    # --- 반응형 ---
    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        cell_pt = scaled_font_pt(8, factor)
        for cell in self._cells.values():
            style = cell.styleSheet()
            # font-size만 갱신 (오늘 강조 배경 유지)
            base = style.split("font-size")[0]
            cell.setStyleSheet(f"{base} font-size:{cell_pt}pt;")
        self.header_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(12, factor)}pt;"
        )
        self.status_label.setStyleSheet(
            f"color:#999; font-size:{scaled_font_pt(8, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        self._apply_responsive()
