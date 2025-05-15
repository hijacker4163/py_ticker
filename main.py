import yfinance as yf

import requests
import numpy as np
import pandas as pd

from tkinter import ttk, scrolledtext
import tkinter as tk
import tkinter.messagebox as messagebox

from stocker.stocker import Stocker

import json
import os
import time
import datetime
import threading
from cachetools import TTLCache
from bs4 import BeautifulSoup

from twstock import Stock
from twstock import BestFourPoint
import twstock

import calculate as ca

from FinMind.data import DataLoader

# 初始化快取 1 day
cache = TTLCache(maxsize=100, ttl=86400)

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
def get_stock_info(ticker, utc_8_loc_time):
    # 使用twstock取得中文名稱及股票類型
    tw_stock_codes = twstock.codes.get(ticker, None)  # 找不到時回傳 None
    
    # 使用twstock取得股票價格歷史資料
    tw_stock = Stock(ticker) 

    if tw_stock_codes is None:
        twTicker = ticker + ".TWO"
    elif tw_stock_codes.market == "上市":
        twTicker = ticker + ".TW"
    elif tw_stock_codes.market == "上櫃":
        twTicker = ticker + ".TWO"

    print(f"twTicker = {twTicker}")

    stock = yf.Ticker(twTicker)

    # 取得今天的日期
    today = datetime.date.today()
    # 計算 xx 天前的日期
    day63 = today - datetime.timedelta(days=63)
    day28 = today - datetime.timedelta(days=28)
    day10 = today - datetime.timedelta(days=10)

    # hist = stock.history(period="1y")  # 過去一年的數據
    hist63 = stock.history(start=day63, end=today)  # 過去63day的數據
    hist28 = stock.history(start=day28, end=today)  # 過去28day的數據
    hist10 = stock.history(start=day10, end=today)  # 過去10day的數據
    # hist5 = stock.history(period="5d")  # 取得最近5天的數據，以防有缺失

    # 取得財報數據
    eps = stock.info.get("trailingEps", 0)  # 每股盈餘
    pe_ratio = stock.info.get("trailingPE", 0)  # 本益比

    # 取得殖利率
    dividend_yield = stock.info.get('trailingAnnualDividendYield')
    if dividend_yield is None:
        dividend_yield = 0
    elif dividend_yield == 0:
        dog_yield = get_dog_yield_rate(ticker)
        dividend_yield = float(dog_yield)
    else:
        dividend_yield = dividend_yield * 100

    # 改使用twstock取得股票名稱
    # stock_name = stock.info.get("longName", twTicker)  # 沒有中文名稱
    # 使用twstock有中文名稱
    stock_name = tw_stock_codes.name if tw_stock_codes is not None else stock.info.get("longName", twTicker)

    low_63 = hist63["Low"].min()  # 取得過去 63 天的最低價
    # print(f"{ticker} - 過去 63 天的最低價: {low_63}")
    high_63 = hist63["High"].max()  # 取得過去 63 天的最高價
    # print(f"{ticker} - 過去 63 天的最高價: {high_63}")

    # lowest_day = hist63["Low"].idxmin()  # 找出最低價的日期
    # print(f"{ticker} - 過去 63 天的最低價: {low_63}，出現在 {lowest_day}")

    # highest_day = hist63["High"].idxmax()
    # print(f"{ticker} - 過去 63 天的最高價: {high_63}，出現在 {highest_day}")

    # 計算平均最低價、最高價
    avg_low = round(np.mean(hist63["Low"]), 2)
    avg_high = round(np.mean(hist63["High"]), 2)

    # 計算建議買賣價格
    suggested_buy_price = round(high_63 - (high_63 - low_63) * 0.95, 2)
    suggested_sell_price = round(high_63 - (high_63 - low_63) * 0.05, 2)

    # 計算交易量
    avg_volume = int(np.mean(hist10["Volume"])/1000)
    today_volume = int(hist10["Volume"].iloc[-1]/1000)

    # 收盤價分析
    avg_close_price = round(np.mean(hist28["Close"]), 2)

    # 取得最近兩天的日期
    # latest_date = hist5.index[-1].strftime("%Y-%m-%d")  # 最新數據的日期
    # previous_date = hist5.index[-2].strftime("%Y-%m-%d")  # 倒數第二筆數據的日期
    
    # latest_date = tw_stock.date[-1].strftime("%Y-%m-%d")  # 最新數據的日期
    # previous_date = tw_stock.date[-2].strftime("%Y-%m-%d") # 倒數第二筆數據的日期

    # print(f"ticker: {ticker}")
    # print(f"today: {today}")
    # print(f"最新數據日期: {latest_date}")
    # print(f"倒數第二筆數據日期: {previous_date}")

    # 判斷昨日收盤價
    # if utc_8_loc_time.tm_hour < 9:
    #   yesterday_close = round(stock.info.get('regularMarketPrice'), 2)
    # elif utc_8_loc_time.tm_hour < 13 or (utc_8_loc_time.tm_hour == 13 and utc_8_loc_time.tm_min < 30):
    #   yesterday_close = round(stock.info.get('regularMarketPreviousClose'), 2)
    # else:
    #   yesterday_close = round(stock.info.get('regularMarketPrice'), 2)

    if not tw_stock.price:
        yesterday_close = round(stock.info.get('regularMarketPreviousClose'), 2)
        # 過13:30可考慮用regularMarketPrice
    else:
        yesterday_close = tw_stock.price[-1]  # 昨日收盤價

    # 今日收盤（當前股價）
    if stock.info.get('currentPrice') is None:
        today_close = round(stock.info.get('regularMarketPrice'), 2)
    else:
        today_close = round(stock.info.get('currentPrice', 0), 2) # 當前價格

    trend = "Up" if today_close > yesterday_close else "Down"

    # 計算震盪幅度
    volatility = round(avg_high - avg_low, 2)

    # 預估低點、高點
    # 判斷當地時間是否是下午 1:30 之前
    if utc_8_loc_time.tm_hour < 13 or (utc_8_loc_time.tm_hour == 13 and utc_8_loc_time.tm_min < 30):
        # 下午 1:30 之前，使用昨天的收盤價來計算預估低點和高點
        estimated_low = round(yesterday_close - volatility, 2)
        estimated_high = round(yesterday_close + volatility, 2)
    else:
        # 下午 1:30 之後，使用今天的收盤價來計算預估低點和高點
        estimated_low = round(today_close - volatility, 2)
        estimated_high = round(today_close + volatility, 2)

    return {
        "代號": twTicker,
        "名稱": stock_name,
        "EPS": round(eps, 2) if stock.info.get("quoteType") != "ETF" else "ETF",        
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

# 爬蟲取得殖利率
def get_dog_yield_rate(code):
    # 嘗試從快取中獲取資料
    if code in cache:
        return cache[code]

    # 取得今天的年份
    today = time.localtime()
    current_year = today.tm_year

    # 構造 API 請求的 URL
    url = f"https://statementdog.com/api/v2/fundamentals/{code}/{current_year}/{current_year}"

    try:
        # 發送 HTTP 請求
        response = requests.get(url)

        if response.status_code == 200:
            result = json.loads(response.text)
            # 提取 CashYield 部分
            cash_yield = result["common"]["LatestValuation"]["data"]["CashYield"]
            # 將結果存入快取中
            cache[code] = cash_yield
            return cash_yield
        else:
            return

    except Exception as error:
        return

# 新增股票資料
def add_stock_data():
    ticker = ticker_entry.get().strip().upper()
    if not ticker:
        print("請輸入有效的股票代號")
        return

    try:
        # # 嘗試獲取股票資料
        # stock_data = get_stock_info(ticker)
        
        # # 檢查是否成功獲取資料
        # if not stock_data:
        #     messagebox.showwarning("查詢失敗", f"無法取得 {ticker} 的股票資訊")
        #     return

        # # 插入表格
        # table.insert("", "end", values=[stock_data.get(key, "N/A") for key in table_columns])

        # 儲存股號
        save_ticker(ticker)

        start_update(loading_window, table, table_columns, status_label)

    except Exception as e:
        messagebox.showerror("發生錯誤", f"獲取股票資訊時發生錯誤：{str(e)}")

# 顯示已儲存的股號
# def display_saved_tickers():
#     saved_tickers = load_saved_tickers()
#     for ticker in saved_tickers:
#         stock_data = get_stock_info(ticker) 

#         # 準備行數據
#         row_data = [stock_data[key] for key in table_columns]
#         print("row_data = ",row_data)

#         # 設置每一列的標籤
#         tags = [""] * len(row_data)  # 預設所有欄位無標籤

#         # # 如果「建議買入」欄位有值，將其設為紅色
#         # suggested_buy_price = row_data[5]  # 假設「建議買入」是第6個欄位
#         # if suggested_buy_price:  # 檢查「建議買入」是否有數值
#         #     tags[5] = "red"  # 設置第6個欄位為紅色

#         # 插入表格並套用顏色標籤
#         table.insert("", "end", values=row_data, tags=tags)

#         # table.insert("", "end", values=[stock_data[key] for key in table_columns])

# 更新所有股票資料
def update_all_stocks(loading_window, table, table_columns, status_label):    
    saved_tickers = load_saved_tickers()

    time_stamp = int(time.time())
    utc_8_time_stamp=time_stamp+8*60*60
    utc_8_loc_time = time.localtime(utc_8_time_stamp)
    utc_8_time = time.strftime("%Y-%m-%d %H:%M:%S", utc_8_loc_time)
    update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 更新時間

    # 清空現有的表格資料
    for row in table.get_children():
        table.delete(row)
    
    # 重新插入更新後的股票資料
    for ticker in saved_tickers:
        stock_data = get_stock_info(ticker, time.localtime())
        # text=ticker 只有股號
        table.insert("", "end", text=ticker, values=[stock_data[key] for key in table_columns])

    # 顯示更新完成的訊息
    status_label.config(text=f"更新完成! 更新時間: {update_time}")

     # 使用 root.after() 在主線程中更新 UI
    root.after(0, update_ui, loading_window, status_label, update_time)

def update_ui(loading_window, status_label, update_time):
    # 顯示更新完成的訊息
    status_label.config(text=f"更新完成! 更新時間: {update_time}")
    # 隱藏 loading
    loading_window.withdraw()

# 取得股票歷史數據
def get_stock_history(twTicker, start_date="2020-01-01", end_date=None):       
    stock = yf.Ticker(twTicker)
    
    # 若沒有指定 end_date，則使用當前日期
    if end_date is None:
        end_date = datetime.date.today().strftime('%Y-%m-%d')  # 獲取今天的日期

    # 取得股價歷史資料，範圍可以指定，這裡範圍是 2020 年到當前日期
    history = stock.history(start=start_date, end=end_date)
    return history

# 預測按鈕事件
def predict_stock():
    selected_item = table.selection()
    if selected_item:
        twTicker = table.item(selected_item[0])["values"][0]  # 取得選中的台灣股票代號（ex. tw, two）
        ticker = table.item(selected_item[0])["text"]  # 取得選中的股票代號

        print(f"預測 {twTicker} 股票資料")  # 預測功能（目前是 print）

        # twTicker = "2330.TW"  # 這裡可以更換為任意股票代號
        stock_data = get_stock_history(twTicker)  # 取得股票歷史資料

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

# 技術分析
def analysis_event():
    selected_item = table.selection()
    if selected_item:
        print(table.item(selected_item[0]))
        # ticker = table.item(selected_item[0])["values"][0]  # 取得選中的股票代號
        ticker = table.item(selected_item[0])["text"]  # 取得選中的股票代號
        twTicker = table.item(selected_item[0])["values"][0]  # 取得選中的台灣股票代號（ex. tw, two）
        ticker_name = table.item(selected_item[0])["values"][1]  # 取得選中的股票名稱
        print(f"四大買賣點 {ticker}-{ticker_name} 股票資料")

        # 解析四大買賣點
        buy_reason, sell_reason, complex_reason = ca.get_four_points(ticker)        
        print(f"complex_reason = {complex_reason}")

        # 顯示新視窗
        show_result_window(ticker, twTicker, ticker_name, buy_reason, sell_reason)

# 大股東持有
def major_shareholders_hold():
    selected_item = table.selection()
    if selected_item:
        # ticker = table.item(selected_item[0])["values"][0]  # 取得選中的股票代號
        ticker = table.item(selected_item[0])["text"]
        ticker_name = table.item(selected_item[0])["values"][1]  # 取得選中的股票名稱

        url = f"https://norway.twsthr.info/StockHolders.aspx?stock={ticker}"
        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(url, headers=headers)
        # print(response.text)  # 看看是不是完整 HTML

        # 使用 BeautifulSoup 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # 找到包含數據的表格（可以根據 <table> id 或 class 進行選擇）
        soup_table = soup.find('table', {'id': 'Details'})  # 假設表格的 id 是 'Details'

        # 提取所有行（<tr>）
        rows = soup_table.find_all('tr')

        # 將表格資料提取並整理
        table_data = []
        for i, row in enumerate(rows):
            if i == 10:
                break
            # 提取每一行中的所有欄位（<td>）
            columns = row.find_all('td')
            
            # 如果欄位數量不為 0，表示有有效的資料
            if columns:
                column_data = [column.text.strip() for column in columns]
                table_data.append(column_data)

        print(len(table_data))  # 顯示資料筆數

        # 輸出整理後的資料
        dates = []
        percentages = []

        for i, row in enumerate(table_data):
            if i == 0:
                continue
            date = row[2]  # 資料日期
            percentage = row[7]  # >400張大股東持有百分比

            # 把資料加到對應的列表中
            dates.append(date)
            percentages.append(percentage)

        # 顯示新視窗
        show_major_shareholders_hold_window(ticker, ticker_name, dates, percentages)
        
        # 返回資料
        # return dates, percentages

# def futures_valuation_hold():

def export_data_hold():    
    selected_item = table.selection()
    ticker = table.item(selected_item[0])["text"]
    ticker_name = table.item(selected_item[0])["values"][1]  # 取得選中的股票名稱
    twTicker = table.item(selected_item[0])["values"][0]  # 取得選中的台灣股票代號（ex. tw, two）

    # 初始化 FinMind
    api = DataLoader()
    api.login_by_token(api_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJkYXRlIjoiMjAyNS0wNS0xNSAxMDowNjo1NSIsInVzZXJfaWQiOiJoaWphY2tlcjQxNjMiLCJpcCI6IjExNC4zMi4xMDcuMjUwIn0.ZS6hbOOfUPNTJnMADwax7_G79qlwaDLiGVfnPTYOHbs")

    # 設定股票代碼與日期範圍
    days = 5
    start_date = (datetime.date.today() - datetime.timedelta(days=days * 2)).strftime("%Y-%m-%d")    
    print("start_date =", start_date)

    # 三大法人買賣
    df_institution = api.taiwan_stock_institutional_investors(
        stock_id=ticker, start_date=start_date
    )
    df_institution['net_buy'] = pd.to_numeric(df_institution['buy']) - pd.to_numeric(df_institution['sell'])
    df_institution_summary = df_institution.groupby('date')[['net_buy']].sum().reset_index()
    df_institution_summary.columns = ['date', '法人合計淨買超']

    # 融資融券
    df_margin_summary = pd.DataFrame(columns=['date', '融資變動', '融券變動'])
    df_margin = api.taiwan_stock_margin_purchase_short_sale(
        stock_id=ticker, start_date=start_date
    )

    if df_margin.empty:
        print(f"⚠️ 股票 {ticker}：df_margin 是空的，可能查無資料")
    else:
        required_columns = [
            'MarginPurchaseTodayBalance', 'MarginPurchaseYesterdayBalance',
            'ShortSaleTodayBalance', 'ShortSaleYesterdayBalance'
        ]
        missing = [col for col in required_columns if col not in df_margin.columns]
        
        if missing:
            print(f"⚠️ 股票 {ticker}：缺少欄位 {missing}，無法計算融資融券變動")
        else:
            df_margin['融資變動'] = df_margin['MarginPurchaseTodayBalance'] - df_margin['MarginPurchaseYesterdayBalance']
            df_margin['融券變動'] = df_margin['ShortSaleTodayBalance'] - df_margin['ShortSaleYesterdayBalance']
            df_margin_summary = df_margin[['date', '融資變動', '融券變動']]
            print(f"✅ 股票 {ticker}：融資融券資料處理完成")

    # 外資持股比例
    df_foreign_holding = api.taiwan_stock_shareholding(
        stock_id=ticker, start_date=start_date
    )
    df_foreign_holding['外資持股變動(%)'] = df_foreign_holding['ForeignInvestmentRemainRatio'].diff()
    df_foreign_summary = df_foreign_holding[['date', 'ForeignInvestmentRemainRatio', '外資持股變動(%)']]
    df_foreign_summary.columns = ['date', '外資持股率(%)', '外資持股變動(%)']

    # 合併資料
    df_all = df_institution_summary.merge(df_margin_summary, on='date', how='outer')
    df_all = df_all.merge(df_foreign_summary, on='date', how='outer')
    df_all = df_all.sort_values(by='date', ascending=False).head(days).reset_index(drop=True)

    # 輸出文字
    def generate_text(row):
        date = row['date']
        text = f"📅 {date}：\n"
        if pd.notna(row['法人合計淨買超']):
            text += f"・法人淨買超：{int(row['法人合計淨買超']):,} 股\n"
        if pd.notna(row.get('融資變動')):
            text += f"・融資變化：{int(row['融資變動']):,} 股\n"
        if pd.notna(row.get('融券變動')):
            text += f"・融券變化：{int(row['融券變動']):,} 股\n"
        if pd.notna(row.get('外資持股變動(%)')):
            text += f"・外資持股變化：{row['外資持股變動(%)']:+.2f}%"
            if pd.notna(row.get('外資持股率(%)')):
                text += f"（目前持股率 {row['外資持股率(%)']:.2f}%）\n"
            else:
                text += "\n"
        return text

    # 輸出
    result = f"""
📈 {ticker} - {ticker_name}

請先幫我從網路上取得這家公司的基本面資訊。
接著，根據下方我提供的詳細技術面與籌碼面數據，進行綜合分析，並給出明確建議（觀望 / 進場 / 減碼）。

分析重點：
・請以技術面與籌碼面為主，基本面為輔
・操作週期以短線為主（1～5 天），若有中長線建議請說明理由
・若發現值得注意的風險、轉折或機會，也請一併指出

以下是詳細資料：
"""
    result += f"📅 最近 {days} 天的法人買賣、融資融券、外資持股變化：\n"
    result += "----------------------------------------\n"
    result += "\n".join([generate_text(row) for _, row in df_all.iterrows()])
    result += "----------------------------------------\n"

    # 解析四大買賣點
    buy_reason, sell_reason, complex_reason = ca.get_four_points(ticker)        
    
    stock_data = get_stock_data(twTicker)
    price = stock_data["Close"].iloc[-1].values[0]  # 當前價格
    vwap = ca.calculate_vwap(stock_data).values[0]

    # 計算 KD 指標
    kd_data = ca.calculate_kd(stock_data)
    k_value = kd_data['K'].iloc[-1]
    d_value = kd_data['D'].iloc[-1]

    # 查看有訊號的日期
    kd_data = ca.check_kd_signal(kd_data)
    signals = kd_data[kd_data['signal'] != 0]
    # print(signals[['K', 'D', 'signal']])
    # 2025-05-09  54.548854  52.029435      1
    # 最近一次的交叉結果日期，結果為 1 代表黃金交叉，-1 代表死亡交叉（取出日期）
    date = signals.index[-1].strftime('%Y-%m-%d')  # 取出最後一筆的日期
    signal_value = signals['signal'].iloc[-1]  # 1: 黃金交叉, -1: 死亡交叉
    signal_text = "最近一次交叉日：無訊號"
    if signal_value == 1:
        signal_text = f"最近一次交叉日：{date}，⚡ 黃金交叉"
    elif signal_value == -1:
        signal_text = f"最近一次交叉日：{date}，死亡交叉"

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

    # 計算 5 日、10 日、20 日乖離率
    bias_values = ca.calculate_bias(stock_data)

    # 補充：
    vwap = ca.calculate_vwap(stock_data).values[0]
    volume_threshold = latest_mav * 3  # 成交量過濾閾值（300%）
    result_five_orders = ca.calculate_five_orders(ticker, twTicker)

    # 檢查買賣點
    result += f"📊 目前股價: {price:.2f}\n"
    result += f"{'✅ 符合四大買點: ' + buy_reason if buy_reason else '❌ 不符合四大買點'}\n"
    result += f"{'⚠️ 符合四大賣點: ' + sell_reason if sell_reason else '✅ 不符合四大賣點'}\n"
    result += "----------------------------------------\n"
    
    # KD 指標
    result += f"\n📉 KD指標：%K={k_value:.2f}, %D={d_value:.2f} → {signal_text}\n"

    # MACD
    result += f"📈 MACD(移動平均線): {macd_signal}\n"
    result += "----------------------------------------\n"

    # RSI
    result += f"📉 RSI(70⬆超買,30⬇超賣): {new_rsi:.2f}\n"
    result += "----------------------------------------\n"

    # 布林帶
    result += f"📊 布林帶:\n・上軌: {upper_band:.2f}\n・下軌: {lower_band:.2f}\n・中軌: {sma:.2f}\n・決策: {decision}\n"
    result += "----------------------------------------\n"

    # 乖離率
    result += "📊 乖離率分析：\n正：避免追高買進，未來幾天可能會有一波股價下跌的修正\n負：避免殺低賣出，未來幾天可能會有一波股價上漲的反彈\n"
    for period, value in bias_values.items():
        value = value.values[0]
        bias_status = "🔴 正乖離" if value > 0 else "🟢 負乖離"
        result += f"・{period} 日 BIAS: {value:.2f}% ({bias_status})\n"
    result += "----------------------------------------\n"

    # 成交量技術指標分析
    result += "📊 中長線指標：\n"
    result += ca.decision_based_on_volume(latest_volume, latest_mav, volume_ratio.values[0], pvt, cmf.values[0], vroc.values[0], latest_obv, previous_obv, latest_price, previous_price)
    result += "\n----------------------------------------\n"

    # VWAP 分析
    if price > vwap:
        vwap_result = f"📈 當前價格 {price:.2f} 高於 VWAP {vwap:.2f}，市場偏多。"
        if latest_volume > volume_threshold:
            vwap_result += "\n⚠️ 成交量暴增，可能是主力拉高吸引散戶進場！"
        else:
            vwap_result += "\n✅ VWAP 支撐多方，可考慮順勢做多。"
    else:
        vwap_result = f"📉 當前價格 {price:.2f} 低於 VWAP {vwap:.2f}，市場偏空。"
        if latest_volume > volume_threshold:
            vwap_result += "\n⚠️ 成交量暴增，可能是主力出貨！"
        else:
            vwap_result += "\n✅ VWAP 壓制空方，可考慮順勢做空。"

    if latest_volume > volume_threshold and abs(price - vwap) > 0.02 * vwap:
        vwap_result += "\n⚠️ 價格遠離 VWAP 且成交量暴增，警惕假突破！"

    result += f"📉 當沖、日內指標：\n{vwap_result}\n"
    result += "----------------------------------------\n"

    # 五檔資訊
    result += f"{result_five_orders}\n"
    result += "----------------------------------------\n"

    # 最後更新時間
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    result += f"🕒 最後更新時間: {now}\n"

    # result = "\n".join([generate_text(row) for _, row in df_all.iterrows()])  

    print(result)
    export_data_window(ticker, ticker_name, result)


# 下載股價資料的公共函數
def get_stock_data(twTicker, period="60d", interval="1d"):
    stock_data = yf.download(twTicker, period=period, interval=interval)  # 最近60天資料
    return stock_data

def create_separator(parent):
    separator = tk.Frame(parent, height=2, bd=1, relief="sunken", bg="gray")
    separator.pack(fill="x", pady=5)
    return separator

def show_major_shareholders_hold_window(ticker, ticker_name, dates, percentages):
    # 建立新視窗
    result_window = tk.Toplevel()
    result_window.title(f"{ticker} - {ticker_name} 大股東持有")
    result_window.geometry("500x200")
    
    tk.Label(result_window, text=f"股票: {ticker} - {ticker_name}", font=("Arial", 14, "bold")).pack(pady=10)
    
    # 找到上個月底 (A) 和最近一次資料 (B)
    # 取得最近一次的資料 (B)
    B = float(percentages[0])  # 假設第一筆資料是最新的數據

    if len(dates) >= 2:
        # 取得當前年、月
        current_year = time.strftime("%Y")
        current_month = time.strftime("%m")
        print(f"current_month = {current_month}, current_year = {current_year}")

        # 找出上個月底的資料 (A)
        last_month = str(int(current_month) - 1).zfill(2)  # 轉換成兩位數格式
        last_month_str = f"{current_year}{last_month}"
        print(f"last_month_str = {last_month_str}")
        
        last_month_end_index = None        

        for i in range(len(dates)):
            date_str = str(dates[i])  # 轉成字串處理
            print(f"date_str = {date_str}")

            if date_str.startswith(last_month_str):
                last_month_end_index = i  # 記錄最後一筆當月資料
                print(f"找到上個月底的資料: {date_str}")
                break

        if last_month_end_index is not None:
            A = float(percentages[last_month_end_index])  # 上個月底的數值
        else:
            A = None  # 沒有找到上個月底的資料

        # 計算增幅
        if A is not None:
            increase = B - A
            increase_percentage = (increase / A) * 100 if A != 0 else 0
            change_text = f"{A:.2f} 變 {B:.2f} 增幅 {increase:.2f} ({increase_percentage:.2f}%)"
        else:
            change_text = f"最近一次持股: {B:.2f}（無法計算增幅）"
    else:
        change_text = "數據不足，無法計算"

    # 前次
    increase = float(percentages[0]) - float(percentages[1])
    increase_percentage = (increase / A) * 100 if A != 0 else 0
    last_text = f"{float(percentages[1]):.2f} 變 {B:.2f} 增幅 {increase:.2f} ({increase_percentage:.2f}%)"

    # 顯示本月大股東持股變化
    current_hold_label = tk.Label(result_window, text=f"大股東本月: {change_text}", font=("Arial", 12, "bold"))
    current_hold_label.pack(pady=5)

    last_hold_label = tk.Label(result_window, text=f"大股東前次: {last_text}", font=("Arial", 12, "bold"))
    last_hold_label.pack(pady=5)

    # 分隔線
    create_separator(result_window)

    # 更新時間顯示
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())  # 更新時間
    update_time_label = tk.Label(result_window, text=f"最後更新時間: {now}", font=("Arial", 10))
    update_time_label.pack(pady=10)

    # 關閉按鈕
    tk.Button(result_window, text="關閉", command=result_window.destroy).pack(pady=20)

def export_data_window(stock_id, ticker_name, text):
    result_window = tk.Toplevel()
    result_window.title(f"{stock_id} 懶惰鬼直接複製問AI")
    result_window.geometry("600x850")

    label = tk.Label(result_window, text=f"股票代碼：{stock_id}\n複製以下文字到ChatGPT吧！", font=("Arial", 14, "bold"))
    label.pack(pady=10)

    # 可捲動的文字框
    text_area = scrolledtext.ScrolledText(result_window, wrap=tk.WORD, font=("Courier", 11))
    text_area.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
    text_area.insert(tk.END, text)
    text_area.config(state=tk.NORMAL)  # 可讓使用者複製

    # 複製按鈕功能
    def copy_to_clipboard():
        result_window.clipboard_clear()
        result_window.clipboard_append(text_area.get("1.0", tk.END).strip())
        result_window.update()  # 更新剪貼簿
        copy_btn.config(text="✅ 已複製", state=tk.DISABLED)

    # 複製按鈕
    copy_btn = tk.Button(result_window, text="📋 複製文字", command=copy_to_clipboard, font=("Arial", 11))
    copy_btn.pack(pady=5)

    # 更新時間
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    update_time_label = tk.Label(result_window, text=f"更新時間：{now}", font=("Arial", 10))
    update_time_label.pack(pady=5)

    # 關閉按鈕
    tk.Button(result_window, text="關閉", command=result_window.destroy).pack(pady=10)

def show_result_window(ticker, twTicker, ticker_name, buy_reason, sell_reason):
    def update_result():
        """每 xx 秒重新獲取數據並更新 UI"""
        stock_data = get_stock_data(twTicker)
        
        # 更新股價
        currentPrice.config(text=f"目前股價: {stock_data['Close'].iloc[-1].values[0]}")
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

        # 補充：
        price = stock_data["Close"].iloc[-1].values[0]  # 當前價格
        vwap = ca.calculate_vwap(stock_data).values[0]
        volume_threshold = latest_mav * 3  # 成交量過濾閾值（300%）

        # print(f"latest_volume: {latest_volume}")
        # print(f"MAV: {latest_mav}")
        # print(f"Volume Ratio: {volume_ratio.values[0]}")
        # print(f"PVT: {pvt}")
        # print(f"CMF: {cmf.values[0]}")
        # print(f"VROC: {vroc.values[0]}")
        # print(f"latest_obv: {latest_obv}")
        # print(f"previous_obv: {previous_obv}")
        # print(f"latest_price: {latest_price}")
        # print(f"previous_price: {previous_price}")

        # 計算 5 日、10 日、20 日乖離率
        bias_values = ca.calculate_bias(stock_data)

        # 生成乖離率的顯示文字
        bias_text = ""
        for period, value in bias_values.items():
            # 取出 value 中的數值
            value = value.values[0]

            bias_status = "🔴 正乖離" if value > 0 else "🟢 負乖離"
            bias_text += f"{period} 日 BIAS: {value:.2f}% ({bias_status})\n"

        result = ca.decision_based_on_volume(latest_volume, latest_mav, volume_ratio.values[0], pvt, cmf.values[0], vroc.values[0], latest_obv, previous_obv, latest_price, previous_price)
        
        result_five_orders = ca.calculate_five_orders(ticker, twTicker)
        
        new_buy_reason, new_sell_reason, complex_reason = ca.get_four_points(ticker)        

        # 更新 Label 內容
        buy_label.config(text=f"✅ 符合四大買點: {new_buy_reason}" if new_buy_reason else "❌ 不符合四大買點")
        sell_label.config(text=f"⚠️ 符合四大賣點: {new_sell_reason}" if new_sell_reason else "✅ 不符合四大賣點")
        macd_label.config(text=f"MACD(移動平均線): {macd_signal}")  # 顯示 MACD 訊號
        rsi_label.config(text=f"RSI(70⬆超買,30⬇超賣): {new_rsi:.2f}")
        bollinger_label.config(text=f"布林帶: 上軌 {upper_band:.2f}, 下軌 {lower_band:.2f}, 中軌 {sma:.2f}\n決策:{decision}")
        bias_label.config(text=f"📊 乖離率分析\n正：避免追高買進，未來幾天可能會有一波股價下跌的修正\n負：避免殺低賣出，未來幾天可能會有一波股價上漲的反彈\n{bias_text}")

        # 顯示交易量投票結果
        volume_label.config(text=f"{result}")

        # VWAP 判斷
        if price > vwap:
            result = (f"📈 當前價格 {price:.2f} 高於 VWAP {vwap:.2f}，市場偏多。")
            if latest_volume > volume_threshold:
                result = (f"{result}\n⚠️ 成交量暴增，可能是主力拉高吸引散戶進場！")
            else:
                result = (f"{result}\n✅ VWAP 支撐多方，可考慮順勢做多。")
        elif price < vwap:
            result = (f"📉 當前價格 {price:.2f} 低於 VWAP {vwap:.2f}，市場偏空。")
            if latest_volume > volume_threshold:
                result = (f"{result}\n⚠️ 成交量暴增，可能是主力出貨！")
            else:
                result = (f"{result}\n✅ VWAP 壓制空方，可考慮順勢做空。")

        # 假突破判斷
        if latest_volume > volume_threshold and abs(price - vwap) > 0.02 * vwap:
            result = (f"{result}\n⚠️ 價格遠離 VWAP 且成交量暴增，警惕假突破！")

        vwap_label.config(text=f"當沖、日內指標：\n{result}")

        five_label.config(text=f"{result_five_orders}")

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
    result_window.title(f"{twTicker} - {ticker_name} 技術分析")
    result_window.geometry("500x800")
    
    stock_data = get_stock_data(twTicker)
    # print(f"stock_data = {stock_data}")
    tk.Label(result_window, text=f"股票: {twTicker} - {ticker_name}", font=("Arial", 14, "bold")).pack(pady=10)
    
    # 目前股價
    currentPrice = tk.Label(result_window, text=f"目前股價: {stock_data['Close'].iloc[-1].values[0]}", font=("Arial", 14, "bold"))
    currentPrice.pack(pady=5)

    # 買入訊息
    buy_label = tk.Label(result_window, text=f"✅ 符合四大買點: {buy_reason}" if buy_reason else "❌ 不符合四大買點", fg="green")
    buy_label.pack(pady=5)

    # 賣出訊息
    sell_label = tk.Label(result_window, text=f"⚠️ 符合四大賣點: {sell_reason}" if sell_reason else "✅ 不符合四大賣點", fg="orange")
    sell_label.pack(pady=5)

    # 分隔線
    create_separator(result_window)

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
    # 補充：
    price = stock_data["Close"].iloc[-1].values[0]  # 當前價格
    vwap = ca.calculate_vwap(stock_data).values[0]
    volume_threshold = latest_mav * 3  # 成交量過濾閾值（300%）

    # 計算 5 日、10 日、20 日乖離率
    bias_values = ca.calculate_bias(stock_data)

    # 生成乖離率的顯示文字
    bias_text = ""
    for period, value in bias_values.items():
        # 取出 value 中的數值
        value = value.values[0]

        bias_status = "🔴 正乖離" if value > 0 else "🟢 負乖離"
        bias_text += f"{period} 日 BIAS: {value:.2f}% ({bias_status})\n"

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
    
    result_five_orders = ca.calculate_five_orders(ticker, twTicker)

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

    # 顯示乖離率分析結果     
    bias_label = tk.Label(result_window, text=f"📊 乖離率分析\n正：避免追高買進，未來幾天可能會有一波股價下跌的修正\n負：避免殺低賣出，未來幾天可能會有一波股價上漲的反彈\n{bias_text}")
    bias_label.pack(pady=10)

    # 分隔線
    create_separator(result_window)

    # 顯示交易量投票結果  
    volume_label = tk.Label(result_window, text=f"中長線指標：\n{result}")
    volume_label.pack(pady=10)

    # 分隔線
    create_separator(result_window)

    # VWAP 判斷
    if price > vwap:
        result = (f"📈 當前價格 {price:.2f} 高於 VWAP {vwap:.2f}，市場偏多。")
        if latest_volume > volume_threshold:
            result = (f"{result}\n⚠️ 成交量暴增，可能是主力拉高吸引散戶進場！")
        else:
            result = (f"{result}\n✅ VWAP 支撐多方，可考慮順勢做多。")
    elif price < vwap:
        result = (f"📉 當前價格 {price:.2f} 低於 VWAP {vwap:.2f}，市場偏空。")
        if latest_volume > volume_threshold:
            result = (f"{result}\n⚠️ 成交量暴增，可能是主力出貨！")
        else:
            result = (f"{result}\n✅ VWAP 壓制空方，可考慮順勢做空。")

    # 假突破判斷
    if latest_volume > volume_threshold and abs(price - vwap) > 0.02 * vwap:
        result = (f"{result}\n⚠️ 價格遠離 VWAP 且成交量暴增，警惕假突破！")

    vwap_label = tk.Label(result_window, text=f"當沖、日內指標：\n{result}")
    vwap_label.pack(pady=10)

    # 分隔線
    create_separator(result_window)

    five_label = tk.Label(result_window, text=f"{result_five_orders}")
    five_label.pack(pady=10)

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

def main():
    # 設定GUI界面
    global root
    global ticker_entry
    global table
    global loading_window, table_columns, status_label

    root = tk.Tk()
    root.title("股票資訊查詢")

    # 創建一個頂層視窗用於顯示 Loading，這個視窗會蓋在主視窗上
    loading_window = tk.Toplevel(root)
    loading_window.title("Loading")
    loading_window.geometry("300x300")
    loading_window.withdraw()  # 預設隱藏 loading 視窗
    # 創建 loading 標籤
    loading_label = tk.Label(loading_window, text="Loading...", font=("Arial", 14))
    loading_label.pack(expand=True)

    # 建立一個 Frame 來包裝這些控制元件
    input_frame = tk.Frame(root)
    input_frame.grid(row=0, column=0, sticky="w")  # 用 grid 放置 Frame

    # 輸入股票代號
    ticker_label = tk.Label(input_frame, text="輸入台灣股票代號 (如 2330 或 0050):")
    ticker_label.pack(side="left")

    ticker_entry = tk.Entry(input_frame)
    ticker_entry.pack(side="left")

    # 按鈕
    add_button = tk.Button(input_frame, text="新增", command=add_stock_data)
    add_button.pack(side="left")
    # update_button = tk.Button(input_frame, text="更新所有", command=lambda: update_all_stocks(loading_label))
    update_button = tk.Button(input_frame, text="更新所有", command=lambda: start_update(loading_window, table, table_columns, status_label))
    update_button.pack(side="left")

    bestFour_button = tk.Button(input_frame, text="技術分析", command=analysis_event)
    predict_button = tk.Button(input_frame, text="預測", command=predict_stock)
    ms_hold_button = tk.Button(input_frame, text="大股東持有", command=major_shareholders_hold)
    # futures_valuation_button = tk.Button(input_frame, text="00715L期貨估值", command=futures_valuation_hold)
    export_button = tk.Button(input_frame, text="懶人匯出問AI", command=export_data_hold)
    
    bestFour_button.pack_forget()  # 隱藏技術分析按鈕
    predict_button.pack_forget()  # 隱藏預測按鈕
    ms_hold_button.pack_forget()  
    export_button.pack_forget()  

    # 設定表格欄位名稱
    table_columns = [
        "代號", "名稱", "EPS", "本益比", "平均最低", 
        "建議買入", "平均最高", "建議賣出", "平均交易量", "今天交易量", 
        "平均收盤", "昨天收盤", "今天收盤", "趨勢", "震盪", "預估最低", 
        "預估最高", "殖利率"
    ]

    # 設定表格
    table = ttk.Treeview(root, columns=table_columns, show="headings", height=25)
    table.grid(row=1, column=0, columnspan=4, padx=10, pady=10)

    # 設定表格標題
    for col in table_columns:
        table.heading(col, text=col)
        table.column(col, width=75, anchor="center")

    # 設定紅色字的標籤
    table.tag_configure("red", foreground="red")
    # 設定綠色字的標籤
    table.tag_configure("green", foreground="green")

    # 監聽表格選擇事件
    def on_item_select(event):
        bestFour_button.pack(side="left")
        predict_button.pack(side="left")
        ms_hold_button.pack(side="left")
        export_button.pack(side="left")
    table.bind("<<TreeviewSelect>>", on_item_select)

    # 顯示更新狀態
    status_label = tk.Label(root, text="尚未更新", anchor="w")
    status_label.grid(row=2, column=0, columnspan=4, sticky="w", padx=10, pady=5)    

    # 在啟動時顯示儲存的股號
    start_update(loading_window, table, table_columns, status_label)    
    # display_saved_tickers()
    
    # 啟動 GUI 界面
    root.mainloop()

# 開始更新操作
def start_update(loading_window, table, table_columns, status_label):
    # 顯示 loading 視窗
    loading_window.deiconify()  # 顯示 loading 視窗
    # 在背景執行更新操作
    threading.Thread(target=update_all_stocks, args=(loading_window, table, table_columns, status_label), daemon=True).start()

# 測試
# twTicker = "1301.TW"
# twTicker = "2603.TW"
# twTicker = "6129.TWO"
# stock = yf.Ticker(twTicker)
# print(stock.info)
# print("========================")

# data = stock.history(period="2d")  # 取得最近兩天的數據，以防有缺失

# previous_date = data.index[-2].strftime("%Y-%m-%d")
# print(f"[1]previous_date = {previous_date}")

# previous_close = data["Close"].iloc[-2]  # 倒數第二筆數據為前一日收盤價
# print(f"[1]previous_close = {previous_close}")

# previous_date = data.index[-1].strftime("%Y-%m-%d")
# print(f"[2]previous_date = {previous_date}")

# previous_close = data["Close"].iloc[-1]
# print(f"[2]previous_close = {previous_close}")
# print("========================")

# tw_stock = Stock("2603")
# print(f"tw_stock = {tw_stock.price}")
# print(f"tw_stock = {tw_stock.date}")
# print("========================")

# tw_stock = Stock("00712")
# print(f"00712 tw_stock = {tw_stock.price}")
# print(f"00712 tw_stock = {tw_stock.date}")
# print("========================")

# tw_stock = Stock("00715L")
# print(f"00715L tw_stock = {tw_stock.price}")
# print(f"00715L tw_stock = {tw_stock.date}")
# last_date = tw_stock.date[-1]
# formatted_date = last_date.strftime("%Y-%m-%d")  # 格式化為 'YYYY-MM-DD'
# print(f"最後一天的日期: {formatted_date}")
# print("========================")


from dotenv import load_dotenv  

# 運行主程式
if __name__ == "__main__":
    main()

    STOCK_CHIP_DOMAIN = "https://www.tdcc.com.tw"
    STOCK_CHIP_URL = f"{STOCK_CHIP_DOMAIN}/portal/zh/smWeb/"

    # load_dotenv()         
    # token=os.environ.get('FinMind_TOKEN')    
    # print(token)

    # # 設定請求 URL 和 POST 資料
    # url = "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock"
    # payload = {
    #     "method": "submit",
    #     "firDate": "20250321",
    #     "scaDate": "20250321",
    #     "sqlMethod": "StockNo",
    #     "stockNo": "6129",
    #     "stockName": ""
    # }

    # # 設定 Headers（模擬瀏覽器）
    # headers = {
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    #     "Content-Type": "application/x-www-form-urlencoded",
    # }

    # # 發送 POST 請求
    # response = requests.post(url, data=payload, headers=headers)

    # # 檢查請求是否成功
    # if response.status_code == 200:
    #     # 解析 HTML
    #     soup = BeautifulSoup(response.text, "html.parser")        

    #     # 找到表格
    #     table = soup.find("div", class_="table-frame securities-overview m-t-20")

    #     if table:
    #         rows = table.find_all("tr")[1:]  # 跳過表頭
    #         data_list = []

    #         for row in rows:
    #             cols = row.find_all("td")
    #             if len(cols) == 5:
    #                 data = {
    #                     "序": cols[0].text.strip(),
    #                     "持股/單位數分級": cols[1].text.strip(),
    #                     "人數": cols[2].text.strip(),
    #                     "股數/單位數": cols[3].text.strip(),
    #                     "占集保庫存數比例 (%)": cols[4].text.strip(),
    #                 }
    #                 data_list.append(data)

    #         # 印出結果
    #         for item in data_list:
    #             print(item)
    #     else:
    #         print("找不到表格")
    # else:
    #     print("請求失敗，狀態碼：", response.status_code)


