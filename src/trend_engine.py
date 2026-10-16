"""Transparent five-rule trend score."""
from __future__ import annotations
import pandas as pd

RULES = ["Close vs MA20", "MA20 vs MA50", "MA50 vs MA100", "MA20 vs MA20 five periods ago", "MACD histogram"]


def score_trend(frame: pd.DataFrame) -> dict:
    if frame is None or frame.empty:
        return {"score": None, "label": "数据不足", "conditions": [], "valid_conditions": 0}
    row = frame.iloc[-1]
    prev_ma20 = frame["MA20"].iloc[-6] if len(frame) >= 6 else float("nan")
    pairs = [(row.get("Close"), row.get("MA20")), (row.get("MA20"), row.get("MA50")),
             (row.get("MA50"), row.get("MA100")), (row.get("MA20"), prev_ma20),
             (row.get("MACD_hist"), 0)]
    labels = ["收盘价高于 MA20", "MA20 高于 MA50", "MA50 高于 MA100",
              "MA20 高于五周期前", "MACD 柱体大于零"]
    conds, vals = [], []
    for name, (lhs, rhs) in zip(labels, pairs):
        valid = pd.notna(lhs) and pd.notna(rhs)
        value = (1 if lhs > rhs else -1) if valid else None
        vals.append(value)
        conds.append({"name": name, "value": value, "reason": (f"{float(lhs):.4g} {'>' if value == 1 else '<='} {float(rhs):.4g}" if valid else "预热数据不足")})
    valid = sum(v is not None for v in vals)
    if valid < 5:
        return {"score": None, "label": "数据不足", "conditions": conds, "valid_conditions": valid}
    score = sum(vals)
    label = "趋势偏多" if score >= 3 else "趋势偏空" if score <= -3 else "震荡或中性"
    return {"score": score, "label": label, "conditions": conds, "valid_conditions": valid}


def multi_timeframe_label(daily: dict, weekly: dict) -> str:
    if daily.get("score") is None or weekly.get("score") is None:
        return "数据不足"
    if daily["score"] >= 3 and weekly["score"] >= 3:
        return "多周期偏多"
    if daily["score"] <= -3 and weekly["score"] <= -3:
        return "多周期偏空"
    if (daily["score"] >= 3 and weekly["score"] <= -3) or (daily["score"] <= -3 and weekly["score"] >= 3):
        return "多周期分歧"
    return "多周期中性"
