"""Main dockable panel for Maya MCP."""

import maya.cmds as cmds
import maya.OpenMayaUI as omui

from . import QtWidgets, wrapInstance
from . import style
from .tab_generation import GenerationTab
from .tab_connection import ConnectionTab
from .tab_asset_browser import AssetBrowserTab

WORKSPACE_CONTROL_NAME = "mayaMCPPanelWorkspaceControl"

_instance = None


class MayaMCPPanel(QtWidgets.QWidget):
    """Main tabbed panel widget for Maya MCP."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Maya MCP")
        self.setStyleSheet(style.PANEL_STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._tabs = QtWidgets.QTabWidget()

        self._gen_tab = GenerationTab()
        self._tabs.addTab(self._gen_tab, "3D Generation")

        self._conn_tab = ConnectionTab()
        self._tabs.addTab(self._conn_tab, "Connection")

        self._browser_tab = AssetBrowserTab()
        self._tabs.addTab(self._browser_tab, "Asset Browser")

        layout.addWidget(self._tabs)

    def closeEvent(self, event):
        self._gen_tab.cleanup()
        self._conn_tab.cleanup()
        super().closeEvent(event)

    @classmethod
    def display(cls):
        """Show the panel, creating it if necessary."""
        global _instance

        # Delete existing workspace control
        if cmds.workspaceControl(WORKSPACE_CONTROL_NAME, q=True, exists=True):
            cmds.deleteUI(WORKSPACE_CONTROL_NAME)

        _instance = cls()

        cmds.workspaceControl(
            WORKSPACE_CONTROL_NAME,
            label="Maya MCP",
            tabToControl=("AttributeEditor", -1),
            widthProperty="preferred",
            initialWidth=400,
        )

        # Re-parent the widget into the workspace control
        ctrl_ptr = omui.MQtUtil.findControl(WORKSPACE_CONTROL_NAME)
        if ctrl_ptr:
            ctrl_widget = wrapInstance(int(ctrl_ptr), QtWidgets.QWidget)
            ctrl_widget.layout().addWidget(_instance)

        return _instance
