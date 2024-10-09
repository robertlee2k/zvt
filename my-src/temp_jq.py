# from jqdatasdk import *
# auth('13501927447','Password123') #账号是申请时所填写的手机号；密码为聚宽官网登录密码
# #查询账号信息
# infos = get_account_info()
# print(infos)


import akshare as ak
stock_code='sh900932'
start_date='20160301'
end_date='20210305'

# stock_hist_df = ak.stock_zh_b_daily(symbol=stock_code, start_date=start_date,
#                                    end_date=end_date,adjust="")
#
# print(stock_hist_df)

# fund_etf_hist_sina_df = ak.fund_etf_hist_sina(symbol="of150172")
# print(fund_etf_hist_sina_df)

import akshare as ak

fund_graded_fund_info_em_df = ak.fund_graded_fund_info_em(fund="150172")
print(fund_graded_fund_info_em_df)

# import pandas as pd
# new_stock_df=pd.read_pickle('stock/新股数据.pkl')
# print(new_stock_df['发行价格'])




