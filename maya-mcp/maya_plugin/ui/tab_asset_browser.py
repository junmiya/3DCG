"""Asset Browser tab - browse and manage generated 3D assets."""

import os
from datetime import datetime
from pathlib import Path

import maya.cmds as cmds

from . import QtWidgets, QtCore
from . import style
from .widgets import AssetThumbnailWidget

from maya_mcp.config import Config


SUPPORTED_EXTS = {".fbx", ".obj", ".glb", ".usdz"}

# Infer provider from filename prefix
PROVIDER_PREFIXES = {
    "rodin": "Rodin",
    "meshy": "Meshy",
    "tripo": "Tripo",
}


class AssetBrowserTab(QtWidgets.QWidget):
    """Tab for browsing generated 3D assets in the asset directory."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = Config.from_env()
        self._selected_path = None
        self._thumb_widgets = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QtWidgets.QHBoxLayout()

        self._path_label = QtWidgets.QLabel()
        self._path_label.setStyleSheet(f"color: {style.TEXT_SECONDARY}; font-size: 10px;")
        toolbar.addWidget(self._path_label)

        toolbar.addStretch()

        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        open_dir_btn = QtWidgets.QPushButton("Open Folder")
        open_dir_btn.clicked.connect(self._open_asset_dir)
        toolbar.addWidget(open_dir_btn)

        layout.addLayout(toolbar)

        # Asset grid (scroll area)
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._grid_container = QtWidgets.QWidget()
        self._grid_layout = QtWidgets.QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(8)
        self._grid_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self._scroll.setWidget(self._grid_container)
        layout.addWidget(self._scroll)

        # Info panel
        info_group = QtWidgets.QGroupBox("Asset Info")
        info_layout = QtWidgets.QFormLayout(info_group)
        self._info_name = QtWidgets.QLabel("-")
        self._info_provider = QtWidgets.QLabel("-")
        self._info_size = QtWidgets.QLabel("-")
        self._info_date = QtWidgets.QLabel("-")
        info_layout.addRow("Name:", self._info_name)
        info_layout.addRow("Provider:", self._info_provider)
        info_layout.addRow("Size:", self._info_size)
        info_layout.addRow("Modified:", self._info_date)
        layout.addWidget(info_group)

        # Action buttons
        btn_layout = QtWidgets.QHBoxLayout()

        self._import_btn = QtWidgets.QPushButton("Import to Maya")
        self._import_btn.setEnabled(False)
        self._import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(self._import_btn)

        self._delete_btn = QtWidgets.QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        self._delete_btn.setStyleSheet(f"color: {style.ERROR};")
        self._delete_btn.clicked.connect(self._on_delete)
        btn_layout.addWidget(self._delete_btn)

        layout.addLayout(btn_layout)

    def refresh(self):
        """Scan asset directory and rebuild the grid."""
        asset_dir = self._config.provider.asset_dir
        self._path_label.setText(str(asset_dir))

        # Clear existing widgets
        for w in self._thumb_widgets:
            w.setParent(None)
            w.deleteLater()
        self._thumb_widgets.clear()
        self._selected_path = None
        self._import_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._clear_info()

        if not asset_dir.exists():
            return

        # Collect asset files sorted by modification time (newest first)
        assets = []
        for f in asset_dir.iterdir():
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
                assets.append(f)
        assets.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Build grid (4 columns)
        cols = 4
        for i, asset_path in enumerate(assets):
            widget = AssetThumbnailWidget(str(asset_path))
            widget.clicked.connect(self._on_asset_clicked)
            self._grid_layout.addWidget(widget, i // cols, i % cols)
            self._thumb_widgets.append(widget)

    def _on_asset_clicked(self, path: str):
        self._selected_path = path

        # Update selection visual
        for w in self._thumb_widgets:
            w.set_selected(w.asset_path == path)

        # Update info panel
        p = Path(path)
        self._info_name.setText(p.name)
        self._info_provider.setText(self._guess_provider(p.name))

        stat = p.stat()
        size_kb = stat.st_size / 1024
        if size_kb > 1024:
            self._info_size.setText(f"{size_kb / 1024:.1f} MB")
        else:
            self._info_size.setText(f"{size_kb:.1f} KB")

        mod_time = datetime.fromtimestamp(stat.st_mtime)
        self._info_date.setText(mod_time.strftime("%Y-%m-%d %H:%M"))

        self._import_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)

    def _guess_provider(self, filename: str) -> str:
        lower = filename.lower()
        for prefix, display_name in PROVIDER_PREFIXES.items():
            if lower.startswith(prefix):
                return display_name
        return "Unknown"

    def _clear_info(self):
        self._info_name.setText("-")
        self._info_provider.setText("-")
        self._info_size.setText("-")
        self._info_date.setText("-")

    def _on_import(self):
        if not self._selected_path:
            return

        path = Path(self._selected_path)
        ext = path.suffix.lower()
        path_str = str(path).replace("\\", "/")

        try:
            if ext == ".fbx":
                cmds.loadPlugin("fbxmaya", quiet=True)
                cmds.file(
                    path_str, i=True, type="FBX",
                    ignoreVersion=True, mergeNamespacesOnClash=False,
                    options="fbx",
                )
            elif ext == ".obj":
                cmds.loadPlugin("objExport", quiet=True)
                cmds.file(
                    path_str, i=True, type="OBJ",
                    ignoreVersion=True, options="mo=1",
                )
            else:
                cmds.warning(f"Unsupported format for direct import: {ext}")
                return

            cmds.inViewMessage(
                amg=f"Imported: {path.name}",
                pos="topCenter", fade=True,
            )
        except Exception as e:
            cmds.warning(f"Import failed: {e}")

    def _on_delete(self):
        if not self._selected_path:
            return

        result = cmds.confirmDialog(
            title="Delete Asset",
            message=f"Delete {Path(self._selected_path).name}?",
            button=["Delete", "Cancel"],
            defaultButton="Cancel",
            cancelButton="Cancel",
            dismissString="Cancel",
        )
        if result == "Delete":
            try:
                os.remove(self._selected_path)
                self.refresh()
            except OSError as e:
                cmds.warning(f"Delete failed: {e}")

    def _open_asset_dir(self):
        asset_dir = str(self._config.provider.asset_dir)
        import subprocess
        subprocess.Popen(["open", asset_dir])
