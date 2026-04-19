"""Object manipulation tools."""

import json
from typing import Any

from ..maya_client import MayaClient


_TYPE_MAP = {
    "cube": "polyCube",
    "sphere": "polySphere",
    "cylinder": "polyCylinder",
    "cone": "polyCone",
    "plane": "polyPlane",
    "torus": "polyTorus",
}


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
        cmd_name = _TYPE_MAP.get(type)
        if cmd_name is None:
            return {"error": f"Unknown type: {type}"}

        # Build the kwargs dict on the Python side so the Maya-side code
        # is simple string-safe JSON instead of fragile string splicing.
        kwargs: dict[str, Any] = dict(options or {})
        if name:
            kwargs["name"] = name

        kwargs_json = json.dumps(kwargs)

        code = (
            "import maya.cmds as cmds\n"
            "import json\n"
            f"kwargs = json.loads({kwargs_json!r})\n"
            f"result = cmds.{cmd_name}(**kwargs)\n"
            "payload = {\n"
            '    "name": result[0],\n'
            '    "shape": result[1] if len(result) > 1 else None,\n'
            "}\n"
            "return json.dumps(payload)\n"
        )
        return self._maya.query(code)

    def delete_object(self, name: str) -> dict:
        """Delete an object by name."""
        name_json = json.dumps(name)
        code = (
            "import maya.cmds as cmds\n"
            f"target = {name_json}\n"
            "if cmds.objExists(target):\n"
            "    cmds.delete(target)\n"
            '    return f"Deleted: {target}"\n'
            "else:\n"
            '    return f"Object not found: {target}"\n'
        )
        return {"result": self._maya.execute(code)}

    def list_objects(self, type_filter: str | None = None) -> list:
        """List objects in the scene."""
        if type_filter:
            tf_json = json.dumps(type_filter)
            code = (
                "import maya.cmds as cmds\n"
                "import json\n"
                f"return json.dumps(cmds.ls(type={tf_json}) or [])\n"
            )
        else:
            code = (
                "import maya.cmds as cmds\n"
                "import json\n"
                "transforms = cmds.ls(transforms=True) or []\n"
                'defaults = {"front", "persp", "side", "top"}\n'
                "filtered = [t for t in transforms if t not in defaults]\n"
                "return json.dumps(filtered)\n"
            )
        return self._maya.query(code)

    def get_object_info(self, name: str) -> dict:
        """Get detailed information about an object."""
        name_json = json.dumps(name)
        code = (
            "import maya.cmds as cmds\n"
            "import json\n"
            f"target = {name_json}\n"
            "if not cmds.objExists(target):\n"
            '    return json.dumps({"error": f"Object not found: {target}"})\n'
            "\n"
            "def _attr(path):\n"
            "    if cmds.attributeQuery(path.split('.')[-1], node=target, exists=True):\n"
            "        return cmds.getAttr(f'{target}.{path}')\n"
            "    return None\n"
            "\n"
            "translate = _attr('translate')\n"
            "rotate = _attr('rotate')\n"
            "scale = _attr('scale')\n"
            "visible = _attr('visibility')\n"
            "\n"
            "info = {\n"
            '    "name": target,\n'
            '    "type": cmds.objectType(target),\n'
            '    "translate": translate[0] if translate else None,\n'
            '    "rotate": rotate[0] if rotate else None,\n'
            '    "scale": scale[0] if scale else None,\n'
            '    "visible": visible,\n'
            '    "parent": cmds.listRelatives(target, parent=True),\n'
            '    "children": cmds.listRelatives(target, children=True),\n'
            "}\n"
            "\n"
            "shapes = cmds.listRelatives(target, shapes=True) or []\n"
            "if shapes and cmds.objectType(shapes[0]) == 'mesh':\n"
            '    info["vertices"] = cmds.polyEvaluate(target, vertex=True)\n'
            '    info["faces"] = cmds.polyEvaluate(target, face=True)\n'
            '    info["edges"] = cmds.polyEvaluate(target, edge=True)\n'
            "return json.dumps(info)\n"
        )
        return self._maya.query(code)
