"""MCP Connection management tab."""

import socket
from datetime import datetime

import maya.cmds as cmds

from . import QtWidgets, QtCore
from . import style
from .widgets import StatusIndicator


class ConnectionTab(QtWidgets.QWidget):
    """Tab for managing Maya commandPort and viewing connection status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_port = None
        self._build_ui()
        self._start_heartbeat()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        # Port controls
        port_group = QtWidgets.QGroupBox("commandPort")
        port_layout = QtWidgets.QHBoxLayout(port_group)

        port_layout.addWidget(QtWidgets.QLabel("Port:"))
        self._port_spin = QtWidgets.QSpinBox()
        self._port_spin.setRange(1024, 65535)
        self._port_spin.setValue(7001)
        port_layout.addWidget(self._port_spin)

        self._start_btn = QtWidgets.QPushButton("Start")
        self._start_btn.clicked.connect(self._on_start)
        port_layout.addWidget(self._start_btn)

        self._stop_btn = QtWidgets.QPushButton("Stop")
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)
        port_layout.addWidget(self._stop_btn)

        layout.addWidget(port_group)

        # Status display
        status_layout = QtWidgets.QHBoxLayout()
        self._indicator = StatusIndicator()
        status_layout.addWidget(self._indicator)
        self._status_label = QtWidgets.QLabel("Disconnected")
        self._status_label.setStyleSheet(f"color: {style.ERROR}; font-weight: bold;")
        status_layout.addWidget(self._status_label)
        status_layout.addStretch()
        layout.addLayout(status_layout)

        # Log viewer
        log_group = QtWidgets.QGroupBox("Log")
        log_layout = QtWidgets.QVBoxLayout(log_group)

        self._log = QtWidgets.QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(1000)
        self._log.setStyleSheet(
            f"font-family: monospace; font-size: 11px; "
            f"background: {style.BG_INPUT}; color: {style.TEXT_PRIMARY};"
        )
        log_layout.addWidget(self._log)

        clear_btn = QtWidgets.QPushButton("Clear Log")
        clear_btn.clicked.connect(self._log.clear)
        log_layout.addWidget(clear_btn)

        layout.addWidget(log_group)

    def _on_start(self):
        port = self._port_spin.value()
        port_name = f":{port}"
        try:
            # Close existing if open
            try:
                cmds.commandPort(name=port_name, close=True)
            except RuntimeError:
                pass

            cmds.commandPort(name=port_name, sourceType="python", echoOutput=True)
            self._active_port = port
            self._start_btn.setEnabled(False)
            self._stop_btn.setEnabled(True)
            self._port_spin.setEnabled(False)
            self._append_log(f"commandPort started on port {port}")
            self._update_status(True)
        except RuntimeError as e:
            self._append_log(f"ERROR: Failed to start port {port}: {e}")
            self._update_status(False)

    def _on_stop(self):
        if self._active_port is None:
            return
        port_name = f":{self._active_port}"
        try:
            cmds.commandPort(name=port_name, close=True)
            self._append_log(f"commandPort on port {self._active_port} closed")
        except RuntimeError:
            pass
        self._active_port = None
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._port_spin.setEnabled(True)
        self._update_status(False)

    def _update_status(self, connected: bool):
        self._indicator.set_connected(connected)
        if connected:
            self._status_label.setText(f"Connected (port {self._active_port})")
            self._status_label.setStyleSheet(f"color: {style.SUCCESS}; font-weight: bold;")
        else:
            self._status_label.setText("Disconnected")
            self._status_label.setStyleSheet(f"color: {style.ERROR}; font-weight: bold;")

    def _append_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log.appendPlainText(f"[{timestamp}] {message}")

    def _start_heartbeat(self):
        self._heartbeat_timer = QtCore.QTimer(self)
        self._heartbeat_timer.timeout.connect(self._check_connection)
        self._heartbeat_timer.start(5000)

    def _check_connection(self):
        if self._active_port is None:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.connect(("localhost", self._active_port))
            sock.close()
            self._update_status(True)
        except (socket.error, OSError):
            self._append_log("WARNING: Connection lost")
            self._update_status(False)

    def cleanup(self):
        """Stop heartbeat timer."""
        if hasattr(self, "_heartbeat_timer"):
            self._heartbeat_timer.stop()
