"""Material management tools."""

import json
from typing import Any

from ..maya_client import MayaClient


def _coerce_value(value: Any) -> Any:
    """Normalize a value that may arrive as a string from the MCP client.

    Some MCP clients serialize numbers and arrays as JSON strings when the
    tool schema doesn't pin the type (e.g. `"0.8"` instead of `0.8`, or
    `"[0.1, 0.2, 0.3]"` instead of a real array). We do a best-effort
    parse so downstream code can rely on real Python types.
    """
    if not isinstance(value, str):
        return value
    s = value.strip()
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        pass
    try:
        return float(s)
    except ValueError:
        return value


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
        name_json = json.dumps(name)
        type_json = json.dumps(type)
        code = (
            "import maya.cmds as cmds\n"
            "import json\n"
            f"_name = {name_json}\n"
            f"_type = {type_json}\n"
            "mat = cmds.shadingNode(_type, asShader=True, name=_name)\n"
            "sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=mat + 'SG')\n"
            "cmds.connectAttr(mat + '.outColor', sg + '.surfaceShader')\n"
            "return json.dumps({'material': mat, 'shading_group': sg, 'type': _type})\n"
        )
        return self._maya.query(code)

    def assign_material(self, object_name: str, material_name: str) -> dict:
        """Assign a material to an object."""
        obj_json = json.dumps(object_name)
        mat_json = json.dumps(material_name)
        code = (
            "import maya.cmds as cmds\n"
            "import json\n"
            f"_obj = {obj_json}\n"
            f"_mat = {mat_json}\n"
            "if not cmds.objExists(_obj):\n"
            "    return json.dumps({'error': f'Object not found: {_obj}'})\n"
            "if not cmds.objExists(_mat):\n"
            "    return json.dumps({'error': f'Material not found: {_mat}'})\n"
            "sgs = cmds.listConnections(_mat, type='shadingEngine') or []\n"
            "if not sgs:\n"
            "    return json.dumps({'error': f'No shading group found for {_mat}'})\n"
            "cmds.sets(_obj, edit=True, forceElement=sgs[0])\n"
            "return json.dumps({'object': _obj, 'material': _mat, 'shading_group': sgs[0]})\n"
        )
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
        # Normalize value in case the MCP client sent it as a JSON string
        # like "0.8" or "[0.08, 0.08, 0.1]" instead of a real number/array.
        value = _coerce_value(value)

        mat_json = json.dumps(material_name)
        attr_json = json.dumps(attr)

        if isinstance(value, (list, tuple)) and len(value) >= 3:
            rgb_json = json.dumps([float(v) for v in value[:3]])
            code = (
                "import maya.cmds as cmds\n"
                "import json\n"
                f"_mat = {mat_json}\n"
                f"_attr = {attr_json}\n"
                f"_rgb = {rgb_json}\n"
                "if not cmds.objExists(_mat):\n"
                "    return json.dumps({'error': f'Material not found: {_mat}'})\n"
                "_full = _mat + '.' + _attr\n"
                "try:\n"
                "    cmds.setAttr(_full, _rgb[0], _rgb[1], _rgb[2], type='float3')\n"
                "except RuntimeError:\n"
                "    cmds.setAttr(_full, _rgb[0], _rgb[1], _rgb[2], type='double3')\n"
                "return json.dumps({'material': _mat, 'attr': _attr, 'value': _rgb})\n"
            )
        else:
            val_json = json.dumps(value)
            code = (
                "import maya.cmds as cmds\n"
                "import json\n"
                f"_mat = {mat_json}\n"
                f"_attr = {attr_json}\n"
                f"_val = {val_json}\n"
                "if not cmds.objExists(_mat):\n"
                "    return json.dumps({'error': f'Material not found: {_mat}'})\n"
                "cmds.setAttr(_mat + '.' + _attr, _val)\n"
                "return json.dumps({'material': _mat, 'attr': _attr, 'value': _val})\n"
            )
        return self._maya.query(code)
