import yfinance as yf

from twstock import Stock
from twstock import BestFourPoint
import twstock

import matplotlib.pyplot as plt

import requests

def get_stock_data(ticker, period="60d", interval="1d"):
    twTicker = f"{ticker}.TW"
    stock_data = yf.download(twTicker, period=period, interval=interval)  # 最近60天資料
    return stock_data

def get_four_points(ticker):
    try:
        tw_stock = Stock(str(ticker))

        # 確保有足夠資料再繼續
        if len(tw_stock.capacity) < 2:
            return "資料不足", "資料不足", "資料不足"

        bfp = BestFourPoint(tw_stock)
        buy_reason = bfp.best_four_point_to_buy()      # 四大買點
        sell_reason = bfp.best_four_point_to_sell()    # 四大賣點
        complex_reason = bfp.best_four_point()         # 綜合判斷

        return buy_reason, sell_reason, complex_reason

    except Exception as e:
        # 可以記錄錯誤，或回傳錯誤訊息
        return f"錯誤：{e}", f"錯誤：{e}", f"錯誤：{e}"

def calculate_kd(data, k_period=9, d_period=3):
    """
    計算 KD 指標
    data: pandas.DataFrame 必須包含 'High', 'Low', 'Close' 欄位
    k_period: 計算K值用的期間 (例如9天)
    d_period: 計算D值用的期間 (例如3天)
    """

    # 計算最近k_period的最高價、最低價
    low_min = data['Low'].rolling(window=k_period, min_periods=1).min()
    high_max = data['High'].rolling(window=k_period, min_periods=1).max()

    # 計算 RSV (Raw Stochastic Value)
    rsv = (data['Close'] - low_min) / (high_max - low_min) * 100

    # 計算 %K，通常用 RSV 平滑3天，但這裡先用 RSV 本身
    k = rsv.ewm(com=d_period-1, adjust=False).mean()

    # 計算 %D，對 %K 取移動平均
    d = k.ewm(com=d_period-1, adjust=False).mean()

    # 把結果加回原資料
    data['K'] = k
    data['D'] = d

    print(f"data['K'] = {data['K'].iloc[-1]}")
    print(f"data['D'] = {data['D'].iloc[-1]}")

    return data

def check_kd_signal(data):
    """
    判斷黃金交叉與死亡交叉，並在 DataFrame 新增欄位 'signal'，
    1 表示黃金交叉買進訊號，
    -1 表示死亡交叉賣出訊號，
    0 表示無訊號
    """
    signal = []
    for i in range(len(data)):
        if i == 0:
            signal.append(0)  # 第一筆沒法判斷交叉
        else:
            k_today = data['K'].iloc[i]
            d_today = data['D'].iloc[i]
            k_yesterday = data['K'].iloc[i - 1]
            d_yesterday = data['D'].iloc[i - 1]

            if k_yesterday < d_yesterday and k_today > d_today:
                # 黃金交叉
                signal.append(1)
            elif k_yesterday > d_yesterday and k_today < d_today:
                # 死亡交叉
                signal.append(-1)
            else:
                signal.append(0)
    data['signal'] = signal
    return data
    # data = data.reset_index()  # 讓 Ticker 和 Date 變成欄位

    # signal = []
    # for i in range(len(data)):
    #     if i == 0:
    #         signal.append(0)
    #     else:
    #         k_today = data['K'].iloc[i]
    #         d_today = data['D'].iloc[i]
    #         k_yesterday = data['K'].iloc[i - 1]
    #         d_yesterday = data['D'].iloc[i - 1]

    #         if k_yesterday < d_yesterday and k_today > d_today:
    #             # 黃金交叉
    #             signal.append(1)
    #         elif k_yesterday > d_yesterday and k_today < d_today:
    #             # 死亡交叉
    #             signal.append(-1)
    #         else:
    #             signal.append(0)

    # data['signal'] = signal
    # return data  # 傳回已 reset index 的資料


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
            # print( stock_data.index[i], "⚡ 黃金交叉")
            msg = f"{msg}({date})：⚡ 黃金交叉\n"
            break
        
        # 死亡交叉 (MACD 由上往下穿越 Signal)
        if prev_macd > prev_signal and curr_macd < curr_signal:
            # print( stock_data.index[i], "💀 死亡交叉")
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
            msg = msg + f"[1]目前：⏳ 尚未接近交叉，前一天 Diff={round(prev_diff,3)}, 當天 Diff={round(curr_diff,3)}" 
    else:
        msg = msg + "[2]目前：⏳ 尚未接近交叉"
    
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
    # print("latest_close = ",latest_close)
    latest_sma = stock_data['SMA'].iloc[-1]
    # print("latest_sma = ",latest_sma)
    latest_upper_band = stock_data['Upper_Band'].iloc[-1]
    # print("latest_upper_band = ",latest_upper_band)
    latest_lower_band = stock_data['Lower_Band'].iloc[-1]
    # print("latest_lower_band = ",latest_lower_band)
    
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

