from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Optional, Iterable

import MetaTrader5 as mt5
import pandas as pd

from hazeater.core.types import Bar
from hazeater.feeds import FeedBase
from hazeater.timeframes import TIMEFRAME_MAP, TimeframeName


class Mt5Feed(FeedBase):
    """
    MT5 からバーを取得する Feed。

    - バックテスト: start/end を指定するとヒストリカルを一括取得し、順次返す
    - ライブ: end を省略すると、ウォームアップ後に新規バーが出るまでポーリングして返す（終端 None は返さない）
    """

    def __init__(
            self,
            symbol: str,
            timeframe: TimeframeName | int,
            start: datetime,
            end: Optional[datetime] = None,
            *,
            poll_interval: float = 1.0,
    ) -> None:
        self.symbol = symbol
        self.timeframe = self._resolve_timeframe(timeframe)
        self.poll_interval = poll_interval
        self.live_mode = end is None
        self._buffer: list[Bar] = []
        self._buffer_idx = 0

        self._mt5_init()

        # 最初のヒストリカルを取得（ライブ時はウォームアップを兼ねる）
        initial_end = end or datetime.utcnow()
        init_rates = mt5.copy_rates_range(symbol, self.timeframe, start, initial_end)
        if init_rates is None:
            code, msg = mt5.last_error()
            raise RuntimeError(f"MT5 copy_rates_range failed: {code} {msg}")

        self._buffer = self._rates_to_bars(init_rates)
        self._last_time: Optional[datetime] = None
        if self._buffer:
            self._last_time = self._buffer[-1].time

        self._ended = False  # バックテスト用

    def __del__(self) -> None:
        try:
            mt5.shutdown()
        except Exception:
            # shutdown で例外が出ても握りつぶす
            pass

    def _mt5_init(self) -> None:
        if not mt5.initialize():
            code, msg = mt5.last_error()
            raise RuntimeError(f"MT5 init failed: {code} {msg}")

    def _resolve_timeframe(self, tf: TimeframeName | int) -> int:
        if isinstance(tf, str):
            if tf not in TIMEFRAME_MAP:
                raise ValueError(f"Unsupported timeframe name: {tf}")
            return TIMEFRAME_MAP[tf]
        return tf

    def _rates_to_bars(self, rates: Iterable[dict]) -> list[Bar]:
        df = pd.DataFrame(rates)
        if df.empty:
            return []
        df["time"] = pd.to_datetime(df["time"], unit="s")

        bars: list[Bar] = []
        for row in df.itertuples(index=False):
            bars.append(
                Bar(
                    time=row.time,
                    open=float(row.open),
                    high=float(row.high),
                    low=float(row.low),
                    close=float(row.close),
                    spread=float(getattr(row, "spread", 0.0)),
                    tick_volume=float(getattr(row, "tick_volume", getattr(row, "real_volume", 0.0))),
                    real_volume=float(row.real_volume) if hasattr(row, "real_volume") else None,
                )
            )
        return bars

    def _fetch_new_bars_live(self) -> None:
        if self._last_time is None:
            return

        # 直近から現在までを取得して、新しいバーだけ残す
        now = datetime.utcnow() + timedelta(seconds=1)  # 端数切り上げ
        rates = mt5.copy_rates_range(self.symbol, self.timeframe, self._last_time, now)
        if rates is None:
            return

        new_bars = self._rates_to_bars(rates)
        new_bars = [b for b in new_bars if b.time > self._last_time]
        if new_bars:
            self._last_time = new_bars[-1].time
            self._buffer.extend(new_bars)

    def get_next_bar(self) -> Optional[Bar]:
        """
        - バックテスト: バッファを順に返し、終端で None
        - ライブ: 新規バーが到着するまでポーリングして返す（終端は返さない）
        """
        # バッファに残っていればそれを返す
        if self._buffer_idx < len(self._buffer):
            bar = self._buffer[self._buffer_idx]
            self._buffer_idx += 1
            return bar

        # バックテストはここで終了
        if not self.live_mode:
            if not self._ended:
                self._ended = True
                mt5.shutdown()
            return None

        # ライブモード: 新しいバーが来るまでポーリング
        while True:
            self._fetch_new_bars_live()
            if self._buffer_idx < len(self._buffer):
                bar = self._buffer[self._buffer_idx]
                self._buffer_idx += 1
                return bar
            time.sleep(self.poll_interval)
