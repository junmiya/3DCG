"""Reusable custom widgets for Maya MCP Panel."""

from pathlib import Path

from . import QtWidgets, QtCore, QtGui
from . import style


class StatusIndicator(QtWidgets.QWidget):
    """A small circle indicator showing connected (green) or disconnected (red)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._connected = False

    def set_connected(self, connected: bool):
        self._connected = connected
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        color = QtGui.QColor(style.SUCCESS if self._connected else style.ERROR)
        painter.setBrush(color)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()


class ImageDropZone(QtWidgets.QLabel):
    """A label that accepts drag-and-drop of image files or click to browse."""

    image_selected = QtCore.Signal(str)

    SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".tiff", ".tif"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_path = None
        self.setAcceptDrops(True)
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.setMinimumHeight(120)
        self.setStyleSheet(
            f"border: 2px dashed {style.BORDER}; "
            f"background: {style.BG_INPUT}; "
            f"color: {style.TEXT_SECONDARY}; "
            f"border-radius: 4px;"
        )
        self._set_placeholder()

    def _set_placeholder(self):
        self.setText("Drop image here\nor click to browse")
        self.image_path = None

    def clear_image(self):
        self._set_placeholder()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, "Select Image", "",
                "Images (*.png *.jpg *.jpeg *.bmp *.tga *.tiff *.tif)"
            )
            if path:
                self._load_image(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if Path(url.toLocalFile()).suffix.lower() in self.SUPPORTED_EXTS:
                event.acceptProposedAction()
                self.setStyleSheet(
                    f"border: 2px solid {style.ACCENT}; "
                    f"background: {style.BG_INPUT}; "
                    f"color: {style.TEXT_PRIMARY}; "
                    f"border-radius: 4px;"
                )

    def dragLeaveEvent(self, event):
        self.setStyleSheet(
            f"border: 2px dashed {style.BORDER}; "
            f"background: {style.BG_INPUT}; "
            f"color: {style.TEXT_SECONDARY}; "
            f"border-radius: 4px;"
        )

    def dropEvent(self, event):
        url = event.mimeData().urls()[0]
        self._load_image(url.toLocalFile())

    def _load_image(self, path: str):
        self.image_path = path
        pixmap = QtGui.QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                self.width() - 8, self.height() - 8,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation,
            )
            self.setPixmap(scaled)
        else:
            self.setText(Path(path).name)
        self.setStyleSheet(
            f"border: 2px solid {style.SUCCESS}; "
            f"background: {style.BG_INPUT}; "
            f"color: {style.TEXT_PRIMARY}; "
            f"border-radius: 4px;"
        )
        self.image_selected.emit(path)


class AssetThumbnailWidget(QtWidgets.QFrame):
    """A clickable card showing an asset thumbnail and filename."""

    clicked = QtCore.Signal(str)

    def __init__(self, asset_path: str, parent=None):
        super().__init__(parent)
        self.asset_path = asset_path
        self._selected = False
        self.setFixedSize(130, 150)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._build_ui()
        self._update_style()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Thumbnail placeholder
        self._thumb = QtWidgets.QLabel()
        self._thumb.setFixedSize(120, 100)
        self._thumb.setAlignment(QtCore.Qt.AlignCenter)
        self._thumb.setStyleSheet(f"background: {style.BG_INPUT}; border: none;")

        ext = Path(asset_path).suffix.lower()
        ext_label = ext.replace(".", "").upper()
        self._thumb.setText(f"[{ext_label}]")
        self._thumb.setStyleSheet(
            f"background: {style.BG_INPUT}; color: {style.ACCENT}; "
            f"font-size: 16px; font-weight: bold; border: none;"
        )

        # Filename
        self._name = QtWidgets.QLabel(Path(asset_path).name)
        self._name.setAlignment(QtCore.Qt.AlignCenter)
        self._name.setWordWrap(True)
        self._name.setStyleSheet(f"color: {style.TEXT_PRIMARY}; font-size: 10px; border: none;")
        self._name.setMaximumHeight(36)

        layout.addWidget(self._thumb)
        layout.addWidget(self._name)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        border_color = style.ACCENT if self._selected else style.BORDER
        self.setStyleSheet(
            f"AssetThumbnailWidget {{ background: {style.BG_SECONDARY}; "
            f"border: 2px solid {border_color}; border-radius: 4px; }}"
        )

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.asset_path)
