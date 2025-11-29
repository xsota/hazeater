from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd
from hazeater.timeframes import TIMEFRAME_MAP, TimeframeName


def _mt5_init() -> None:
    if not mt5.initialize():
        code, msg = mt5.last_error()
        raise RuntimeError(f"MT5 init failed: {code} {msg}")


def _mt5_shutdown() -> None:
    mt5.shutdown()


def fetch_rates(
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        *,
        mt5_timeframe: int,
) -> pd.DataFrame:
    """
    任意タイムフレームを取得し返す
    """

    _mt5_init()
    try:
        rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)

        if rates is None or len(rates) == 0:
            code, msg = mt5.last_error()
            raise RuntimeError(
                f"No data returned for {symbol}. timeframe={mt5_timeframe}. "
                f"last_error={code} {msg}"
            )

        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(df["time"], unit="s")

        cols = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
        return df[[c for c in cols if c in df.columns]]

    finally:
        _mt5_shutdown()


def fetch_rates_by_name(
        symbol: str,
        timeframe_name: TimeframeName,
        start_date: datetime,
        end_date: datetime,
) -> pd.DataFrame:
    if timeframe_name not in TIMEFRAME_MAP:
        raise ValueError(f"Unsupported timeframe {timeframe_name}")

    mt5_tf = TIMEFRAME_MAP[timeframe_name]

    return fetch_rates(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        mt5_timeframe=mt5_tf,
    )
