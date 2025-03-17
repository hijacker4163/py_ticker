import yfinance as yf
import numpy as np
import pandas as pd

from tkinter import ttk
import tkinter as tk
import tkinter.messagebox as messagebox

from stocker.stocker import Stocker

import json
import os
import time
from datetime import datetime

from twstock import Stock
from twstock import BestFourPoint
import twstock

import calculate as ca

# 儲存股號到 JSON 檔案
def save_ticker(ticker_symbol):
    file_path = "saved_tickers.json"
    
    # 如果檔案存在，則讀取現有資料
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            saved_tickers = json.load(file)
    else:
        saved_tickers = []

    # 如果股號不在清單中，則儲存股號
    if ticker_symbol not in saved_tickers:
        saved_tickers.append(ticker_symbol)

    # 寫入檔案
    with open(file_path, "w") as file:
        json.dump(saved_tickers, file, ensure_ascii=False, indent=4)

# 讀取儲存的股號
def load_saved_tickers():
    file_path = "saved_tickers.json"
    
    # 如果檔案存在，則讀取股號清單
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            saved_tickers = json.load(file)
    else:
        saved_tickers = []

    # 移除 ".TW"
    cleaned_tickers = [ticker.replace(".TW", "") for ticker in saved_tickers]
    # 若有變更，寫回檔案
    if cleaned_tickers != saved_tickers:
        with open(file_path, "w") as file:
            json.dump(cleaned_tickers, file, indent=4)

    return cleaned_tickers


# 取得股票資訊的函數
def get_stock_info(ticker_symbol):
    twTicker = ticker_symbol + ".TW"
    stock = yf.Ticker(twTicker)
    # hist = stock.history(period="1y")  # 過去一年的數據
    hist = stock.history(period="63d")  # 過去63day的數據
    
    # 取得財報數據
    eps = stock.info.get("trailingEps", 0)  # 每股盈餘
    pe_ratio = stock.info.get("trailingPE", 0)  # 本益比
    dividend_yield = stock.info.get("dividendYield", 0) * 100  # 年收殖利率（%）
    # 改使用twstock取得股票名稱
    # stock_name = stock.info.get("longName", ticker_symbol)  # 股票中文名稱（若無則顯示代號）    
    stock_name = twstock.codes[ticker_symbol].name

    low_63 = hist["Low"].min()  # 取得過去 63 天的最低價
    # print(f"過去 63 天的最低價: {low_63}")
    high_63 = hist["High"].max()  # 取得過去 63 天的最高價
    # print(f"過去 63 天的最高價: {high_63}")

    lowest_day = hist["Low"].idxmin()  # 找出最低價的日期
    low_63 = hist["Low"].min()  # 取得最低價
    print(f"過去 63 天的最低價: {low_63}，出現在 {lowest_day}")

    # 計算平均最低價、最高價
    avg_low = round(np.mean(hist["Low"]), 2)
    avg_high = round(np.mean(hist["High"]), 2)

    # 計算建議買賣價格
    suggested_buy_price = round(high_63 - (high_63 - low_63) * 0.95, 2)
    suggested_sell_price = round(high_63 - (high_63 - low_63) * 0.05, 2)

    # 計算交易量
    avg_volume = int(np.mean(hist["Volume"])/1000)
    today_volume = int(hist["Volume"].iloc[-1]/1000)

    # 收盤價分析
    avg_close_price = round(np.mean(hist["Close"]), 2)
    yesterday_close = round(hist["Close"].iloc[-2], 2)
    today_close = round(hist["Close"].iloc[-1], 2)
    trend = "Up" if today_close > yesterday_close else "Down"

    # 計算震盪幅度
    today_high = round(hist["High"].iloc[-1], 2)
    today_low = round(hist["Low"].iloc[-1], 2)
    volatility = round(today_high - today_low, 2)

    # 預估低點、高點
    estimated_low = round(avg_low * 0.95, 2)
    estimated_high = round(avg_high * 1.05, 2)

    return {
        "代號": ticker_symbol,
        "名稱": stock_name,
        "EPS": round(eps, 2),
        "本益比": round(pe_ratio, 2),
        "平均最低": avg_low,
        "建議買入": suggested_buy_price,
        "平均最高": avg_high,
        "建議賣出": suggested_sell_price,
        "平均交易量": avg_volume,
        "今天交易量": today_volume,
        "平均收盤": avg_close_price,
        "昨天收盤": yesterday_close,
        "今天收盤": today_close,
        "趨勢": trend,
        "震盪": volatility,
        "預估最低": estimated_low,
        "預估最高": estimated_high,
        "殖利率": round(dividend_yield, 2)
    }

