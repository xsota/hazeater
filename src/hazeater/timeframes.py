from typing import Dict, Literal
import MetaTrader5 as mt5

TIMEFRAME_MAP: Dict[str, int] = {
    "m1": mt5.TIMEFRAME_M1,
    "m2": mt5.TIMEFRAME_M2,
    "m3": mt5.TIMEFRAME_M3,
    "m4": mt5.TIMEFRAME_M4,
    "m5": mt5.TIMEFRAME_M5,
    "m6": mt5.TIMEFRAME_M6,
    "m10": mt5.TIMEFRAME_M10,
    "m12": mt5.TIMEFRAME_M12,
    "m15": mt5.TIMEFRAME_M15,
    "m20": mt5.TIMEFRAME_M20,
    "m30": mt5.TIMEFRAME_M30,
    "h1": mt5.TIMEFRAME_H1,
    "h2": mt5.TIMEFRAME_H2,
    "h3": mt5.TIMEFRAME_H3,
    "h4": mt5.TIMEFRAME_H4,
    "h6": mt5.TIMEFRAME_H6,
    "h8": mt5.TIMEFRAME_H8,
    "h12": mt5.TIMEFRAME_H12,
    "d1": mt5.TIMEFRAME_D1,
    "w1": mt5.TIMEFRAME_W1,
    "mn1": mt5.TIMEFRAME_MN1,
}

TimeframeName = Literal[
    "m1", "m2", "m3", "m4", "m5", "m6",
    "m10", "m12", "m15", "m20", "m30",
    "h1", "h2", "h3", "h4", "h6", "h8", "h12",
    "d1",
    "w1",
    "mn1",
]
