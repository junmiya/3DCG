"""Tests for Maya commandPort client."""

import json
import socket
import threading
import time

import pytest

from maya_mcp.config import MayaConfig
from maya_mcp.maya_client import MayaClient, MayaConnectionError


class FakeMayaServer:
    """Minimal TCP server that mimics Maya's commandPort behavior."""

    def __init__(self, host: str = "localhost", port: int = 0):
        self._host = host
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((host, port))
        self._server.listen(5)
        self.port = self._server.getsockname()[1]
        self._running = False
        self._thread = None
        self._stored_result = ""

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._server.close()
        if self._thread:
            self._thread.join(timeout=2)

    def _serve(self):
        while self._running:
            try:
                self._server.settimeout(0.5)
                conn, _ = self._server.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle(self, conn: socket.socket):
        try:
            data = conn.recv(8192).decode("utf-8").strip()

            if "_mcp_exec" in data:
                # Command connection: store a simulated result
                self._stored_result = '"test_result"'
                conn.sendall(b"")
            elif data == "_mcp_result":
                # Result connection: return stored result
                conn.sendall(self._stored_result.encode("utf-8"))
            elif "json.dumps" in data:
                # Simple query that returns JSON
                self._stored_result = json.dumps({"test": True})
                conn.sendall(b"")
            else:
                conn.sendall(data.encode("utf-8"))
        except Exception:
            pass
        finally:
            conn.close()


@pytest.fixture
def fake_maya():
    server = FakeMayaServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def client(fake_maya):
    config = MayaConfig(host="localhost", port=fake_maya.port, command_timeout=5.0)
    return MayaClient(config)


class TestMayaClient:
    def test_is_connected(self, client):
        assert client.is_connected() is True

    def test_is_not_connected_wrong_port(self):
        config = MayaConfig(host="localhost", port=19999, command_timeout=1.0)
        c = MayaClient(config)
        assert c.is_connected() is False

    def test_connect_with_retry_success(self, client):
        assert client.connect_with_retry(max_retries=1) is True

    def test_connect_with_retry_failure(self):
        config = MayaConfig(host="localhost", port=19999, command_timeout=0.5)
        c = MayaClient(config)
        assert c.connect_with_retry(max_retries=1, base_delay=0.1) is False

    def test_execute(self, client):
        result = client.execute('return "hello"')
        # The fake server returns "test_result" for _mcp_exec commands
        assert result is not None


class TestMayaConnectionError:
    def test_connection_refused(self):
        config = MayaConfig(host="localhost", port=19999, command_timeout=1.0)
        c = MayaClient(config)
        with pytest.raises(MayaConnectionError):
            c.execute('return "test"')
