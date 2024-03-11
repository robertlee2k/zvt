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

from jqdatasdk import *
auth('13501927447','Password123') #账号是申请时所填写的手机号；密码为聚宽官网登录密码
#查询账号信息
infos = get_account_info()
print(infos)

from zvt.domain import FinanceFactor
# FinanceFactor.help()
FinanceFactor.record_data(provider='eastmoney',code='000338')
df=FinanceFactor.query_data(provider='eastmoney',code='000338',columns=FinanceFactor.important_cols(),index='timestamp')
print(df)



# from zvt.domain import StockInstitutionalInvestorHolder
# entity_ids = ["stock_sz_000338", "stock_sz_000001"]
# StockInstitutionalInvestorHolder.record_data(entity_ids=entity_ids)
# df = StockInstitutionalInvestorHolder.query_data(entity_ids=entity_ids)
# print(df)