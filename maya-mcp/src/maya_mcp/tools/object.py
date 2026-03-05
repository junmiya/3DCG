"""Object manipulation tools."""

import json
from typing import Any

from ..maya_client import MayaClient


class ObjectTools:
    """Tools for Maya object manipulation."""

    def __init__(self, maya_client: MayaClient):
        self._maya = maya_client

    def create_object(
        self,
        type: str,
        name: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict:
        """Create a primitive object.

        Args:
            type: Object type (cube, sphere, cylinder, cone, plane, torus).
            name: Optional name for the object.
            options: Optional creation parameters (subdivisions, radius, etc).
        """
        opts = options or {}
        opts_json = json.dumps(opts)
        name_arg = f', name="{name}"' if name else ""
        code = f"""\
import maya.cmds as cmds
import json
opts = json.loads('{opts_json}')
type_map = {{
    "cube": "polyCube",
    "sphere": "polySphere",
    "cylinder": "polyCylinder",
    "cone": "polyCone",
    "plane": "polyPlane",
    "torus": "polyTorus",
}}
cmd_name = type_map.get("{type}", "{type}")
cmd = getattr(cmds, cmd_name, None)
if cmd is None:
    return json.dumps({{"error": "Unknown type: {type}"}})
result = cmd({name_arg} **opts)
return json.dumps({{"name": result[0], "shape": result[1] if len(result) > 1 else None}})
"""
        return self._maya.query(code)

    def delete_object(self, name: str) -> dict:
        """Delete an object by name."""
        code = f"""\
import maya.cmds as cmds
if cmds.objExists("{name}"):
    cmds.delete("{name}")
    return "Deleted: {name}"
else:
    return "Object not found: {name}"
"""
        return {"result": self._maya.execute(code)}

    def list_objects(self, type_filter: str | None = None) -> list:
        """List objects in the scene."""
        if type_filter:
            code = f"""\
import maya.cmds as cmds
import json
return json.dumps(cmds.ls(type="{type_filter}") or [])
"""
        else:
            code = """\
import maya.cmds as cmds
import json
transforms = cmds.ls(transforms=True)
# Exclude default cameras
defaults = {"front", "persp", "side", "top"}
filtered = [t for t in transforms if t not in defaults]
return json.dumps(filtered)
"""
        return self._maya.query(code)

    def get_object_info(self, name: str) -> dict:
        """Get detailed information about an object."""
        code = f"""\
import maya.cmds as cmds
import json
if not cmds.objExists("{name}"):
    return json.dumps({{"error": "Object not found: {name}"}})
info = {{
    "name": "{name}",
    "type": cmds.objectType("{name}"),
    "translate": cmds.getAttr("{name}.translate")[0] if cmds.attributeQuery("translate", node="{name}", exists=True) else None,
    "rotate": cmds.getAttr("{name}.rotate")[0] if cmds.attributeQuery("rotate", node="{name}", exists=True) else None,
    "scale": cmds.getAttr("{name}.scale")[0] if cmds.attributeQuery("scale", node="{name}", exists=True) else None,
    "visible": cmds.getAttr("{name}.visibility") if cmds.attributeQuery("visibility", node="{name}", exists=True) else None,
    "parent": cmds.listRelatives("{name}", parent=True),
    "children": cmds.listRelatives("{name}", children=True),
}}
shapes = cmds.listRelatives("{name}", shapes=True) or []
if shapes:
    shape = shapes[0]
    if cmds.objectType(shape) == "mesh":
        info["vertices"] = cmds.polyEvaluate("{name}", vertex=True)
        info["faces"] = cmds.polyEvaluate("{name}", face=True)
        info["edges"] = cmds.polyEvaluate("{name}", edge=True)
return json.dumps(info)
"""
        return self._maya.query(code)
