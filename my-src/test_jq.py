# from jqdatasdk import *
# auth('13501927447','Password123') #账号是申请时所填写的手机号；密码为聚宽官网登录密码
# #查询账号信息
# infos = get_account_info()
# print(infos)


import akshare as ak
stock_code='sh900932'
start_date='20160301'
end_date='20190305'

stock_hist_df = ak.stock_zh_b_daily(symbol=stock_code, start_date=start_date,
                                   end_date=end_date)

print(stock_hist_df)


