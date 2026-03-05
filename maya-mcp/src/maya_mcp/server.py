"""Maya MCP Server - Main entry point.

Connects AI clients (Claude, etc.) to Autodesk Maya for 3D generation and scene manipulation.
"""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from .config import Config
from .maya_client import MayaClient
from .resources.scene import SceneResources
from .tools.animation import AnimationTools
from .tools.general import GeneralTools
from .tools.generation import GenerationTools
from .tools.material import MaterialTools
from .tools.object import ObjectTools
from .tools.render import RenderTools
from .tools.scene import SceneTools
from .tools.transform import TransformTools

logger = logging.getLogger(__name__)


def create_server() -> tuple[Server, Config, MayaClient, GenerationTools]:
    """Create and configure the MCP server with all tools and resources."""
    config = Config.from_env()
    maya_client = MayaClient(config.maya)

    # Initialize tool modules
    generation_tools = GenerationTools(config, maya_client)
    scene_tools = SceneTools(maya_client)
    object_tools = ObjectTools(maya_client)
    transform_tools = TransformTools(maya_client)
    material_tools = MaterialTools(maya_client)
    animation_tools = AnimationTools(maya_client)
    render_tools = RenderTools(maya_client)
    general_tools = GeneralTools(maya_client)

    # Initialize resources
    scene_resources = SceneResources(maya_client)

    server = Server("maya-mcp")

    # ── Tool definitions ──

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            # Generation tools
            Tool(
                name="generate_from_text",
                description="Generate a 3D model from text description using AI (Rodin/Meshy/Tripo). Returns a task_id for async tracking.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "description": "Text description of the 3D model to generate"},
                        "provider": {"type": "string", "enum": ["rodin", "meshy", "tripo"], "description": "AI provider (default: configured default)"},
                        "output_format": {"type": "string", "enum": ["fbx", "obj", "glb"], "default": "fbx"},
                    },
                    "required": ["prompt"],
                },
            ),
            Tool(
                name="generate_from_image",
                description="Generate a 3D model from a single image (photo/illustration). Image-to-3D produces higher quality than text-to-3D.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {"type": "string", "description": "Path to the input image file"},
                        "provider": {"type": "string", "enum": ["rodin", "meshy", "tripo"]},
                        "output_format": {"type": "string", "enum": ["fbx", "obj", "glb"], "default": "fbx"},
                    },
                    "required": ["image_path"],
                },
            ),
            Tool(
                name="generate_from_images",
                description="Generate a 3D model from multiple images (multi-view). Best accuracy for complex objects.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_paths": {"type": "array", "items": {"type": "string"}, "description": "Paths to input images"},
                        "provider": {"type": "string", "enum": ["rodin", "meshy", "tripo"]},
                        "output_format": {"type": "string", "enum": ["fbx", "obj", "glb"], "default": "fbx"},
                    },
                    "required": ["image_paths"],
                },
            ),
            Tool(
                name="check_generation_status",
                description="Check the progress of a 3D generation task.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID from a generate call"},
                    },
                    "required": ["task_id"],
                },
            ),
            Tool(
                name="import_generated_model",
                description="Import a generated or existing 3D model file (FBX/OBJ) into Maya.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task ID of a completed generation"},
                        "file_path": {"type": "string", "description": "Direct path to model file (alternative to task_id)"},
                        "name": {"type": "string", "description": "Name for the imported object in Maya"},
                        "scale": {"type": "number", "default": 1.0, "description": "Scale factor"},
                    },
                },
            ),
            # Scene tools
            Tool(
                name="scene_info",
                description="Get current Maya scene information (file, renderer, object count, etc).",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="scene_new",
                description="Create a new empty Maya scene.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "force": {"type": "boolean", "default": False, "description": "Force new scene without save prompt"},
                    },
                },
            ),
            Tool(
                name="scene_open",
                description="Open a Maya scene file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the .ma or .mb file"},
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="scene_save",
                description="Save the current Maya scene.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Save path (optional, uses current if omitted)"},
                    },
                },
            ),
            # Object tools
            Tool(
                name="create_object",
                description="Create a primitive object in Maya (cube, sphere, cylinder, cone, plane, torus).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["cube", "sphere", "cylinder", "cone", "plane", "torus"]},
                        "name": {"type": "string", "description": "Object name"},
                        "options": {"type": "object", "description": "Creation options (width, height, subdivisions, etc)"},
                    },
                    "required": ["type"],
                },
            ),
            Tool(
                name="delete_object",
                description="Delete an object from the Maya scene.",
                inputSchema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            ),
            Tool(
                name="list_objects",
                description="List objects in the Maya scene.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type_filter": {"type": "string", "description": "Filter by type (e.g., 'mesh', 'light', 'camera')"},
                    },
                },
            ),
            Tool(
                name="get_object_info",
                description="Get detailed info about a Maya object (type, transform, vertex/face count).",
                inputSchema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            ),
            # Transform tools
            Tool(
                name="set_transform",
                description="Set position, rotation, and/or scale of an object.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "translate": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                        "rotate": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                        "scale": {"type": "array", "items": {"type": "number"}, "minItems": 3, "maxItems": 3},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="get_transform",
                description="Get the transform values (position, rotation, scale, bounding box) of an object.",
                inputSchema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            ),
            # Material tools
            Tool(
                name="create_material",
                description="Create a new material/shader in Maya.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string", "enum": ["lambert", "blinn", "phong", "aiStandardSurface"], "default": "lambert"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="assign_material",
                description="Assign a material to an object.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {"type": "string"},
                        "material_name": {"type": "string"},
                    },
                    "required": ["object_name", "material_name"],
                },
            ),
            Tool(
                name="set_material_attr",
                description="Set a material attribute (color, transparency, etc).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "material_name": {"type": "string"},
                        "attr": {"type": "string", "description": "Attribute name (e.g., color, transparency)"},
                        "value": {"description": "Value - single number or [r,g,b] array for colors"},
                    },
                    "required": ["material_name", "attr", "value"],
                },
            ),
            # Animation tools
            Tool(
                name="set_keyframe",
                description="Set a keyframe on an object attribute.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "attribute": {"type": "string", "description": "Attribute (translateX, rotateY, scaleZ, etc)"},
                        "time": {"type": "number", "description": "Frame number"},
                        "value": {"type": "number"},
                    },
                    "required": ["name", "attribute", "time", "value"],
                },
            ),
            Tool(
                name="set_playback_range",
                description="Set the animation playback frame range.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start": {"type": "number"},
                        "end": {"type": "number"},
                    },
                    "required": ["start", "end"],
                },
            ),
            Tool(
                name="play_animation",
                description="Start or stop animation playback.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "forward": {"type": "boolean", "default": True},
                    },
                },
            ),
            # Render tools
            Tool(
                name="render_frame",
                description="Render the current frame to an image.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "width": {"type": "integer", "default": 960},
                        "height": {"type": "integer", "default": 540},
                        "output_path": {"type": "string"},
                    },
                },
            ),
            Tool(
                name="set_render_settings",
                description="Configure render settings (renderer, quality, etc).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "renderer": {"type": "string", "description": "Renderer name (arnold, mayaSoftware, mayaHardware2)"},
                    },
                },
            ),
            Tool(
                name="capture_viewport",
                description="Capture the Maya viewport as an image for visual feedback.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "output_path": {"type": "string", "description": "Output image file path"},
                        "width": {"type": "integer", "default": 960},
                        "height": {"type": "integer", "default": 540},
                    },
                    "required": ["output_path"],
                },
            ),
            # General tools
            Tool(
                name="execute_python",
                description="Execute arbitrary Python code in Maya. Use for advanced operations not covered by other tools.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Python code to execute"},
                    },
                    "required": ["code"],
                },
            ),
            Tool(
                name="execute_mel",
                description="Execute a MEL command in Maya.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "MEL command string"},
                    },
                    "required": ["command"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            result = await _dispatch_tool(
                name, arguments,
                generation_tools, scene_tools, object_tools,
                transform_tools, material_tools, animation_tools,
                render_tools, general_tools,
            )
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]

    # ── Resource definitions ──

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(uri="maya://scene/info", name="Scene Info", description="Current scene metadata"),
            Resource(uri="maya://scene/hierarchy", name="Scene Hierarchy", description="Node hierarchy tree"),
        ]

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        if uri == "maya://scene/info":
            result = scene_resources.get_scene_info()
        elif uri == "maya://scene/hierarchy":
            result = scene_resources.get_scene_hierarchy()
        elif uri.startswith("maya://object/") and uri.endswith("/attributes"):
            obj_name = uri.replace("maya://object/", "").replace("/attributes", "")
            result = scene_resources.get_object_attributes(obj_name)
        else:
            result = {"error": f"Unknown resource: {uri}"}
        return json.dumps(result, ensure_ascii=False, indent=2)

    return server, config, maya_client, generation_tools


