import requests
import pandas as pd
import numpy as np
import time
from ta.volatility import AverageTrueRange


bot_token = '7570184245:AAE7OWZlAgr933j660Asx2GIHPTa6stftEs'
chat_id = '668694490'
url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
last_trend = None


# === Step 1: Fetch 1-minute candlestick data from Delta Exchange ===
def fetch_candles():
    end_time = int(time.time())
    start_time = end_time - (200 * 60)
    url = 'https://api.delta.exchange/v2/history/candles'
    params = {
        "symbol": "BTCUSDT",
        "resolution": "1m",
        "start": start_time,
        "end": end_time
    }
    response = requests.get(url, params=params)
    #print(response.json())
    data = response.json()['result']

    # Create DataFrame
    df = pd.DataFrame(data, columns=["close", "high", "low", "open", "time", "volume"])
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["time"] = df["time"].dt.tz_convert("Asia/Kolkata")
    #df.set_index('time', inplace=True)
    df = df.sort_values("time")
    #print(df["time"])
    print(len(df))
    return df


# === Step 2: Calculate SuperTrend ===
def calculate_supertrend(df, atr_period=16, multiplier=1.5):
    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=atr_period).average_true_range()
    df['ATR'] = atr
    hl2 = (df['high'] + df['low']) / 2
    df['UpperBand'] = hl2 + (multiplier * df['ATR'])
    df['LowerBand'] = hl2 - (multiplier * df['ATR'])
    df['SuperTrend'] = np.nan
    df['Trend'] = True  # True for uptrend, False for downtrend

    for i in range(atr_period, len(df)):
        curr_close = df['close'].iat[i]
        prev_close = df['close'].iat[i - 1]
        upper_band = df['UpperBand'].iat[i]
        lower_band = df['LowerBand'].iat[i]
        prev_supertrend = df['SuperTrend'].iat[i - 1] if i > atr_period else 0
        prev_trend = df['Trend'].iat[i - 1]

        # Check for trend reversal
        if curr_close > df['UpperBand'].iat[i - 1]:
            trend = True
        elif curr_close < df['LowerBand'].iat[i - 1]:
            trend = False
        else:
            trend = prev_trend

        # Set SuperTrend based on current trend
        if trend:
            # In uptrend, use lower band
            supertrend = lower_band
            # But make sure we don't decrease SuperTrend
            if prev_trend and i > atr_period:
                supertrend = max(supertrend, prev_supertrend)
        else:
            # In downtrend, use upper band
            supertrend = upper_band
            # But don't raise SuperTrend during downtrend
            if not prev_trend and i > atr_period:
                supertrend = min(supertrend, prev_supertrend)

        df.at[df.index[i], 'Trend'] = trend
        df.at[df.index[i], 'SuperTrend'] = supertrend

    df['Trend'] = df['Trend'].map({True: 'up', False: 'down'})
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


def main():
    while True:
        # === Step 3: Run it ===
        df = fetch_candles()
        df = calculate_supertrend(df)

        # Show the last few rows with SuperTrend and Trend direction
        print(df[['time','close', 'SuperTrend', 'Trend']].tail(20))
        #print(df.tail(10))
        last = df.iloc[-1]
        trend_str = "🟢 Uptrend" if last["Trend"]=='up' else "🔴 Downtrend"

        message=(
            f"\n🕒 Time: {last['time']}\n"
            f"💰 Close Price: {last['close']}\n"
            f"📈 SuperTrend: {round(last['SuperTrend'], 2)}\n"
            f"📊 Trend: {trend_str}"
        )
        print(f"🕒 Time: {last['time']}")
        print(f"💰 Close Price: {last['close']}")
        print(f"📈 SuperTrend: {round(last['SuperTrend'], 2)}")
        print(f"📊 Trend: {trend_str}")
        send_notification_to_telegram(message, last["Trend"])
        time.sleep(50)

if __name__ == '__main__':
    main()
