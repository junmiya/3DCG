"""General-purpose command execution tools."""

from ..maya_client import MayaClient


class GeneralTools:
    """Tools for executing arbitrary commands in Maya."""

    def __init__(self, maya_client: MayaClient):
        self._maya = maya_client

    def execute_python(self, code: str) -> dict:
        """Execute arbitrary Python code in Maya.

        ⚠️ This tool executes arbitrary code. Use with caution.

        Args:
            code: Python code to execute in Maya's Python interpreter.

        Returns:
            Dict with stdout output from the execution.
        """
        result = self._maya.execute_python(code)
        return {"output": result}

    def execute_mel(self, command: str) -> dict:
        """Execute a MEL command in Maya.

        ⚠️ This tool executes arbitrary commands. Use with caution.

        Args:
            command: MEL command string to execute.

        Returns:
            Dict with the command result.
        """
        result = self._maya.execute_mel(command)
        return {"output": result}
