import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from gxTransData import AccountSummary
from stockPriceHistory import StockPriceHistory


# 计算股票当日市值
def cal_market_value(stock_holding_records, stock_price_df):
    stock_holding_records['交收日期'] = pd.to_datetime(stock_holding_records['交收日期'])
    stock_holding_records['当日市值'] = 0.0

    # Perform inner join on '证券代码' and '交收日期'
    merged_df = pd.merge(stock_holding_records, stock_price_df[['证券代码', '日期', '收盘']], how='left',
                         left_on=['证券代码', '交收日期'], right_on=['证券代码', '日期'])

    print(merged_df)
    # Update '当日市值' based on fetched close prices
    merged_df['当日市值'] = merged_df.apply(lambda row: row['持股成本'] if pd.isnull(row['收盘']) else row['收盘'] * row['持股数量'],
                                        axis=1)
    merged_df['浮动盈亏'] = merged_df['当日市值'] - merged_df['持股成本']

    merged_df = merged_df[['交收日期', '账户类型', '证券代码', '证券名称', '持股数量', '持股成本', '当日市值', '浮动盈亏']]
    return merged_df


# 计算账户市值
def cal_account_profit(df_market_value, account_balance_records):
    # 使用groupby和sum函数按日期分组求和当日市值
    df_sum = df_market_value.groupby(['交收日期', '账户类型'])['当日市值'].sum().reset_index()

    # 当日市值丢弃，用df_sum里的重新计算
    account_balance_records.drop('当日市值', axis=1, inplace=True)

    df_account_profit = pd.merge(account_balance_records, df_sum, how='left', on=['交收日期', '账户类型'])
    df_account_profit['当日市值'] = df_account_profit['当日市值'].fillna(0.0)
    df_account_profit['盈亏'] = df_account_profit['资金余额'] + df_account_profit['当日市值'] - df_account_profit['累计净转入资金']
    print(df_account_profit)
    df_total_profit = calcu_total_profit(df_account_profit)
    return df_total_profit, df_account_profit


# 计算账户的综合累计盈利和区间相对盈利
def calcu_total_profit(df_account_profit):
    df_total_profit = df_account_profit.groupby(['交收日期'])['盈亏'].sum().reset_index()
    return df_total_profit


# 分析实际交易的信息，并保存到文件里
def analyze_and_update(start_date=None):
    account_summary = AccountSummary()
    # Load data from AccountSummary
    stock_holding_records, account_balance_records = account_summary.load_account_summaries(start_date)
    # 加载股票价格
    stock_price_df = StockPriceHistory().get_stock_price_df(start_date)
    # 获取股票的market_value
    df_market_value = cal_market_value(stock_holding_records, stock_price_df)

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


# 绘制盈利图像
def draw_profit(start_date):
    # 从文件里重新加载再计算
    account_summary = AccountSummary()
    stock_holding_records, df_account_profit = account_summary.load_account_summaries(start_date)
    df_total_profit = calcu_total_profit(df_account_profit)

    visualize_profit(df_total_profit)


def annotate_profit(x, y, text, ax):
    ax.annotate(text, (x, y), textcoords="offset points", xytext=(0, 10), ha='center')


def format_date(x, pos, df_profit):
    index = find_nearest_date_in_figure(df_profit, x)
    if 0 < index < len(df_profit['交收日期']):
        return df_profit['交收日期'].iloc[index].strftime('%Y-%m-%d')
    else:
        return ''


def find_nearest_date_in_figure(df_profit, x):
    index = -999
    if x is not None:
        input_date = pd.to_datetime(mdates.num2date(x)).tz_localize(None).normalize()
        index = df_profit['交收日期'].searchsorted(input_date)
    return index


def on_click_show_profit(event, df_profit, fig, ax):
    index = find_nearest_date_in_figure(df_profit, event.xdata)
    if 0 < index < len(df_profit):
        profit = df_profit['盈亏'].iloc[index] / 10000
        annotate_profit(event.xdata, event.ydata, f"{df_profit['交收日期'].iloc[index].strftime('%Y/%m/%d')}: {profit:.2f}",
                        ax)
        fig.canvas.draw_idle()


