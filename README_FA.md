# BTC Decision Engine v0.2 — راهنمای فارسی

## این نسخه چه می‌کند؟
- دریافت رایگان کندل‌های بسته‌شدهٔ BTCUSDT از Binance USD-M Futures
- تحلیل تایم‌فریم 15m، 1h و 4h
- بررسی رژیم بازار، جهت، ساختار سادهٔ شکست محدوده، RSI، ADX، ATR و حجم
- دریافت snapshot عمومی Funding، Open Interest و عدم‌تعادل 20 سطح اول دفتر سفارش
- محاسبهٔ Entry / Stop / دو هدف / Net R:R / حجم تخمینی
- ثبت تصمیم‌ها در فایل محلی SQLite

## نصب و اجرا در Mac
فایل ZIP را در Downloads ذخیره کن و Terminal را باز کن:

```bash
cd ~/Downloads
unzip -o btc_decision_engine_v0_2.zip
cd btc_decision_engine_v0_2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

مرورگر را در صورت نیاز روی http://localhost:8501 باز کن.

## اجرای آزمون‌های اولیه
در Terminal و داخل پوشهٔ پروژه:

```bash
python -m pip install pytest
python -m pytest -q
```

## استفاده
1. تنظیمات هزینه، سرمایه و ریسک را وارد کن.
2. روی «دریافت داده و تحلیل» بزن.
3. اگر خروجی WAIT یا NO TRADE بود، وارد نشو.
4. حتی در صورت LONG/SHORT SETUP، ابتدا Paper Trading انجام بده.

## رایگان بودن
کد و کتابخانه‌ها رایگان‌اند. داده‌ها از API عمومی Binance Futures دریافت می‌شوند و به API Key نیاز ندارند. اتصال به اینترنت لازم است. ممکن است دسترسی API از بعضی شبکه‌ها یا کشورها محدود شود.

## محدودیت‌های مهم
- Funding و Open Interest فعلاً snapshot هستند؛ تغییرات تاریخی آن‌ها هنوز تحلیل نشده است.
- عدم‌تعادل دفتر سفارش یک snapshot از 20 سطح است و می‌تواند سریع تغییر کند.
- ساختار بازار فعلاً شکست 20 کندل قبلی است؛ هنوز الگوریتم کامل swing/pivot و liquidity sweep نیست.
- امتیاز جهت، احتمال آماری نیست.
- اندازهٔ موقعیت تخمینی است و مشخصات قرارداد/گام حجم/حداقل سفارش باید قبل از استفادهٔ واقعی تأیید شود.
- هیچ سفارش یا معامله‌ای ثبت نمی‌شود.
- این نسخه بک‌تست کامل، Walk-Forward یا Paper Trading خودکار ندارد.
- این نسخه برای تصمیم‌گیری با پول واقعی تأیید نشده است.

## ثبت تصمیم
هر بار که تحلیل تازه می‌گیری، تصمیم در `decision_journal.sqlite3` ذخیره می‌شود. این دفتر برای ارزیابی بعدی است و به‌تنهایی سابقهٔ اجرای معامله نیست.
