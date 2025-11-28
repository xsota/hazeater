import pandas as pd
from datetime import datetime
from hazeater.data.get_rates import fetch_rates_by_name

def test_fetch_rates_returns_dataframe(monkeypatch):
    """MT5 response mock"""

    dummy_rates = [
        {
            "time": 1735657200,
            "open": 196.595,
            "high": 196.599,
            "low": 196.519,
            "close": 196.587,
            "tick_volume": 673,
            "spread": 9,
            "real_volume": 0,
        }
    ]

    from hazeater.data import get_rates

    monkeypatch.setattr(
        get_rates.mt5,
        "copy_rates_range",
        lambda *args, **kwargs: dummy_rates,
    )
    monkeypatch.setattr(get_rates.mt5, "initialize", lambda: True)
    monkeypatch.setattr(get_rates.mt5, "shutdown", lambda: True)
    monkeypatch.setattr(get_rates.mt5, "last_error", lambda: (0, ""))

    df = fetch_rates_by_name(
        "GBPJPY",
        "m1",
        datetime(2025, 1, 1),
        datetime(2025, 1, 2),
    )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1

    assert "time" in df.columns
    assert "open" in df.columns

    assert df.iloc[0]["open"] == 196.595
    assert df.iloc[0]["high"] == 196.599
    assert df.iloc[0]["tick_volume"] == 673
