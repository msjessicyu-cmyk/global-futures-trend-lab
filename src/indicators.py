"""Indicator and bar aggregation functions without external market data."""
from __future__ import annotations

import pandas as pd
import numpy as np

PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def normalize_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Return validated Date-indexed OHLCV data; reject malformed input clearly."""
    if frame is None or frame.empty:
        raise ValueError("CSV 没有数据行。")
    df = frame.copy()
    df.columns = [str(c).strip() for c in df.columns]
    # Accept common yfinance and human CSV variants, while requiring all fields.
    aliases = {"date": "Date", "datetime": "Date", "open": "Open", "high": "High",
               "low": "Low", "close": "Close", "adj close": "Adj Close",
               "volume": "Volume"}
    rename = {c: aliases.get(c.lower(), c) for c in df.columns}
    df = df.rename(columns=rename)
    if "Date" not in df.columns and isinstance(df.index, pd.DatetimeIndex):
        df["Date"] = df.index
    missing = [c for c in ["Date", *PRICE_COLUMNS] if c not in df.columns]
    if missing:
        raise ValueError("缺少必需列：" + ", ".join(missing))
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", utc=True).dt.tz_convert(None)
    if df["Date"].isna().any():
        raise ValueError("Date 列包含无法识别的日期，请使用 YYYY-MM-DD。")
    for col in PRICE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[PRICE_COLUMNS].isna().any().any():
        bad = int(df[PRICE_COLUMNS].isna().any(axis=1).sum())
        raise ValueError(f"OHLCV 有 {bad} 行包含缺失值或非数值。")
    if not np.isfinite(df[PRICE_COLUMNS].to_numpy(dtype=float)).all():
        raise ValueError("OHLCV 不能包含无穷大等非有限数值。")
    if (df["Volume"] < 0).any():
        raise ValueError("Volume 不能为负数。")
    bad_ohlc = ((df.High < df[["Open", "Close", "Low"]].max(axis=1)) |
                (df.Low > df[["Open", "Close", "High"]].min(axis=1)))
    if bad_ohlc.any():
        raise ValueError(f"发现 {int(bad_ohlc.sum())} 行 OHLC 关系异常（High/Low 不符合价格范围）。")
    df = df.sort_values("Date", kind="stable").drop_duplicates("Date", keep="last").set_index("Date")
    return df[PRICE_COLUMNS].astype(float)


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    close, high, low = df["Close"], df["High"], df["Low"]
    for n in (20, 50, 100):
        df[f"MA{n}"] = close.rolling(n, min_periods=n).mean()
    ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False, min_periods=9).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = -delta.clip(upper=0).rolling(14, min_periods=14).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["RSI14"] = 100 - (100 / (1 + rs))
    # Explicit boundary behavior for monotonic series.
    df.loc[(loss == 0) & (gain > 0), "RSI14"] = 100.0
    df.loc[(gain == 0) & (loss > 0), "RSI14"] = 0.0
    df.loc[(gain == 0) & (loss == 0), "RSI14"] = 50.0
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    df["ATR14"] = tr.rolling(14, min_periods=14).mean()
    df["MA20_change_5"] = df["MA20"] - df["MA20"].shift(5)
    df["ChangePct"] = close.pct_change() * 100
    return df


def to_weekly(frame: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Aggregate daily bars to Monday-start weeks; mark a still-open current week."""
    if frame.empty:
        result = frame.copy()
        result["IsIncomplete"] = pd.Series(dtype=bool)
        return result
    # W-SUN is a Monday-start calendar week.
    weekly = frame.resample("W-SUN", label="right", closed="right").agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    ).dropna(subset=["Open", "High", "Low", "Close"])
    current = pd.Timestamp.now().normalize() if now is None else pd.Timestamp(now).normalize()
    # Any bar in the calendar week containing now belongs to an unfinished week.
    current_week_end = current + pd.Timedelta(days=(6 - current.weekday()))
    weekly["IsIncomplete"] = weekly.index >= current_week_end
    return weekly