# 補充
# 計算 VWAP
def calculate_vwap(stock_data):
    vwap = (stock_data['Volume'] * stock_data['Close']).cumsum() / stock_data['Volume'].cumsum()
    return vwap.iloc[-1]

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

# 計算 5 日、10 日和 20 日的乖離率：
def calculate_bias(stock_data, periods=[5, 10, 20]):
    close_prices = stock_data['Close']    
    bias_values = {}
    print(f"close_prices = {close_prices}")
    print(f"================================================")

    # 手動計算移動平均
    ma_values = []  # 用來存放每一個時段的均價
    # 取最後五天的收盤價格然後做平均    
    for period in periods:
        for i in range(period):
            # print(f"i = {i}")
            period_close_prices = round(close_prices.iloc[-(i+1)], 2)
            ma_values.append(period_close_prices)
        average_price = round(sum(ma_values) / len(ma_values), 2)  # 計算均價並四捨五入到 2 位小數

        bias = ((close_prices.iloc[-1] - average_price) / average_price) * 100  # 乖離率公式
        bias_values[period] = bias
        
        print(f"================================================")
        print(f"average_price = {average_price}")
        print(f"================================================")
        # print(f"ma_values = {ma_values}")

    # for period in periods:
    #     # 計算 n 日均線
    #     ma = close_prices.rolling(window=period).mean()        
    #     # 取出最新的移動平均值 (也就是最後一筆)
    #     latest_ma = ma.iloc[-1]

    #     print(f"period = {period}, latest_ma = {latest_ma}")
    #     bias = ((close_prices - latest_ma) / latest_ma) * 100  # 乖離率公式
    #     bias_values[period] = bias.iloc[-1]  # 取最新一天的乖離率
    
    print(f"bias_values = {bias_values}")
    return bias_values        

