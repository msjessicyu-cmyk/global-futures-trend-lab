"""Yahoo Finance adapter; network failures stay local to each symbol."""
from __future__ import annotations
import pandas as pd
from .indicators import normalize_ohlcv

def download_symbol(symbol: str, period: str = "5y") -> tuple[pd.DataFrame | None, str, str]:
    try:
        import yfinance as yf
        raw = yf.download(symbol, period=period, interval="1d", auto_adjust=False,
                          progress=False, threads=False, timeout=10)
        if raw is None or raw.empty:
            return None, "失败", "Yahoo Finance 未返回数据（代码无效、无覆盖或请求受限）。"
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.reset_index()
        if "Adj Close" in raw.columns and "Close" not in raw.columns:
            raw = raw.rename(columns={"Adj Close": "Close"})
        clean = normalize_ohlcv(raw)
        return clean, "成功", "行情已获取并通过 OHLCV 校验。"
    except Exception as exc:
        return None, "失败", f"{type(exc).__name__}: {str(exc)[:300]}"
