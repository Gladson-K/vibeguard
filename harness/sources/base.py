"""Frame source contract shared by simulated, SIL and replay nodes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable


class FrameSource(ABC):
    @abstractmethod
    def frames(self) -> Iterable[dict]:
        """Yield feature frames ready to POST to the gateway."""
