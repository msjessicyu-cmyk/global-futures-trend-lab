import numpy as np
import pandas as pd
import pytest
from src.indicators import add_indicators, normalize_ohlcv, to_weekly

def bars(n=140):
    dates = pd.date_range("2022-01-03", periods=n, freq="B")
    close = np.arange(n, dtype=float) + 100
    return pd.DataFrame({"Open": close-.5, "High": close+1, "Low": close-1,
                         "Close": close, "Volume": np.ones(n)*10}, index=dates)

def test_moving_averages_and_warmup():
    out = add_indicators(bars())
    assert np.isnan(out.MA20.iloc[18])
    assert out.MA20.iloc[19] == pytest.approx(np.mean(np.arange(100,120)))
    assert out.MA100.notna().sum() == 41

def test_macd_and_atr_are_finite_after_warmup():
    out = add_indicators(bars())
    assert np.isfinite(out.MACD_hist.iloc[-1])
    assert out.ATR14.iloc[-1] == pytest.approx(2.0)

def test_rsi_monotonic_boundaries():
    up = add_indicators(bars(40))
    assert up.RSI14.iloc[-1] == 100
    x = bars(40); x["Close"] = np.arange(40, dtype=float)[::-1]+100; x["Open"] = x.Close; x["High"] = x.Close+1; x["Low"] = x.Close-1
    assert add_indicators(x).RSI14.iloc[-1] == 0

def test_short_history_has_indicator_warmup_nans():
    out = add_indicators(bars(10))
    assert out.MA20.isna().all() and out.ATR14.isna().all()

def test_weekly_ohlcv_rules_and_incomplete_marker():
    daily = bars(10)
    weekly = to_weekly(daily, now=pd.Timestamp("2022-01-12"))
    assert weekly.iloc[0].Open == daily.iloc[0].Open
    assert weekly.iloc[0].High == daily.iloc[:5].High.max()
    assert weekly.iloc[0].Volume == daily.iloc[:5].Volume.sum()
    assert weekly.iloc[-1].IsIncomplete

def test_bad_csv_ohlc_rejected():
    with pytest.raises(ValueError, match="OHLC"):
        normalize_ohlcv(pd.DataFrame({"Date":["2024-01-01"],"Open":[5],"High":[2],"Low":[1],"Close":[4],"Volume":[1]}))

def test_csv_non_finite_number_rejected():
    with pytest.raises(ValueError, match="无穷大"):
        normalize_ohlcv(pd.DataFrame({"Date":["2024-01-01"],"Open":[1],"High":[float("inf")],"Low":[0],"Close":[1],"Volume":[1]}))
