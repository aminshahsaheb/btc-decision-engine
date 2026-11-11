import plotly.graph_objects as go
import streamlit as st

from src.data import load_all
from src.decision import decide
from src.engine import indicators
from src.journal import input_fingerprint, recent_decisions, save_analysis

st.set_page_config(page_title="BTC Decision Engine v0.3", page_icon="₿", layout="wide")
st.title("BTC Decision Engine")
st.caption("v0.3 (در حال توسعه و اعتبارسنجی‌نشده) | کندل بسته‌شده | دادهٔ عمومی Binance Futures | بدون ثبت سفارش")


def fmt(value, spec):
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return "—"


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
    run = st.button("دریافت داده و تحلیل", type="primary", width="stretch")

st.info("این نسخه فقط دادهٔ عمومی می‌خواند. هیچ API Key لازم نیست و هیچ سفارشی ثبت نمی‌کند.")

if run or "result_v3" not in st.session_state:
    try:
        with st.spinner("دریافت کندل‌ها و داده‌های مشتقات..."):
            market, deriv = load_all()
            cfg = {
                "equity": equity, "risk_pct": risk_pct, "fee_pct_side": fee,
                "slippage_pct_side": slip, "max_leverage": leverage,
                "min_net_rr": min_rr, "min_adx": min_adx,
                "min_volume_ratio": min_vol, "min_atr_pct": min_atr,
                "max_atr_pct": max_atr,
            }
            result = decide(market, deriv, cfg)
            saved = save_analysis(result, cfg, input_fingerprint(market, deriv, cfg))
            st.session_state.market_v3 = market
            st.session_state.deriv_v3 = deriv
            st.session_state.result_v3 = result
            st.session_state.saved_v3 = saved
    except Exception as e:
        st.error(f"دریافت یا تحلیل داده ناموفق بود (هیچ تحلیلی ثبت نشد): {type(e).__name__}: {e}")
        st.stop()

result = st.session_state.result_v3
market = st.session_state.market_v3
deriv = st.session_state.deriv_v3
saved = st.session_state.saved_v3
label = result["label"]

if label.endswith("SETUP"):
    st.success(label)
elif label == "NO TRADE":
    st.error(label)
elif label == "WAIT":
    st.warning("WAIT — فعلاً ورود نکن")
else:
    st.info(label)

if result.get("error"):
    st.error(f"خطای غیرمنتظره (تصمیم بسته شد): {result['error']}")

direction = result["direction"]
c = st.columns(4)
c[0].metric("وضعیت داده", result["data"]["status"])
c[1].metric("وضعیت بازار", result["market"]["status"])
c[2].metric("جهت", direction["status"])
c[2].caption(f"امتیاز صعود / نزول: {direction['bull']} / {direction['bear']} (احتمال آماری نیست)")
c[3].metric("وضعیت ستاپ", result["setup"]["status"])

reasons = (
    list(result["data"].get("reasons", []))
    + list(result["market"].get("reasons", []))
    + list(result["setup"].get("reasons", []))
)
if reasons:
    st.write("**دلایل:**")
    for reason in reasons:
        st.write(f"- {reason}")

with st.expander("شواهد جهت"):
    st.write("صعودی:", direction.get("bull_evidence", []))
    st.write("نزولی:", direction.get("bear_evidence", []))

df = indicators(market["15m"]).dropna()
if not df.empty:
    last = df.iloc[-1]
    st.subheader("شواهد بازار")
    m = st.columns(4)
    m[0].metric("آخرین قیمت بسته‌شده", fmt(last["close"], ",.2f"))
    m[1].metric("RSI / ADX", f'{fmt(last["rsi"], ".1f")} / {fmt(last["adx"], ".1f")}')
    m[2].metric("ATR %", fmt(last["atr_pct"], ".3f") + "%")
    m[3].metric("نسبت حجم", fmt(last["vol_ratio"], ".2f"))
    m = st.columns(4)
    m[0].metric("Funding", fmt(float(deriv["funding_rate"]) * 100, ".4f") + "%")
    m[1].metric("دفتر سفارش", fmt(deriv["book_imbalance"], "+.3f"))
    m[2].metric("Open Interest", fmt(deriv["open_interest"], ",.2f"))
    m[3].metric("زمان کندل (UTC)", str(last["time"])[:16])
    st.caption("دفتر سفارش و Funding فقط snapshot هستند و جهت آینده را ثابت نمی‌کنند.")

plan = result["setup"].get("plan")
if plan and "entry" in plan:
    ok = plan.get("status") == "OK"
    st.subheader("برنامهٔ معامله" if ok else f"برنامهٔ ردشده ({plan.get('status')})")
    p = st.columns(6)
    p[0].metric("Entry", fmt(plan.get("entry"), ",.2f"))
    p[1].metric("Stop", fmt(plan.get("stop"), ",.2f"))
    p[2].metric("Target 1", fmt(plan.get("target1"), ",.2f"))
    p[3].metric("Target 2", fmt(plan.get("target2"), ",.2f"))
    p[4].metric("Net R:R", fmt(plan.get("net_rr"), ".2f"))
    p[5].metric("Qty (تخمینی)", fmt(plan.get("quantity_estimate"), ".5f") + " BTC")
    st.caption(
        "مقدار تخمینی است و قابل اجرا نیست: گام حجم، حداقل سفارش و حداقل notional "
        "قرارداد هنوز اعمال نمی‌شود."
    )

if not df.empty:
    st.subheader("نمودار 15 دقیقه")
    view = df.tail(180)
    fig = go.Figure([go.Candlestick(
        x=view.time, open=view.open, high=view.high, low=view.low, close=view.close, name="BTC")])
    fig.add_trace(go.Scatter(x=view.time, y=view.ema20, name="EMA 20"))
    fig.add_trace(go.Scatter(x=view.time, y=view.ema50, name="EMA 50"))
    if plan and "entry" in plan:
        for key, name in [("entry", "Entry"), ("stop", "Stop"),
                          ("target1", "Target 1"), ("target2", "Target 2")]:
            if key in plan:
                fig.add_hline(y=plan[key], line_dash="dash", annotation_text=name)
    fig.update_layout(height=570, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, width="stretch")

st.subheader("دفتر ثبت تصمیم‌ها")
if saved["duplicate"]:
    st.caption(f"ورودی دقیقاً مشابه تحلیل #{saved['id']} بود و دوباره ثبت نشد.")
else:
    st.caption(f"تحلیل #{saved['id']} ثبت شد.")
st.dataframe(recent_decisions(), width="stretch", hide_index=True)
st.caption("این نسخه بک‌تست، walk-forward و Paper Trading ندارد و برای معامله با پول واقعی تأیید نشده است.")
