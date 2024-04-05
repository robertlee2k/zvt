## 模拟某个checkpoint日的操作结果

import matplotlib.pyplot as plt
import pandas as pd
from datetime import timedelta
from gxTransData import AccountSummary
from stockPriceHistory import StockPriceHistory


checkpoint_date = pd.to_datetime('20231124', format='%Y%m%d')
account_summary = AccountSummary()
# 初始化当日持股数据及资金余额数据:
startDate = checkpoint_date + timedelta(days=1)
init_stockhold, init_balance = account_summary.init_start_holdings(startDate)
