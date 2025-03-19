import yfinance as yf

from twstock import Stock
from twstock import BestFourPoint
import twstock

import matplotlib.pyplot as plt

def get_stock_data(ticker, period="60d", interval="1d"):
    twTicker = f"{ticker}.TW"
    stock_data = yf.download(twTicker, period=period, interval=interval)  # 最近60天資料
    return stock_data

def get_four_points(ticker):
    # 解析四大買賣點
    tw_stock = Stock(str(ticker))
    bfp = BestFourPoint(tw_stock)
    buy_reason = bfp.best_four_point_to_buy()  # 判斷是否為四大買點
    sell_reason = bfp.best_four_point_to_sell()  # 判斷是否為四大賣點
    complex_reason = bfp.best_four_point()
    return buy_reason, sell_reason, complex_reason

def calculate_macd(stock_data):
    # 計算 12 日和 26 日指數移動平均線 (EMA)
    stock_data['EMA_12'] = stock_data['Close'].ewm(span=12, adjust=False).mean()
    stock_data['EMA_26'] = stock_data['Close'].ewm(span=26, adjust=False).mean()

    # 計算 MACD 線與信號線
    stock_data['MACD'] = stock_data['EMA_12'] - stock_data['EMA_26']
    stock_data['DEA'] = stock_data['MACD'].ewm(span=9, adjust=False).mean()    
    
    # 計算 MACD 柱狀圖 (Histogram)
    # stock_data['Histogram'] = stock_data['MACD'] - stock_data['DEA']
    # 計算 MACD 差值
    stock_data['DIFF'] = stock_data['MACD'] - stock_data['DEA']  
    
    msg = "\n最近一次"
    """尋找最近一次 MACD 交叉點"""
    for i in range(len(stock_data) - 1, 1, -1):  # 從最新數據往回找
        prev_macd, prev_signal = stock_data['MACD'].iloc[i - 1], stock_data['DEA'].iloc[i - 1]
        curr_macd, curr_signal = stock_data['MACD'].iloc[i], stock_data['DEA'].iloc[i]
        date = stock_data.index[i].strftime('%Y-%m-%d')
        # 黃金交叉 (MACD 由下往上穿越 Signal)
        if prev_macd < prev_signal and curr_macd > curr_signal:
            print( stock_data.index[i], "⚡ 黃金交叉")
            msg = f"{msg}({date})：⚡ 黃金交叉\n"
            break
        
        # 死亡交叉 (MACD 由上往下穿越 Signal)
        if prev_macd > prev_signal and curr_macd < curr_signal:
            print( stock_data.index[i], "💀 死亡交叉")
            msg = f"{msg}({date})：💀 死亡交叉\n"
            break


    """檢查 MACD 是否即將發生交叉"""
    prev_diff = stock_data['DIFF'].iloc[-2]  # 前一天 Diff
    curr_diff = stock_data['DIFF'].iloc[-1]  # 當天 Diff
    
    threshold=0.05
    # 檢查交叉門檻
    if abs(curr_diff) < threshold:
        if prev_diff < 0 and curr_diff > 0:
            msg = msg + "目前：⚡ 即將發生黃金交叉(買入)"                        
        elif prev_diff > 0 and curr_diff < 0:
            msg = msg + "目前：💀 即將發生死亡交叉(賣出)"
    else:
        msg = msg + "目前：⏳ 尚未接近交叉"
    
    return msg

    # return stock_data

    # # 至少需要兩筆資料才能比對交叉
    # if len(stock_data) < 2:
    #     return "無明確信號"

    # # 前一筆與當前筆
    # prev_macd = stock_data['MACD'].iloc[-2]
    # prev_signal = stock_data['Signal_Line'].iloc[-2]
    # curr_macd = stock_data['MACD'].iloc[-1]
    # curr_signal = stock_data['Signal_Line'].iloc[-1]

    # # 判斷交叉情形
    # if prev_macd <= prev_signal and curr_macd > curr_signal:
    #     return "買入"
    # elif prev_macd >= prev_signal and curr_macd < curr_signal:
    #     return "賣出"
    # else:
    #     return "無明確信號"
    
