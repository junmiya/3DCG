"""Meshy provider for 3D generation.

API docs: https://docs.meshy.ai/en/api/text-to-3d
Best for: Most consistent quality, PBR textures, broadest format support.
"""

import base64
import logging
from pathlib import Path
from typing import Any

import httpx

from .base import GenerationProvider, GenerationTask, TaskStatus

logger = logging.getLogger(__name__)

BASE_URL = "https://api.meshy.ai/openapi/v2"


class MeshyProvider(GenerationProvider):
    """Meshy 3D generation provider."""

    def __init__(self, api_key: str, timeout: float = 300.0):
        self._api_key = api_key
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout),
        )

    @property
    def name(self) -> str:
        return "meshy"

    async def generate_from_text(
        self,
        prompt: str,
        output_format: str = "fbx",
        **options: Any,
    ) -> GenerationTask:
        data = {
            "mode": "preview",
            "prompt": prompt,
            "art_style": options.get("art_style", "realistic"),
            "should_remesh": options.get("should_remesh", True),
        }
        if options.get("negative_prompt"):
            data["negative_prompt"] = options["negative_prompt"]

        response = await self._client.post("/text-to-3d", json=data)
        response.raise_for_status()
        result = response.json()

        task_id = result.get("result", result.get("id", ""))
        return GenerationTask(
            task_id=task_id,
            provider=self.name,
            status=TaskStatus.PENDING,
            metadata={"output_format": output_format, "type": "text_to_3d", **options},
        )

    async def generate_from_image(
        self,
        image_path: Path,
        output_format: str = "fbx",
        **options: Any,
    ) -> GenerationTask:
        image_data = image_path.read_bytes()
        encoded = base64.b64encode(image_data).decode("utf-8")
        mime = "image/png" if image_path.suffix == ".png" else "image/jpeg"
        data_uri = f"data:{mime};base64,{encoded}"

        data = {
            "image_url": data_uri,
            "should_remesh": options.get("should_remesh", True),
            "enable_pbr": options.get("enable_pbr", True),
        }

        response = await self._client.post("/image-to-3d", json=data)
        response.raise_for_status()
        result = response.json()

        task_id = result.get("result", result.get("id", ""))
        return GenerationTask(
            task_id=task_id,
            provider=self.name,
            status=TaskStatus.PENDING,
            metadata={"output_format": output_format, "type": "image_to_3d", **options},
        )

    async def generate_from_images(
        self,
        image_paths: list[Path],
        output_format: str = "fbx",
        **options: Any,
    ) -> GenerationTask:
        encoded_images = []
        for path in image_paths:
            image_data = path.read_bytes()
            encoded = base64.b64encode(image_data).decode("utf-8")
            mime = "image/png" if path.suffix == ".png" else "image/jpeg"
            encoded_images.append(f"data:{mime};base64,{encoded}")

        data = {
            "image_urls": encoded_images,
            "should_remesh": options.get("should_remesh", True),
            "enable_pbr": options.get("enable_pbr", True),
        }

        response = await self._client.post("/multi-image-to-3d", json=data)
        response.raise_for_status()
        result = response.json()

        task_id = result.get("result", result.get("id", ""))
        return GenerationTask(
            task_id=task_id,
            provider=self.name,
            status=TaskStatus.PENDING,
            metadata={"output_format": output_format, "type": "multi_image_to_3d", **options},
        )

    async def check_status(self, task_id: str) -> GenerationTask:
        task_type = "text-to-3d"
        response = await self._client.get(f"/{task_type}/{task_id}")
        if response.status_code == 404:
            response = await self._client.get(f"/image-to-3d/{task_id}")
        response.raise_for_status()
        result = response.json()

        status_str = result.get("status", "")
        status_map = {
            "PENDING": TaskStatus.PENDING,
            "IN_PROGRESS": TaskStatus.IN_PROGRESS,
            "SUCCEEDED": TaskStatus.SUCCEEDED,
            "FAILED": TaskStatus.FAILED,
            "EXPIRED": TaskStatus.FAILED,
        }
        status = status_map.get(status_str, TaskStatus.PENDING)

        task = GenerationTask(
            task_id=task_id,
            provider=self.name,
            status=status,
            progress=result.get("progress", 0),
        )

        if status == TaskStatus.SUCCEEDED:
            model_urls = result.get("model_urls", {})
            # Prefer FBX, then OBJ, then GLB
            task.result_url = (
                model_urls.get("fbx")
                or model_urls.get("obj")
                or model_urls.get("glb")
                or ""
            )

        if status == TaskStatus.FAILED:
            task.error = result.get("task_error", {}).get("message", "Generation failed")

        return task

    async def download_result(self, task: GenerationTask, output_dir: Path) -> Path:
        if not task.result_url:
            raise ValueError(f"Task {task.task_id} has no result URL")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_format = task.metadata.get("output_format", "fbx")
        output_path = output_dir / f"meshy_{task.task_id}.{output_format}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(task.result_url)
            response.raise_for_status()
            output_path.write_bytes(response.content)

        task.local_path = output_path
        logger.info("Downloaded Meshy result to %s", output_path)
        return output_path

    async def close(self) -> None:
        await self._client.aclose()