# 新增股票資料
def add_stock_data():
    ticker = ticker_entry.get().strip().upper()
    if not ticker:
        print("請輸入有效的股票代號")
        return

    try:
        # 嘗試獲取股票資料
        stock_data = get_stock_info(ticker)
        
        # 檢查是否成功獲取資料
        if not stock_data:
            messagebox.showwarning("查詢失敗", f"無法取得 {ticker} 的股票資訊")
            return

        # 插入表格
        table.insert("", "end", values=[stock_data.get(key, "N/A") for key in table_columns])

        # 儲存股號
        save_ticker(ticker)

    except Exception as e:
        messagebox.showerror("發生錯誤", f"獲取股票資訊時發生錯誤：{str(e)}")

# 顯示已儲存的股號
def display_saved_tickers():
    saved_tickers = load_saved_tickers()
    for ticker in saved_tickers:
        stock_data = get_stock_info(ticker) 

        # 準備行數據
        row_data = [stock_data[key] for key in table_columns]
        print("row_data = ",row_data)

        # 設置每一列的標籤
        tags = [""] * len(row_data)  # 預設所有欄位無標籤

        # # 如果「建議買入」欄位有值，將其設為紅色
        # suggested_buy_price = row_data[5]  # 假設「建議買入」是第6個欄位
        # if suggested_buy_price:  # 檢查「建議買入」是否有數值
        #     tags[5] = "red"  # 設置第6個欄位為紅色

        # 插入表格並套用顏色標籤
        table.insert("", "end", values=row_data, tags=tags)

        # table.insert("", "end", values=[stock_data[key] for key in table_columns])

# 更新所有股票資料
def update_all_stocks():
    saved_tickers = load_saved_tickers()
    update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 更新時間

    # 清空現有的表格資料
    for row in table.get_children():
        table.delete(row)
    
    # 重新插入更新後的股票資料
    for ticker in saved_tickers:
        stock_data = get_stock_info(ticker)
        table.insert("", "end", values=[stock_data[key] for key in table_columns])

    # 顯示更新完成的訊息
    status_label.config(text=f"更新完成! 更新時間: {update_time}")



# 取得股票歷史數據
def get_stock_history(ticker_symbol, start_date="2020-01-01", end_date=None):        
    twTicker = f"{ticker_symbol}.TW"
    stock = yf.Ticker(twTicker)
    
    # 若沒有指定 end_date，則使用當前日期
    if end_date is None:
        end_date = datetime.today().strftime('%Y-%m-%d')  # 獲取今天的日期

    # 取得股價歷史資料，範圍可以指定，這裡範圍是 2020 年到當前日期
    history = stock.history(start=start_date, end=end_date)
    return history


# 預測按鈕事件
def predict_stock():
    selected_item = table.selection()
    if selected_item:
        ticker = table.item(selected_item[0])["values"][0]  # 取得選中的股票代號
        print(f"預測 {ticker} 股票資料")  # 預測功能（目前是 print）

        # ticker = "2330.TW"  # 這裡可以更換為任意股票代號
        stock_data = get_stock_history(ticker)  # 取得股票歷史資料

        # 取出 Close 欄位
        close_prices = stock_data['Close']

        # 重新命名索引為 'Date'
        close_prices = close_prices.rename_axis('date')

        # 去除時間部分，保留日期
        # close_prices.index = close_prices.index.date
        close_prices.index = pd.to_datetime(close_prices.index.date)
        # print(close_prices)

        # df = pd.read_csv('stocker/price.csv', index_col='date', parse_dates=['date'])
        # price = df.squeeze()
        # price.head()
        # print(price)

        plot = Stocker(close_prices,ticker)
        model, model_data = plot.create_prophet_model(days=90)

    else:
        print("請選擇一支股票進行預測")
        # 顯示錯誤訊息彈出視窗
        messagebox.showwarning("警告", "請選擇一支股票進行預測")

def best_four_point():
    selected_item = table.selection()
    if selected_item:
        ticker = table.item(selected_item[0])["values"][0]  # 取得選中的股票代號
        ticker_name = table.item(selected_item[0])["values"][1]  # 取得選中的股票名稱
        print(f"四大買賣點 {ticker}-{ticker_name} 股票資料")

        # 解析四大買賣點
        tw_stock = Stock(str(ticker))
        bfp = BestFourPoint(tw_stock)
        buy_reason = bfp.best_four_point_to_buy()  # 判斷是否為四大買點
        sell_reason = bfp.best_four_point_to_sell()  # 判斷是否為四大賣點
        complex_reason = bfp.best_four_point()
        print(f"complex_reason = {complex_reason}")

        # 顯示新視窗
        show_result_window(ticker, ticker_name, buy_reason, sell_reason)

# 下載股價資料的公共函數
def get_stock_data(ticker, period="60d", interval="1d"):
    twTicker = f"{ticker}.TW"
    stock_data = yf.download(twTicker, period=period, interval=interval)  # 最近60天資料
    return stock_data

