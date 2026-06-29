"""시계 위젯: 시각 + 날짜 + 한글 요일."""

from __future__ import annotations

import datetime

from PySide6 import QtCore, QtWidgets

from ..core.base_widget import BaseWidget
from ..core.config_store import ConfigStore
from ..core.responsive import scale_factor, scaled_font_pt

_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def format_clock(
    dt: datetime.datetime, hour24: bool = True, show_seconds: bool = True
) -> dict:
    if hour24:
        fmt = "%H:%M:%S" if show_seconds else "%H:%M"
        time_str = dt.strftime(fmt)
    else:
        ampm = "오전" if dt.hour < 12 else "오후"
        hour12 = dt.hour % 12 or 12
        if show_seconds:
            time_str = f"{ampm} {hour12}:{dt.minute:02d}:{dt.second:02d}"
        else:
            time_str = f"{ampm} {hour12}:{dt.minute:02d}"
    return {
        "time": time_str,
        "date": dt.strftime("%Y-%m-%d"),
        "weekday": _WEEKDAYS[dt.weekday()],
    }


class ClockWidget(BaseWidget):
    BASE_SIZE = (220, 128)

    def __init__(self, store: ConfigStore):
        super().__init__("clock", store)
        self.hour24 = True
        self.show_seconds = True

        self.time_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.date_label = QtWidgets.QLabel("", alignment=QtCore.Qt.AlignCenter)
        self.time_label.setStyleSheet("color: #2b2b2b; font-weight: 600;")
        self.date_label.setStyleSheet("color: #666;")
        self.content_layout.addWidget(self.time_label)
        self.content_layout.addWidget(self.date_label)

        self._tick = QtCore.QTimer(self)
        self._tick.timeout.connect(self._refresh)
        self._tick.start(1000)
        self._refresh()

    def paintEvent(self, event):  # 반투명 라운드 배경
        from PySide6 import QtGui

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    def _refresh(self) -> None:
        parts = format_clock(datetime.datetime.now(), self.hour24, self.show_seconds)
        self.time_label.setText(parts["time"])
        self.date_label.setText(f"{parts['date']} ({parts['weekday']})")
        self._apply_responsive()

    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.time_label.setStyleSheet(
            f"color:#2b2b2b; font-weight:600; font-size:{scaled_font_pt(28, factor)}pt;"
        )
        self.date_label.setStyleSheet(
            f"color:#666; font-size:{scaled_font_pt(11, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        self._apply_responsive()
