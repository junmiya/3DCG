"""QThread-based workers for async 3D generation provider calls."""

import asyncio
import time
import traceback
from pathlib import Path

from . import QtCore

from maya_mcp.providers.base import GenerationProvider, GenerationTask, TaskStatus


class GenerationWorker(QtCore.QThread):
    """Worker thread that runs async provider generation in its own event loop.

    Each worker creates a fresh asyncio event loop to avoid conflicts with
    Maya's main thread. The provider instance should be created fresh for
    thread safety (httpx.AsyncClient is not thread-safe).
    """

    started = QtCore.Signal(object)         # GenerationTask
    status_updated = QtCore.Signal(object)  # GenerationTask
    completed = QtCore.Signal(object)       # GenerationTask
    error = QtCore.Signal(str)

    POLL_INTERVAL = 3  # seconds

    def __init__(
        self,
        provider: GenerationProvider,
        asset_dir: Path,
        prompt: str | None = None,
        image_path: str | None = None,
        image_paths: list[str] | None = None,
        output_format: str = "fbx",
        parent=None,
    ):
        super().__init__(parent)
        self._provider = provider
        self._asset_dir = asset_dir
        self._prompt = prompt
        self._image_path = image_path
        self._image_paths = image_paths
        self._output_format = output_format
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._execute())
        except Exception as e:
            self.error.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
        finally:
            try:
                if hasattr(self._provider, "close"):
                    loop.run_until_complete(self._provider.close())
            except Exception:
                pass
            loop.close()

    async def _execute(self):
        # Submit generation request
        if self._image_paths:
            paths = [Path(p) for p in self._image_paths]
            task = await self._provider.generate_from_images(paths, self._output_format)
        elif self._image_path:
            task = await self._provider.generate_from_image(
                Path(self._image_path), self._output_format
            )
        elif self._prompt:
            task = await self._provider.generate_from_text(
                self._prompt, self._output_format
            )
        else:
            self.error.emit("No prompt or image provided.")
            return

        self.started.emit(task)

        # Poll until complete
        while task.status not in (TaskStatus.SUCCEEDED, TaskStatus.FAILED):
            if self._cancelled:
                self.error.emit("Generation cancelled.")
                return
            time.sleep(self.POLL_INTERVAL)
            task = await self._provider.check_status(task.task_id)
            self.status_updated.emit(task)

        if task.status == TaskStatus.FAILED:
            self.error.emit(task.error or "Generation failed.")
            return

        # Download result
        self._asset_dir.mkdir(parents=True, exist_ok=True)
        local_path = await self._provider.download_result(task, self._asset_dir)
        task.local_path = local_path
        self.completed.emit(task)
