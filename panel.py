import time

import streamlit as st

from src.data import load_all
from src.decision import decide
from src.engine import indicators
from src.risk_calc import position_size

REFRESH_SECONDS = 60
WARNING_TEXT = {
    "WIDE_STOP": "فاصلهٔ استاپ بیش از ۲.۵٪ قیمت است.",
    "LEVERAGE_CAPPED": "حجم به‌خاطر سقف اهرم کم شد؛ ریسک واقعی کمتر از بودجه است.",
}

st.set_page_config(page_title="BTC Panel", page_icon="₿", layout="centered")
st.title("BTC Panel")
st.caption("فقط‌خواندنی | هر ۶۰ ثانیه به‌روز می‌شود | چیزی ثبت نمی‌شود | v0.3 اعتبارسنجی‌نشده")


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

cfg = {
    "equity": equity, "risk_pct": risk_pct, "fee_pct_side": fee,
    "slippage_pct_side": slip, "max_leverage": leverage,
    "min_net_rr": min_rr, "min_adx": min_adx,
    "min_volume_ratio": min_vol, "min_atr_pct": min_atr,
    "max_atr_pct": max_atr,
}


@st.fragment(run_every=REFRESH_SECONDS)
def live(cfg):
    try:
        market, deriv = load_all()
        result = decide(market, deriv, cfg)
    except Exception as exc:
        st.error(f"دریافت داده ناموفق بود (هیچ تصمیمی نمایش داده نمی‌شود): {type(exc).__name__}: {exc}")
        st.caption(f"آخرین تلاش: {time.strftime('%H:%M:%S')}")
        return

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
    c[0].metric("داده", result["data"]["status"])
    c[1].metric("بازار", result["market"]["status"])
    c[2].metric("جهت", direction["status"])
    c[3].metric("ستاپ", result["setup"]["status"])
    st.caption(f"امتیاز صعود / نزول: {direction['bull']} / {direction['bear']} (احتمال آماری نیست)")

    reasons = (list(result["data"].get("reasons", []))
               + list(result["market"].get("reasons", []))
               + list(result["setup"].get("reasons", [])))
    for reason in reasons:
        st.write(f"- {reason}")

    df = indicators(market["15m"]).dropna()
    if not df.empty:
        last = df.iloc[-1]
        m = st.columns(4)
        m[0].metric("قیمت (کندل بسته)", fmt(last["close"], ",.1f"))
        m[1].metric("RSI / ADX", f'{fmt(last["rsi"], ".0f")} / {fmt(last["adx"], ".0f")}')
        m[2].metric("ATR %", fmt(last["atr_pct"], ".2f") + "%")
        m[3].metric("نسبت حجم", fmt(last["vol_ratio"], ".2f"))
        m = st.columns(3)
        m[0].metric("Funding", fmt(float(deriv["funding_rate"]) * 100, ".4f") + "%")
        m[1].metric("دفتر سفارش", fmt(deriv["book_imbalance"], "+.2f"))
        m[2].metric("کندل (UTC)", str(last["time"])[11:16])

    plan = result["setup"].get("plan")
    if plan and "entry" in plan:
        st.subheader("برنامهٔ موتور" if plan.get("status") == "OK" else f"برنامهٔ ردشده ({plan.get('status')})")
        p = st.columns(4)
        p[0].metric("Entry", fmt(plan.get("entry"), ",.1f"))
        p[1].metric("Stop", fmt(plan.get("stop"), ",.1f"))
        p[2].metric("Target 1", fmt(plan.get("target1"), ",.1f"))
        p[3].metric("Target 2", fmt(plan.get("target2"), ",.1f"))
        st.caption(f"Net R:R {fmt(plan.get('net_rr'), '.2f')} | حجم تخمینی {fmt(plan.get('quantity_estimate'), '.4f')} BTC | قابل اجرا نیست")

    st.caption(f"آخرین به‌روزرسانی: {time.strftime('%H:%M:%S')} (ساعت لپ‌تاپ)")


live(cfg)

st.divider()
st.subheader("ماشین‌حساب حجم")
st.caption("ورود و استاپ خودت را بده. نتیجه تخمینی است: مشخصات قرارداد و قیمت لیکوئید شدن اعمال نمی‌شود.")
side = st.radio("جهت", ["LONG", "SHORT"], horizontal=True)
entry = st.number_input("قیمت ورود", min_value=0.0, value=0.0, step=10.0, format="%.1f")
stop = st.number_input("قیمت استاپ", min_value=0.0, value=0.0, step=10.0, format="%.1f")
if entry > 0 and stop > 0:
    calc = position_size(side, entry, stop, equity, risk_pct, fee, slip, leverage)
    if calc["status"] != "OK":
        st.error(calc["reason"])
    else:
        q = st.columns(4)
        q[0].metric("حجم تخمینی (BTC)", fmt(calc["quantity_estimate"], ".4f"))
        q[1].metric("ریسک (USDT)", fmt(calc["risk_cash_estimate"], ".2f"))
        q[2].metric("ارزش اسمی (USDT)", fmt(calc["notional_estimate"], ",.0f"))
        q[3].metric("فاصلهٔ استاپ", fmt(calc["stop_pct"], ".2f") + "%")
        t = st.columns(3)
        t[0].metric("1R", fmt(calc["target_1r"], ",.1f"))
        t[1].metric("2R", fmt(calc["target_2r"], ",.1f"))
        t[2].metric("3R", fmt(calc["target_3r"], ",.1f"))
        st.caption(f"هزینهٔ رفت‌وبرگشت (کارمزد + لغزش): {fmt(calc['cost_estimate'], '.2f')} USDT")
        for code in calc["warnings"]:
            st.warning(WARNING_TEXT.get(code, code))
