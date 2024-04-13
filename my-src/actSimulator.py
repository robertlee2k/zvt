## 模拟某个checkpoint日的操作结果

import matplotlib.pyplot as plt
import pandas as pd
import datetime
from gxTransData import AccountSummary
from stockPriceHistory import StockPriceHistory


def simulate():
    checkpoint_date = pd.to_datetime('20231124', format='%Y%m%d')
    sim_stock_holding_records, sim_account_balance_records=get_sim_account_history(checkpoint_date)



# 获取从变动仓位日期开始至今天的模拟账户信息
def get_sim_account_history(checkpoint_date):
    filtered_dates = get_trade_dates(checkpoint_date)
    account_summary = AccountSummary()
    today_holdings, today_balance = account_summary.init_start_holdings(checkpoint_date)
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
def get_trade_dates(startDate):
    # 获取当前日期
    today = datetime.date.today()
    # 生成日期序列
    date_range = pd.date_range(start=startDate, end=today, freq='D')
    # 获取所有的交易日日期
    trade_dates = StockPriceHistory.load_trade_dates()
    trade_dates = trade_dates[trade_dates['trade_date'] > startDate]
    # 使用isin()方法过滤日期
    filtered_dates = date_range[date_range.isin(trade_dates['trade_date'])]
    return filtered_dates


simulate()
