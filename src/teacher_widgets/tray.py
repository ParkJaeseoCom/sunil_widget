"""시스템 트레이 런처."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtGui, QtWidgets

from .core.registry import WidgetRegistry

_ICON_PATH = Path(__file__).resolve().parents[2] / "assets" / "icon.png"


def build_tray_menu(registry: WidgetRegistry) -> QtWidgets.QMenu:
    menu = QtWidgets.QMenu()
    for name in registry.names():
        action = menu.addAction(name)
        action.setCheckable(True)
        action.setChecked(registry.is_visible(name))

        def make_handler(widget_name: str):
            def handler(checked: bool):
                if checked:
                    registry.show(widget_name)
                else:
                    registry.hide(widget_name)

            return handler

        action.toggled.connect(make_handler(name))

    menu.addSeparator()
    menu.addAction("종료")

    # 메뉴가 열릴 때마다 각 위젯의 visible 상태를 registry 에서 다시 읽어 동기화.
    # 신호를 차단한 채 setChecked 하여 toggle 핸들러가 재실행되지 않도록 한다.
    def _refresh_checks() -> None:
        for action in menu.actions():
            name = action.text()
            if action.isCheckable() and name in registry.names():
                action.blockSignals(True)
                action.setChecked(registry.is_visible(name))
                action.blockSignals(False)

    menu.aboutToShow.connect(_refresh_checks)
    return menu


class TrayLauncher:
    def __init__(self, app: QtWidgets.QApplication, registry: WidgetRegistry):
        self.app = app
        self.registry = registry
        icon = QtGui.QIcon(str(_ICON_PATH))
        self.tray = QtWidgets.QSystemTrayIcon(icon)
        self.tray.setToolTip("교사용 위젯")
        self.menu = build_tray_menu(registry)
        quit_action = next(a for a in self.menu.actions() if a.text() == "종료")
        quit_action.triggered.connect(self.app.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.show()
