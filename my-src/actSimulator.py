## 模拟某个checkpoint日的操作结果

import matplotlib.pyplot as plt
import pandas as pd
import datetime
from gxTransData import AccountSummary
from stockPriceHistory import StockPriceHistory


checkpoint_date = pd.to_datetime('20231124', format='%Y%m%d')
account_summary = AccountSummary()
# checkpoint后一日:
startDate = checkpoint_date + datetime.timedelta(days=1)
# 获取当前日期
today = datetime.date.today()
# 生成日期序列
date_range = pd.date_range(start=startDate, end=today, freq='D')
print(date_range)
trade_dates=StockPriceHistory.load_trade_dates()
print((trade_dates))
# 使用isin()方法过滤日期
filtered_dates = date_range[date_range['date'].isin(trade_dates['trade_date'])]
print(filtered_dates)

today_holdings, today_balance = account_summary.init_start_holdings(startDate)
# 打印过滤后的日期
for date in filtered_dates['date']:
    print(date)

    # # 新的一天，将之前一天的记录更新追加到history里，并初始化新的日期
    # # 将上一交易日的记录加入历史记录df中
    # account_summary.add_to_history(today_balance, today_holdings)
    # # copy一份作为新的交易日的空白记录
    # today_holdings = today_holdings.copy()
    # today_balance = today_balance.copy()
    # today_holdings['交收日期'] = current_date
    # today_balance['交收日期'] = current_date
    # current_date += datetime.timedelta(days=1)
