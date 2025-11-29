from abc import ABC, abstractmethod
from typing import Sequence, Optional

from hazeater.core.types import Bar, OrderSpec, ExitDecision, Position


class StrategyBase(ABC):

    @abstractmethod
    def decide_entry(
            self,
            bars: Sequence[Bar],
            equity: float,
            positions: Sequence[Position],
    ) -> Optional[OrderSpec]:
        """
        エントリーするなら OrderSpec を返す。
        positions には現在のオープンポジション一覧が渡されるので、
        「何ポジまで建てるか」「既存ポジションと同方向か」などをここで判断できる。
        """
        ...

    @abstractmethod
    def decide_exit(
            self,
            bars: Sequence[Bar],
            equity: float,
            position: Position
    ) -> Optional[ExitDecision]:
        """ExitRule を組み込んで ExitDecision を返す"""
        ...
