def test_package_imports():
    import teacher_widgets

    assert teacher_widgets.__version__ == "0.1.0"


def test_pyside6_available():
    from PySide6 import QtWidgets

    assert QtWidgets is not None
