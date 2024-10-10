import datetime

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
# 计算股票当日市值
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter

from gxTransData import AccountSummary
from stockPriceHistory import StockPriceHistory


def cal_market_value(stock_holding_records, stock_price_df):
    # 转换交收日期为日期格式，并初始化当日市值为0
    stock_holding_records['交收日期'] = pd.to_datetime(stock_holding_records['交收日期'])
    stock_holding_records['当日市值'] = 0.0

    # 合并持仓记录与股票价格数据
    merged_df = pd.merge(stock_holding_records, stock_price_df[['证券代码', '日期', '收盘']], how='left',
                         left_on=['证券代码', '交收日期'], right_on=['证券代码', '日期'])

    # 对正常有收盘价的，更新当日市值
    merged_df['当日市值'] = merged_df.apply(
        lambda row: row['当日市值'] if pd.isnull(row['收盘']) else row['收盘'] * row['持股数量'],
        axis=1
    )

    # 初始化备注列
    merged_df['备注'] = ''

    # 筛选出收盘价缺失的行
    missing_close_prices = merged_df[merged_df['收盘'].isnull()]

    # 留存有收盘价的记录，用于更新当日市值
    temp_history_df = stock_price_df[stock_price_df['收盘'].notnull()]

    # 遍历收盘价缺失的记录，尝试查找上一个交易日的市值
    for index, row in missing_close_prices.iterrows():
        security_code = row['证券代码']
        settlement_date = row['交收日期']

        # 查找上一个交易日的股价
        previous_price = find_previous_market_value(temp_history_df, security_code, settlement_date)
        if pd.notnull(previous_price):
            merged_df.at[index, '当日市值'] = previous_price * row['持股数量']
            merged_df.at[index, '备注'] = '停牌'
        else:
            # 添加持股成本小于0时按0赋值的逻辑
            holding_cost = max(0, row['持股成本'])
            merged_df.at[index, '当日市值'] = holding_cost
            merged_df.at[index, '备注'] = '估算'

    # 计算浮动盈亏
    merged_df['浮动盈亏'] = merged_df['当日市值'] - merged_df['持股成本']

    # 选择需要的列
    merged_df = merged_df[
        ['交收日期', '账户类型', '证券代码', '证券名称', '持股数量', '持股成本', '当日市值', '浮动盈亏', '备注']]

    return merged_df


def find_previous_market_value(stock_price_df, security_code, settlement_date):
    # 查找上一个交易日的市值
    previous_dates = stock_price_df[
        (stock_price_df['证券代码'] == security_code) & (stock_price_df['日期'] < settlement_date)]
    if not previous_dates.empty:
        latest_date = previous_dates['日期'].max()
        return previous_dates.loc[previous_dates['日期'] == latest_date, '收盘'].values[0]
    return None


# 计算账户市值
def cal_account_profit(df_market_value, account_balance_records):
    # 使用groupby和sum函数按日期分组求和当日账户资产净值市值
    df_sum = df_market_value.groupby(['交收日期', '账户类型'])['当日市值'].sum().reset_index()

    df_account_profit = pd.merge(account_balance_records, df_sum, how='left', on=['交收日期', '账户类型'],
                                 suffixes=('', '_sum'))

    # 使用 df_sum 中的 '当日市值' 替换 account_balance_records 中的 '当日市值'
    df_account_profit['当日市值'] = df_account_profit['当日市值_sum']
    # 删除多余的列
    df_account_profit.drop(columns=['当日市值_sum'], inplace=True)

    df_account_profit['当日市值'] = df_account_profit['当日市值'].fillna(0.0)
    df_account_profit['资产净值'] = (df_account_profit['资金余额'] + df_account_profit['当日市值'] - (
                df_account_profit['融资借款'] + df_account_profit['冻结资金']))
    df_account_profit['盈亏'] = df_account_profit['资产净值'] - df_account_profit['累计净转入资金']

    # 筛选数值型列，遍历数值型列并处理，去除特别小的科学记数法数据
    numeric_columns = df_account_profit.select_dtypes(include=['number']).columns
    for column in numeric_columns:
        df_account_profit.loc[abs(df_account_profit[column]) < 0.001, column] = 0

    # 计算账户的累计盈亏
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
    stock_price_df['收盘'] = stock_price_df['收盘'].astype(float)
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