def calculate_rsi(stock_data, period=14):
    # 計算價格變動
    stock_data['Price_Change'] = stock_data['Close'].diff()

    # 計算增幅和減幅
    stock_data['Gain'] = stock_data['Price_Change'].apply(lambda x: x if x > 0 else 0)
    stock_data['Loss'] = stock_data['Price_Change'].apply(lambda x: -x if x < 0 else 0)

    # 計算平均增幅與減幅
    stock_data['Avg_Gain'] = stock_data['Gain'].rolling(window=period).mean()
    stock_data['Avg_Loss'] = stock_data['Loss'].rolling(window=period).mean()

    # 計算相對強度 (RS)
    stock_data['RS'] = stock_data['Avg_Gain'] / stock_data['Avg_Loss']

    # 計算 RSI
    stock_data['RSI'] = 100 - (100 / (1 + stock_data['RS']))

    # 取得最新的 RSI 值
    latest_rsi = stock_data['RSI'].iloc[-1]
    return latest_rsi

def calculate_bollinger_bands(stock_data, window=20):
    # 計算簡單移動平均 (SMA)
    stock_data['SMA'] = stock_data['Close'].rolling(window=window).mean()

    # 計算標準差
    stock_data['STD'] = stock_data['Close'].rolling(window=window).std()

    # 計算布林帶
    stock_data['Upper_Band'] = stock_data['SMA'] + (2 * stock_data['STD'])  # 上軌
    stock_data['Lower_Band'] = stock_data['SMA'] - (2 * stock_data['STD'])  # 下軌

    # 取得最後一天的布林帶資料
    latest_close = stock_data['Close'].iloc[-1].values[0]  # 轉換為純數值
    print("latest_close = ",latest_close)
    latest_sma = stock_data['SMA'].iloc[-1]
    print("latest_sma = ",latest_sma)
    latest_upper_band = stock_data['Upper_Band'].iloc[-1]
    print("latest_upper_band = ",latest_upper_band)
    latest_lower_band = stock_data['Lower_Band'].iloc[-1]
    print("latest_lower_band = ",latest_lower_band)
    
     # 判斷買入、賣出或持有信號
    if latest_close > latest_upper_band:
        decision = "賣出：股價突破上軌，可能過高"
    elif latest_close < latest_lower_band:
        decision = "買入：股價突破下軌，可能過低"
    else:
        decision = "持有：股價在上下軌之間，觀望中"

    return latest_sma, latest_upper_band, latest_lower_band, decision

# 成交量均線 (Moving Average of Volume, MAV)
def calculate_mav(stock_data, window=20):
    stock_data['MAV'] = stock_data['Volume'].rolling(window=window).mean()
    latest_volume = stock_data['Volume'].iloc[-1].values[0]  # 取得最後一天的成交量
    latest_mav = stock_data['MAV'].iloc[-1]  # 取得最後一天的成交量均線
    return latest_volume, latest_mav

# 成交量比 (Volume Ratio)
def calculate_volume_ratio(stock_data, window=20):
    average_volume = stock_data['Volume'].rolling(window=window).mean().iloc[-1]
    latest_volume = stock_data['Volume'].iloc[-1]
    return latest_volume / average_volume

# 成交量價格趨勢 (Price-Volume Trend, PVT)
def calculate_pvt(stock_data):
    stock_data['PVT'] = (stock_data['Volume'] * (stock_data['Close'].pct_change())).cumsum()
    return stock_data['PVT'].iloc[-1]

# 成交量震盪指標 (Chaikin Money Flow, CMF)
def calculate_cmf(stock_data, window=20):
    money_flow = (stock_data['Close'] - stock_data['Low']) - (stock_data['High'] - stock_data['Close'])
    money_flow *= stock_data['Volume']
    cmf = money_flow.rolling(window=window).sum() / stock_data['Volume'].rolling(window=window).sum()
    return cmf.iloc[-1]

