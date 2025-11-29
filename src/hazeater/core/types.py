from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    spread: float
    tick_volume: float
    real_volume: float | None = None

@dataclass
class Signal:
    time: datetime
    side: Side          # long / short / flat
    reason: str         # ログ用（「tp_hit_prob_diff>0.02」など）


@dataclass
class OrderSpec:
    symbol: str
    side: Side
    volume: float
    entry_price: Optional[float]  # 成行なら None
    sl: float
    tp: float
    comment: str = ""

@dataclass
class Position:
    symbol: str
    side: Side
    volume: float
    entry_price: float
    sl: float
    tp: float
    open_time: datetime
    close_price: Optional[float] = None
    close_time: Optional[datetime] = None
    position_id: Optional[int] = None

class ExitActionType(str, Enum):
    HOLD = "hold"
    CLOSE = "close"
    UPDATE_SL_TP = "update_sl_tp"
    PARTIAL_CLOSE = "partial_close"


@dataclass
class ExitDecision:
    action: ExitActionType = ExitActionType.HOLD
    new_sl: float | None = None
    new_tp: float | None = None
    close_volume: float | None = None  # 部分決済用
    reason: str = ""