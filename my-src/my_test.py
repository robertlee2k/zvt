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

