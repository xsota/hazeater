import importlib
import sys
import types
from datetime import datetime

import pytest


@pytest.fixture()
def mt5_env(monkeypatch):
    """
    MetaTrader5 をモックして Mt5Feed を安全に読み込む。
    """
    stub = types.SimpleNamespace()
    base_ts = int(datetime(2024, 1, 1, 0, 0, 0).timestamp())
    stub.initial_rates = [
        {
            "time": base_ts,
            "open": 100.0,
            "high": 101.0,
            "low": 99.5,
            "close": 100.5,
            "spread": 1.0,
            "tick_volume": 10.0,
            "real_volume": 20.0,
        },
        {
            "time": base_ts + 60,
            "open": 100.5,
            "high": 101.5,
            "low": 100.0,
            "close": 101.0,
            "spread": 1.0,
            "tick_volume": 11.0,
            "real_volume": 21.0,
        },
    ]
    stub.live_rates_queue: list[list[dict]] = []
    stub.initial_returned = False
    stub.shutdown_called = False

    def initialize():
        return True

    def shutdown():
        stub.shutdown_called = True
        return True

    def last_error():
        return 0, "ok"

    def copy_rates_range(symbol, timeframe, start, end):
        if not stub.initial_returned:
            stub.initial_returned = True
            return stub.initial_rates
        if stub.live_rates_queue:
            return stub.live_rates_queue.pop(0)
        return []

    stub.initialize = initialize
    stub.shutdown = shutdown
    stub.last_error = last_error
    stub.copy_rates_range = copy_rates_range
    # タイムフレーム定数（timeframes.py が参照する全キーを定義）
    tf_values = {
        "TIMEFRAME_M1": 1,
        "TIMEFRAME_M2": 2,
        "TIMEFRAME_M3": 3,
        "TIMEFRAME_M4": 4,
        "TIMEFRAME_M5": 5,
        "TIMEFRAME_M6": 6,
        "TIMEFRAME_M10": 10,
        "TIMEFRAME_M12": 12,
        "TIMEFRAME_M15": 15,
        "TIMEFRAME_M20": 20,
        "TIMEFRAME_M30": 30,
        "TIMEFRAME_H1": 60,
        "TIMEFRAME_H2": 120,
        "TIMEFRAME_H3": 180,
        "TIMEFRAME_H4": 240,
        "TIMEFRAME_H6": 360,
        "TIMEFRAME_H8": 480,
        "TIMEFRAME_H12": 720,
        "TIMEFRAME_D1": 1440,
        "TIMEFRAME_W1": 10080,
        "TIMEFRAME_MN1": 43200,
    }
    for k, v in tf_values.items():
        setattr(stub, k, v)

    monkeypatch.setitem(sys.modules, "MetaTrader5", stub)

    # stub を反映させるため再読み込み
    timeframes = importlib.reload(importlib.import_module("hazeater.timeframes"))
    feeds_mt5 = importlib.reload(importlib.import_module("hazeater.feeds.mt5_feed"))
    return stub, timeframes, feeds_mt5


def test_backtest_mode_returns_bars_and_none(mt5_env):
    stub, _, feeds_mt5 = mt5_env
    Mt5Feed = feeds_mt5.Mt5Feed

    start = datetime.utcfromtimestamp(stub.initial_rates[0]["time"])
    end = datetime.utcfromtimestamp(stub.initial_rates[-1]["time"])
    feed = Mt5Feed(symbol="EURUSD", timeframe="m1", start=start, end=end)

    bars = list(feed.iter_bars())
    assert len(bars) == len(stub.initial_rates)
    assert bars[0].close == stub.initial_rates[0]["close"]
    assert feed.get_next_bar() is None  # バックテスト終端で None


def test_live_mode_returns_warmup_then_new_bar(mt5_env, monkeypatch):
    stub, _, feeds_mt5 = mt5_env
    Mt5Feed = feeds_mt5.Mt5Feed

    # ポーリング待機を無効化
    monkeypatch.setattr(feeds_mt5.time, "sleep", lambda _: None)

    start = datetime.utcfromtimestamp(stub.initial_rates[0]["time"])
    feed = Mt5Feed(symbol="EURUSD", timeframe="m1", start=start, end=None, poll_interval=0.0)

    # ウォームアップ分（initial_rates）が先に流れる
    warmup_bars = [feed.get_next_bar() for _ in range(len(stub.initial_rates))]
    assert warmup_bars[-1].close == stub.initial_rates[-1]["close"]

    # 次のライブバーをキューへ積む
    next_time = stub.initial_rates[-1]["time"] + 60
    live_close = 102.5
    stub.live_rates_queue.append(
        [
            {
                "time": next_time,
                "open": 101.5,
                "high": 103.0,
                "low": 101.0,
                "close": live_close,
                "spread": 1.2,
                "tick_volume": 12.0,
                "real_volume": 22.0,
            }
        ]
    )

    new_bar = feed.get_next_bar()
    assert new_bar.close == live_close
