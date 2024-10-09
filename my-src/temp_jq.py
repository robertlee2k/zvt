# from jqdatasdk import *
# auth('13501927447','Password123') #账号是申请时所填写的手机号；密码为聚宽官网登录密码
# #查询账号信息
# infos = get_account_info()
# print(infos)


import akshare as ak
stock_code='sh900947'
start_date='20060301'
end_date='20070305'
stock_hist_df = ak.stock_zh_b_daily(symbol=stock_code, start_date=start_date,
                                   end_date=end_date,adjust="")

print(stock_hist_df)

# fund_etf_hist_sina_df = ak.fund_etf_hist_sina(symbol="of150172")
# print(fund_etf_hist_sina_df)




# stock_hist_df = ak.fund_etf_fund_info_em(fund=stock_code, start_date=start_date, end_date=end_date)
# stock_hist_df.rename(columns={'净值日期': '日期', '单位净值': '收盘'}, inplace=True)
# stock_hist_df = stock_hist_df[['日期', '收盘']]
# stock_hist_df['证券代码']=stock_code
# print(stock_hist_df)






