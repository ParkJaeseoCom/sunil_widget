"""진입점: 설정 로드 → 위젯 등록 → 복원 → 트레이 → 실행."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6 import QtWidgets

from .core.config_store import ConfigStore
from .core.registry import WidgetRegistry
from .tray import TrayLauncher
from .widgets.clock import ClockWidget
from .widgets.timer import TimerWidget
from .widgets.memo import MemoWidget


def _config_path() -> Path:
    if getattr(sys, "frozen", False):  # PyInstaller exe
        base = Path(sys.executable).parent
    else:
        base = Path.cwd()
    return base / "teacher-widgets-data" / "config.json"


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 위젯 닫아도 트레이 유지

    store = ConfigStore(_config_path())
    store.load()

    registry = WidgetRegistry(store)
    registry.register("clock", lambda: ClockWidget(store))
    registry.register("timer", lambda: TimerWidget(store))
    registry.register("memo", lambda: MemoWidget(store, "memo"))

    # 최초 실행: config에 위젯 기록이 없으면 시계만 기본 표시
    if not store.data["widgets"]:
        store.set_widget_visible("clock", True)

    registry.restore_visible()
    TrayLauncher(app, registry)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
