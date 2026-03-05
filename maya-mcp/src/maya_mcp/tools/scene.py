"""Scene management tools."""

from ..maya_client import MayaClient


class SceneTools:
    """Tools for Maya scene management."""

    def __init__(self, maya_client: MayaClient):
        self._maya = maya_client

    def scene_info(self) -> dict:
        """Get current scene information."""
        code = """\
import maya.cmds as cmds
import json
info = {
    "file": cmds.file(q=True, sceneName=True) or "untitled",
    "modified": cmds.file(q=True, modified=True),
    "up_axis": cmds.upAxis(q=True, axis=True),
    "linear_unit": cmds.currentUnit(q=True, linear=True),
    "time_unit": cmds.currentUnit(q=True, time=True),
    "frame_range": [cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True)],
    "renderer": cmds.getAttr("defaultRenderGlobals.currentRenderer"),
    "object_count": len(cmds.ls(transforms=True)),
    "mesh_count": len(cmds.ls(type="mesh")),
}
return json.dumps(info)
"""
        return self._maya.query(code)

    def scene_new(self, force: bool = False) -> dict:
        """Create a new scene."""
        code = f"""\
import maya.cmds as cmds
cmds.file(new=True, force={force})
return "New scene created"
"""
        return {"result": self._maya.execute(code)}

    def scene_open(self, file_path: str) -> dict:
        """Open a scene file."""
        file_path_escaped = file_path.replace("\\", "/")
        code = f"""\
import maya.cmds as cmds
cmds.file("{file_path_escaped}", open=True, force=True)
return cmds.file(q=True, sceneName=True)
"""
        return {"result": self._maya.execute(code), "file": file_path}

    def scene_save(self, file_path: str | None = None) -> dict:
        """Save the current scene."""
        if file_path:
            file_path_escaped = file_path.replace("\\", "/")
            code = f"""\
import maya.cmds as cmds
cmds.file(rename="{file_path_escaped}")
cmds.file(save=True, type="mayaAscii")
return cmds.file(q=True, sceneName=True)
"""
        else:
            code = """\
import maya.cmds as cmds
cmds.file(save=True)
return cmds.file(q=True, sceneName=True)
"""
        return {"result": self._maya.execute(code)}
