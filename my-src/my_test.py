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

print(failed_codes)
# 将DataFrame序列化到pickle文件
all_stock_hist_df.to_pickle('all_stock_hist_df.pkl')

# 从pickle文件反序列化加载DataFrame
df_loaded = pd.read_pickle('all_stock_hist_df.pkl')
print(df_loaded)


# Failed to process stock code: 580006. Error: '580006'
# Failed to process stock code: 900947. Error: 'amount'
# Failed to process stock code: 900932. Error: 'amount'
# Failed to process stock code: 031002. Error: '031002'
# Failed to process stock code: 030002. Error: '030002'
# Failed to process stock code: 580989. Error: '580989'
# Failed to process stock code: 580010. Error: '580010'
# Failed to process stock code: 184691. Error: '184691'
# Failed to process stock code: 031003. Error: '031003'
# Failed to process stock code: 580012. Error: '580012'
# Failed to process stock code: 038006. Error: '038006'
# Failed to process stock code: 038004. Error: '038004'
# Failed to process stock code: 580009. Error: '580009'
# Failed to process stock code: 580011. Error: '580011'
# Failed to process stock code: 031004. Error: '031004'
# Failed to process stock code: 580014. Error: '580014'
# Failed to process stock code: 580016. Error: '580016'
# Failed to process stock code: 580019. Error: '580019'
# Failed to process stock code: 580013. Error: '580013'
# Failed to process stock code: 031006. Error: '031006'
# Failed to process stock code: 580026. Error: '580026'
# Failed to process stock code: 150019. Error: '150019'
# Failed to process stock code: 205001. Error: '205001'
# Failed to process stock code: 204001. Error: '204001'
# Failed to process stock code: 150172. Error: '150172'
# Failed to process stock code: 150182. Error: '150182'
# Failed to process stock code: 161024. Error: '161024'
# Failed to process stock code: 150181. Error: '150181'
# Failed to process stock code: 150222. Error: '150222'
# Failed to process stock code: 510050. Error: '510050'
# Failed to process stock code: 159919. Error: '159919'
# Failed to process stock code: 150231. Error: '150231'
# Failed to process stock code: 150235. Error: '150235'
# Failed to process stock code: 150194. Error: '150194'
# Failed to process stock code: 150152. Error: '150152'
# Failed to process stock code: 150153. Error: '150153'
# Failed to process stock code: 502008. Error: '502008'
# Failed to process stock code: 150210. Error: '150210'
# Failed to process stock code: 150204. Error: '150204'
# Failed to process stock code: 150218. Error: '150218'
# Failed to process stock code: 150206. Error: '150206'
# Failed to process stock code: 150187. Error: '150187'
# Failed to process stock code: 159915. Error: '159915'
# Failed to process stock code: 519888. Error: '519888'
# Failed to process stock code: 204007. Error: '204007'
# Failed to process stock code: 204003. Error: '204003'
# Failed to process stock code: 204004. Error: '204004'
# Failed to process stock code: 072142. Error: '072142'
# Failed to process stock code: 370433. Error: '370433'
# Failed to process stock code: 123003. Error: '123003'
# Failed to process stock code: 128024. Error: '128024'
# Failed to process stock code: 510500. Error: '510500'
# Failed to process stock code: 510300. Error: '510300'


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