"""3D model generation tools - the core pipeline for text/image to 3D."""

import asyncio
import logging
from pathlib import Path
from typing import Any

from ..config import Config
from ..maya_client import MayaClient
from ..providers import (
    GenerationProvider,
    GenerationTask,
    MeshyProvider,
    RodinProvider,
    TaskStatus,
    TripoProvider,
)

logger = logging.getLogger(__name__)


class GenerationTools:
    """Tools for generating 3D models from text/images and importing into Maya."""

    def __init__(self, config: Config, maya_client: MayaClient):
        self._config = config
        self._maya = maya_client
        self._providers: dict[str, GenerationProvider] = {}
        self._tasks: dict[str, GenerationTask] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        pc = self._config.provider
        if pc.rodin_api_key:
            self._providers["rodin"] = RodinProvider(pc.rodin_api_key, pc.generation_timeout)
        if pc.meshy_api_key:
            self._providers["meshy"] = MeshyProvider(pc.meshy_api_key, pc.generation_timeout)
        if pc.tripo_api_key:
            self._providers["tripo"] = TripoProvider(pc.tripo_api_key, pc.generation_timeout)

    def _get_provider(self, name: str | None = None) -> GenerationProvider:
        provider_name = name or self._config.provider.default_provider
        if provider_name not in self._providers:
            available = list(self._providers.keys())
            if not available:
                raise ValueError(
                    "No 3D generation providers configured. "
                    "Set at least one API key (RODIN_API_KEY, MESHY_API_KEY, or TRIPO_API_KEY)."
                )
            raise ValueError(
                f"Provider '{provider_name}' not configured. Available: {available}"
            )
        return self._providers[provider_name]

    async def generate_from_text(
        self,
        prompt: str,
        provider: str | None = None,
        output_format: str = "fbx",
        **options: Any,
    ) -> dict[str, Any]:
        """Generate a 3D model from text description.

        Args:
            prompt: Text description of the model to generate.
            provider: Provider name (rodin/meshy/tripo). Uses default if not specified.
            output_format: Output format (fbx/obj/glb).
            **options: Provider-specific options.

        Returns:
            Dict with task_id and status info.
        """
        p = self._get_provider(provider)
        task = await p.generate_from_text(prompt, output_format, **options)
        self._tasks[task.task_id] = task
        return {
            "task_id": task.task_id,
            "provider": task.provider,
            "status": task.status.value,
            "message": f"3D generation started with {task.provider}. Use check_generation_status to monitor progress.",
        }

    async def generate_from_image(
        self,
        image_path: str,
        provider: str | None = None,
        output_format: str = "fbx",
        **options: Any,
    ) -> dict[str, Any]:
        """Generate a 3D model from a single image.

        Args:
            image_path: Path to the input image.
            provider: Provider name (rodin/meshy/tripo).
            output_format: Output format (fbx/obj/glb).
            **options: Provider-specific options.

        Returns:
            Dict with task_id and status info.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        p = self._get_provider(provider)
        task = await p.generate_from_image(path, output_format, **options)
        self._tasks[task.task_id] = task
        return {
            "task_id": task.task_id,
            "provider": task.provider,
            "status": task.status.value,
            "message": f"Image-to-3D generation started with {task.provider}.",
        }

    async def generate_from_images(
        self,
        image_paths: list[str],
        provider: str | None = None,
        output_format: str = "fbx",
        **options: Any,
    ) -> dict[str, Any]:
        """Generate a 3D model from multiple images.

        Args:
            image_paths: Paths to input images.
            provider: Provider name (rodin/meshy/tripo).
            output_format: Output format (fbx/obj/glb).
            **options: Provider-specific options.

        Returns:
            Dict with task_id and status info.
        """
        paths = []
        for ip in image_paths:
            p = Path(ip)
            if not p.exists():
                raise FileNotFoundError(f"Image not found: {ip}")
            paths.append(p)

        p = self._get_provider(provider)
        task = await p.generate_from_images(paths, output_format, **options)
        self._tasks[task.task_id] = task
        return {
            "task_id": task.task_id,
            "provider": task.provider,
            "status": task.status.value,
            "message": f"Multi-image-to-3D generation started with {task.provider}.",
        }

    async def check_generation_status(self, task_id: str) -> dict[str, Any]:
        """Check the status of a generation task.

        Args:
            task_id: The task ID returned from a generate call.

        Returns:
            Dict with current status and progress.
        """
        cached = self._tasks.get(task_id)
        if not cached:
            raise ValueError(f"Unknown task ID: {task_id}")

        p = self._get_provider(cached.provider)
        updated = await p.check_status(task_id)

        # Preserve metadata from original task
        updated.metadata = cached.metadata
        self._tasks[task_id] = updated

        result: dict[str, Any] = {
            "task_id": task_id,
            "provider": updated.provider,
            "status": updated.status.value,
            "progress": updated.progress,
        }
        if updated.error:
            result["error"] = updated.error
        if updated.status == TaskStatus.SUCCEEDED:
            result["message"] = "Generation complete! Use import_generated_model to import into Maya."
        return result

    async def import_generated_model(
        self,
        task_id: str | None = None,
        file_path: str | None = None,
        name: str | None = None,
        scale: float = 1.0,
    ) -> dict[str, Any]:
        """Import a generated 3D model into Maya.

        Provide either task_id (to download and import) or file_path (direct import).

        Args:
            task_id: Task ID of a completed generation.
            file_path: Direct path to a model file (FBX/OBJ/GLB).
            name: Optional name for the imported object in Maya.
            scale: Scale factor for import.

        Returns:
            Dict with import result and object info.
        """
        import_path: Path | None = None

        if task_id:
            cached = self._tasks.get(task_id)
            if not cached:
                raise ValueError(f"Unknown task ID: {task_id}")

            if cached.local_path and cached.local_path.exists():
                import_path = cached.local_path
            else:
                # Download first
                p = self._get_provider(cached.provider)
                if cached.status != TaskStatus.SUCCEEDED:
                    updated = await p.check_status(task_id)
                    if updated.status != TaskStatus.SUCCEEDED:
                        return {
                            "error": f"Task not yet complete. Status: {updated.status.value}",
                            "progress": updated.progress,
                        }
                    cached = updated

                asset_dir = self._config.provider.asset_dir
                import_path = await p.download_result(cached, asset_dir)
        elif file_path:
            import_path = Path(file_path)
            if not import_path.exists():
                raise FileNotFoundError(f"Model file not found: {file_path}")
        else:
            raise ValueError("Provide either task_id or file_path")

        # Import into Maya
        ext = import_path.suffix.lower()
        import_path_str = str(import_path).replace("\\", "/")

        if ext in (".fbx",):
            import_code = f"""\
