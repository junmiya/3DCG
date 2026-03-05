"""Animation tools."""

from ..maya_client import MayaClient


class AnimationTools:
    """Tools for Maya animation operations."""

    def __init__(self, maya_client: MayaClient):
        self._maya = maya_client

    def set_keyframe(
        self,
        name: str,
        attribute: str,
        time: float,
        value: float,
    ) -> dict:
        """Set a keyframe on an object attribute.

        Args:
            name: Object name.
            attribute: Attribute name (e.g., translateX, rotateY, scaleZ).
            time: Frame number.
            value: Attribute value at this keyframe.
        """
        code = f"""\
import maya.cmds as cmds
import json
if not cmds.objExists("{name}"):
    return json.dumps({{"error": "Object not found: {name}"}})
cmds.setKeyframe("{name}", attribute="{attribute}", time={time}, value={value})
return json.dumps({{"name": "{name}", "attribute": "{attribute}", "time": {time}, "value": {value}}})
"""
        return self._maya.query(code)

    def set_playback_range(self, start: float, end: float) -> dict:
        """Set the animation playback range."""
        code = f"""\
import maya.cmds as cmds
import json
cmds.playbackOptions(min={start}, max={end})
cmds.playbackOptions(animationStartTime={start}, animationEndTime={end})
return json.dumps({{"start": {start}, "end": {end}}})
"""
        return self._maya.query(code)

    def play_animation(self, forward: bool = True) -> dict:
        """Start animation playback."""
        code = f"""\
import maya.cmds as cmds
cmds.play(forward={forward})
return "Playing {'forward' if {forward} else 'backward'}"
"""
        return {"result": self._maya.execute(code)}