def visualize_profit(df_total_profit):
    # 计算每日盈利
    df_daily_profit = df_total_profit['盈亏'].diff()
    df_daily_profit = pd.DataFrame({'交收日期': df_total_profit['交收日期'], '盈亏': df_daily_profit})

    plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
    plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
    # 创建一个新的figure，共享X轴
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # 绘制按日累计盈利曲线
    ax1.plot(df_total_profit['交收日期'], df_total_profit['盈亏'] / 10000, color='r', label='累计盈利')
    ax1.set_title('累计盈利曲线图')
    ax1.set_ylabel('盈利(万元)')
    ax1.tick_params(axis='x', rotation=45)
    ax1.ticklabel_format(style='plain', axis='y', useOffset=False)
    ax1.grid(True)
    ax1.legend()

    # 绘制每日盈利柱状图
    ax2.bar(df_daily_profit['交收日期'], df_daily_profit['盈亏'] / 10000,
            color=df_daily_profit['盈亏'].apply(lambda x: 'g' if x < 0 else 'r'))
    ax2.set_title('每日盈利', loc='center')
    ax2.set_xlabel('日期')
    ax2.tick_params(axis='x', rotation=45)
    ax2.set_ylabel('盈利(万元)')
    ax2.grid(True)

    # 设置 x 轴刻度范围
    min_date = df_total_profit['交收日期'].min()
    max_date = df_total_profit['交收日期'].max()
    ax1.set_xlim(min_date, max_date)
    ax2.set_xlim(min_date, max_date)

    # 添加点击事件,显示具体数值
    fig.canvas.mpl_connect('button_press_event', lambda event: on_click_show_profit(event, df_total_profit, fig, ax1))
    fig.canvas.mpl_connect('button_press_event', lambda event: on_click_show_profit(event, df_daily_profit, fig, ax2))

    # 调整子图间距,让它们能够充满整个画布
    plt.subplots_adjust(hspace=0.5)

    plt.tight_layout()
    plt.show()


# 模拟某日没有做操作的信息
def simulate(checkpoint_date):
    sim_stock_holding_records, sim_account_balance_records = get_sim_account_history(checkpoint_date)
    # 获取股票后复权信息
    stock_price_df = StockPriceHistory().cal_hfq_price(sim_stock_holding_records, checkpoint_date)
    # 获取股票的market_value
    df_market_value = cal_market_value(sim_stock_holding_records, stock_price_df)
    df_total_profit, df_account_profit = cal_account_profit(df_market_value, sim_account_balance_records)
    visualize_profit(df_total_profit)


# 获取从变动仓位日期开始至今天的模拟账户信息
def get_sim_account_history(checkpoint_date):
    filtered_dates = get_trade_dates(checkpoint_date)
    account_summary = AccountSummary()
    today_holdings, today_balance = account_summary.init_start_holdings(checkpoint_date)
    today_balance['盈亏'] = 0.0
    today_balance['当日市值'] = 0.0
    for current_date in filtered_dates:
        today_holdings['交收日期'] = current_date
        today_balance['交收日期'] = current_date
        # 将该日的市值持仓的记录更新追加到history里
        account_summary.add_to_history(today_balance, today_holdings)
        # copy一份作为新的交易日的空白记录
        today_holdings = today_holdings.copy()
        today_balance = today_balance.copy()

    return account_summary.stockhold_history, account_summary.balance_history


# 获取从startDate到今天的所有沪深股市交易日list
def get_trade_dates(start_date):
    # 获取当前日期
    today = datetime.date.today()
    # 生成日期序列
    date_range = pd.date_range(start=start_date, end=today, freq='D')
    # 获取所有的交易日日期
    trade_dates = StockPriceHistory.load_trade_dates()
    trade_dates = trade_dates[trade_dates['trade_date'] > start_date]
    # 使用isin()方法过滤日期
    filtered_dates = date_range[date_range.isin(trade_dates['trade_date'])]
    return filtered_dates


def run():
    start_date = pd.to_datetime('20230101', format='%Y%m%d')
    # analyze_and_update(start_date)
    draw_profit(start_date)

    # checkpoint_date = pd.to_datetime('20231124', format='%Y%m%d')
    # simulate(checkpoint_date)


if __name__ == "__main__":
    run()
