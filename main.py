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
import datetime

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

    return saved_tickers


# 取得股票資訊的函數
def get_stock_info(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    hist = stock.history(period="1y")  # 過去一年的數據
    
    # 取得財報數據
    eps = stock.info.get("trailingEps", 0)  # 每股盈餘
    pe_ratio = stock.info.get("trailingPE", 0)  # 本益比
    dividend_yield = stock.info.get("dividendYield", 0) * 100  # 年收殖利率（%）
    stock_name = stock.info.get("longName", ticker_symbol)  # 股票中文名稱（若無則顯示代號）

    # 計算平均最低價、最高價
    avg_low = round(np.mean(hist["Low"]), 2)
    avg_high = round(np.mean(hist["High"]), 2)

    # 計算建議買賣價格
    suggested_buy_price = round(avg_low * 0.9, 2)
    suggested_sell_price = round(avg_high * 1.1, 2)

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

    # 儲存股號
    save_ticker(ticker)

    # 顯示股票資料
    stock_data = get_stock_info(ticker)
    table.insert("", "end", values=[stock_data[key] for key in table_columns])

# 顯示已儲存的股號
def display_saved_tickers():
    saved_tickers = load_saved_tickers()
    for ticker in saved_tickers:
        stock_data = get_stock_info(ticker)
        table.insert("", "end", values=[stock_data[key] for key in table_columns])

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
    stock = yf.Ticker(ticker_symbol)
    
    # 若沒有指定 end_date，則使用當前日期
    if end_date is None:
        end_date = datetime.datetime.today().strftime('%Y-%m-%d')  # 獲取今天的日期

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

        print(close_prices)

        # df = pd.read_csv('stocker/price.csv', index_col='date', parse_dates=['date'])
        # price = df.squeeze()
        # price.head()
        # print(price)

        tsmc = Stocker(close_prices,ticker)
        model, model_data = tsmc.create_prophet_model(days=90)

    else:
        print("請選擇一支股票進行預測")
        # 顯示錯誤訊息彈出視窗
        messagebox.showwarning("警告", "請選擇一支股票進行預測")

# 設定GUI界面
root = tk.Tk()
root.title("股票資訊查詢")

# 輸入股票代號
ticker_label = tk.Label(root, text="輸入股票代號 (如 2330.TW 或 AAPL):")
ticker_label.grid(row=0, column=0, padx=10, pady=5)

ticker_entry = tk.Entry(root)
ticker_entry.grid(row=0, column=1, padx=10, pady=5)

# 設定新增與更新按鈕
add_button = tk.Button(root, text="新增", command=add_stock_data)
add_button.grid(row=0, column=2, padx=5, pady=5)

update_button = tk.Button(root, text="更新所有", command=update_all_stocks)
update_button.grid(row=0, column=3, padx=5, pady=5)

# 預測按鈕，初始隱藏
predict_button = tk.Button(root, text="預測", command=predict_stock)
predict_button.grid(row=0, column=4, padx=5, pady=5)
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

# 監聽表格選擇事件
def on_item_select(event):
    predict_button.grid()  # 顯示預測按鈕

table.bind("<<TreeviewSelect>>", on_item_select)

# 在啟動時顯示儲存的股號
display_saved_tickers()

# 顯示更新狀態
status_label = tk.Label(root, text="尚未更新", anchor="w")
status_label.grid(row=2, column=0, columnspan=4, sticky="w", padx=10, pady=5)

# 啟動 GUI 界面
root.mainloop()
