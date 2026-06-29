"""타이머 위젯: 순수 모델 + GUI."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.base_widget import BaseWidget
from ..core.config_store import ConfigStore


def format_mmss(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


class TimerModel:
    def __init__(self, minutes: int = 5, seconds: int = 0):
        self._initial = minutes * 60 + seconds
        self.remaining = self._initial
        self.state = "idle"

    def set_duration(self, minutes: int, seconds: int) -> None:
        self._initial = minutes * 60 + seconds
        self.remaining = self._initial
        self.state = "idle"

    def start(self) -> None:
        if self.remaining > 0:
            self.state = "running"

    def pause(self) -> None:
        if self.state == "running":
            self.state = "paused"

    def reset(self) -> None:
        self.remaining = self._initial
        self.state = "idle"

    def tick(self) -> int:
        if self.state == "running":
            self.remaining = max(0, self.remaining - 1)
            if self.remaining == 0:
                self.state = "finished"
        return self.remaining


class TimerWidget(BaseWidget):
    BASE_SIZE = (220, 180)

    def __init__(self, store: ConfigStore):
        super().__init__("timer", store)
        saved = store.data.get("timer", {"minutes": 5, "seconds": 0})
        self.model = TimerModel(saved.get("minutes", 5), saved.get("seconds", 0))

        self.display_label = QtWidgets.QLabel(
            format_mmss(self.model.remaining), alignment=QtCore.Qt.AlignCenter
        )
        self.display_label.setStyleSheet("font-size:40pt; font-weight:700; color:#2b2b2b;")
        self.content_layout.addWidget(self.display_label)

        buttons = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("시작")
        self.reset_btn = QtWidgets.QPushButton("리셋")
        self.start_btn.clicked.connect(self._toggle)
        self.reset_btn.clicked.connect(self._reset)
        buttons.addWidget(self.start_btn)
        buttons.addWidget(self.reset_btn)
        self.content_layout.addLayout(buttons)

        self._tick = QtCore.QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(1000)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def _toggle(self) -> None:
        if self.model.state == "running":
            self.model.pause()
            self.start_btn.setText("시작")
        else:
            self.model.start()
            self.start_btn.setText("일시정지")

    def _reset(self) -> None:
        self.model.reset()
        self.start_btn.setText("시작")
        self.display_label.setText(format_mmss(self.model.remaining))

    def _on_tick(self) -> None:
        before = self.model.state
        self.model.tick()
        self.display_label.setText(format_mmss(self.model.remaining))
        if before == "running" and self.model.state == "finished":
            QtWidgets.QApplication.beep()
            self.start_btn.setText("시작")