# 成交量變化率 (Volume Rate of Change, VROC)
def calculate_vroc(stock_data, window=20):
    vroc = (stock_data['Volume'].pct_change(periods=window) * 100)
    return vroc.iloc[-1]

# 成交量增長指標 (On-Balance Volume, OBV)
def calculate_obv(stock_data):
    obv = stock_data['Volume'] * (stock_data['Close'].diff() > 0).astype(int)
    obv -= stock_data['Volume'] * (stock_data['Close'].diff() < 0).astype(int)
    obv = obv.cumsum()
    latest_obv = obv.iloc[-1].values[0]  # 取得最後一天的 OBV
    previous_obv = obv.iloc[-2].values[0]  # 取前一天的 OBV

    latest_price = stock_data['Close'].iloc[-1].values[0]  # 取得最後一天的收盤價
    previous_price = stock_data['Close'].iloc[- 2].values[0] # 取前一天的收盤價

    return latest_obv, previous_obv, latest_price, previous_price

def decision_based_on_volume(latest_volume, latest_mav, volume_ratio, pvt, cmf, vroc, latest_obv, previous_obv, latest_price, previous_price):
    buy_votes = 0
    sell_votes = 0

    # 1. 成交量均線 (MAV)
    if latest_volume > latest_mav:
        buy_votes += 1
    else:
        sell_votes += 1

    # 2. 成交量比 (Volume Ratio)
    if volume_ratio > 1.5:
        buy_votes += 1
    elif volume_ratio < 0.8:
        sell_votes += 1

    # 3. PVT (成交量價格趨勢)
    if pvt > 0:
        buy_votes += 1
    else:
        sell_votes += 1

    # 4. CMF (成交量震盪指標)
    if cmf > 0:
        buy_votes += 1
    else:
        sell_votes += 1

    # 5. VROC (成交量變化率)
    if vroc > 10:
        buy_votes += 1
    elif vroc < -10:
        sell_votes += 1

    # 6. OBV (成交量增長指標)
    if latest_obv > previous_obv and latest_price < previous_price:
        buy_votes += 1
    elif latest_obv < previous_obv and latest_price > previous_price:
        sell_votes += 1
    else:
        print("No decision")

    # if obv > prev_obv:
    #     buy_votes += 1
    # else:
    #     sell_votes += 1

    # 總結判斷
    if buy_votes > sell_votes:
        return f"🔼 建議買入 (買票數: {buy_votes}, 賣票數: {sell_votes})"
    elif buy_votes < sell_votes:
        return f"🔽 建議賣出 (買票數: {buy_votes}, 賣票數: {sell_votes})"
    else:
        return f"🔁 持觀望態度 (買票數: {buy_votes}, 賣票數: {sell_votes})"

# 測試數據
# latest_volume = 35000000
# latest_mav = 29540154.3
# volume_ratio = 2.154787
# pvt = 10454729.56
# cmf = 0.336658
# vroc = -26.42236
# obv = 60606103
# prev_obv = 60000000  # 之前的 OBV 值 (這需要存歷史數據)


# stock_data = get_stock_data(1102)

# 計算 MACD 與信號線
# stock_data = calculate_macd(stock_data)

# 繪製 MACD 與信號線圖表
# plt.figure(figsize=(14, 7))
# plt.plot(stock_data.index, stock_data['MACD'], label="MACD", color="blue")
# plt.plot(stock_data.index, stock_data['DEA'], label="DEA", color="red")
# plt.bar(stock_data.index, stock_data['DIFF'], label="DIFF", color=['green' if v >= 0 else 'red' for v in stock_data['DIFF']], alpha=0.5)
# plt.title("MACD")
# plt.xlabel("日期")
# plt.ylabel("數值")
# plt.legend()
# plt.xticks(rotation=45)
# plt.grid(True)
# plt.tight_layout()
# plt.show()