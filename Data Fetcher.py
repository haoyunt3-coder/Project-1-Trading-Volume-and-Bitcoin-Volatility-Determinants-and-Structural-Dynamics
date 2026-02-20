import requests
import pandas as pd
import time
import datetime

# Binance API 配置
BINANCE_BASE_URL = "https://api.binance.com/api/v3/klines"
BINANCE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "LTCUSDT", "DOGEUSDT", "BNBUSDT", "XRPUSDT"]  # 主要币种
INTERVAL = "1d"  # 1天K线
START_DATE = "2017-01-01"
LIMIT = 1000  # Binance 每次最多返回 1000 条数据

# 计算起始时间戳（毫秒）
start_timestamp = int(time.mktime(datetime.datetime.strptime(START_DATE, "%Y-%m-%d").timetuple())) * 1000


# 函数：获取 Binance 交易数据
def get_binance_data(symbol):
    all_data = []
    start_time = start_timestamp
    while True:
        url = f"{BINANCE_BASE_URL}?symbol={symbol}&interval={INTERVAL}&startTime={start_time}&limit={LIMIT}"
        response = requests.get(url)
        data = response.json()

        if not isinstance(data, list):  # 如果 API 返回错误信息，则打印出来
            print(f"获取 {symbol} 数据失败: {data}")
            break

        if not data:
            break  # 如果没有数据，停止获取

        for entry in data:
            all_data.append([
                datetime.datetime.fromtimestamp(entry[0] / 1000).strftime('%Y-%m-%d'),  # 日期
                symbol,
                float(entry[1]),  # 开盘价
                float(entry[2]),  # 最高价
                float(entry[3]),  # 最低价
                float(entry[4]),  # 收盘价
                float(entry[5])  # 交易量
            ])

        start_time = data[-1][0] + 1  # 移动到下一个时间段
        time.sleep(0.5)  # 避免 API 速率限制

    return all_data


# 获取所有币种数据

for symbol in BINANCE_SYMBOLS:
    binance_data = []
    print(f"正在获取 {symbol} 的数据...")
    binance_data.extend(get_binance_data(symbol))
    df = pd.DataFrame(binance_data, columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])
    df.to_csv(f"{symbol}crypto_market_data_binance.csv", index=False)


'''
# 转换为 DataFrame 并保存为 CSV
df = pd.DataFrame(binance_data, columns=["Date", "Symbol", "Open", "High", "Low", "Close", "Volume"])
df.to_csv("crypto_market_data_binance.csv", index=False)

print("数据抓取完成，已保存为 crypto_market_data_binance.csv")
'''