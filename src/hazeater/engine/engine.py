from collections import deque
from typing import Deque

from hazeater.broker.broker_base import BrokerBase
from hazeater.core.types import Bar, OrderSpec, ExitDecision
from hazeater.feeds import FeedBase
from hazeater.strategy.strategy_base import StrategyBase


def run_loop(
        feed: FeedBase,
        broker: BrokerBase,
        strategy: StrategyBase,
        symbol: str,
        window_size: int,
) -> None:
    bars: Deque[Bar] = deque(maxlen=window_size)

    for bar in feed.iter_bars():
        bars.append(bar)
        if len(bars) < window_size:
            continue

        # ===== Exit 判定 =====
        equity = broker.get_equity()
        positions = broker.get_positions(symbol)

        # 既存ポジションに対する Exit 判定（複数ポジ）
        bars_list = list(bars)
        for pos in list(positions):
            decision: ExitDecision | None = strategy.decide_exit(
                bars=bars_list,
                equity=equity,
                position=pos,
            )
            if decision is not None:
                broker.apply_exit_decision(pos, decision, bar)

        # ===== Entry 判定 =====
        equity = broker.get_equity()  # Exit 後の残高を取り直す
        positions = broker.get_positions(symbol)

        order: OrderSpec | None = strategy.decide_entry(
            bars=bars_list,
            equity=equity,
            positions=positions,
        )
        if order is not None:
            broker.execute_entry(order, bar)