def create_separator(parent):
    separator = tk.Frame(parent, height=2, bd=1, relief="sunken", bg="gray")
    separator.pack(fill="x", pady=5)
    return separator

def show_result_window(ticker, ticker_name, buy_reason, sell_reason):
    def update_result():
        """每 30 秒重新獲取數據並更新 UI"""
        stock_data = get_stock_data(ticker)
        # 計算 MACD 指標的買賣信號
        macd_signal = ca.calculate_macd(stock_data)
        # 計算 RSI
        new_rsi = ca.calculate_rsi(stock_data)
        # 計算布林帶
        sma, upper_band, lower_band, decision = ca.calculate_bollinger_bands(stock_data)

        # 計算交易量多種技術指標    
        latest_volume, latest_mav = ca.calculate_mav(stock_data)
        volume_ratio = ca.calculate_volume_ratio(stock_data)
        pvt = ca.calculate_pvt(stock_data)
        cmf = ca.calculate_cmf(stock_data)
        vroc = ca.calculate_vroc(stock_data)
        latest_obv, previous_obv, latest_price, previous_price = ca.calculate_obv(stock_data)
        print(f"latest_volume: {latest_volume}")
        print(f"MAV: {latest_mav}")
        print(f"Volume Ratio: {volume_ratio.values[0]}")
        print(f"PVT: {pvt}")
        print(f"CMF: {cmf.values[0]}")
        print(f"VROC: {vroc.values[0]}")
        print(f"latest_obv: {latest_obv}")
        print(f"previous_obv: {previous_obv}")
        print(f"latest_price: {latest_price}")
        print(f"previous_price: {previous_price}")
        result = ca.decision_based_on_volume(latest_volume, latest_mav, volume_ratio.values[0], pvt, cmf.values[0], vroc.values[0], latest_obv, previous_obv, latest_price, previous_price)

        tw_stock = Stock(str(ticker))
        bfp = BestFourPoint(tw_stock)
        new_buy_reason = bfp.best_four_point_to_buy()
        new_sell_reason = bfp.best_four_point_to_sell()

        # 更新 Label 內容
        buy_label.config(text=f"✅ 符合四大買點: {new_buy_reason}" if new_buy_reason else "❌ 不符合四大買點")
        sell_label.config(text=f"⚠️ 符合四大賣點: {new_sell_reason}" if new_sell_reason else "✅ 不符合四大賣點")
        macd_label.config(text=f"MACD(移動平均線): {macd_signal}")  # 顯示 MACD 訊號
        rsi_label.config(text=f"RSI(70⬆超買,30⬇超賣): {new_rsi:.2f}")
        bollinger_label.config(text=f"布林帶: 上軌 {upper_band:.2f}, 下軌 {lower_band:.2f}, 中軌 {sma:.2f}\n決策:{decision}")
        # 顯示交易量投票結果
        volume_label.config(text=f"{result}")

        # 更新時間
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        update_time_label.config(text=f"最後更新時間: {now}")

        # 30 秒後再次執行更新
        result_window.after(30000, update_result)

    # 檢查視窗是否已存在
    global result_window
    if "result_window" in globals() and result_window.winfo_exists():
        print("視窗已存在，直接更新")
        update_result()
        return

    # 建立新視窗
    result_window = tk.Toplevel()
    result_window.title(f"{ticker} - {ticker_name} 預測結果")
    result_window.geometry("400x500")

    tk.Label(result_window, text=f"股票: {ticker} - {ticker_name}", font=("Arial", 14, "bold")).pack(pady=10)

    # 買入訊息
    buy_label = tk.Label(result_window, text=f"✅ 符合四大買點: {buy_reason}" if buy_reason else "❌ 不符合四大買點", fg="green")
    buy_label.pack(pady=5)

    # 賣出訊息
    sell_label = tk.Label(result_window, text=f"⚠️ 符合四大賣點: {sell_reason}" if sell_reason else "✅ 不符合四大賣點", fg="orange")
    sell_label.pack(pady=5)

    # 分隔線
    create_separator(result_window)

    stock_data = get_stock_data(ticker)
    # 計算 MACD 指標的買賣信號
    macd_signal = ca.calculate_macd(stock_data)
    # 計算 RSI
    rsi_value = ca.calculate_rsi(stock_data)
    # 計算布林帶
    sma, upper_band, lower_band, decision = ca.calculate_bollinger_bands(stock_data)

    # 計算交易量多種技術指標   
    latest_volume, latest_mav = ca.calculate_mav(stock_data)
    volume_ratio = ca.calculate_volume_ratio(stock_data)
    pvt = ca.calculate_pvt(stock_data)
    cmf = ca.calculate_cmf(stock_data)
    vroc = ca.calculate_vroc(stock_data)    
    latest_obv, previous_obv, latest_price, previous_price = ca.calculate_obv(stock_data)
    print(f"latest_volume: {latest_volume}")
    print(f"MAV: {latest_mav}")
    print(f"Volume Ratio: {volume_ratio.values[0]}")
    print(f"PVT: {pvt}")
    print(f"CMF: {cmf.values[0]}")
    print(f"VROC: {vroc.values[0]}")
    
    print(f"latest_obv: {latest_obv}")
    print(f"previous_obv: {previous_obv}")
    print(f"latest_price: {latest_price}")
    print(f"previous_price: {previous_price}")

    result = ca.decision_based_on_volume(latest_volume, latest_mav, volume_ratio.values[0], pvt, cmf.values[0], vroc.values[0], latest_obv, previous_obv, latest_price, previous_price)
    
    # 顯示 MACD 訊號
    macd_label = tk.Label(result_window, text=f"MACD(移動平均線): {macd_signal}")                          
    macd_label.pack(pady=5)

    # 分隔線
    create_separator(result_window)

    # 顯示 RSI (RSI值在70以上表示超買，30以下表示超賣)
    rsi_label = tk.Label(result_window, text=f"RSI(70⬆超買,30⬇超賣): {rsi_value:.2f}")
    rsi_label.pack(pady=5)

    # 分隔線
    create_separator(result_window)

    # 顯示布林帶
    bollinger_label = tk.Label(result_window, text=f"布林帶: 上軌 {upper_band:.2f}, 下軌 {lower_band:.2f}, 中軌 {sma:.2f}\n決策:{decision}")
    bollinger_label.pack(pady=10)

    # 分隔線
    create_separator(result_window)

    # 顯示交易量投票結果
    volume_label = tk.Label(result_window, text=f"{result}")
    volume_label.pack(pady=10)

    # 分隔線
    create_separator(result_window)

    # 更新時間顯示
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 更新時間
    update_time_label = tk.Label(result_window, text=f"最後更新時間: {now}", font=("Arial", 10))
    update_time_label.pack(pady=10)

    # 關閉按鈕
    tk.Button(result_window, text="關閉", command=result_window.destroy).pack(pady=20)

    # 啟動自動更新
    result_window.after(30000, update_result)