def format_date(x, df_profit):
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
        annotate_profit(event.xdata, event.ydata,
                        f"{df_profit['交收日期'].iloc[index].strftime('%Y/%m/%d')}: {profit:.2f}",
                        ax)
        fig.canvas.draw_idle()


def on_motion(event, fig, vline1, vline2):
    vline1.set_xdata(np.array([event.xdata]))
    vline2.set_xdata(np.array([event.xdata]))
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
    ax1 = sns.lineplot(x=df_total_profit['交收日期'], y=df_total_profit['盈亏'] / 10000, color='r', label='累计盈利',
                       ax=ax1)
    ax1.set_title('累计盈利曲线图', fontsize=16)
    ax1.set_ylabel('盈利(万元)', fontsize=14)
    ax1.tick_params(axis='x', rotation=45, labelsize=12)
    ax1.tick_params(axis='y', labelsize=12)
    ax1.grid(True)
    ax1.legend(fontsize=12)

    # 绘制每日盈利柱状图
    ax2.bar(df_daily_profit['交收日期'], df_daily_profit['盈亏'] / 10000,
            color=df_daily_profit['盈亏'].apply(lambda x: 'g' if x < 0 else 'r'))
    ax2.set_title('每日盈利', loc='center', fontsize=16)
    ax2.set_xlabel('日期', fontsize=14)
    ax2.set_ylabel('盈利(万元)', fontsize=14)
    ax2.tick_params(axis='x', rotation=45, labelsize=12)
    ax2.tick_params(axis='y', labelsize=12)
    ax2.grid(True)

    # 设置 x 轴刻度格式化器
    ax1.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: format_date(x, df_total_profit)))
    ax2.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: format_date(x, df_total_profit)))

    # 添加点击事件,显示具体数值
    fig.canvas.mpl_connect('button_press_event', lambda event: on_click_show_profit(event, df_total_profit, fig, ax1))
    fig.canvas.mpl_connect('button_press_event', lambda event: on_click_show_profit(event, df_daily_profit, fig, ax2))

    # 添加鼠标移动时的垂直参考线
    min_date = df_total_profit['交收日期'].min()
    vline1 = ax1.axvline(x=min_date, color='k', linestyle='-', linewidth=1)
    vline2 = ax2.axvline(x=min_date, color='k', linestyle='-', linewidth=1)
    fig.canvas.mpl_connect('motion_notify_event', lambda event: on_motion(event, fig, vline1, vline2))

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


# import plotly.graph_objects as go
#
# def visualize_profit_plotly(df_total_profit):
#     # 计算每日盈利
#     df_daily_profit = df_total_profit['盈亏'].diff()
#     df_daily_profit = pd.DataFrame({'交收日期': df_total_profit['交收日期'], '盈亏': df_daily_profit})
#
#     # 创建累计盈利曲线图
#     fig = go.Figure()
#     fig.add_trace(go.Scatter(x=df_total_profit['交收日期'], y=df_total_profit['盈亏'] / 10000, mode='lines', name='累计盈利'))
#     fig.update_layout(
#         title='累计盈利曲线图',
#         xaxis_title='日期',
#         yaxis_title='盈利(万元)',
#         xaxis_tickangle=-45,
#         font=dict(size=12)
#     )
#
#     # 创建每日盈利柱状图
#     bar_width = 0.8
#
#     fig.add_trace(go.Bar(x=np.arange(len(df_daily_profit)), y=df_daily_profit['盈亏'] / 10000, width=bar_width,
#                         marker_color=['green' if x < 0 else 'red' for x in df_daily_profit['盈亏']], name='每日盈利'))
#     fig.update_layout(
#         title='每日盈利',
#         xaxis_title='日期',
#         yaxis_title='盈利(万元)',
#         xaxis_tickangle=-45,
#         font=dict(size=12)
#     )
#
#     # 添加点击事件,显示具体数值
#     fig.update_layout(
#         hoverlabel=dict(
#             bgcolor="white",
#             font_size=16,
#             font_family="Rockwell"
#         )
#     )
#
#     fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers', visible=False))
#
#     fig.show()

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
    start_date = pd.to_datetime('20070501', format='%Y%m%d')
    analyze_and_update(start_date)
    draw_profit(start_date)

    # checkpoint_date = pd.to_datetime('20231124', format='%Y%m%d')
    # simulate(checkpoint_date)


if __name__ == "__main__":
    run()
