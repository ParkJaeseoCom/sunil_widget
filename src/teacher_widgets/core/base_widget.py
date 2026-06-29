"""모든 위젯이 상속하는 공통 베이스: 프레임리스·반투명·이동·리사이즈·저장."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .config_store import ConfigStore


class BaseWidget(QtWidgets.QWidget):
    BASE_SIZE: tuple[int, int] = (220, 140)

    def __init__(self, widget_name: str, store: ConfigStore):
        super().__init__()
        self.widget_name = widget_name
        self.store = store
        self._locked = False
        self._drag_offset: QtCore.QPoint | None = None

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Tool
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.content_layout = QtWidgets.QVBoxLayout(self)
        self.content_layout.setContentsMargins(12, 12, 12, 12)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

        self.apply_opacity(self.store.get_opacity())
        self.set_locked(self.store.data.get("layout_locked", False))

    # --- 위치/크기 저장·복원 ---
    def restore_geometry(self) -> None:
        x, y, w, h = self.store.get_widget(self.widget_name)["geometry"]
        self.setGeometry(int(x), int(y), int(w), int(h))

    def persist_geometry(self) -> None:
        g = self.geometry()
        self.store.set_widget_geometry(
            self.widget_name, [g.x(), g.y(), g.width(), g.height()]
        )
        self.store.save()

    # --- 표시/숨김 ---
    def hide_to_config(self) -> None:
        self.hide()
        self.store.set_widget_visible(self.widget_name, False)
        self.store.save()

    # --- 외형 ---
    def apply_opacity(self, percent: int) -> None:
        self.setWindowOpacity(max(0.2, min(1.0, percent / 100)))

    def set_locked(self, locked: bool) -> None:
        self._locked = bool(locked)

    # --- 드래그 이동 ---
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and not self._locked:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_offset is not None and not self._locked:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_offset is not None:
            self._drag_offset = None
            self.persist_geometry()
            event.accept()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.on_resized(self.width(), self.height())

    def on_resized(self, width: int, height: int) -> None:
        """서브클래스가 반응형 갱신을 위해 오버라이드."""

    # --- 우클릭 메뉴 ---
    def _show_menu(self, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        lock_action = menu.addAction("이동 잠금 해제" if self._locked else "이동 잠금")
        close_action = menu.addAction("이 위젯 닫기")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == lock_action:
            self.set_locked(not self._locked)
        elif chosen == close_action:
            self.hide_to_config()
