"""체크 위젯: 상태 헬퍼 + 다이얼로그 + ChecklistWidget.

이 파일의 상단부(헬퍼 함수)는 Task 4, 다이얼로그·위젯은 Task 6에서 추가된다.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from teacher_widgets.core.base_widget import BaseWidget
from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.core.responsive import scale_factor, scaled_font_pt
from teacher_widgets.core.roster import roster_numbers

_DEFAULT_TITLE = "체크"


class _RosterBus(QtCore.QObject):
    """학급 구성 변경을 모든 열린 체크 위젯 인스턴스에 알리는 시그널 버스.

    Qt는 수신자(위젯)가 파괴되면 연결을 자동 해제하므로 별도 정리가 필요 없다.
    """

    changed = QtCore.Signal()


roster_bus = _RosterBus()


def _slot(store: ConfigStore, name: str) -> dict:
    # 주의: setdefault를 사용하므로 조회만 해도(getter) config에 슬롯이 생성된다.
    checklists = store.data.setdefault("checklists", {})
    return checklists.setdefault(name, {"title": _DEFAULT_TITLE, "checked": []})


def get_title(store: ConfigStore, name: str) -> str:
    return _slot(store, name).get("title", _DEFAULT_TITLE)


def set_title(store: ConfigStore, name: str, title: str) -> None:
    _slot(store, name)["title"] = title
    store.save()


def get_checked(store: ConfigStore, name: str) -> set[int]:
    return {int(n) for n in _slot(store, name).get("checked", [])}


def set_checked(store: ConfigStore, name: str, numbers: set[int]) -> None:
    _slot(store, name)["checked"] = sorted(int(n) for n in numbers)
    store.save()


def toggle(store: ConfigStore, name: str, number: int) -> bool:
    checked = get_checked(store, name)
    if number in checked:
        checked.discard(number)
        result = False
    else:
        checked.add(number)
        result = True
    set_checked(store, name, checked)
    return result


class RosterDialog(QtWidgets.QDialog):
    def __init__(self, boys: int, girls: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("학급 구성 설정")
        form = QtWidgets.QFormLayout(self)

        self.boys_spin = QtWidgets.QSpinBox()
        self.boys_spin.setRange(0, 30)
        self.boys_spin.setValue(int(boys))
        self.girls_spin = QtWidgets.QSpinBox()
        self.girls_spin.setRange(0, 30)
        self.girls_spin.setValue(int(girls))

        form.addRow("남학생 수", self.boys_spin)
        form.addRow("여학생 수", self.girls_spin)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> tuple[int, int]:
        return self.boys_spin.value(), self.girls_spin.value()


class TitleDialog(QtWidgets.QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("제목 변경")
        layout = QtWidgets.QVBoxLayout(self)
        self.edit = QtWidgets.QLineEdit(title)
        layout.addWidget(self.edit)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> str:
        return self.edit.text()


class ChecklistWidget(BaseWidget):
    BASE_SIZE = (240, 320)

    def __init__(self, store: ConfigStore, name: str = "checklist"):
        super().__init__(name, store)
        self._buttons: dict[int, QtWidgets.QToolButton] = {}

        self.title_label = QtWidgets.QLabel(get_title(store, name))
        self.title_label.setAlignment(QtCore.Qt.AlignCenter)
        self.title_label.setStyleSheet("font-weight:700; color:#2b2b2b;")

        self.count_label = QtWidgets.QLabel("")
        self.count_label.setAlignment(QtCore.Qt.AlignCenter)
        self.count_label.setStyleSheet("color:#666;")

        self.grid_container = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        reset_btn = QtWidgets.QPushButton("초기화")
        reset_btn.clicked.connect(self.reset)

        self.content_layout.addWidget(self.title_label)
        self.content_layout.addWidget(self.count_label)
        self.content_layout.addWidget(self.grid_container)
        self.content_layout.addStretch(1)
        self.content_layout.addWidget(reset_btn)

        roster_bus.changed.connect(self.rebuild_grid)

        self.rebuild_grid()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor(255, 255, 255, 235))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 16, 16)

    # --- 그리드 ---
    def rebuild_grid(self) -> None:
        for btn in self._buttons.values():
            btn.deleteLater()
        self._buttons.clear()
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        boys, girls = self.store.get_roster()
        checked = get_checked(self.store, self.widget_name)
        numbers = roster_numbers(boys, girls)
        cols = 3
        for idx, num in enumerate(numbers):
            btn = QtWidgets.QToolButton()
            btn.setCheckable(True)
            btn.setText(str(num))
            btn.setChecked(num in checked)
            btn.clicked.connect(lambda _checked, n=num: self._on_toggle(n))
            self._buttons[num] = btn
            self.grid_layout.addWidget(btn, idx // cols, idx % cols)
        self.update_count()
        self._apply_responsive()

    def update_count(self) -> None:
        boys, girls = self.store.get_roster()
        valid = set(roster_numbers(boys, girls))
        done = len(get_checked(self.store, self.widget_name) & valid)
        self.count_label.setText(f"제출 {done}/{len(valid)}")

    def _on_toggle(self, number: int) -> None:
        toggle(self.store, self.widget_name, number)
        self.update_count()

    def reset(self) -> None:
        set_checked(self.store, self.widget_name, set())
        for btn in self._buttons.values():
            btn.setChecked(False)
        self.update_count()

    # --- 메뉴 / 다이얼로그 ---
    def _custom_menu_actions(self, menu) -> dict:
        title_action = menu.addAction("제목 변경")
        roster_action = menu.addAction("학급 구성 설정")
        reset_action = menu.addAction("초기화")
        return {
            title_action: self.change_title,
            roster_action: self.change_roster,
            reset_action: self.reset,
        }

    def change_title(self) -> None:
        dlg = TitleDialog(get_title(self.store, self.widget_name), self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            set_title(self.store, self.widget_name, dlg.value())
            self.title_label.setText(dlg.value())

    def change_roster(self) -> None:
        boys, girls = self.store.get_roster()
        dlg = RosterDialog(boys, girls, self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            new_boys, new_girls = dlg.values()
            self.store.set_roster(new_boys, new_girls)
            self.store.save()
            roster_bus.changed.emit()

    # --- 반응형 ---
    def _apply_responsive(self) -> None:
        factor = scale_factor((self.width(), self.height()), self.BASE_SIZE)
        self.title_label.setStyleSheet(
            f"font-weight:700; color:#2b2b2b; font-size:{scaled_font_pt(13, factor)}pt;"
        )
        self.count_label.setStyleSheet(
            f"color:#666; font-size:{scaled_font_pt(10, factor)}pt;"
        )

    def on_resized(self, width: int, height: int) -> None:
        self._apply_responsive()
