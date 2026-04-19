"""Maya commandPort TCP communication client using sentinel-based protocol."""

import json
import logging
import socket
import textwrap
import time
import uuid
from typing import Any

from .config import MayaConfig

logger = logging.getLogger(__name__)


class MayaConnectionError(Exception):
    """Raised when connection to Maya fails."""


class MayaCommandError(Exception):
    """Raised when a Maya command execution fails."""


# Sentinel markers used to reliably parse Maya's commandPort response.
# commandPort returns both the expression return value and stdout output,
# with no terminator, so we wrap every payload in markers we control and
# extract exactly the bytes between them.
_BEGIN = "<<<MCP_BEGIN>>>"
_END = "<<<MCP_END>>>"


class MayaClient:
    """Client for communicating with Maya via commandPort (TCP).

    Protocol:
      1. Open a single TCP connection to Maya commandPort.
      2. Send Python code wrapped in a function that `return`s a value.
         The wrapper prints `<<<MCP_BEGIN>>>{value}<<<MCP_END>>>`.
      3. Keep recv()ing until the END sentinel appears in the buffer.
      4. Extract the payload between the sentinels.
    """

    # Short idle timeout used as a fallback if the END sentinel never arrives.
    _IDLE_TIMEOUT = 0.5

    def __init__(self, config: MayaConfig | None = None):
        self.config = config or MayaConfig()
        self._host = self.config.host
        self._port = self.config.port
        self._timeout = self.config.command_timeout

    # ── connection ────────────────────────────────────────────────────

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

    # ── low-level send/recv ───────────────────────────────────────────

    def _send(self, sock: socket.socket, code: str) -> None:
        """Send a single block of Python code to Maya."""
        sock.sendall(code.encode("utf-8") + b"\n")

    def _recv_until_sentinel(self, sock: socket.socket, end_marker: str) -> str:
        """Read from the socket until `end_marker` is seen, or timeout."""
        buffer = bytearray()
        deadline = time.monotonic() + self._timeout
        sock.settimeout(self._IDLE_TIMEOUT)
        end_bytes = end_marker.encode("utf-8")

        while True:
            if end_bytes in buffer:
                break
            if time.monotonic() > deadline:
                logger.warning(
                    "Maya response timed out waiting for sentinel %r", end_marker
                )
                break
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                # No data for _IDLE_TIMEOUT; loop and check deadline.
                continue
            if not chunk:
                # Maya closed the connection.
                break
            buffer.extend(chunk)

        return buffer.decode("utf-8", errors="replace")

    # ── high-level execute ────────────────────────────────────────────

    def execute(self, code: str) -> str:
        """Execute Python code in Maya and return its result as a string.

        The `code` must be a block that uses `return` to produce a value,
        as in the existing tool implementations. The wrapper executes it
        inside a function, catches exceptions, and prints the result
        between unique sentinels for reliable extraction.
        """
        call_id = uuid.uuid4().hex[:8]
        begin = f"{_BEGIN}:{call_id}"
        end = f"{_END}:{call_id}"

        # Normalize user code: strip outer blank lines and any common
        # leading whitespace so we control indentation ourselves.
        user_body = textwrap.dedent(code).strip("\n")
        if not user_body.strip():
            # Protect against empty input creating a `try:` with no body.
            user_body = "return None"

        # Indent user body by 8 spaces so it sits inside `try:` which
        # itself is inside `def _mcp_exec():` (4-space indent).
        indented_body = textwrap.indent(user_body, "        ")

        # Build the wrapper with explicit string concatenation.
        # We intentionally avoid `textwrap.dedent(f"""...""")` here: it
        # mis-detects the common leading whitespace when `indented_body`
        # contains deeper indents than the surrounding skeleton, which
        # would corrupt the resulting Python source.
        wrapped = (
            "def _mcp_exec():\n"
            "    import json as _json\n"
            "    import traceback as _tb\n"
            "    try:\n"
            f"{indented_body}\n"
            "    except Exception as _e:\n"
            "        return _json.dumps({\n"
            '            "error": str(_e),\n'
            '            "traceback": _tb.format_exc(),\n'
            "        })\n"
            "\n"
            "_mcp_val = _mcp_exec()\n"
            "_mcp_payload = '' if _mcp_val is None else str(_mcp_val)\n"
            "import sys as _sys\n"
            f"_sys.stdout.write('{begin}' + _mcp_payload + '{end}' + '\\n')\n"
            "_sys.stdout.flush()\n"
            "del _mcp_exec, _mcp_val, _mcp_payload\n"
        )

        sock = self._connect()
        try:
            self._send(sock, wrapped)
            raw = self._recv_until_sentinel(sock, end)
        finally:
            sock.close()

        try:
            start_idx = raw.index(begin) + len(begin)
            end_idx = raw.index(end, start_idx)
        except ValueError:
            logger.error(
                "Maya response missing sentinels. Raw (first 500 chars): %r",
                raw[:500],
            )
            raise MayaCommandError(
                "Maya did not return a valid response. Check that the "
                "commandPort is open and that Maya processed the command "
                "without fatal errors."
            )
        return raw[start_idx:end_idx]

    def execute_mel(self, command: str) -> str:
        """Execute a MEL command in Maya."""
        code = (
            "import maya.mel as mel\n"
            f"result = mel.eval({command!r})\n"
            'return str(result) if result is not None else ""\n'
        )
        return self.execute(code)

    def execute_python(self, code: str) -> str:
        """Execute arbitrary Python code in Maya and return captured stdout."""
        indented = textwrap.indent(textwrap.dedent(code), "    ")
        wrapped = (
            "import io, sys\n"
            "_mcp_buf = io.StringIO()\n"
            "_mcp_old_stdout = sys.stdout\n"
            "sys.stdout = _mcp_buf\n"
            "try:\n"
            f"{indented}\n"
            "finally:\n"
            "    sys.stdout = _mcp_old_stdout\n"
            "return _mcp_buf.getvalue()\n"
        )
        return self.execute(wrapped)

    def query(self, code: str) -> Any:
        """Execute code and parse the JSON-encoded result."""
        result = self.execute(code)
        if not result:
            return None
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            # Return raw string if not valid JSON.
            return result
        if isinstance(parsed, dict) and "error" in parsed:
            raise MayaCommandError(
                f"Maya error: {parsed['error']}\n{parsed.get('traceback', '')}"
            )
        return parsed

    # ── diagnostics ───────────────────────────────────────────────────

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