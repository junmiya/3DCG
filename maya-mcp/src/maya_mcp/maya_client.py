"""Maya commandPort TCP communication client using dual-connection pattern."""

import json
import logging
import socket
import textwrap
import time
from typing import Any

from .config import MayaConfig

logger = logging.getLogger(__name__)


class MayaConnectionError(Exception):
    """Raised when connection to Maya fails."""


class MayaCommandError(Exception):
    """Raised when a Maya command execution fails."""


class MayaClient:
    """Client for communicating with Maya via commandPort (TCP).

    Uses the dual-connection pattern:
      - Connection 1 (command): sends code that stores result in _mcp_result
      - Connection 2 (result): reads back _mcp_result
    """

    def __init__(self, config: MayaConfig | None = None):
        self.config = config or MayaConfig()
        self._host = self.config.host
        self._port = self.config.port
        self._timeout = self.config.command_timeout

    def _connect(self) -> socket.socket:
        """Create a TCP connection to Maya's commandPort."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self._timeout)
        try:
            sock.connect((self._host, self._port))
        except (ConnectionRefusedError, OSError) as e:
            sock.close()
            raise MayaConnectionError(
                f"Cannot connect to Maya at {self._host}:{self._port}. "
                "Ensure Maya is running and commandPort is open."
            ) from e
        return sock

    def _send_and_recv(self, sock: socket.socket, data: str) -> str:
        """Send data to socket and receive response."""
        sock.sendall(data.encode("utf-8") + b"\n")
        # Read response in chunks
        chunks: list[bytes] = []
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
                # If we received less than buffer size, likely done
                if len(chunk) < 4096:
                    break
            except socket.timeout:
                break
        return b"".join(chunks).decode("utf-8").strip()

    def execute(self, code: str) -> str:
        """Execute Python code in Maya and return the result as string.

        Uses dual-connection pattern for reliable result retrieval.
        """
        # Wrap code in a scoped function to avoid namespace pollution
        wrapped = textwrap.dedent(f"""\
            def _mcp_exec():
                import json as _json
                import traceback as _tb
                try:
            {textwrap.indent(textwrap.dedent(code), "        ")}
                except Exception as _e:
                    return _json.dumps({{"error": str(_e), "traceback": _tb.format_exc()}})
            _mcp_result = _mcp_exec()
            del _mcp_exec""")

        conn_cmd = None
        conn_res = None
        try:
            conn_cmd = self._connect()
            conn_res = self._connect()

            # Connection 1: execute the code
            self._send_and_recv(conn_cmd, wrapped)

            # Small delay to allow Maya to process
            time.sleep(0.05)

            # Connection 2: retrieve result
            result = self._send_and_recv(conn_res, "_mcp_result")

            return result
        finally:
            if conn_cmd:
                conn_cmd.close()
            if conn_res:
                conn_res.close()

    def execute_mel(self, command: str) -> str:
        """Execute a MEL command in Maya."""
        code = f"""\
import maya.mel as mel
result = mel.eval({command!r})
return str(result) if result is not None else ""
"""
        return self.execute(code)

    def execute_python(self, code: str) -> str:
        """Execute arbitrary Python code in Maya and return stdout + result."""
        wrapped = f"""\
import io, sys
_mcp_buf = io.StringIO()
_mcp_old_stdout = sys.stdout
sys.stdout = _mcp_buf
try:
{textwrap.indent(code, "    ")}
finally:
    sys.stdout = _mcp_old_stdout
_mcp_output = _mcp_buf.getvalue()
return _mcp_output if _mcp_output else ""
"""
        return self.execute(wrapped)

    def query(self, code: str) -> Any:
        """Execute code and parse the JSON result."""
        result = self.execute(code)
        if not result:
            return None
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "error" in parsed:
                raise MayaCommandError(
                    f"Maya error: {parsed['error']}\n{parsed.get('traceback', '')}"
                )
            return parsed
        except json.JSONDecodeError:
            # Return raw string if not valid JSON
            return result

    def is_connected(self) -> bool:
        """Check if Maya is reachable."""
        try:
            sock = self._connect()
            sock.close()
            return True
        except MayaConnectionError:
            return False

    def connect_with_retry(self, max_retries: int = 3, base_delay: float = 1.0) -> bool:
        """Try to connect to Maya with exponential backoff."""
        for attempt in range(max_retries):
            if self.is_connected():
                logger.info("Connected to Maya at %s:%d", self._host, self._port)
                return True
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Maya connection attempt %d/%d failed, retrying in %.1fs",
                attempt + 1, max_retries, delay,
            )
            time.sleep(delay)
        return False