import maya.cmds as cmds
import json
cmds.loadPlugin("fbxmaya", quiet=True)
before = set(cmds.ls(transforms=True))
cmds.file("{import_path_str}", i=True, type="FBX", ignoreVersion=True, mergeNamespacesOnClash=False, options="fbx")
after = set(cmds.ls(transforms=True))
new_nodes = list(after - before)
return json.dumps({{"imported_nodes": new_nodes}})
"""
        elif ext in (".obj",):
            import_code = f"""\
import maya.cmds as cmds
import json
cmds.loadPlugin("objExport", quiet=True)
before = set(cmds.ls(transforms=True))
cmds.file("{import_path_str}", i=True, type="OBJ", ignoreVersion=True, options="mo=1")
after = set(cmds.ls(transforms=True))
new_nodes = list(after - before)
return json.dumps({{"imported_nodes": new_nodes}})
"""
        else:
            return {"error": f"Unsupported format: {ext}. Use FBX or OBJ."}

        result = self._maya.query(import_code)

        if isinstance(result, dict) and "imported_nodes" in result:
            nodes = result["imported_nodes"]

            # Apply scale and rename if requested
            if scale != 1.0 or name:
                for node in nodes:
                    if scale != 1.0:
                        scale_code = f"""\
import maya.cmds as cmds
cmds.setAttr("{node}.scaleX", {scale})
cmds.setAttr("{node}.scaleY", {scale})
cmds.setAttr("{node}.scaleZ", {scale})
return "ok"
"""
                        self._maya.execute(scale_code)

                    if name and len(nodes) == 1:
                        rename_code = f"""\
import maya.cmds as cmds
cmds.rename("{node}", "{name}")
return "{name}"
"""
                        new_name = self._maya.execute(rename_code)
                        nodes = [new_name.strip('"').strip("'")]

            return {
                "success": True,
                "imported_nodes": nodes,
                "file": str(import_path),
                "message": f"Successfully imported {len(nodes)} object(s) into Maya.",
            }

        return {"success": True, "result": str(result), "file": str(import_path)}

    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            if hasattr(provider, "close"):
                await provider.close()
