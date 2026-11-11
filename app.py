import streamlit as st
import plotly.graph_objects as go
from src.data import load_all
from src.engine import indicators, analyze
from src.journal import save_decision, recent_decisions

st.set_page_config(page_title="BTC Decision Engine v0.2", page_icon="₿", layout="wide")
st.title("BTC Decision Engine")
st.caption("v0.2 | تحلیل کندل بسته‌شده | دادهٔ عمومی Binance Futures | بدون ثبت سفارش")

with st.sidebar:
    st.header("تنظیمات")
    equity = st.number_input("سرمایه (USDT)", min_value=10.0, value=1000.0, step=100.0)
    risk_pct = st.number_input("ریسک هر معامله (%)", min_value=0.1, max_value=2.0, value=0.5, step=0.1)
    fee = st.number_input("کارمزد هر سمت (%)", min_value=0.0, value=0.05, step=0.01)
    slip = st.number_input("لغزش هر سمت (%)", min_value=0.0, value=0.03, step=0.01)
    leverage = st.number_input("حداکثر اهرم", min_value=1.0, max_value=10.0, value=2.0, step=0.5)
    min_rr = st.number_input("حداقل Net R:R", min_value=1.0, max_value=5.0, value=1.5, step=0.1)
    min_adx = st.number_input("حداقل ADX", min_value=5.0, max_value=50.0, value=18.0, step=1.0)
    min_vol = st.number_input("حداقل نسبت حجم", min_value=0.1, max_value=3.0, value=0.8, step=0.1)
    min_atr = st.number_input("حداقل ATR (%)", min_value=0.01, max_value=1.0, value=0.05, step=0.01)
    max_atr = st.number_input("حداکثر ATR (%)", min_value=0.2, max_value=5.0, value=1.2, step=0.1)
    run = st.button("دریافت داده و تحلیل", type="primary", use_container_width=True)

st.info("این نسخه فقط دادهٔ عمومی می‌خواند. هیچ API Key خصوصی یا دسترسی حساب لازم ندارد و هیچ سفارشی ثبت نمی‌کند.")

if run or "result_v2" not in st.session_state:
    try:
        with st.spinner("دریافت کندل‌ها و داده‌های مشتقات..."):
            market, deriv = load_all()
            cfg = {"equity":equity, "risk_pct":risk_pct, "fee_pct_side":fee,
                   "slippage_pct_side":slip, "max_leverage":leverage,
                   "min_net_rr":min_rr, "min_adx":min_adx,
                   "min_volume_ratio":min_vol, "min_atr_pct":min_atr,
                   "max_atr_pct":max_atr}
            result = analyze(market, deriv, cfg)
            st.session_state.market_v2 = market
            st.session_state.deriv_v2 = deriv
            st.session_state.result_v2 = result
            st.session_state.cfg_v2 = cfg
            save_decision(result)
    except Exception as e:
        st.error(f"دریافت یا تحلیل داده ناموفق بود: {type(e).__name__}: {e}")
        st.stop()

result = st.session_state.result_v2
decision = result.get("decision","NO TRADE")
if decision.endswith("SETUP"):
    st.success(decision)
elif decision == "WAIT":
    st.warning("WAIT — فعلاً ورود نکن")
else:
    st.error(decision)

st.write("**دلیل تصمیم:**", result.get("reason",""))
if "price" in result:
    c = st.columns(5)
    for col, (label, value) in zip(c, [
        ("آخرین قیمت بسته‌شده", f'{result["price"]:,.2f}'),
        ("رژیم بازار", result.get("regime","—")),
        ("جهت", result.get("bias","—")),
        ("امتیاز صعود / نزول", f'{result.get("bull",0)} / {result.get("bear",0)}'),
        ("زمان کندل (UTC)", str(result.get("candle_time","—"))[:16])
    ]):
        col.metric(label, value)

    st.subheader("شواهد بازار")
    c = st.columns(4)
    for col, (label, value) in zip(c, [
        ("1h", result.get("h1","—")), ("4h", result.get("h4","—")),
        ("ساختار 15m", result.get("structure","—")),
        ("RSI / ADX", f'{result.get("rsi",0):.1f} / {result.get("adx",0):.1f}')
    ]):
        col.metric(label, value)
    c = st.columns(4)
    for col, (label, value) in zip(c, [
        ("ATR %", f'{result.get("atr_pct",0):.3f}%'),
        ("نسبت حجم", f'{result.get("vol_ratio",0):.2f}'),
        ("Funding", f'{result.get("funding_rate",0)*100:.4f}%'),
        ("دفتر سفارش", f'{result.get("book_imbalance",0):+.3f}')
    ]):
        col.metric(label, value)
    st.caption("Open Interest: " + f'{result.get("open_interest",0):,.2f} BTC contracts (snapshot only; change/trend not yet computed)')

if "entry" in result:
    st.subheader("برنامهٔ معامله")
    c = st.columns(6)
    for col, (label, value) in zip(c, [
        ("Entry", f'{result["entry"]:,.2f}'), ("Stop", f'{result["stop"]:,.2f}'),
        ("Target 1", f'{result["target1"]:,.2f}'), ("Target 2", f'{result["target2"]:,.2f}'),
        ("Net R:R", f'{result["net_rr"]:.2f}'),
        ("Qty estimate", f'{result["quantity_estimate"]:.5f} BTC')
    ]):
        col.metric(label, value)
    st.caption(f'ریسک نقدی تخمینی: {result["risk_cash_estimate"]:.2f} USDT | ارزش اسمی: {result["notional_estimate"]:.2f} USDT')

st.subheader("نمودار 15 دقیقه")
df = indicators(st.session_state.market_v2["15m"]).dropna().tail(180)
fig = go.Figure([go.Candlestick(x=df.time, open=df.open, high=df.high, low=df.low, close=df.close, name="BTC")])
fig.add_trace(go.Scatter(x=df.time, y=df.ema20, name="EMA 20"))
fig.add_trace(go.Scatter(x=df.time, y=df.ema50, name="EMA 50"))
if "entry" in result:
    for y, label in [(result["entry"],"Entry"),(result["stop"],"Stop"),(result["target1"],"Target 1"),(result["target2"],"Target 2")]:
        fig.add_hline(y=y, line_dash="dash", annotation_text=label)
fig.update_layout(height=570, xaxis_rangeslider_visible=False, margin=dict(l=10,r=10,t=20,b=10))
st.plotly_chart(fig, use_container_width=True)

st.subheader("دفتر ثبت تصمیم‌ها")
st.dataframe(recent_decisions(), use_container_width=True, hide_index=True)
st.caption("محدودیت: دفتر سفارش فقط یک عکس لحظه‌ای است؛ Funding و Open Interest فعلاً snapshot هستند. این‌ها به‌تنهایی جهت آینده را ثابت نمی‌کنند. امتیازها احتمال آماری نیستند. نسخه هنوز بک‌تست و Paper Trading مستقل ندارد.")
