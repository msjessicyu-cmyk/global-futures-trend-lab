from __future__ import annotations
import io
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.data_provider import download_symbol
from src.indicators import add_indicators, normalize_ohlcv, to_weekly
from src.trend_engine import score_trend, multi_timeframe_label
from src.utils import load_markets

st.set_page_config(page_title="全球期货趋势研究", page_icon="📈", layout="wide")
st.title("🌐 Global Futures Trend Lab V1.0")
st.caption("全球期货历史行情研究工具 · 不提供交易指令，也不保证投资收益")
markets = load_markets()
PERIODS = {"1 年": "1y", "2 年": "2y", "5 年": "5y", "10 年": "10y", "最大": "max"}

@st.cache_data(ttl=3600, show_spinner=False)
def cached_download(symbol: str, period: str):
    data, status, message = download_symbol(symbol, period)
    return data, status, message

def retrieve(symbol: str, period: str, force=False):
    uploads = st.session_state.get("uploaded_prices", {})
    if symbol in uploads and not force:
        return uploads[symbol], "CSV 上传", "使用当前会话中的 CSV 数据（临时，不会持久保存）。"
    if force:
        cached_download.clear()
    data, status, message = cached_download(symbol, period)
    return data, status, message

def analyzed(data, timeframe):
    if data is None or data.empty:
        return None, {"score": None, "label": "数据不足", "conditions": [], "valid_conditions": 0}
    bars = to_weekly(data) if timeframe == "周线" else data.copy()
    return add_indicators(bars), score_trend(add_indicators(bars))

def display_conditions(result):
    if not result["conditions"]:
        st.info("历史数据不足，无法生成趋势评分。")
        return
    st.dataframe(pd.DataFrame([{"评分依据": c["name"], "方向分": c["value"] if c["value"] is not None else "不足", "原因": c["reason"]} for c in result["conditions"]]), hide_index=True, use_container_width=True)

pages = ["全球市场总览", "单品种深度分析", "趋势排行榜", "数据管理"]
page = st.sidebar.radio("页面", pages)
period_label = st.sidebar.selectbox("历史区间", list(PERIODS), index=2)
period = PERIODS[period_label]
st.sidebar.caption("Yahoo Finance 免费数据可能延迟、缺失；连续合约存在拼接/调整差异，不适用于结算或实盘决策。")

if page == "全球市场总览":
    st.header("全球市场总览")
    st.write("选择分类和关键词筛选品种。点击加载按钮后逐项请求 Yahoo Finance；初次请求可能需要一些时间。")
    c1, c2, c3 = st.columns([1, 1, 2])
    categories = ["全部"] + sorted({m["category"] for m in markets})
    category = c1.selectbox("市场分类", categories)
    query = c2.text_input("搜索名称或代码")
    force = c3.button("🔄 刷新并加载全部候选品种", type="primary")
    chosen = [m for m in markets if (category == "全部" or m["category"] == category) and (not query or query.lower() in (m["symbol"]+m["name_zh"]+m["name_en"]).lower())]
    if st.button("加载当前筛选结果", disabled=not chosen) or force:
        rows = []
        bar = st.progress(0, text="逐个尝试获取历史行情…")
        for idx, m in enumerate(chosen):
            data, status, msg = retrieve(m["symbol"], period, force=force)
            if data is None:
                rows.append({"品种":m["name_zh"],"代码":m["symbol"],"分类":m["category"],"日线评分":"—","周线评分":"—","多周期":"数据不足","涨跌幅(%)":None,"RSI14":None,"最新日期":"—","状态":status,"说明":msg})
            else:
                d, ds = analyzed(data, "日线"); w, ws = analyzed(data, "周线")
                rows.append({"品种":m["name_zh"],"代码":m["symbol"],"分类":m["category"],"日线评分":ds["score"] if ds["score"] is not None else "数据不足","周线评分":ws["score"] if ws["score"] is not None else "数据不足","多周期":multi_timeframe_label(ds,ws),"涨跌幅(%)":round(float(d.ChangePct.dropna().iloc[-1]),2) if d.ChangePct.notna().any() else None,"RSI14":round(float(d.RSI14.iloc[-1]),1) if pd.notna(d.RSI14.iloc[-1]) else None,"最新日期":str(data.index[-1].date()),"状态":status,"说明":msg})
            bar.progress((idx+1)/len(chosen), text=f"已尝试 {idx+1}/{len(chosen)}")
        st.session_state["overview"] = pd.DataFrame(rows)
    table = st.session_state.get("overview")
    if table is not None:
        table = table[table["代码"].isin([m["symbol"] for m in chosen])]
        successes = int((table["状态"].isin(["成功", "CSV 上传"])).sum())
        a,b = st.columns(2); a.metric("成功获取", successes); b.metric("失败/不可用", len(table)-successes)
        sortby = st.selectbox("排序", ["涨跌幅(%)", "日线评分", "周线评分"])
        if sortby in table: table = table.sort_values(sortby, ascending=False, na_position="last")
        st.dataframe(table, hide_index=True, use_container_width=True)
    else:
        st.info("尚未加载。点击“加载当前筛选结果”开始请求数据；加载前不会假装数据已经验证。")

