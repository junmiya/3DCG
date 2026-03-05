"""Tripo3D provider for 3D generation.

API docs: https://platform.tripo3d.ai/docs
Best for: Complete pipeline (generation → retopology → rigging), competitive pricing.
"""

import base64
import logging
from pathlib import Path
from typing import Any

import httpx

from .base import GenerationProvider, GenerationTask, TaskStatus

logger = logging.getLogger(__name__)

BASE_URL = "https://api.tripo3d.ai/v2/openapi"


class TripoProvider(GenerationProvider):
    """Tripo3D generation provider."""

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
        return "tripo"

    async def _upload_image(self, image_path: Path) -> str:
        """Upload an image and return the file token."""
        mime = "image/png" if image_path.suffix == ".png" else "image/jpeg"
        files = {"file": (image_path.name, image_path.read_bytes(), mime)}
        response = await self._client.post("/upload", files=files)
        response.raise_for_status()
        result = response.json()
        return result["data"]["image_token"]

    async def generate_from_text(
        self,
        prompt: str,
        output_format: str = "fbx",
        **options: Any,
    ) -> GenerationTask:
        data = {
            "type": "text_to_model",
            "prompt": prompt,
        }
        if options.get("model_version"):
            data["model_version"] = options["model_version"]

        response = await self._client.post("/task", json=data)
        response.raise_for_status()
        result = response.json()

        task_id = result["data"]["task_id"]
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
        image_token = await self._upload_image(image_path)

        data = {
            "type": "image_to_model",
            "file": {"type": "jpg" if image_path.suffix in (".jpg", ".jpeg") else "png", "file_token": image_token},
        }

        response = await self._client.post("/task", json=data)
        response.raise_for_status()
        result = response.json()

        task_id = result["data"]["task_id"]
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
        image_tokens = []
        for path in image_paths:
            token = await self._upload_image(path)
            image_tokens.append({
                "type": "jpg" if path.suffix in (".jpg", ".jpeg") else "png",
                "file_token": token,
            })

        data = {
            "type": "multi_image_to_model",
            "files": image_tokens,
        }

        response = await self._client.post("/task", json=data)
        response.raise_for_status()
        result = response.json()

        task_id = result["data"]["task_id"]
        return GenerationTask(
            task_id=task_id,
            provider=self.name,
            status=TaskStatus.PENDING,
            metadata={"output_format": output_format, "type": "multi_image_to_3d", **options},
        )

    async def check_status(self, task_id: str) -> GenerationTask:
        response = await self._client.get(f"/task/{task_id}")
        response.raise_for_status()
        result = response.json()

        data = result.get("data", {})
        status_str = data.get("status", "")
        status_map = {
            "queued": TaskStatus.PENDING,
            "running": TaskStatus.IN_PROGRESS,
            "success": TaskStatus.SUCCEEDED,
            "failed": TaskStatus.FAILED,
            "cancelled": TaskStatus.FAILED,
            "unknown": TaskStatus.PENDING,
        }
        status = status_map.get(status_str, TaskStatus.PENDING)

        task = GenerationTask(
            task_id=task_id,
            provider=self.name,
            status=status,
            progress=data.get("progress", 0),
        )

        if status == TaskStatus.SUCCEEDED:
            output = data.get("output", {})
            model = output.get("model")
            if model:
                task.result_url = model

        if status == TaskStatus.FAILED:
            task.error = data.get("message", "Generation failed")

        return task

    async def download_result(self, task: GenerationTask, output_dir: Path) -> Path:
        if not task.result_url:
            raise ValueError(f"Task {task.task_id} has no result URL")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_format = task.metadata.get("output_format", "fbx")
        output_path = output_dir / f"tripo_{task.task_id}.{output_format}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(task.result_url)
            response.raise_for_status()
            output_path.write_bytes(response.content)

        task.local_path = output_path
        logger.info("Downloaded Tripo result to %s", output_path)
        return output_path

    async def close(self) -> None:
        await self._client.aclose()
