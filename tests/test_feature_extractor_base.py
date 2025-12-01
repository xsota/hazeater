from datetime import datetime, timedelta
from typing import Optional, Iterable

import pandas as pd
from pandas.testing import assert_frame_equal

from hazeater.core.types import Bar
from hazeater.features.feature_extractor_base import FeatureExtractorBase
from hazeater.feeds import FeedBase


class _SimpleExtractor(FeatureExtractorBase):
    """テスト用の簡易特徴量: close, 3本SMA, 1本遅れ"""

    @property
    def min_bars(self) -> int:
        return 3

    @property
    def feature_names(self) -> list[str]:
        return ["close", "sma3", "lag1"]

    def _on_update(self) -> None:
        df = self.df
        df["sma3"] = df["close"].rolling(3).mean()
        df["lag1"] = df["close"].shift(1)


class _ListFeed(FeedBase):
    """リストから Bar を返すだけの簡易 Feed"""

    def __init__(self, bars: Iterable[Bar]):
        self._bars = list(bars)
        self._idx = 0

    def get_next_bar(self) -> Optional[Bar]:
        if self._idx >= len(self._bars):
            return None
        bar = self._bars[self._idx]
        self._idx += 1
        return bar


def _sample_bars() -> list[Bar]:
    base = datetime(2024, 1, 1, 0, 0, 0)
    closes = [100, 101, 102, 103, 104]
    bars: list[Bar] = []
    for i, close in enumerate(closes):
        bars.append(
            Bar(
                time=base + timedelta(minutes=i),
                open=close - 0.5,
                high=close + 0.5,
                low=close - 1.0,
                close=close,
                spread=1.2,
                tick_volume=10 + i,
                real_volume=None,
            )
        )
    return bars


def _bars_to_df(bars: Iterable[Bar]) -> pd.DataFrame:
    rows = []
    for b in bars:
        rows.append(
            {
                "time": b.time,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "spread": b.spread,
                "tick_volume": b.tick_volume,
                "real_volume": b.real_volume,
            }
        )
    return pd.DataFrame(rows)


def test_streaming_vs_bulk_dataframe_match() -> None:
    bars = _sample_bars()

    # ストリーミング計算
    stream_extractor = _SimpleExtractor()
    stream_rows: list[dict] = []
    for bar in bars:
        stream_extractor.update_bar(bar)
        if stream_extractor.ready():
            stream_rows.append(stream_extractor.compute_features())
    stream_df = pd.DataFrame(stream_rows)

    # DataFrame ベクトル化計算
    bulk_extractor = _SimpleExtractor()
    df = _bars_to_df(bars)
    bulk_df = bulk_extractor.build_frame_from_dataframe(df)

    assert_frame_equal(stream_df.reset_index(drop=True), bulk_df.reset_index(drop=True))


def test_feed_path_matches_dataframe_bulk() -> None:
    bars = _sample_bars()
    feed = _ListFeed(bars)

    extractor = _SimpleExtractor()
    df_from_feed = extractor.build_frame_from_feed(feed)

    # 同じ元データで DataFrame から直接計算
    df_bulk = extractor.build_frame_from_dataframe(_bars_to_df(bars))

    assert_frame_equal(df_from_feed.reset_index(drop=True), df_bulk.reset_index(drop=True))
