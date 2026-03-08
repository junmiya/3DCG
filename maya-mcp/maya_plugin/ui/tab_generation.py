"""3D Generation tab - text/image to 3D model pipeline."""

from pathlib import Path

import maya.cmds as cmds

from . import QtWidgets, QtCore
from . import style
from .widgets import ImageDropZone
from .workers import GenerationWorker

from maya_mcp.config import Config
from maya_mcp.providers import RodinProvider, MeshyProvider, TripoProvider
from maya_mcp.providers.base import GenerationTask, TaskStatus


PROVIDERS = {
    "Rodin (Hyper3D)": "rodin",
    "Meshy": "meshy",
    "Tripo3D": "tripo",
}

FORMATS = ["fbx", "obj", "glb"]


class GenerationTab(QtWidgets.QWidget):
    """Tab for generating 3D models from text or images."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config.from_env()
        self._worker = None
        self._current_task = None
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        # Provider & format selection
        options_layout = QtWidgets.QHBoxLayout()

        options_layout.addWidget(QtWidgets.QLabel("Provider:"))
        self._provider_combo = QtWidgets.QComboBox()
        self._provider_combo.addItems(PROVIDERS.keys())
        options_layout.addWidget(self._provider_combo)

        options_layout.addWidget(QtWidgets.QLabel("Format:"))
        self._format_combo = QtWidgets.QComboBox()
        self._format_combo.addItems(FORMATS)
        options_layout.addWidget(self._format_combo)

        layout.addLayout(options_layout)

        # Text prompt
        layout.addWidget(QtWidgets.QLabel("Text Prompt:"))
        self._prompt_edit = QtWidgets.QTextEdit()
        self._prompt_edit.setMaximumHeight(70)
        self._prompt_edit.setPlaceholderText("e.g. A medieval wooden chair with intricate carvings")
        layout.addWidget(self._prompt_edit)

        # Image input
        layout.addWidget(QtWidgets.QLabel("Image Input (optional, higher quality):"))
        self._image_zone = ImageDropZone()
        layout.addWidget(self._image_zone)

        # Generate button
        self._generate_btn = QtWidgets.QPushButton("Generate 3D Model")
        self._generate_btn.setStyleSheet(
            f"background: {style.ACCENT}; color: white; "
            f"font-weight: bold; padding: 10px; font-size: 13px;"
        )
        self._generate_btn.clicked.connect(self._on_generate)
        layout.addWidget(self._generate_btn)

        # Progress
        progress_layout = QtWidgets.QHBoxLayout()
        self._progress_bar = QtWidgets.QProgressBar()
        self._progress_bar.setVisible(False)
        progress_layout.addWidget(self._progress_bar)

        self._cancel_btn = QtWidgets.QPushButton("Cancel")
        self._cancel_btn.setVisible(False)
        self._cancel_btn.clicked.connect(self._on_cancel)
        progress_layout.addWidget(self._cancel_btn)
        layout.addLayout(progress_layout)

        self._status_label = QtWidgets.QLabel("")
        self._status_label.setStyleSheet(f"color: {style.TEXT_SECONDARY};")
        layout.addWidget(self._status_label)

        # Import controls
        import_layout = QtWidgets.QHBoxLayout()

        import_layout.addWidget(QtWidgets.QLabel("Name:"))
        self._name_edit = QtWidgets.QLineEdit()
        self._name_edit.setPlaceholderText("(auto)")
        import_layout.addWidget(self._name_edit)

        import_layout.addWidget(QtWidgets.QLabel("Scale:"))
        self._scale_spin = QtWidgets.QDoubleSpinBox()
        self._scale_spin.setRange(0.001, 1000.0)
        self._scale_spin.setValue(1.0)
        self._scale_spin.setDecimals(3)
        import_layout.addWidget(self._scale_spin)

        layout.addLayout(import_layout)

        self._import_btn = QtWidgets.QPushButton("Import to Maya")
        self._import_btn.setEnabled(False)
        self._import_btn.clicked.connect(self._on_import)
        layout.addWidget(self._import_btn)

        # Result info
        self._result_label = QtWidgets.QLabel("")
        self._result_label.setWordWrap(True)
        layout.addWidget(self._result_label)

        layout.addStretch()

    def _create_provider(self, provider_key: str):
        """Create a fresh provider instance for the worker thread."""
        pc = self._config.provider
        timeout = pc.generation_timeout
        if provider_key == "rodin":
            if not pc.rodin_api_key:
                raise ValueError("RODIN_API_KEY not set. Set it as an environment variable.")
            return RodinProvider(pc.rodin_api_key, timeout)
        elif provider_key == "meshy":
            if not pc.meshy_api_key:
                raise ValueError("MESHY_API_KEY not set. Set it as an environment variable.")
            return MeshyProvider(pc.meshy_api_key, timeout)
        elif provider_key == "tripo":
            if not pc.tripo_api_key:
                raise ValueError("TRIPO_API_KEY not set. Set it as an environment variable.")
            return TripoProvider(pc.tripo_api_key, timeout)
        raise ValueError(f"Unknown provider: {provider_key}")

    def _on_generate(self):
        prompt = self._prompt_edit.toPlainText().strip()
        image_path = self._image_zone.image_path
        if not prompt and not image_path:
            self._status_label.setText("Please enter a prompt or select an image.")
            self._status_label.setStyleSheet(f"color: {style.WARNING};")
            return

        provider_display = self._provider_combo.currentText()
        provider_key = PROVIDERS[provider_display]
        output_format = self._format_combo.currentText()

        try:
            provider = self._create_provider(provider_key)
        except ValueError as e:
            self._status_label.setText(str(e))
            self._status_label.setStyleSheet(f"color: {style.ERROR};")
            return

        asset_dir = self._config.provider.asset_dir

        self._worker = GenerationWorker(
            provider=provider,
            asset_dir=asset_dir,
            prompt=prompt if prompt else None,
            image_path=image_path,
            output_format=output_format,
            parent=self,
        )
        self._worker.started.connect(self._on_task_started)
        self._worker.status_updated.connect(self._on_status_updated)
        self._worker.completed.connect(self._on_completed)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)

        # UI state: generating
        self._generate_btn.setEnabled(False)
        self._import_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._cancel_btn.setVisible(True)
        self._status_label.setText(f"Submitting to {provider_display}...")
        self._status_label.setStyleSheet(f"color: {style.TEXT_SECONDARY};")
        self._result_label.setText("")

        self._worker.start()

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()
            self._status_label.setText("Cancelling...")

    def _on_task_started(self, task: GenerationTask):
        self._current_task = task
        self._status_label.setText(f"Generation started (ID: {task.task_id[:12]}...)")

    def _on_status_updated(self, task: GenerationTask):
        self._current_task = task
        self._progress_bar.setValue(task.progress)
        self._status_label.setText(
            f"Status: {task.status.value} ({task.progress}%)"
        )

    def _on_completed(self, task: GenerationTask):
        self._current_task = task
        self._progress_bar.setValue(100)
        self._status_label.setText("Generation complete!")
        self._status_label.setStyleSheet(f"color: {style.SUCCESS};")
        self._import_btn.setEnabled(True)
        self._result_label.setText(f"File: {task.local_path}")

    def _on_error(self, error_msg: str):
        self._status_label.setText(f"Error: {error_msg.split(chr(10))[0]}")
        self._status_label.setStyleSheet(f"color: {style.ERROR};")
        self._progress_bar.setVisible(False)
        self._cancel_btn.setVisible(False)

    def _on_worker_finished(self):
        self._generate_btn.setEnabled(True)
        self._cancel_btn.setVisible(False)
        if self._progress_bar.value() < 100:
            self._progress_bar.setVisible(False)

    def _on_import(self):
        if not self._current_task or not self._current_task.local_path:
            return

        import_path = self._current_task.local_path
        if not import_path.exists():
            self._result_label.setText(f"File not found: {import_path}")
            return

        ext = import_path.suffix.lower()
        path_str = str(import_path).replace("\\", "/")
        scale = self._scale_spin.value()
        name = self._name_edit.text().strip() or None

        try:
            # Load required plugin
            if ext == ".fbx":
                cmds.loadPlugin("fbxmaya", quiet=True)
                file_type = "FBX"
                options = "fbx"
            elif ext == ".obj":
                cmds.loadPlugin("objExport", quiet=True)
                file_type = "OBJ"
                options = "mo=1"
            else:
                self._result_label.setText(f"Unsupported format: {ext}")
                return

            before = set(cmds.ls(transforms=True))
            cmds.file(
                path_str, i=True, type=file_type,
                ignoreVersion=True, mergeNamespacesOnClash=False,
                options=options,
            )
            after = set(cmds.ls(transforms=True))
            new_nodes = list(after - before)

            # Apply scale
            if scale != 1.0:
                for node in new_nodes:
                    cmds.setAttr(f"{node}.scaleX", scale)
                    cmds.setAttr(f"{node}.scaleY", scale)
                    cmds.setAttr(f"{node}.scaleZ", scale)

            # Rename
            if name and len(new_nodes) == 1:
                cmds.rename(new_nodes[0], name)
                new_nodes = [name]

            self._result_label.setText(
                f"Imported {len(new_nodes)} object(s): {', '.join(new_nodes)}"
            )
            self._result_label.setStyleSheet(f"color: {style.SUCCESS};")

        except Exception as e:
            self._result_label.setText(f"Import error: {e}")
            self._result_label.setStyleSheet(f"color: {style.ERROR};")

    def cleanup(self):
        """Stop any running worker."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.quit()
            self._worker.wait(5000)
