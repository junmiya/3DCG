"""Tests for 3D generation providers."""

import pytest

from maya_mcp.providers.base import GenerationTask, TaskStatus


class TestGenerationTask:
    def test_default_status(self):
        task = GenerationTask(task_id="test-123", provider="rodin")
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0
        assert task.result_url is None
        assert task.local_path is None
        assert task.error is None

    def test_task_with_metadata(self):
        task = GenerationTask(
            task_id="test-456",
            provider="meshy",
            status=TaskStatus.SUCCEEDED,
            progress=100,
            result_url="https://example.com/model.fbx",
            metadata={"output_format": "fbx", "type": "image_to_3d"},
        )
        assert task.status == TaskStatus.SUCCEEDED
        assert task.progress == 100
        assert task.metadata["output_format"] == "fbx"


class TestTaskStatus:
    def test_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.SUCCEEDED.value == "succeeded"
        assert TaskStatus.FAILED.value == "failed"
