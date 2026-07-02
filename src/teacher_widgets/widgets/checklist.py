"""체크 위젯: 상태 헬퍼 + 다이얼로그 + ChecklistWidget.

이 파일의 상단부(헬퍼 함수)는 Task 4, 다이얼로그·위젯은 Task 6에서 추가된다.
"""

from __future__ import annotations

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
