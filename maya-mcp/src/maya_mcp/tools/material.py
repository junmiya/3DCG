"""Material management tools."""

from typing import Any

from ..maya_client import MayaClient


class MaterialTools:
    """Tools for Maya material operations."""

    def __init__(self, maya_client: MayaClient):
        self._maya = maya_client

    def create_material(
        self, name: str, type: str = "lambert"
    ) -> dict:
        """Create a new material.

        Args:
            name: Material name.
            type: Material type (lambert, blinn, phong, aiStandardSurface).
        """
        code = f"""\
import maya.cmds as cmds
import json
mat = cmds.shadingNode("{type}", asShader=True, name="{name}")
sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="{name}SG")
cmds.connectAttr(mat + ".outColor", sg + ".surfaceShader")
return json.dumps({{"material": mat, "shading_group": sg, "type": "{type}"}})
"""
        return self._maya.query(code)

    def assign_material(self, object_name: str, material_name: str) -> dict:
        """Assign a material to an object."""
        code = f"""\
import maya.cmds as cmds
import json
if not cmds.objExists("{object_name}"):
    return json.dumps({{"error": "Object not found: {object_name}"}})
if not cmds.objExists("{material_name}"):
    return json.dumps({{"error": "Material not found: {material_name}"}})
# Find shading group
sgs = cmds.listConnections("{material_name}", type="shadingEngine") or []
if not sgs:
    return json.dumps({{"error": "No shading group found for {material_name}"}})
cmds.sets("{object_name}", edit=True, forceElement=sgs[0])
return json.dumps({{"object": "{object_name}", "material": "{material_name}", "shading_group": sgs[0]}})
"""
        return self._maya.query(code)

    def set_material_attr(
        self, material_name: str, attr: str, value: Any
    ) -> dict:
        """Set a material attribute.

        Args:
            material_name: Name of the material.
            attr: Attribute name (e.g., "color", "transparency").
            value: Attribute value (single value or [r,g,b] for colors).
        """
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            code = f"""\
import maya.cmds as cmds
import json
if not cmds.objExists("{material_name}"):
    return json.dumps({{"error": "Material not found: {material_name}"}})
cmds.setAttr("{material_name}.{attr}", {value[0]}, {value[1]}, {value[2]}, type="double3")
return json.dumps({{"material": "{material_name}", "attr": "{attr}", "value": {list(value[:3])}}})
"""
        else:
            code = f"""\
import maya.cmds as cmds
import json
if not cmds.objExists("{material_name}"):
    return json.dumps({{"error": "Material not found: {material_name}"}})
cmds.setAttr("{material_name}.{attr}", {value})
return json.dumps({{"material": "{material_name}", "attr": "{attr}", "value": {value}}})
"""
        return self._maya.query(code)
