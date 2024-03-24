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

import akshare as ak

# 根据股票代码返回市场
def judge_stock_market(stock_code):
    if len(stock_code) == 5:
        return '港股股票'
    elif stock_code.startswith('6') or\
            stock_code.startswith('00') or stock_code.startswith('30'):
        return 'A股股票'
    elif stock_code.startswith('900'):
        return 'B股股票'
    elif stock_code.startswith('5') :
        return 'A股基金'
    elif stock_code.startswith('7') :
        return 'A股新股'
    else:
        return '未知类型'


import pandas as pd
data=pd.read_excel('analyze_summary.xlsx', sheet_name="股票持仓历史",header=0,dtype={'证券代码': str})
codes=data['证券代码'].unique()
all_stock_hist_df=pd.DataFrame()
failed_codes = []
startdate="20070501"
enddate='20240322'

for stock_code in codes:
    market=judge_stock_market(stock_code)
    try:
        if market=='A股股票':
            stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=startdate,
                                               end_date=enddate, adjust="")

        elif market=='B股股票':
            stock_hist_df = ak.stock_zh_b_daily(symbol='sh'+stock_code, start_date=startdate,
                                               end_date=enddate, adjust="")
        elif market=='港股股票':
            stock_hist_df = ak.stock_hk_hist(symbol=stock_code, period="daily", start_date=startdate,
                                                end_date=enddate, adjust="")
        elif market== 'A股新股':
            stock_hist_df=pd.DataFrame() #ignore 新股
        else: #缺省值
            stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=startdate,
                                               end_date=enddate, adjust="")
        stock_hist_df['证券代码']=stock_code
        all_stock_hist_df = pd.concat([all_stock_hist_df, stock_hist_df])
    except Exception as e:
        print(f"Failed to process stock code: {stock_code}. Error: {e}")
        failed_codes.append(stock_code)

# 将DataFrame序列化到pickle文件
all_stock_hist_df.to_pickle('all_stock_hist_df.pkl')

# 从pickle文件反序列化加载DataFrame
df_loaded = pd.read_pickle('all_stock_hist_df.pkl')
print(df_loaded)


# import akshare as ak
# stock_xgsglb_em_df = ak.stock_xgsglb_em(symbol="全部股票")
# print(stock_xgsglb_em_df)
# stock_xgsglb_em_df.to_pickle('新股数据.pkl')

# import akshare as ak
# df=ak.fund_etf_fund_info_em(fund='510050',start_date='20050701',
#                                                 end_date='20050701')
# print(df)

# import akshare as ak
# stock_hist_df = ak.stock_zh_b_daily(symbol='sh900932', start_date='20200701',
#                                                end_date='20200901', adjust="")
# print(stock_hist_df)