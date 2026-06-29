"""메모 위젯: 여러 인스턴스 지원, 자동 저장."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ..core.base_widget import BaseWidget
from ..core.config_store import ConfigStore


def get_memo_text(store: ConfigStore, name: str) -> str:
    return store.data.setdefault("memo_texts", {}).get(name, "")


def set_memo_text(store: ConfigStore, name: str, text: str) -> None:
    store.data.setdefault("memo_texts", {})[name] = text
    store.save()


class MemoWidget(BaseWidget):
    BASE_SIZE = (240, 190)

    def __init__(self, store: ConfigStore, name: str = "memo"):
        super().__init__(name, store)
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setPlainText(get_memo_text(store, name))
        self.editor.setStyleSheet(
            "background: transparent; border: none; font-size: 12pt; color:#2b2b2b;"
        )
        self.content_layout.addWidget(self.editor)

        self._save_timer = QtCore.QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._save_text)
        self.editor.textChanged.connect(self._save_timer.start)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 249, 196, 240))  # 포스트잇 노랑
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 12, 12)

    def _save_text(self) -> None:
        set_memo_text(self.store, self.widget_name, self.editor.toPlainText())