elif page == "单品种深度分析":
    st.header("单品种深度分析")
    labels = {f"{m['name_zh']} ({m['symbol']})":m for m in markets}
    selected = st.selectbox("品种", list(labels))
    tf = st.radio("周期", ["日线", "周线"], horizontal=True)
    m = labels[selected]
    data, status, message = retrieve(m["symbol"], period)
    if data is None:
        st.error(f"{m['symbol']} 行情获取失败：{message}")
        st.info("可在“数据管理”页上传该品种 CSV。")
    else:
        bars, result = analyzed(data, tf)
        if tf == "周线" and bars.iloc[-1].get("IsIncomplete", False):
            st.warning("最后一根周线处于当前交易周，尚未完成。")
        last = bars.iloc[-1]
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("最新收盘", f"{last.Close:,.4f}"); c2.metric("有效日期", str(bars.index[-1].date()))
        c3.metric("趋势评分", f"{result['score']}/5" if result["score"] is not None else "数据不足")
        c4.metric("分类", result["label"])
        st.caption(f"数据源：{message} · 日线最新有效日期：{data.index[-1].date()} · 最近变动：{last.ChangePct:.2f}%" if pd.notna(last.ChangePct) else f"数据源：{message}")
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=.035, row_heights=[.52,.18,.15,.15], subplot_titles=("价格与均线", "MACD", "RSI(14)", "ATR(14)"))
        fig.add_trace(go.Candlestick(x=bars.index,open=bars.Open,high=bars.High,low=bars.Low,close=bars.Close,name="OHLC"),row=1,col=1)
        for n in (20,50,100): fig.add_trace(go.Scatter(x=bars.index,y=bars[f"MA{n}"],name=f"MA{n}",mode="lines"),row=1,col=1)
        fig.add_trace(go.Bar(x=bars.index,y=bars.MACD_hist,name="MACD 柱体"),row=2,col=1)
        fig.add_trace(go.Scatter(x=bars.index,y=bars.MACD,name="MACD"),row=2,col=1); fig.add_trace(go.Scatter(x=bars.index,y=bars.MACD_signal,name="信号线"),row=2,col=1)
        fig.add_trace(go.Scatter(x=bars.index,y=bars.RSI14,name="RSI14"),row=3,col=1)
        fig.add_trace(go.Scatter(x=bars.index,y=bars.ATR14,name="ATR14"),row=4,col=1)
        fig.update_layout(height=900,xaxis_rangeslider_visible=False,legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True)
        display_conditions(result)
        st.caption("指标只描述历史价格行为；评分不是成功率、买卖指令或收益保证。")

