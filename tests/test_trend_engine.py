import numpy as np
import pandas as pd
from src.trend_engine import score_trend, multi_timeframe_label

def frame(up=True, n=120):
    close = np.linspace(50, 200, n) if up else np.linspace(200, 50, n)
    d = pd.DataFrame(index=range(n))
    d["Close"] = close; d["MA20"] = close-2 if up else close+2
    d["MA50"] = close-5 if up else close+5; d["MA100"] = close-10 if up else close+10
    if n < 50: d["MA50"] = np.nan
    if n < 100: d["MA100"] = np.nan
    d["MACD_hist"] = 1 if up else -1
    return d

def test_score_positive_and_negative_directions():
    assert score_trend(frame(True))["score"] > 0
    assert score_trend(frame(False))["score"] < 0

def test_insufficient_history_is_not_scored():
    result = score_trend(frame(True, 30))
    assert result["score"] is None and result["label"] == "数据不足"

def test_multi_timeframe_alignment_and_disagreement():
    bull = {"score": 4}; bear = {"score": -4}
    assert multi_timeframe_label(bull, bull) == "多周期偏多"
    assert multi_timeframe_label(bear, bull) == "多周期分歧"
