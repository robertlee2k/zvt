# from zvt.domain import Stock
# Stock.record_data()
# df = Stock.query_data()
# print(df)

# from zvt.domain import *
# print(Stock1dKdata.get_storages())
# entity_ids = ["stock_sz_000338", "stock_sz_000001"]
# Stock1dKdata.record_data(entity_ids=entity_ids, provider="em")
# df = Stock1dKdata.query_data(entity_ids=entity_ids, provider="em")
# print(df)
#
# from zvt.domain import *
# from zvt.contract import *
# print(zvt_context.tradable_schema_map)
# Index.record_data()
# df= Index.query_data(filters=[Index.exchange=='sh'])
# print(df)

# from jqdatasdk import *
# auth('13501927447','Password123') #账号是申请时所填写的手机号；密码为聚宽官网登录密码
# #查询账号信息
# infos = get_account_info()
# print(infos)
#
# from zvt.domain import FinanceFactor
# # FinanceFactor.help()
# FinanceFactor.record_data(provider='eastmoney',code='000338')
# df=FinanceFactor.query_data(provider='eastmoney',code='000338',columns=FinanceFactor.important_cols(),index='timestamp')
# print(df)




# from zvt.domain import StockInstitutionalInvestorHolder
# entity_ids = ["stock_sz_000338", "stock_sz_000001"]
# StockInstitutionalInvestorHolder.record_data(entity_ids=entity_ids)
# df = StockInstitutionalInvestorHolder.query_data(entity_ids=entity_ids)
# print(df)


# import akshare as ak
# stock_xgsglb_em_df = ak.stock_xgsglb_em(symbol="全部股票")
# print(stock_xgsglb_em_df)
# stock_xgsglb_em_df.to_pickle('新股数据.pkl')

# import akshare as ak
# #df=ak.fund_etf_fund_info_em(fund='510050',start_date='20150301',
# #                                                end_date='20160325')
#
# # 这是etf的所有数据，和股票的结构一致
# df=ak.fund_etf_hist_em(symbol='184691',start_date='20080301',
#                                                 end_date='20080325')
# print(df)
# stock_hist_df = ak.stock_zh_a_hist(symbol='002515', start_date='20200701',
#                                                 end_date='20200901', adjust="")
# print(stock_hist_df.columns)


#print(ak.fund_graded_fund_info_em(fund='159915'))  #这是获取分级基金的所有历史净值

# import akshare as ak
# stock_hist_df = ak.stock_zh_b_daily(symbol='sh900932', start_date='20200701',
#                                                end_date='20200901', adjust="")
# print(stock_hist_df)
# import akshare as ak
# stock_hist_df = ak.stock_zh_a_daily(symbol='of150182', start_date='2015-12-31',
#                                                 end_date='2016-01-05', adjust="")
# print(stock_hist_df)

import pandas as pd
from getStockPriceHistory import StockPriceHistory
from tqdm import tqdm

# Initialize data at the beginning
StockPriceHistory.initialize_data(auto_fetch_from_ak=True)

stock_history_df = pd.read_excel('analyze_summary.xlsx', sheet_name="股票持仓历史", header=0, dtype={'证券代码': str})
stock_history_df['交收日期'] = pd.to_datetime(stock_history_df['交收日期'])
stock_history_df['当日市值']=0.0
# total_rows=stock_history_df.shape[0]
# for index,row in tqdm(stock_history_df.iterrows(), total=total_rows):
#     close_price=StockPriceHistory.fetch_stock_close_price(row['证券代码'],row['交收日期'])
#     if close_price is None:
#         stock_history_df.loc[index,'当日市值']=stock_history_df.loc[index,'持股成本'] #取不到市值时用成本价替代
#     else:
#         stock_history_df.loc[index, '当日市值'] =close_price

# Perform inner join on '证券代码' and '交收日期'
merged_df = pd.merge(stock_history_df, StockPriceHistory.stock_price_df[['证券代码','日期','收盘']], how='left', left_on=['证券代码', '交收日期'], right_on=['证券代码', '日期'])
print(merged_df)

# Update '当日市值' based on fetched close prices
merged_df['当日市值'] = merged_df.apply(lambda row: row['持股成本'] if pd.isnull(row['收盘'])  else row['收盘']*row['持股数量'], axis=1)

# 使用groupby和sum函数按日期分组求和当日市值
df_sum = merged_df.groupby(['交收日期','账户类型'])['当日市值'].sum().reset_index()
# 打印新的DataFrame，包含日期和当日市值的总和
print(df_sum)

df_account = pd.read_excel('analyze_summary.xlsx', sheet_name="账户余额历史", header=0)
df_account_profit=pd.merge(df_account,df_sum,how='left', on=['交收日期','账户类型'])
df_account_profit['当日市值'].fillna(0.0, inplace=True)
df_account_profit['盈亏']=df_account_profit['资金余额']+df_account_profit['当日市值']-df_account_profit['累计净转入资金']
df_account_profit.to_excel("temp_out.xlsx")

df_total_profit=df_account_profit.groupby(['交收日期'])['盈亏'].sum().reset_index()
print(df_total_profit.describe())

import matplotlib.pyplot as plt

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