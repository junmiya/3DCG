"""Maya MCP Panel UI - PySide2/PySide6 compatibility layer."""

import sys
from pathlib import Path

# Add project src/ to path for provider imports
_project_root = Path(__file__).resolve().parent.parent.parent
_src_path = str(_project_root / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# PySide2 (Maya 2022-2024) / PySide6 (Maya 2025+) compatibility
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance
    PYSIDE_VERSION = 6
except ImportError:
    from PySide2 import QtWidgets, QtCore, QtGui
    from shiboken2 import wrapInstance
    PYSIDE_VERSION = 2

import maya.OpenMayaUI as omui


def get_maya_main_window() -> QtWidgets.QWidget:
    """Return the Maya main window as a QWidget."""
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
