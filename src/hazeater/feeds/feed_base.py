from abc import ABC, abstractmethod
from typing import Iterable, Optional
from hazeater.core.types import Bar


class FeedBase(ABC):
    """フォワード/バックテスト共通のデータ供給インターフェース"""

    @abstractmethod
    def get_next_bar(self) -> Optional[Bar]:
        """次のバーを1本返す（データ終端なら None）"""
        ...


    def iter_bars(self) -> Iterable[Bar]:
        """バックテスト用：最後まで順に流す"""
        while True:
            bar = self.get_next_bar()
            if bar is None:
                break
            yield bar
