"""Rodin Gen-2 (Hyper3D) provider for 3D generation.

API docs: https://developer.hyper3d.ai/api-specification/overview
Best for: Highest texture quality, quad mesh output, T/A-pose characters.
"""

import base64
import logging
from pathlib import Path
from typing import Any

import httpx

from .base import GenerationProvider, GenerationTask, TaskStatus

logger = logging.getLogger(__name__)

BASE_URL = "https://hyperhuman.deemos.com/api/v2"


class RodinProvider(GenerationProvider):
    """Rodin Gen-2 (Hyper3D) 3D generation provider."""

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
        return "rodin"

    async def generate_from_text(
        self,
        prompt: str,
        output_format: str = "fbx",
        **options: Any,
    ) -> GenerationTask:
        data = {
            "prompt": prompt,
            "condition_mode": "concat",
            "mesh_mode": options.get("mesh_mode", "quad"),
            "quality": options.get("quality", "high"),
        }
        if options.get("geometry", ""):
            data["geometry"] = options["geometry"]

        response = await self._client.post("/rodin", json=data)
        response.raise_for_status()
        result = response.json()

        task_id = result.get("uuid", result.get("task_id", ""))
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

        data = {
            "images": [encoded],
            "condition_mode": "concat",
            "mesh_mode": options.get("mesh_mode", "quad"),
            "quality": options.get("quality", "high"),
        }

        response = await self._client.post("/rodin", json=data)
        response.raise_for_status()
        result = response.json()

        task_id = result.get("uuid", result.get("task_id", ""))
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
            encoded_images.append(base64.b64encode(image_data).decode("utf-8"))

        data = {
            "images": encoded_images,
            "condition_mode": "concat",
            "mesh_mode": options.get("mesh_mode", "quad"),
            "quality": options.get("quality", "high"),
        }

        response = await self._client.post("/rodin", json=data)
        response.raise_for_status()
        result = response.json()

        task_id = result.get("uuid", result.get("task_id", ""))
        return GenerationTask(
            task_id=task_id,
            provider=self.name,
            status=TaskStatus.PENDING,
            metadata={"output_format": output_format, "type": "multi_image_to_3d", **options},
        )

    async def check_status(self, task_id: str) -> GenerationTask:
        response = await self._client.post(
            "/status", json={"uuid": task_id}
        )
        response.raise_for_status()
        result = response.json()

        jobs = result.get("jobs", {})
        status_str = jobs.get("status", result.get("status", ""))
        progress = jobs.get("progress", 0)

        status_map = {
            "Pending": TaskStatus.PENDING,
            "Running": TaskStatus.IN_PROGRESS,
            "Done": TaskStatus.SUCCEEDED,
            "Failed": TaskStatus.FAILED,
        }
        status = status_map.get(status_str, TaskStatus.PENDING)

        task = GenerationTask(
            task_id=task_id,
            provider=self.name,
            status=status,
            progress=int(progress * 100) if isinstance(progress, float) else progress,
        )

        if status == TaskStatus.SUCCEEDED:
            # Extract download URL
            outputs = jobs.get("output", [])
            if outputs:
                task.result_url = outputs[0] if isinstance(outputs[0], str) else outputs[0].get("url")

        if status == TaskStatus.FAILED:
            task.error = jobs.get("message", "Generation failed")

        return task

    async def download_result(self, task: GenerationTask, output_dir: Path) -> Path:
        if not task.result_url:
            raise ValueError(f"Task {task.task_id} has no result URL")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_format = task.metadata.get("output_format", "fbx")
        output_path = output_dir / f"rodin_{task.task_id}.{output_format}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(task.result_url)
            response.raise_for_status()
            output_path.write_bytes(response.content)

        task.local_path = output_path
        logger.info("Downloaded Rodin result to %s", output_path)
        return output_path

    async def close(self) -> None:
        await self._client.aclose()
