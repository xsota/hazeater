from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Iterable, Optional, List, Sequence

import pandas as pd

from hazeater.core.types import Bar
from hazeater.feeds import FeedBase


class FeatureExtractorBase(ABC):
    """
    フォワード / バックテスト共通の特徴量生成インターフェース。

    - データの流れは FeedBase(= Bar を1本ずつ流す) に任せる
    - このクラスは Bar を受け取り、内部の DataFrame(self.df) を更新しつつ
      pandas の rolling / shift などで特徴量を計算する役。

    使い方のイメージ:

        extractor = MyFeatureExtractor(window=300)

        for bar in feed.iter_bars():
            extractor.update_bar(bar)
            if not extractor.ready():
                continue
            feat_dict = extractor.compute_features()
            # ライブならそのままモデルへ / 学習ならリストに貯める

    サブクラス側では主に:

        - min_bars を実装（何本貯まれば ready になるか）
        - feature_names を実装（返したい特徴量カラム名）
        - _on_update() で self.df に対して rolling 等の計算を書く

    だけ書けばOK。
    """

    def __init__(self, window: Optional[int] = None) -> None:
        """
        window: 内部で保持する最大バー本数（None の場合は全保持）
        """
        self.window = window
        self.df: pd.DataFrame = pd.DataFrame()

    # 内部で扱う標準カラム
    _BASE_COLS: Sequence[str] = (
        "time",
        "open",
        "high",
        "low",
        "close",
        "spread",
        "tick_volume",
        "real_volume",
        "volume",  # tick_volume のエイリアス（後方互換）
    )

    # ========= 抽象インターフェース =========

    @property
    @abstractmethod
    def min_bars(self) -> int:
        """
        ready() が True になるために最低限必要なバー本数。
        例: SMA200 を使うなら 200 など。
        """
        ...

    @property
    @abstractmethod
    def feature_names(self) -> List[str]:
        """
        compute_features() で返したい特徴量カラム名のリスト。
        self.df の列名と対応している必要がある
        """
        ...

    @abstractmethod
    def _on_update(self) -> None:
        """
        self.df が最新の状態に更新されたあとに呼ばれるフック。

        ここで pandas の rolling / shift などを使って
        self.df に特徴量カラムを生やす実装を書いてほしい。

        例:

            close_lag1 = self.df["close"].shift(1)
            self.df["sma21"] = close_lag1.rolling(21).mean()
            ...
        """
        ...

    # ========= 共通実装（Bar -> df 変換） =========

    def reset(self) -> None:
        """内部状態をクリアする。"""
        self.df = pd.DataFrame()

    def _bar_to_row(self, bar: Bar) -> Dict[str, Any]:
        """Bar -> DataFrame 1行分の dict に変換。"""
        return {
            "time": bar.time,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "spread": bar.spread,
            "tick_volume": bar.tick_volume,
            "real_volume": bar.real_volume,
            # 後方互換用に volume カラムも残す（tick_volume と同値）
            "volume": bar.tick_volume,
        }

    def _normalize_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        入力 DataFrame を内部標準カラムに揃える。

        必須: time, open, high, low, close, spread
        任意: tick_volume, real_volume, volume
        """
        required = ["time", "open", "high", "low", "close", "spread"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        out = df.copy()
        if "tick_volume" not in out.columns:
            out["tick_volume"] = 0.0
        if "real_volume" not in out.columns:
            out["real_volume"] = pd.NA
        # 後方互換: volume が無ければ tick_volume をコピー
        if "volume" not in out.columns:
            out["volume"] = out["tick_volume"]

        # 順番を揃えておく
        present_cols = [c for c in self._BASE_COLS if c in out.columns]
        return out[present_cols].reset_index(drop=True)

    def update_bar(self, bar: Bar) -> None:
        """
        Bar を1本受け取って DataFrame に追加し、window 分だけ保持。
        そのあと _on_update() を呼んで特徴量を更新する共通実装。
        """
        row_df = pd.DataFrame([self._bar_to_row(bar)])

        if self.df.empty:
            self.df = row_df
        else:
            # index は連番でOKなので ignore_index=True
            self.df = pd.concat([self.df, row_df], ignore_index=True)

        # window 指定があれば末尾だけ残す
        if self.window is not None and len(self.df) > self.window:
            self.df = self.df.tail(self.window).reset_index(drop=True)

        # 実際の特徴量計算はサブクラスに任せる
        self._on_update()

    def update_bars(self, bars: Iterable[Bar]) -> None:
        """
        複数の Bar をまとめて流したいとき用のヘルパー。
        """
        for bar in bars:
            self.update_bar(bar)

    def ready(self) -> bool:
        """
        特徴量が計算できる状態かどうか（ウォームアップ完了判定）。
        デフォルトは min_bars 本以上あれば True 。
        """
        return len(self.df) >= self.min_bars

    def compute_features(self) -> Dict[str, Any]:
        """
        最新の1サンプル分の特徴量を dict にして返す。

        - ライブトレード: そのままモデルに渡す
        - 学習/バックテスト: ループで集めて DataFrame に変換する

        ready() が False のときに呼ぶと RuntimeError を投げる。
        """
        if not self.ready():
            raise RuntimeError("FeatureExtractor not ready: not enough bars.")

        last = self.df.iloc[-1]
        return {name: last[name] for name in self.feature_names}

    # ========= 学習用のヘルパー =========

    def build_frame_from_feed(self, feed: FeedBase) -> pd.DataFrame:
        """
        FeedBase からバーをまとめて受け取り、特徴量 DataFrame を一括計算する高速パス。

        ライブと同じロジックを使いつつ、学習/バックテストでは pandas ベクトル化で
        計算コストを抑えたい場合に使う。
        """
        rows: list[Dict[str, Any]] = [self._bar_to_row(bar) for bar in feed.iter_bars()]
        if not rows:
            return pd.DataFrame(columns=self.feature_names)

        df = pd.DataFrame(rows)
        return self.build_frame_from_dataframe(df)

    def build_frame_from_dataframe(self, df: pd.DataFrame, *, apply_window: bool = False) -> pd.DataFrame:
        """
        既存の DataFrame（CSVやMT5から取得した履歴など）から特徴量を一括生成する。

        - カラム time/open/high/low/close/spread は必須
        - tick_volume/real_volume/volume は無ければ補完
        - ライブと同じ _on_update() ロジックを1回実行するだけなので高速
        """
        self.reset()
        self.df = self._normalize_frame(df)

        if apply_window and self.window is not None and len(self.df) > self.window:
            self.df = self.df.tail(self.window).reset_index(drop=True)

        self._on_update()

        # pandas の rolling 等を使えば先頭は自動的に NaN になるのでそのまま返す
        feature_df = self.df[self.feature_names].copy()

        # 過去データが足りない先頭部分は ready() と同等に落とす
        if self.min_bars > 1:
            feature_df = feature_df.iloc[self.min_bars - 1 :].reset_index(drop=True)

        return feature_df
