import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta

candle_interval = 15

bot_token = '7570184245:AAE7OWZlAgr933j660Asx2GIHPTa6stftEs'
chat_id = '-1002558840727'
url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
last_trend = None


def fetch_candles():
    end_time = int(time.time())
    start_time = end_time - 2000 * 60 * candle_interval  # Fetch ~2000 candle interval time candles
    url = "https://api.delta.exchange/v2/history/candles"
    params = {
        "symbol": "BTCUSDT",
        "resolution": f"{candle_interval}m",
        "start": start_time,
        "end": end_time
    }
    response = requests.get(url, params=params)
    data = response.json()['result']

    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["time"] = df["time"].dt.tz_convert("Asia/Kolkata")
    df.set_index('time', inplace=True)
    df = df[['high', 'low', 'close']].astype(float)
    df = df.sort_values("time")
    return df

def calculate_rma(series, period):
    rma = [np.nan] * len(series)
    rma[period - 1] = np.mean(series.iloc[:period])
    alpha = 1 / period
    for i in range(period, len(series)):
        rma[i] = alpha * series.iloc[i] + (1 - alpha) * rma[i - 1]
    return pd.Series(rma, index=series.index)


def calculate_supertrend(df, period, multiplier):
    df = df.copy()
    hl2 = (df['high'] + df['low']) / 2
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)

    atr = calculate_rma(tr, period)

    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr

    supertrend = [np.nan] * len(df)
    direction = [0] * len(df)

    for i in range(period, len(df)):
        prev_upper = upperband.iloc[i - 1]
        prev_lower = lowerband.iloc[i - 1]
        prev_supertrend = supertrend[i - 1]
        close_prev = df['close'].iloc[i - 1]

        # Band continuation logic
        if lowerband.iloc[i] < prev_lower and close_prev > prev_lower:
            lowerband.iloc[i] = prev_lower
        if upperband.iloc[i] > prev_upper and close_prev < prev_upper:
            upperband.iloc[i] = prev_upper


        # Trend direction logic
        if np.isnan(prev_supertrend):
            direction[i] = -1  # Assume down at first
        elif prev_supertrend == prev_upper:
            direction[i] = -1 if df['close'].iloc[i] > upperband.iloc[i] else 1
        else:
            direction[i] = 1 if df['close'].iloc[i] < lowerband.iloc[i] else -1

        supertrend[i] = lowerband.iloc[i] if direction[i] == -1 else upperband.iloc[i]

    df['SuperTrend'] = supertrend
    df['Direction'] = direction
    return df

def send_notification_to_telegram(message, current_trend):
    global last_trend
    if last_trend is None:
        last_trend = current_trend
    elif current_trend != last_trend:
        print(f"prev Trend :{last_trend}  -- current trend :{current_trend}")
        last_trend = current_trend
        send_to_telegram(message)

def send_to_telegram(message):
    #message = '✅ Live test successful! Message sent from Python 🐍'
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    telegram_res = requests.post(url, data=payload)
    print(telegram_res.status_code)
    #print(telegram_res.text)

def run_live_supertrend():
    while True:
        df = fetch_candles()
        df = calculate_supertrend(df, period=16, multiplier=1.5)
        last_row = df.iloc[-1]
        print(f"{last_row.name} | Close: {last_row['close']:.2f} | SuperTrend: {last_row['SuperTrend']:.2f} | Trend: {'Up' if last_row['Direction'] == -1 else 'Down'}")
        trend_str = "🟢 Uptrend" if last_row['Direction'] == -1 else "🔴 Downtrend"
        message = (
            f"\n Alert Set on Time Frame of : {candle_interval} min \n"
            f"\n🕒 Time: {last_row.name}\n"
            f"💰 Close Price: {last_row['close']}\n"
            f"📈 SuperTrend: {round(last_row['SuperTrend'],2)}\n"
            f"📊 Trend Changed To : {trend_str}"
        )
        send_notification_to_telegram(message, last_row['Direction'])
        time.sleep(60*candle_interval)

# Uncomment to run
run_live_supertrend()
