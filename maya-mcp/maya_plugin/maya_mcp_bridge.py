"""Maya plugin to open commandPort for MCP Server communication.

Usage in Maya:
    # Load the plugin
    import maya.cmds as cmds
    cmds.loadPlugin("/path/to/maya_mcp_bridge.py")

    # Or run directly in Maya's Script Editor:
    exec(open("/path/to/maya_mcp_bridge.py").read())

    # Manual start/stop:
    from maya_mcp_bridge import start_mcp_bridge, stop_mcp_bridge
    start_mcp_bridge(port=7001)
    stop_mcp_bridge()

    # Open UI panel:
    from maya_mcp_bridge import open_panel
    open_panel()
"""

import sys
from pathlib import Path

import maya.cmds as cmds
import maya.api.OpenMaya as om

PLUGIN_NAME = "maya_mcp_bridge"
PLUGIN_VERSION = "0.2.0"
MENU_NAME = "mayaMCPMenu"
DEFAULT_PORT = 7001

_active_port = None


def maya_useNewAPI():
    """Tell Maya this plugin uses Maya Python API 2.0."""
    pass


def start_mcp_bridge(port: int = DEFAULT_PORT) -> None:
    """Open Maya commandPort for MCP Server connections."""
    global _active_port

    port_name = f":{port}"

    # Close existing port if open
    if _active_port is not None:
        stop_mcp_bridge()

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
    # Ensure maya_plugin directory is in sys.path for ui package imports
    plugin_dir = str(Path(__file__).resolve().parent)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

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
    start_mcp_bridge()
    _create_menu()


def uninitializePlugin(plugin: om.MObject) -> None:
    """Called when the plugin is unloaded from Maya."""
    _remove_menu()
    stop_mcp_bridge()
