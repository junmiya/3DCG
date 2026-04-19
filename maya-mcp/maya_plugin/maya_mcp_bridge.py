"""Maya plugin to open commandPort for MCP Server communication.

Usage in Maya:
    # 推奨: プラグインとしてロード
    import maya.cmds as cmds
    cmds.loadPlugin("/path/to/maya_mcp_bridge.py")

    # 手動操作:
    from maya_mcp_bridge import start_mcp_bridge, stop_mcp_bridge, open_panel
    start_mcp_bridge(port=7001)
    open_panel()
    stop_mcp_bridge()
"""

import sys
from pathlib import Path

import maya.cmds as cmds
import maya.api.OpenMaya as om

PLUGIN_NAME = "maya_mcp_bridge"
PLUGIN_VERSION = "0.2.1"
MENU_NAME = "mayaMCPMenu"
DEFAULT_PORT = 7001

# --- プラグインディレクトリを一元解決 ---------------------------------------
# __file__ が定義されていないケース（execで読み込まれた場合など）にも対応
try:
    _PLUGIN_DIR = Path(__file__).resolve().parent
except NameError:
    # フォールバック: 既知の絶対パス
    _PLUGIN_DIR = Path(
        "/Users/muli/Documents/AI/3DCG/maya-mcp/maya_plugin"
    ).resolve()

_active_port = None


def maya_useNewAPI():
    """Tell Maya this plugin uses Maya Python API 2.0."""
    pass


def _ensure_plugin_dir_on_syspath() -> None:
    """Insert plugin directory into sys.path if missing."""
    plugin_dir = str(_PLUGIN_DIR)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)


def start_mcp_bridge(port: int = DEFAULT_PORT) -> None:
    """Open Maya commandPort for MCP Server connections."""
    global _active_port

    port_name = f":{port}"

    # 既存ポートがあれば閉じる
    if _active_port is not None:
        stop_mcp_bridge()

    # 同じポートが残っていた場合に備えて、事前に close を試みる（失敗は無視）
    try:
        cmds.commandPort(name=port_name, close=True)
    except RuntimeError:
        pass

    try:
        cmds.commandPort(name=port_name, sourceType="python", echoOutput=True)
        _active_port = port
        om.MGlobal.displayInfo(
            f"[MCP Bridge] commandPort opened on port {port}. "
            f"MCP Server can now connect."
        )
    except RuntimeError as e:
        om.MGlobal.displayError(f"[MCP Bridge] Failed to open port {port}: {e}")
        raise


def stop_mcp_bridge() -> None:
    """Close the MCP commandPort."""
    global _active_port

    if _active_port is None:
        om.MGlobal.displayWarning("[MCP Bridge] No active port to close.")
        return

    port_name = f":{_active_port}"
    try:
        cmds.commandPort(name=port_name, close=True)
        om.MGlobal.displayInfo(
            f"[MCP Bridge] commandPort on port {_active_port} closed."
        )
    except RuntimeError:
        pass
    finally:
        _active_port = None


def open_panel(*args) -> None:
    """Open the Maya MCP UI panel."""
    _ensure_plugin_dir_on_syspath()

    from ui.panel import MayaMCPPanel
    MayaMCPPanel.display()


def _create_menu() -> None:
    """Create the Maya MCP menu in the main menu bar."""
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)

    cmds.menu(MENU_NAME, label="Maya MCP", parent="MayaWindow", tearOff=True)
    cmds.menuItem(label="Open Panel", command=open_panel)
    cmds.menuItem(divider=True)
    cmds.menuItem(label="Start Bridge", command=lambda _: start_mcp_bridge())
    cmds.menuItem(label="Stop Bridge", command=lambda _: stop_mcp_bridge())


def _remove_menu() -> None:
    """Remove the Maya MCP menu."""
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)


def initializePlugin(plugin: om.MObject) -> None:
    """Called when the plugin is loaded in Maya."""
    om.MFnPlugin(plugin, "Maya MCP", PLUGIN_VERSION)

    # sys.path を即座に通しておく（他のコマンドから import できるように）
    _ensure_plugin_dir_on_syspath()

    start_mcp_bridge()

    # MayaWindow が未生成のタイミングで呼ばれる場合に備えて遅延実行
    cmds.evalDeferred(_create_menu)


def uninitializePlugin(plugin: om.MObject) -> None:
    """Called when the plugin is unloaded from Maya."""
    _remove_menu()
    stop_mcp_bridge()