import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ScreenshotFrame:
    index: int
    step: int
    tool: str
    url: str
    title: str
    image_b64: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "index":     self.index,
            "step":      self.step,
            "tool":      self.tool,
            "url":       self.url,
            "title":     self.title,
            "image":     self.image_b64,
            "timestamp": self.timestamp,
        }


class ScreenshotRecorder:
    def __init__(self):
        self._frames: List[ScreenshotFrame] = []

    def record(self, step: int, tool: str, url: str, title: str, image_b64: str) -> ScreenshotFrame:
        frame = ScreenshotFrame(
            index=len(self._frames),
            step=step,
            tool=tool,
            url=url,
            title=title,
            image_b64=image_b64,
        )
        self._frames.append(frame)
        return frame

    def get(self, index: int) -> Optional[ScreenshotFrame]:
        if 0 <= index < len(self._frames):
            return self._frames[index]
        return None

    def count(self) -> int:
        return len(self._frames)

    def to_list(self) -> List[Dict]:
        return [f.to_dict() for f in self._frames]

    @property
    def frames(self) -> List[ScreenshotFrame]:
        return list(self._frames)
