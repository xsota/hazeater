from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, Iterable, Optional, List

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

    def update_bar(self, bar: Bar) -> None:
        """
        Bar を1本受け取って DataFrame に追加し、window 分だけ保持。
        そのあと _on_update() を呼んで特徴量を更新する共通実装。
        """
        row = {
            "time": bar.time,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        new_row_df = pd.DataFrame([row])

        if self.df.empty:
            self.df = new_row_df
        else:
            # index は連番でOKなので ignore_index=True
            self.df = pd.concat([self.df, new_row_df], ignore_index=True)

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
        FeedBase からバーを流し込みながら、特徴量 DataFrame を構築するユーティリティ。

        これを使うと「ライブと同じロジックで特徴量を作った学習データ」が
        そのまま手に入る。

        例:

            feed = CsvFeed("gbpjpy_m1.csv")
            extractor = MyFeatureExtractor(window=300)
            df_feat = extractor.build_frame_from_feed(feed)
        """
        rows: list[Dict[str, Any]] = []

        for bar in feed.iter_bars():
            self.update_bar(bar)
            if not self.ready():
                continue
            rows.append(self.compute_features())

        if not rows:
            return pd.DataFrame(columns=self.feature_names)

        return pd.DataFrame(rows)
