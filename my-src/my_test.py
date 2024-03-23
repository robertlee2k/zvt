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
import pandas as pd

# 创建示例数据
data = {'交易字段': ["-600060", "-  -", "海信电器 600060", "GC001 204001"]}
df = pd.DataFrame(data)

# 拆分逻辑：根据空格分隔拆分证券名称和证券代码
def split_security(row):
    parts = row['交易字段'].split()
    if len(parts) == 2:
        return parts[0], parts[1]
    elif len(parts) == 1 and parts[0].isdigit() and len(parts[0]) == 6:
        return parts[0], '-'
    else:
        return '-'.join(parts[:-1]), parts[-1]

# 应用拆分逻辑
df[['证券名称', '证券代码']] = df.apply(split_security, axis=1, result_type='expand')

# 输出结果
print(df[['交易字段', '证券代码', '证券名称']])

# from zvt.domain import StockInstitutionalInvestorHolder
# entity_ids = ["stock_sz_000338", "stock_sz_000001"]
# StockInstitutionalInvestorHolder.record_data(entity_ids=entity_ids)
# df = StockInstitutionalInvestorHolder.query_data(entity_ids=entity_ids)
# print(df)