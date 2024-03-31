import matplotlib.pyplot as plt
import pandas as pd

from stockPriceHistory import StockPriceHistory
from gxTransData import AccountSummary


# 计算股票当日市值
def cal_market_value(stock_holding_records, start_date):
    stock_holding_records['交收日期'] = pd.to_datetime(stock_holding_records['交收日期'])
    stock_holding_records['当日市值'] = 0.0
    stock_price_df = StockPriceHistory().get_stock_price_df(start_date)

    # Perform inner join on '证券代码' and '交收日期'
    merged_df = pd.merge(stock_holding_records, stock_price_df[['证券代码', '日期', '收盘']], how='left',
                         left_on=['证券代码', '交收日期'], right_on=['证券代码', '日期'])

    print(merged_df)
    # Update '当日市值' based on fetched close prices
    merged_df['当日市值'] = merged_df.apply(lambda row: row['持股成本'] if pd.isnull(row['收盘']) else row['收盘'] * row['持股数量'],
                                        axis=1)
    merged_df['浮动盈亏'] = merged_df['当日市值'] - merged_df['持股成本']

    merged_df = merged_df[['交收日期', '账户类型','证券代码', '证券名称', '持股数量', '持股成本', '当日市值', '浮动盈亏']]
    return merged_df


# 计算账户市值
def cal_account_profit(df_market_value, account_balance_records):
    # 使用groupby和sum函数按日期分组求和当日市值
    df_sum = df_market_value.groupby(['交收日期', '账户类型'])['当日市值'].sum().reset_index()

    # 当日市值丢弃，用df_sum里的重新计算
    account_balance_records.drop('当日市值', axis=1, inplace=True)

    df_account_profit = pd.merge(account_balance_records, df_sum, how='left', on=['交收日期', '账户类型'])
    df_account_profit['当日市值'].fillna(0.0, inplace=True)
    df_account_profit['盈亏'] = df_account_profit['资金余额'] + df_account_profit['当日市值'] - df_account_profit['累计净转入资金']
    print(df_account_profit)
    df_total_profit = df_account_profit.groupby(['交收日期'])['盈亏'].sum().reset_index()
    return df_total_profit, df_account_profit


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


def analyze(start_date=None):
    account_summary = AccountSummary()
    # Load data from AccountSummary
    stock_holding_records, account_balance_records = account_summary.load_account_summaries(start_date)

    # 获取股票的market_valeu
    df_market_value = cal_market_value(stock_holding_records, start_date)

    df_total_profit, df_account_profit = cal_account_profit(df_market_value, account_balance_records)

    if start_date is None:
        start_date = pd.to_datetime('20070501', format='%Y%m%d')
    with pd.ExcelWriter(AccountSummary.ACCOUNT_SUMMARY_FILE, engine='openpyxl',
                        mode='a', if_sheet_exists='overlay') as writer:
        # 将数据写入Excel文件的不同sheet
        account_summary.append_data_to_sheet(writer, '账户余额历史', df_account_profit, start_date)
        account_summary.append_data_to_sheet(writer, '股票持仓历史', df_market_value, start_date)

    # 设置数据格式
    account_summary.format_account_summary_file()

    visualize_profit(df_total_profit)


analyze()  # start_date=pd.to_datetime('20231125', format='%Y%m%d'))
