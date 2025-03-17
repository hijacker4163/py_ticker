def calculate_macd(stock_data):
    # 計算 12日和 26日指數移動平均線 (EMA)
    stock_data['EMA_12'] = stock_data['Close'].ewm(span=12, adjust=False).mean()  # 快速線
    stock_data['EMA_26'] = stock_data['Close'].ewm(span=26, adjust=False).mean()  # 慢速線

    # 計算 MACD 線和信號線
    stock_data['MACD'] = stock_data['EMA_12'] - stock_data['EMA_26']  # MACD線
    stock_data['Signal_Line'] = stock_data['MACD'].ewm(span=9, adjust=False).mean()  # 信號線

    # 判斷是否為買入或賣出信號
    latest_macd = stock_data['MACD'].iloc[-1]
    latest_signal = stock_data['Signal_Line'].iloc[-1]
    
    # 如果 MACD 線穿越信號線，則為買入或賣出信號
    if latest_macd > latest_signal:
        return "買入"
    elif latest_macd < latest_signal:
        return "賣出"
    else:
        return "無明確信號"
    
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
