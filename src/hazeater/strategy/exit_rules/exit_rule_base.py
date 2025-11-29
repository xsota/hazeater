from abc import ABC, abstractmethod
from typing import Sequence, Optional

from hazeater.core.types import Bar, Position, ExitDecision


class ExitRuleBase(ABC):
    @abstractmethod
    def decide(
            self,
            bars: Sequence[Bar],
            equity: float,
            position: Position,
    ) -> Optional[ExitDecision]:
        """
        - 何もしない → None or ExitDecision(HOLD)
        - クローズしたい → ExitDecision(CLOSE, ...)
        - SL/TPだけ動かしたい → ExitDecision(UPDATE_SL_TP, new_sl=..., new_tp=...)
        """
        ...
