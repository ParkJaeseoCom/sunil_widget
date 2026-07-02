"""체크 위젯: 상태 헬퍼 + 다이얼로그 + ChecklistWidget.

이 파일의 상단부(헬퍼 함수)는 Task 4, 다이얼로그·위젯은 Task 6에서 추가된다.
"""

from __future__ import annotations

from PySide6 import QtWidgets

from teacher_widgets.core.config_store import ConfigStore

_DEFAULT_TITLE = "체크"


def _slot(store: ConfigStore, name: str) -> dict:
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