async def _dispatch_tool(
    name: str,
    args: dict[str, Any],
    generation: GenerationTools,
    scene: SceneTools,
    obj: ObjectTools,
    transform: TransformTools,
    material: MaterialTools,
    animation: AnimationTools,
    render: RenderTools,
    general: GeneralTools,
) -> Any:
    """Route tool calls to the appropriate handler."""
    # Generation tools (async)
    if name == "generate_from_text":
        return await generation.generate_from_text(**args)
    if name == "generate_from_image":
        return await generation.generate_from_image(**args)
    if name == "generate_from_images":
        return await generation.generate_from_images(**args)
    if name == "check_generation_status":
        return await generation.check_generation_status(**args)
    if name == "import_generated_model":
        return await generation.import_generated_model(**args)

    # Scene tools (sync, run in executor)
    loop = asyncio.get_event_loop()
    if name == "scene_info":
        return await loop.run_in_executor(None, scene.scene_info)
    if name == "scene_new":
        return await loop.run_in_executor(None, lambda: scene.scene_new(**args))
    if name == "scene_open":
        return await loop.run_in_executor(None, lambda: scene.scene_open(**args))
    if name == "scene_save":
        return await loop.run_in_executor(None, lambda: scene.scene_save(**args))

    # Object tools
    if name == "create_object":
        return await loop.run_in_executor(None, lambda: obj.create_object(**args))
    if name == "delete_object":
        return await loop.run_in_executor(None, lambda: obj.delete_object(**args))
    if name == "list_objects":
        return await loop.run_in_executor(None, lambda: obj.list_objects(**args))
    if name == "get_object_info":
        return await loop.run_in_executor(None, lambda: obj.get_object_info(**args))

    # Transform tools
    if name == "set_transform":
        return await loop.run_in_executor(None, lambda: transform.set_transform(**args))
    if name == "get_transform":
        return await loop.run_in_executor(None, lambda: transform.get_transform(**args))

    # Material tools
    if name == "create_material":
        return await loop.run_in_executor(None, lambda: material.create_material(**args))
    if name == "assign_material":
        return await loop.run_in_executor(None, lambda: material.assign_material(**args))
    if name == "set_material_attr":
        return await loop.run_in_executor(None, lambda: material.set_material_attr(**args))

    # Animation tools
    if name == "set_keyframe":
        return await loop.run_in_executor(None, lambda: animation.set_keyframe(**args))
    if name == "set_playback_range":
        return await loop.run_in_executor(None, lambda: animation.set_playback_range(**args))
    if name == "play_animation":
        return await loop.run_in_executor(None, lambda: animation.play_animation(**args))

    # Render tools
    if name == "render_frame":
        return await loop.run_in_executor(None, lambda: render.render_frame(**args))
    if name == "set_render_settings":
        return await loop.run_in_executor(None, lambda: render.set_render_settings(**args))
    if name == "capture_viewport":
        return await loop.run_in_executor(None, lambda: render.capture_viewport(**args))

    # General tools
    if name == "execute_python":
        return await loop.run_in_executor(None, lambda: general.execute_python(**args))
    if name == "execute_mel":
        return await loop.run_in_executor(None, lambda: general.execute_mel(**args))

    raise ValueError(f"Unknown tool: {name}")


async def run_server() -> None:
    """Run the MCP server with stdio transport."""
    server, config, maya_client, generation_tools = create_server()

    logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")
    logger.info("Starting Maya MCP Server")
    logger.info("Maya: %s:%d", config.maya.host, config.maya.port)
    logger.info("Default provider: %s", config.provider.default_provider)

    # Ensure asset directory exists
    config.provider.asset_dir.mkdir(parents=True, exist_ok=True)

    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        await generation_tools.close()


def main() -> None:
    """Entry point for the maya-mcp-server command."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
