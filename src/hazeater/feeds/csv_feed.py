from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from hazeater.core.types import Bar
from hazeater.feeds import FeedBase


class CsvFeed(FeedBase):
    """
    CSV から Bar を順番に返すバックテスト用 Feed。

    必須カラム:
      - time, open, high, low, close, spread

    任意カラム:
      - tick_volume
      - real_volume

    tick_volume / real_volume が無ければ tick_volume=0.0, real_volume=None で埋める。
    """

    _REQUIRED_COLUMNS = ("time", "open", "high", "low", "close", "spread")

    def __init__(self, csv_path: str | Path, *, limit: Optional[int] = None) -> None:
        self.csv_path = Path(csv_path)
        df = pd.read_csv(self.csv_path)

        missing = [c for c in self._REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns in CSV: {missing}")

        df = df.copy()
        df["time"] = pd.to_datetime(df["time"])

        if limit is not None:
            df = df.head(limit)

        if "tick_volume" not in df.columns:
            df["tick_volume"] = 0.0

        if "real_volume" not in df.columns:
            df["real_volume"] = pd.NA

        # 必要列だけ残す（順番揃えておく）
        self._df = df[
            ["time", "open", "high", "low", "close", "spread", "tick_volume", "real_volume"]
        ].reset_index(drop=True)

        self._bars = self._df_to_bars(self._df)
        self._idx = 0

    def _df_to_bars(self, df: pd.DataFrame) -> list[Bar]:
        bars: list[Bar] = []
        for row in df.itertuples(index=False):
            real_volume = None if pd.isna(row.real_volume) else float(row.real_volume)
            bars.append(
                Bar(
                    time=row.time,
                    open=float(row.open),
                    high=float(row.high),
                    low=float(row.low),
                    close=float(row.close),
                    spread=float(row.spread),
                    tick_volume=float(row.tick_volume),
                    real_volume=real_volume,
                )
            )
        return bars

    def get_next_bar(self) -> Optional[Bar]:
        if self._idx >= len(self._bars):
            return None

        bar = self._bars[self._idx]
        self._idx += 1
        return bar