# 設定GUI界面
root = tk.Tk()
root.title("股票資訊查詢")

# 輸入股票代號
ticker_label = tk.Label(root, text="輸入台灣股票代號 (如 2330 或 0050):")
ticker_label.grid(row=0, column=0, padx=10, pady=5)

ticker_entry = tk.Entry(root)
ticker_entry.grid(row=0, column=1, padx=10, pady=5)

# 設定新增與更新按鈕
add_button = tk.Button(root, text="新增", command=add_stock_data)
add_button.grid(row=0, column=2, padx=5, pady=5)

update_button = tk.Button(root, text="更新所有", command=update_all_stocks)
update_button.grid(row=0, column=3, padx=5, pady=5)

bestFour_button = tk.Button(root, text="四大買賣點判斷", command=best_four_point)
bestFour_button.grid(row=0, column=4, padx=5, pady=5)
bestFour_button.grid_remove()

# 預測按鈕，初始隱藏
predict_button = tk.Button(root, text="預測", command=predict_stock)
predict_button.grid(row=0, column=5, padx=5, pady=5)
# 初始隱藏按鈕
predict_button.grid_remove()

# 設定表格欄位名稱
table_columns = [
    "代號", "名稱", "EPS", "本益比", "平均最低", 
    "建議買入", "平均最高", "建議賣出", "平均交易量", "今天交易量", 
    "平均收盤", "昨天收盤", "今天收盤", "趨勢", "震盪", "預估最低", 
    "預估最高", "殖利率"
]

# 設定表格
table = ttk.Treeview(root, columns=table_columns, show="headings", height=10)
table.grid(row=1, column=0, columnspan=4, padx=10, pady=10)

# 設定表格標題
for col in table_columns:
    table.heading(col, text=col)
    table.column(col, width=70, anchor="center")

# 設定紅色字的標籤
table.tag_configure("red", foreground="red")
# 設定綠色字的標籤
table.tag_configure("green", foreground="green")

# 監聽表格選擇事件
def on_item_select(event):
    predict_button.grid()  # 顯示預測按鈕
    bestFour_button.grid() # 顯示四大買賣點按鈕

table.bind("<<TreeviewSelect>>", on_item_select)

# 在啟動時顯示儲存的股號
display_saved_tickers()

# 顯示更新狀態
status_label = tk.Label(root, text="尚未更新", anchor="w")
status_label.grid(row=2, column=0, columnspan=4, sticky="w", padx=10, pady=5)

# 啟動 GUI 界面
root.mainloop()

