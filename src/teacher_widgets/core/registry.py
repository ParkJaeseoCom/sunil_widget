"""위젯 등록·표시·숨김 컨트롤러 (트레이 UI와 분리하여 테스트 가능)."""

from __future__ import annotations

from typing import Callable

from .base_widget import BaseWidget
from .config_store import ConfigStore


class WidgetRegistry:
    def __init__(self, store: ConfigStore):
        self.store = store
        self._factories: dict[str, Callable[[], BaseWidget]] = {}
        self._instances: dict[str, BaseWidget] = {}

    def register(self, name: str, factory: Callable[[], BaseWidget]) -> None:
        self._factories[name] = factory

    def names(self) -> list[str]:
        return list(self._factories.keys())

    def is_visible(self, name: str) -> bool:
        return self.store.get_widget(name)["visible"]

    def show(self, name: str) -> BaseWidget:
        widget = self._instances.get(name)
        if widget is None:
            widget = self._factories[name]()
            self._instances[name] = widget
        widget.restore_geometry()
        widget.show()
        self.store.set_widget_visible(name, True)
        self.store.save()
        return widget

    def hide(self, name: str) -> None:
        widget = self._instances.get(name)
        if widget is not None:
            widget.hide_to_config()
        else:
            self.store.set_widget_visible(name, False)
            self.store.save()

    def restore_visible(self) -> None:
        for name in self._factories:
            if self.is_visible(name):
                self.show(name)
