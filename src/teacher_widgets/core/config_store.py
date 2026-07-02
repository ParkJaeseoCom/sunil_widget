"""단일 config.json 상태 저장소."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

DEFAULT_WIDGET = {"visible": True, "geometry": [100, 100, 220, 140]}

DEFAULT_CONFIG: dict = {
    "theme": "pastel",
    "widget_opacity": 96,
    "layout_locked": False,
    "class_roster": {"boys": 14, "girls": 14},
    "widgets": {},
}


def deep_merge(base: dict, override: dict) -> dict:
    """override 값을 base 위에 재귀 병합한 새 dict 반환."""
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


class ConfigStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict = deepcopy(DEFAULT_CONFIG)

    def load(self) -> dict:
        if self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.data = deep_merge(DEFAULT_CONFIG, raw)
        else:
            self.data = deepcopy(DEFAULT_CONFIG)
        return self.data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_widget(self, name: str) -> dict:
        """위젯 설정 사본을 반환하는 순수 getter.

        알 수 없는 위젯이면 기본값 사본만 반환하고 self.data["widgets"]에
        슬롯을 생성하지 않는다 (슬롯 생성은 set_widget_* 의 _widget_slot 책임).
        """
        widget = self.data["widgets"].get(name)
        if widget is None:
            return deepcopy(DEFAULT_WIDGET)
        return deep_merge(DEFAULT_WIDGET, widget)

    def _widget_slot(self, name: str) -> dict:
        return self.data["widgets"].setdefault(name, deepcopy(DEFAULT_WIDGET))

    def set_widget_visible(self, name: str, visible: bool) -> None:
        self._widget_slot(name)["visible"] = bool(visible)

    def set_widget_geometry(self, name: str, geometry: list[int]) -> None:
        self._widget_slot(name)["geometry"] = [int(v) for v in geometry]

    def get_opacity(self) -> int:
        return int(self.data["widget_opacity"])

    def set_opacity(self, percent: int) -> None:
        self.data["widget_opacity"] = int(percent)

    def get_roster(self) -> tuple[int, int]:
        roster = self.data["class_roster"]
        return int(roster["boys"]), int(roster["girls"])

    def set_roster(self, boys: int, girls: int) -> None:
        self.data["class_roster"] = {"boys": int(boys), "girls": int(girls)}
