from abc import ABC, abstractmethod
from typing import Optional, Sequence
from hazeater.core.types import Bar, OrderSpec, Position, ExitDecision


class BrokerBase(ABC):
    """フォワード/バックテスト共通の注文実行インターフェース"""

    @abstractmethod
    def get_equity(self) -> float:
        ...

    @abstractmethod
    def get_positions(self, symbol: Optional[str] = None) -> Sequence[Position]:
        """
        現在のオープンポジション一覧。
        symbol を指定すればそのシンボルだけに絞る。
        """
        ...

    def get_position(self, symbol: str) -> Optional[Position]:
        positions = self.get_positions(symbol)
        return positions[0] if positions else None

    @abstractmethod
    def execute_entry(self, order: OrderSpec, bar: Bar) -> None:
        """
        成行 or 指値などで新規エントリー
        - Backtest: bar.close で即約定
        - MT5: bar はログ用
        """
        ...

    @abstractmethod
    def apply_exit_decision(self, position: Position, decision: ExitDecision, bar: Bar) -> None:
        """
        特定の Position に対する ExitDecision を解釈して、
        実際のブローカー(MT5, バックテストなど)に反映する。
        """
        ...