elif page == "趋势排行榜":
    st.header("趋势排行榜")
    mode = st.selectbox("筛选方向", ["全部", "趋势偏多", "趋势偏空", "多周期偏多", "多周期偏空", "多周期分歧", "数据不足"])
    if st.button("计算排行榜", type="primary"):
        records=[]; bar=st.progress(0)
        for i,m in enumerate(markets):
            data,status,msg=retrieve(m["symbol"],period)
            if data is None:
                records.append({"品种":m["name_zh"],"代码":m["symbol"],"日线评分":None,"周线评分":None,"日线方向":"数据不足","周线方向":"数据不足","方向":"数据不足","涨跌幅(%)":None,"最新日期":"—","状态":f"{status}: {msg}"})
            else:
                d,ds=analyzed(data,"日线"); w,ws=analyzed(data,"周线")
                records.append({"品种":m["name_zh"],"代码":m["symbol"],"日线评分":ds["score"],"周线评分":ws["score"],"日线方向":ds["label"],"周线方向":ws["label"],"方向":multi_timeframe_label(ds,ws),"涨跌幅(%)":float(d.ChangePct.dropna().iloc[-1]) if d.ChangePct.notna().any() else None,"最新日期":str(data.index[-1].date()),"状态":status})
            bar.progress((i+1)/len(markets))
        st.session_state["ranking"]=pd.DataFrame(records)
    table=st.session_state.get("ranking")
    if table is not None:
        if mode == "趋势偏多": table=table[(table["日线方向"]==mode)|(table["周线方向"]==mode)]
        elif mode == "趋势偏空": table=table[(table["日线方向"]==mode)|(table["周线方向"]==mode)]
        elif mode != "全部": table=table[table["方向"]==mode]
        order=st.selectbox("排序方式",["日线评分","周线评分","涨跌幅(%)"])
        st.dataframe(table.sort_values(order,ascending=False,na_position="last"),hide_index=True,use_container_width=True)
        st.caption("排行榜仅按历史规则排序，不构成投资建议。")
    else: st.info("点击“计算排行榜”后逐个查询配置中的品种。")

else:
    st.header("数据管理")
    st.write("每个代码单独请求和报告状态。刷新按钮会清除应用缓存并重新请求当前区间数据。")
    pick = st.selectbox("刷新单个品种", [f"{m['symbol']} — {m['name_zh']}" for m in markets])
    symbol = pick.split(" — ")[0]
    if st.button("手动刷新所选品种"):
        data,status,msg=retrieve(symbol,period,force=True)
        if data is None: st.error(f"{status}: {msg}")
        else: st.success(f"{status}：{len(data)} 行，最新日期 {data.index[-1].date()}。")
    st.subheader("CSV 模板与导入")
    template=pd.DataFrame({"Date":["2024-01-02"],"Open":[100.0],"High":[102.0],"Low":[99.0],"Close":[101.0],"Volume":[1000]})
    st.download_button("下载 CSV 模板",template.to_csv(index=False).encode("utf-8-sig"),"ohlcv_template.csv","text/csv")
    upload_symbol=st.selectbox("此 CSV 对应的品种",[m["symbol"] for m in markets],key="upload_symbol")
    uploaded=st.file_uploader("上传 CSV（必需列：Date, Open, High, Low, Close, Volume）",type=["csv"])
    if uploaded:
        try:
            raw=pd.read_csv(uploaded)
            clean=normalize_ohlcv(raw)
            st.success(f"校验通过：{len(clean)} 行；日期 {clean.index.min().date()} 至 {clean.index.max().date()}；重复日期保留最后一条。")
            st.dataframe(clean.tail(10),use_container_width=True)
            if st.button("在本次会话使用此 CSV"):
                st.session_state.setdefault("uploaded_prices",{})[upload_symbol]=clean
                st.success("已在当前会话暂存。云端重启后不会保留。")
        except Exception as exc: st.error(f"CSV 校验失败：{exc}")
    st.subheader("品种状态")
    if st.button("逐一检查全部品种行情状态"):
        results=[]; progress=st.progress(0)
        for i,mkt in enumerate(markets):
            prices,state,reason=retrieve(mkt["symbol"],period,force=True)
            results.append({"代码":mkt["symbol"],"品种":mkt["name_zh"],"分类":mkt["category"],"数据源":mkt["source"],"启用":mkt["enabled"],"状态":state,"最新有效日期":str(prices.index[-1].date()) if prices is not None and not prices.empty else "—","原因":reason})
            progress.progress((i+1)/len(markets))
        st.session_state["market_status_report"]=pd.DataFrame(results)
    status_report=st.session_state.get("market_status_report")
    if status_report is not None:
        st.dataframe(status_report,hide_index=True,use_container_width=True)
    else:
        st.dataframe(pd.DataFrame([{"代码":m["symbol"],"品种":m["name_zh"],"分类":m["category"],"数据源":m["source"],"启用":m["enabled"],"状态":"尚未请求","最新有效日期":"—","原因":"点击上方按钮逐个检查"} for m in markets]),hide_index=True,use_container_width=True)
    st.info("免费行情可能有延迟、历史缺口、连续合约滚动调整和覆盖限制。上传文件只在当前 Streamlit 会话内存中使用，不写入云端永久磁盘。")
