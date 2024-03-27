import matplotlib.pyplot as plt
import pandas as pd

from stockPriceHistory import StockPriceHistory


# 计算当日市值
def cal_market_value(stock_holding_records):
    stock_holding_records['交收日期'] = pd.to_datetime(stock_holding_records['交收日期'])
    stock_holding_records['当日市值'] = 0.0
    # Perform inner join on '证券代码' and '交收日期'
    merged_df = pd.merge(stock_holding_records, StockPriceHistory.stock_price_df[['证券代码', '日期', '收盘']], how='left',
                         left_on=['证券代码', '交收日期'], right_on=['证券代码', '日期'])
    print(merged_df)
    # Update '当日市值' based on fetched close prices
    merged_df['当日市值'] = merged_df.apply(lambda row: row['持股成本'] if pd.isnull(row['收盘']) else row['收盘'] * row['持股数量'],
                                        axis=1)
    # 使用groupby和sum函数按日期分组求和当日市值
    df_sum = merged_df.groupby(['交收日期', '账户类型'])['当日市值'].sum().reset_index()
    print(df_sum)
    return df_sum


def cal_account_profit(df_market_value):
    df_account = pd.read_excel('analyze_summary.xlsx', sheet_name="账户余额历史", header=0)
    df_account_profit = pd.merge(df_account, df_market_value, how='left', on=['交收日期', '账户类型'])
    df_account_profit['当日市值'].fillna(0.0, inplace=True)
    df_account_profit['盈亏'] = df_account_profit['资金余额'] + df_account_profit['当日市值'] - df_account_profit['累计净转入资金']
    df_account_profit.to_excel("temp_out.xlsx")
    df_total_profit = df_account_profit.groupby(['交收日期'])['盈亏'].sum().reset_index()
    print(df_total_profit.describe())
    return df_account_profit


def visualize_profit(df_total_profit):
    # 绘制盈利曲线
    plt.figure(figsize=(12, 6))
    plt.plot(df_total_profit['交收日期'], df_total_profit['盈亏'], marker='o', color='b', linestyle='-')
    # 设置图形标题和标签
    plt.title('Daily Profit Over Time')
    plt.xlabel('Date')
    plt.ylabel('Profit')
    plt.xticks(rotation=45)  # 旋转日期标签，使其更易读
    # 显示网格线和图例
    plt.grid(True)
    plt.legend(['Profit'])
    # 显示图形
    plt.show()


def analyze():
    # Initialize data at the beginning
    StockPriceHistory.initialize_data(auto_fetch_from_ak=True)
    stock_holding_records = pd.read_excel('analyze_summary.xlsx', sheet_name="股票持仓历史", header=0, dtype={'证券代码': str})

    # 获取新的DataFrame，包含日期和当日市值的总和
    df_market_value = cal_market_value(stock_holding_records)
    # 获取账户每日盈利
    df_total_profit = cal_account_profit(df_market_value)
    # 可视化
    visualize_profit(df_total_profit)


analyze()
