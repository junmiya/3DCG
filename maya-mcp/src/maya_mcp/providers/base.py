"""Base interface for 3D generation providers."""

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class TaskStatus(enum.Enum):
    """Status of a generation task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class GenerationTask:
    """Represents a 3D generation task."""

    task_id: str
    provider: str
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    result_url: str | None = None
    local_path: Path | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class GenerationProvider(ABC):
    """Abstract base class for 3D generation AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""

    @abstractmethod
    async def generate_from_text(
        self,
        prompt: str,
        output_format: str = "fbx",
        **options: Any,
    ) -> GenerationTask:
        """Generate a 3D model from text description.

        Args:
            prompt: Text description of the 3D model to generate.
            output_format: Desired output format (fbx, obj, glb).
            **options: Provider-specific options.

        Returns:
            GenerationTask with task_id for status polling.
        """

    @abstractmethod
    async def generate_from_image(
        self,
        image_path: Path,
        output_format: str = "fbx",
        **options: Any,
    ) -> GenerationTask:
        """Generate a 3D model from a single image.

        Args:
            image_path: Path to the input image file.
            output_format: Desired output format (fbx, obj, glb).
            **options: Provider-specific options.

        Returns:
            GenerationTask with task_id for status polling.
        """

    @abstractmethod
    async def generate_from_images(
        self,
        image_paths: list[Path],
        output_format: str = "fbx",
        **options: Any,
    ) -> GenerationTask:
        """Generate a 3D model from multiple images.

        Args:
            image_paths: Paths to input image files.
            output_format: Desired output format (fbx, obj, glb).
            **options: Provider-specific options.

        Returns:
            GenerationTask with task_id for status polling.
        """

    @abstractmethod
    async def check_status(self, task_id: str) -> GenerationTask:
        """Check the status of a generation task.

        Args:
            task_id: The task identifier returned from a generate call.

        Returns:
            Updated GenerationTask with current status.
        """

    @abstractmethod
    async def download_result(self, task: GenerationTask, output_dir: Path) -> Path:
        """Download the generated model file.

        Args:
            task: A completed GenerationTask.
            output_dir: Directory to save the downloaded file.

        Returns:
            Path to the downloaded model file.
        """
