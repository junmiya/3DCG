"""Transform manipulation tools."""

from ..maya_client import MayaClient


class TransformTools:
    """Tools for Maya transform operations."""

    def __init__(self, maya_client: MayaClient):
        self._maya = maya_client

    def set_transform(
        self,
        name: str,
        translate: list[float] | None = None,
        rotate: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> dict:
        """Set transform values for an object."""
        commands = []
        if translate is not None:
            commands.append(f'cmds.setAttr("{name}.translate", {translate[0]}, {translate[1]}, {translate[2]})')
        if rotate is not None:
            commands.append(f'cmds.setAttr("{name}.rotate", {rotate[0]}, {rotate[1]}, {rotate[2]})')
        if scale is not None:
            commands.append(f'cmds.setAttr("{name}.scale", {scale[0]}, {scale[1]}, {scale[2]})')

        if not commands:
            return {"error": "No transform values specified"}

        cmds_str = "\n    ".join(commands)
        code = f"""\
import maya.cmds as cmds
import json
if not cmds.objExists("{name}"):
    return json.dumps({{"error": "Object not found: {name}"}})
{cmds_str}
return json.dumps({{
    "name": "{name}",
    "translate": list(cmds.getAttr("{name}.translate")[0]),
    "rotate": list(cmds.getAttr("{name}.rotate")[0]),
    "scale": list(cmds.getAttr("{name}.scale")[0]),
}})
"""
        return self._maya.query(code)

    def get_transform(self, name: str) -> dict:
        """Get transform values for an object."""
        code = f"""\
import maya.cmds as cmds
import json
if not cmds.objExists("{name}"):
    return json.dumps({{"error": "Object not found: {name}"}})
return json.dumps({{
    "name": "{name}",
    "translate": list(cmds.getAttr("{name}.translate")[0]),
    "rotate": list(cmds.getAttr("{name}.rotate")[0]),
    "scale": list(cmds.getAttr("{name}.scale")[0]),
    "world_position": list(cmds.xform("{name}", q=True, worldSpace=True, translation=True)),
    "bounding_box": cmds.exactWorldBoundingBox("{name}"),
}})
"""
        return self._maya.query(code)
