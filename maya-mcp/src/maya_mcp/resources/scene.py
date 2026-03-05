"""Scene-related MCP resources."""

from ..maya_client import MayaClient


class SceneResources:
    """Resources providing Maya scene information."""

    def __init__(self, maya_client: MayaClient):
        self._maya = maya_client

    def get_scene_info(self) -> dict:
        """Get scene metadata."""
        code = """\
import maya.cmds as cmds
import json
info = {
    "file": cmds.file(q=True, sceneName=True) or "untitled",
    "modified": cmds.file(q=True, modified=True),
    "up_axis": cmds.upAxis(q=True, axis=True),
    "linear_unit": cmds.currentUnit(q=True, linear=True),
    "time_unit": cmds.currentUnit(q=True, time=True),
    "renderer": cmds.getAttr("defaultRenderGlobals.currentRenderer"),
}
return json.dumps(info)
"""
        return self._maya.query(code)

    def get_scene_hierarchy(self) -> dict:
        """Get scene node hierarchy."""
        code = """\
import maya.cmds as cmds
import json

def get_hierarchy(node):
    children = cmds.listRelatives(node, children=True, type="transform") or []
    return {
        "name": node,
        "type": cmds.objectType(node),
        "children": [get_hierarchy(c) for c in children],
    }

# Get root transforms (no parent)
all_transforms = cmds.ls(transforms=True)
defaults = {"front", "persp", "side", "top"}
roots = []
for t in all_transforms:
    if t in defaults:
        continue
    parent = cmds.listRelatives(t, parent=True)
    if not parent:
        roots.append(get_hierarchy(t))

return json.dumps({"roots": roots})
"""
        return self._maya.query(code)

    def get_object_attributes(self, name: str) -> dict:
        """Get all keyable attributes of an object."""
        code = f"""\
import maya.cmds as cmds
import json
if not cmds.objExists("{name}"):
    return json.dumps({{"error": "Object not found: {name}"}})
attrs = cmds.listAttr("{name}", keyable=True) or []
result = {{}}
for attr in attrs:
    try:
        val = cmds.getAttr("{name}." + attr)
        if isinstance(val, list) and len(val) == 1 and isinstance(val[0], tuple):
            val = list(val[0])
        result[attr] = val
    except Exception:
        result[attr] = None
return json.dumps(result)
"""
        return self._maya.query(code)
