"""모든 위젯이 상속하는 공통 베이스: 프레임리스·반투명·이동·리사이즈·저장."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from .config_store import ConfigStore

# 리사이즈 경계 두께 (픽셀)
_RESIZE_MARGIN = 8


def _resize_edges(pos: QtCore.QPoint, rect: QtCore.QRect) -> QtCore.Qt.Edges:
    """위젯 로컬 좌표 pos 가 rect 의 어느 모서리/에지에 해당하는지 반환.

    경계 없으면 Qt.Edges() (값 0) 반환. 이 함수는 독립적으로 테스트 가능하다.
    """
    edges = QtCore.Qt.Edges()
    m = _RESIZE_MARGIN
    x, y = pos.x(), pos.y()
    w, h = rect.width(), rect.height()

    if x < m:
        edges |= QtCore.Qt.LeftEdge
    elif x >= w - m:
        edges |= QtCore.Qt.RightEdge

    if y < m:
        edges |= QtCore.Qt.TopEdge
    elif y >= h - m:
        edges |= QtCore.Qt.BottomEdge

    return edges


class BaseWidget(QtWidgets.QWidget):
    BASE_SIZE: tuple[int, int] = (220, 140)

    def __init__(self, widget_name: str, store: ConfigStore):
        super().__init__()
        self.widget_name = widget_name
        self.store = store
        self._locked = False
        self._drag_offset: QtCore.QPoint | None = None

        # 리사이즈 상태
        self._resize_edges: QtCore.Qt.Edges = QtCore.Qt.Edges()
        self._resize_start_global: QtCore.QPoint | None = None
        self._resize_start_geom: QtCore.QRect | None = None

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Tool
            | QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(120, 80)

        self.content_layout = QtWidgets.QVBoxLayout(self)
        self.content_layout.setContentsMargins(12, 12, 12, 12)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

        # 마우스 추적: 커서 모양 갱신을 위해 필요
        self.setMouseTracking(True)

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
        if self._locked:
            self.unsetCursor()

    # --- 리사이즈 hit-test 헬퍼 (public for testing) ---
    @staticmethod
    def hit_test_resize(pos: QtCore.QPoint, rect: QtCore.QRect) -> QtCore.Qt.Edges:
        """로컬 좌표 pos 가 rect 의 리사이즈 경계에 해당하는 에지를 반환."""
        return _resize_edges(pos, rect)

    def _cursor_for_edges(self, edges: QtCore.Qt.Edges) -> QtCore.Qt.CursorShape:
        Left = QtCore.Qt.LeftEdge
        Right = QtCore.Qt.RightEdge
        Top = QtCore.Qt.TopEdge
        Bottom = QtCore.Qt.BottomEdge

        if edges & Left and edges & Top:
            return QtCore.Qt.SizeFDiagCursor
        if edges & Right and edges & Bottom:
            return QtCore.Qt.SizeFDiagCursor
        if edges & Right and edges & Top:
            return QtCore.Qt.SizeBDiagCursor
        if edges & Left and edges & Bottom:
            return QtCore.Qt.SizeBDiagCursor
        if edges & (Left | Right):
            return QtCore.Qt.SizeHorCursor
        if edges & (Top | Bottom):
            return QtCore.Qt.SizeVerCursor
        return QtCore.Qt.ArrowCursor

    # --- 드래그 이동 + 리사이즈 ---
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and not self._locked:
            edges = _resize_edges(event.position().toPoint(), self.rect())
            if edges:
                # 리사이즈 모드 시작
                self._resize_edges = edges
                self._resize_start_global = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                self._drag_offset = None
                event.accept()
                return
            # 일반 드래그 이동
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        local_pos = event.position().toPoint()

        # 리사이즈 진행 중
        if self._resize_start_global is not None and not self._locked:
            delta = event.globalPosition().toPoint() - self._resize_start_global
            g = self._resize_start_geom
            new_x, new_y, new_w, new_h = g.x(), g.y(), g.width(), g.height()
            edges = self._resize_edges

            if edges & QtCore.Qt.RightEdge:
                new_w = max(self.minimumWidth(), g.width() + delta.x())
            if edges & QtCore.Qt.BottomEdge:
                new_h = max(self.minimumHeight(), g.height() + delta.y())
            if edges & QtCore.Qt.LeftEdge:
                new_w = max(self.minimumWidth(), g.width() - delta.x())
                new_x = g.x() + (g.width() - new_w)
            if edges & QtCore.Qt.TopEdge:
                new_h = max(self.minimumHeight(), g.height() - delta.y())
                new_y = g.y() + (g.height() - new_h)

            self.setGeometry(new_x, new_y, new_w, new_h)
            event.accept()
            return

        # 드래그 이동 진행 중
        if self._drag_offset is not None and not self._locked:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return

        # 단순 마우스 이동: 커서 모양 업데이트
        if not self._locked:
            edges = _resize_edges(local_pos, self.rect())
            if edges:
                self.setCursor(self._cursor_for_edges(edges))
            else:
                self.unsetCursor()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._resize_start_global is not None:
            self._resize_edges = QtCore.Qt.Edges()
            self._resize_start_global = None
            self._resize_start_geom = None
            self.persist_geometry()
            event.accept()
            return
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
