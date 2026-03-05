"""Rendering and viewport tools."""

from ..maya_client import MayaClient


class RenderTools:
    """Tools for Maya rendering and viewport capture."""

    def __init__(self, maya_client: MayaClient):
        self._maya = maya_client

    def render_frame(
        self,
        width: int = 960,
        height: int = 540,
        output_path: str | None = None,
    ) -> dict:
        """Render the current frame.

        Args:
            width: Image width in pixels.
            height: Image height in pixels.
            output_path: Optional output file path.
        """
        output_arg = f', "{output_path.replace(chr(92), "/")}"' if output_path else ""
        code = f"""\
import maya.cmds as cmds
import json
cmds.setAttr("defaultRenderGlobals.imageFormat", 8)  # JPEG
cmds.setAttr("defaultResolution.width", {width})
cmds.setAttr("defaultResolution.height", {height})
result = cmds.render(batch=False{output_arg})
return json.dumps({{"rendered_image": result, "width": {width}, "height": {height}}})
"""
        return self._maya.query(code)

    def set_render_settings(self, renderer: str | None = None, **settings) -> dict:
        """Set render settings.

        Args:
            renderer: Renderer name (e.g., "arnold", "mayaSoftware", "mayaHardware2").
            **settings: Additional render settings.
        """
        commands = []
        if renderer:
            commands.append(f'cmds.setAttr("defaultRenderGlobals.currentRenderer", "{renderer}", type="string")')

        for key, val in settings.items():
            if isinstance(val, str):
                commands.append(f'cmds.setAttr("defaultRenderGlobals.{key}", "{val}", type="string")')
            else:
                commands.append(f'cmds.setAttr("defaultRenderGlobals.{key}", {val})')

        cmds_str = "\n    ".join(commands)
        code = f"""\
import maya.cmds as cmds
import json
{cmds_str}
renderer = cmds.getAttr("defaultRenderGlobals.currentRenderer")
return json.dumps({{"renderer": renderer}})
"""
        return self._maya.query(code)

    def capture_viewport(
        self,
        output_path: str,
        width: int = 960,
        height: int = 540,
    ) -> dict:
        """Capture the current viewport as an image.

        Args:
            output_path: Output file path for the captured image.
            width: Image width.
            height: Image height.
        """
        output_escaped = output_path.replace("\\", "/")
        code = f"""\
import maya.cmds as cmds
import json
cmds.playblast(
    completeFilename="{output_escaped}",
    format="image",
    compression="jpg",
    quality=100,
    width={width},
    height={height},
    frame=cmds.currentTime(q=True),
    forceOverwrite=True,
    viewer=False,
    showOrnaments=False,
    percent=100,
)
return json.dumps({{"output_path": "{output_escaped}", "width": {width}, "height": {height}}})
"""
        return self._maya.query(code)
