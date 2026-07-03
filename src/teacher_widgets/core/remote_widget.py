"""외부 데이터 위젯 공통 베이스.

시간표·주간계획·급식·날씨가 공유하던 수명주기(캐시 로드, showEvent
타이머+지터 fetch, hideEvent 정지, 종료 시 bounded wait, 429 백오프)를
한곳에 모은다. 서브클래스는 CONFIG_KEY·TIERS·_make_worker·_render만 구현.
"""

from __future__ import annotations

import random
import time
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from .base_widget import BaseWidget
from .config_store import ConfigStore
from .data_remote import read_cache, write_cache
from .responsive import resolve_breakpoint

_BACKOFF_SECONDS = 2 * 60 * 60  # 429(할당량 소진) 시 2시간 자동 fetch 중지


def initial_jitter_ms() -> int:
    """시작 fetch 지터(0~15초) — 다수 PC 동시 부팅 버스트 완화."""
    return random.randint(0, 15000)


class RemoteWidget(BaseWidget):
    CONFIG_KEY: str = ""
    TIERS: list | None = None

    def __init__(self, store: ConfigStore):
        super().__init__(self.CONFIG_KEY, store)
        self.cache_path = Path(store.path).parent / "cache" / f"{self.CONFIG_KEY}.json"
        self._data: dict | None = read_cache(self.cache_path)
        self._worker = None
        self._tier = ""
        self._backoff_until: float = 0.0

        self.status_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color:#999;")
        if self._data is not None:
            self.status_label.setText(f"갱신: {self._data.get('fetched_at', '')[:16]}")
        else:
            self.status_label.setText("데이터 없음 — 우클릭 → 새로고침")

        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh)

        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._shutdown_worker)

    # --- 서브클래스 훅 ---
    def _make_worker(self):
        raise NotImplementedError

    def _render(self) -> None:
        raise NotImplementedError

    def _apply_responsive(self) -> None:  # 기본 no-op
        pass

    @property
    def settings(self) -> dict:
        return self.store.data[self.CONFIG_KEY]

    # --- 수명주기 ---
    def showEvent(self, event) -> None:
        super().showEvent(event)
        minutes = int(self.settings.get("refresh_minutes", 30))
        self._refresh_timer.start(minutes * 60 * 1000)
        if not self.settings.get("_skip_initial_fetch", False):
            QtCore.QTimer.singleShot(initial_jitter_ms(), self.refresh)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._refresh_timer.stop()

    def _shutdown_worker(self) -> None:
        worker = self._worker
        if worker is not None and worker.isRunning():
            worker.wait(2000)

    # --- fetch ---
    def refresh(self, force: bool = False) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        if not force and time.monotonic() < self._backoff_until:
            return
        self._worker = self._make_worker()
        self._worker.finished_ok.connect(self._on_fetch_ok)
        self._worker.failed.connect(self._on_fetch_failed)
        self._worker.start()

    def _on_fetch_ok(self, data: dict) -> None:
        self._data = data
        write_cache(self.cache_path, data)
        self.status_label.setText(f"갱신: {data.get('fetched_at', '')[:16]}")
        self._render()

    def _on_fetch_failed(self, msg: str) -> None:
        self.status_label.setText("갱신 실패 — 캐시 표시 중")
        self.setToolTip(msg)
        if "429" in msg:
            self._backoff_until = time.monotonic() + _BACKOFF_SECONDS

    # --- tier / 반응형 ---
    def current_tier(self) -> str:
        if self.TIERS is None:
            return ""
        return resolve_breakpoint(self.height(), self.TIERS)

    def on_resized(self, width: int, height: int) -> None:
        if self.TIERS is not None and self.current_tier() != self._tier:
            self._render()
        else:
            self._apply_responsive()

    # --- 공통 외형 ---
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)