# 取得五檔買賣價與委託量
def calculate_five_orders(ticker, twTicker):

    # 如果twTicker有包含TWO字串則...
    if twTicker.find("TWO") != -1:        
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=otc_{ticker}.tw&json=1&delay=0"
    else:
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{ticker}.tw&json=1&delay=0"

    print(f"url = {url}")
    
    response = requests.get(url)
    data = response.json()

    # 解析 JSON 資料
    if "msgArray" in data and len(data["msgArray"]) > 0:
        stock_info = data["msgArray"][0]
        
        # 取得五檔買賣價與委託量
        buy_prices = list(map(float, stock_info["b"].split("_")[:-1]))  # 買入價格
        sell_prices = list(map(float, stock_info["a"].split("_")[:-1]))  # 賣出價格
        buy_volumes = list(map(int, stock_info["g"].split("_")[:-1]))  # 買入委託量
        sell_volumes = list(map(int, stock_info["f"].split("_")[:-1]))  # 賣出委託量

        # 總成交量
        total_volume = int(stock_info["v"])
        
        # 計算買賣掛單比率
        total_buy_order = sum(buy_volumes)
        total_sell_order = sum(sell_volumes)
        
        # 交易情緒分析
        if total_buy_order > total_sell_order * 1.5 and total_volume < total_buy_order * 0.1:
            suggestion = "⚠️ 買單遠大於賣單，但成交量低，可能是假突破，需謹慎。"
        elif total_sell_order > total_buy_order * 1.5 and total_volume > total_sell_order * 0.1:
            suggestion = "❌ 賣單壓制，且成交量增長，可能為空方主導，可考慮做空。"
        elif total_buy_order > total_sell_order and total_volume > total_buy_order * 0.2:
            suggestion = "✅ 買單與成交量同步上升，穩健上漲，可考慮買入。"
        else:
            suggestion = "🔍 市場無明顯方向，觀察後再行動。"
        
        # 輸出結果
        # print(f"🎯 台積電 (2330) 五檔買賣掛單分析")
        # print(f"📊 成交量: {total_volume}")
        # print(f"💰 五檔買入價量: {list(zip(buy_prices, buy_volumes))}")
        # print(f"💰 五檔賣出價量: {list(zip(sell_prices, sell_volumes))}")
        # print(f"📈 總買單: {total_buy_order}, 總賣單: {total_sell_order}")
        # print(f"📢 交易建議: {suggestion}")
        msg = (
            f"📊 成交量: {total_volume}\n"
            f"💰 五檔買入價量: {list(zip(buy_prices, buy_volumes))}\n"
            f"💰 五檔賣出價量: {list(zip(sell_prices, sell_volumes))}\n"
            f"📈 總買單: {total_buy_order}, 總賣單: {total_sell_order}\n"
            f"📢 交易建議: {suggestion}"
        )

        return msg

    else:
        return "❌ 無法取得股票資訊，無法處理五檔買賣掛單分析。"
    
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
# stock_data = get_stock_data(2330)
# stock_data = get_stock_data(2603)

# kd_data = calculate_kd(stock_data)

# # 查看有訊號的日期
# kd_data = check_kd_signal(kd_data)
# signals = kd_data[kd_data['signal'] != 0]

# d_value = signals['D'].iloc[-1]
# print(f"d_value = {d_value}")

# signal_value = signals['signal'].iloc[-1]   # 1: 黃金交叉, -1: 死亡交叉
# print(f"signal_value = {signal_value}")

# # Price               K          D signal
# # Ticker                                 
# # Date  
# date_value = signals.index[-1]
# print(f"date_value = {date_value.strftime('%Y-%m-%d')}")
# print(signals[['K', 'D', 'signal']])


# 計算乖離率
# bias_values = calculate_bias(stock_data)

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

# VWAP
# ✅ 當 VWAP 向上 & 價格在 VWAP 之上 → 可考慮多單
# ✅ 當 VWAP 向下 & 價格在 VWAP 之下 → 可考慮空單
# ⚠️ 當價格遠離 VWAP，且成交量暴增 → 可能是陷阱！

# 若當前價格明顯高於 VWAP，但成交量未跟上，可能是假突破。
# 若當前價格低於 VWAP，代表市場成本高於現價，可能有支撐。

# 判斷買賣方向：
# 當價格 高於 VWAP，表示市場偏多，適合順勢做多。
# 當價格 低於 VWAP，表示市場偏空，適合順勢做空。

# 輔助確認成交量指標：
# 若成交量暴增，但價格未突破 VWAP，可能是假突破。
# 若價格突破 VWAP 並且成交量同步放大，代表趨勢可能成立。

# 當價格高於 VWAP，且成交量暴增 → 可能是主力拉高吸引散戶進場
# 當價格低於 VWAP，且成交量暴增 → 可能是主力出貨

# vwap = calculate_vwap(stock_data)
# print(f"VWAP = {vwap.values[0]}")


# latest_volume, latest_mav = calculate_mav(stock_data)
# print(f"latest_volume = {latest_volume}")
# print(f"latest_mav = {latest_mav}")
# print(f"latest_mav*3 = {latest_mav*3}")

# price = stock_data["Close"].iloc[-1].values[0]
# print(f"price = {price}")

# stock = twstock.realtime.get('2330')
# print(stock['realtime']['best_bid_price'])  # 買五檔價格
# print(stock['realtime']['best_ask_price'])  # 賣五檔價格
