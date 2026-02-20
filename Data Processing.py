import pandas as pd
import numpy as np

# 监管事件日期
RegSin = pd.to_datetime(["2020-01-28"])
RegEU = pd.to_datetime(["2023-07-19"])


# 代币列表
SYMBOLS = ["BTCUSDT", "ETHUSDT", "LTCUSDT", "DOGEUSDT", "BNBUSDT", "XRPUSDT"]
symbols = ["BTC", "ETH", "LTC", "DOGE", "BNB", "XRP"]

for symbol in SYMBOLS:
    # 读取市场数据
    index = SYMBOLS.index(symbol)
    symbol_data = pd.read_csv(f"{symbol}crypto_market_data_binance.csv")
    symbol_data['Date'] = pd.to_datetime(symbol_data['Date']).dt.date
    currency = symbols[index]

    # **计算 (t-1) 日最高价格的对数**
    symbol_data["Price"] = np.log(symbol_data["High"].shift(1).replace(0, np.nan))

    # **计算交易量的对数**
    symbol_data['Log_Volume'] = np.log(symbol_data['Volume'].replace(0, np.nan))

    # **计算日内价格波动**
    symbol_data['Volatility of Intraday Price'] = np.sqrt(
        np.log(symbol_data['High'] / symbol_data['Low']) * np.log(symbol_data['High'] / symbol_data['Open']) +
        np.log(symbol_data['Low'] / symbol_data['Close']) * np.log(symbol_data['Low'] / symbol_data['Open'])
    )

    # **计算 7 日指数加权移动平均 (EWMA)**
    symbol_data['7D_EWMA_Intraday_Price_Volatility'] = (
        symbol_data['Volatility of Intraday Price'].ewm(span=7, adjust=False).mean())

    # **计算收益率**
    symbol_data["Return"] = np.log(symbol_data["Close"] / symbol_data["Close"].shift(1))

    # **计算滞后一周期的收益率**
    symbol_data["Lagged_Return"] = symbol_data["Return"].shift(1)

    # **计算收益率波动性 σRt (6 天滚动标准差)**
    symbol_data["σ_Rt"] = symbol_data["Return"].rolling(window=6).std()
    '''
    # **计算价差估计量 Spread**
    beta_t = (np.log(symbol_data["High"] / symbol_data["Low"])) ** 2 + (
        np.log(symbol_data["High"].shift(1) / symbol_data["Low"].shift(1))) ** 2
    gamma_t = (np.log(np.maximum(symbol_data["High"], symbol_data["High"].shift(1)) /
                      np.minimum(symbol_data["Low"], symbol_data["Low"].shift(1)))) ** 2
    alpha_t = (np.sqrt(2 * beta_t) - np.sqrt(beta_t)) / (3 - 2 * np.sqrt(2) - np.sqrt(3) - gamma_t * np.sqrt(2))

    symbol_data["Spread"] = 2 * (np.exp(alpha_t) - 1) / (np.exp(alpha_t) + 1)

    # 负值设为 0
    symbol_data["Spread"] = symbol_data["Spread"].clip(lower=0)

    # **计算流动性波动性 σLIQt (6 天滚动标准差)**
    symbol_data["σ_LIQt"] = symbol_data["Spread"].rolling(window=6).std()
    '''

    # 确保交易量非零，避免除零错误
    symbol_data["Amihud"] = symbol_data["Return"].abs() / symbol_data["Log_Volume"]
    symbol_data["Amihud"].replace([np.inf, -np.inf], np.nan, inplace=True)
    symbol_data["Amihud"].fillna(0, inplace=True)

    # 计算 6 天滚动标准差，作为流动性波动性
    symbol_data["σ_LIQt"] = symbol_data["Amihud"].rolling(window=6).std()


    # 读取市值数据
    CapData = pd.read_csv(f"CRYPTOCAP_{currency}, 1D.csv")
    BTCD = pd.read_csv("BTC_Dominance_converted.csv")

    # **处理市值数据**
    CapData['Date'] = pd.to_datetime(CapData['time'], unit='s').dt.date
    CapData['Cap'] = (CapData['close'] + CapData['open'] + CapData['high'] + CapData['low']) / 4

    # **计算市值的对数**
    CapData['Log_Cap'] = np.log(CapData['Cap'].replace(0, np.nan))
    CapData.drop(columns=['high', 'low', 'open', 'close', 'Volume', 'time', 'Cap'], inplace=True)

    # **处理比特币主导数据**
    BTCD['Date'] = pd.to_datetime(BTCD['Datetime']).dt.date
    BTCD['BitcoinDominance'] = (BTCD['close'] + BTCD['open'] + BTCD['high'] + BTCD['low']) / 4
    BTCD.drop(columns=['close', 'open', 'high', 'low', 'Volume', 'time'], inplace=True)

    # **合并数据集**
    merged_df = pd.merge(symbol_data, CapData, on="Date", how="inner")
    merged_df = pd.merge(merged_df, BTCD, on="Date", how="inner")
    merged_df["Date"] = pd.to_datetime(merged_df["Date"])


    # **添加监管事件 Dummy 变量**
    merged_df["RegSin"] = merged_df["Date"].isin(pd.to_datetime(RegSin)).astype(int)
    merged_df["RegEU"] = merged_df["Date"].isin(pd.to_datetime(RegEU)).astype(int)

    # **读取 EPU 数据**
    EPU_EU = pd.read_csv("EPU_EU.csv")
    EPU_Sin = pd.read_csv("EPU_Sin.csv")

    # **删除无关数据**
    EPU_EU.drop(columns=["Germany_News_Index","Italy_News_Index","UK_News_Index","France_News_Index","Spain_News_Index"], inplace=True)

    for EPU in [EPU_EU, EPU_Sin]:
        EPU["Year"] = pd.to_numeric(EPU["Year"], errors="coerce")
        EPU["Month"] = pd.to_numeric(EPU["Month"], errors="coerce")
        EPU.dropna(subset=["Year", "Month"], inplace=True)
        EPU["Year"] = EPU["Year"].astype(int)
        EPU["Month"] = EPU["Month"].astype(int)
        EPU["Month_Date"] = pd.to_datetime(EPU["Year"].astype(str) + "-" + EPU["Month"].astype(str) + "-01")

        # **EPU 数据取对数**
        numeric_cols = EPU.select_dtypes(include=[np.number]).columns
        EPU[numeric_cols] = EPU[numeric_cols].apply(lambda x: np.log(x.replace(0, np.nan)))

    # **按月合并 EPU**
    merged_df = pd.merge_asof(
        merged_df.sort_values("Date"),
        EPU_EU.sort_values("Month_Date"),
        left_on="Date",
        right_on="Month_Date",
        direction="backward",
        tolerance=pd.Timedelta("31 days")
    ).drop(columns=["Month_Date"], errors="ignore")

    merged_df = pd.merge_asof(
        merged_df.sort_values("Date"),
        EPU_Sin.sort_values("Month_Date"),
        left_on="Date",
        right_on="Month_Date",
        direction="backward",
        tolerance=pd.Timedelta("31 days")
    ).drop(columns=["Month_Date"], errors="ignore")

    # **保存最终数据**
    merged_df.to_csv(f"{currency}_merged_data.csv", index=False)
    print(f"✅ {currency} 数据合并完成，仅保留共有时间区间:")
    print(merged_df.info())

# **合并所有币种的数据**
dfs = []
for symbol in symbols:
    file_name = f"{symbol}_merged_data.csv"
    df = pd.read_csv(file_name)
    df["Date"] = pd.to_datetime(df["Date"])
    df["Symbol"] = symbol
    dfs.append(df)

merged_df = pd.concat(dfs, ignore_index=True)

# **找到所有币种的共同时间段**
common_dates = merged_df.groupby("Date")["Symbol"].nunique()
valid_dates = common_dates[common_dates == len(symbols)].index

# **过滤数据**
merged_df = merged_df[merged_df["Date"].isin(valid_dates)]

# **保存最终数据**
merged_df.to_csv("merged_data.csv", index=False)
print("✅ 数据合并完成，仅保留共有时间区间。")

import pandas as pd

# 读取数据
df = pd.read_csv("merged_data.csv")

# 检查数据框的每一列缺失值情况
missing_values = df.isna().sum()
print("缺失值统计：\n", missing_values)

# 检查数据的行数是否一致
print("\n数据形状 (行, 列):", df.shape)
df_cleaned = df.dropna()
df_cleaned.to_csv("merged_data.csv", index=False)
