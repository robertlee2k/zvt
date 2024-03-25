import akshare as ak
import pandas as pd


# 根据股票代码返回市场
def judge_stock_market(code):
    if len(code) == 5:
        return '港股股票'
    elif code.startswith('6') or \
            code.startswith('00') or code.startswith('30'):
        return 'A股股票'
    elif code.startswith('900'):
        return 'B股股票'
    elif code.startswith('5'):
        return 'A股基金'
    elif code.startswith('7'):
        return 'A股新股'
    else:
        return '未知类型'


data = pd.read_excel('analyze_summary.xlsx', sheet_name="股票持仓历史", header=0, dtype={'证券代码': str})
codes = data['证券代码'].unique()
all_stock_hist_df = pd.DataFrame()
failed_codes = []
startdate = "20070501"
enddate = '20240322'

for stock_code in codes:
    market = judge_stock_market(stock_code)
    try:
        if market == 'A股股票':
            stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=startdate,
                                               end_date=enddate, adjust="")

        elif market == 'B股股票':
            stock_hist_df = ak.stock_zh_b_daily(symbol='sh' + stock_code, start_date=startdate,
                                                end_date=enddate, adjust="")
        elif market == '港股股票':
            stock_hist_df = ak.stock_hk_hist(symbol=stock_code, period="daily", start_date=startdate,
                                             end_date=enddate, adjust="")
        elif market == 'A股新股':
            stock_hist_df = pd.DataFrame()  # ignore 新股
        else:  # 缺省值
            stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=startdate,
                                               end_date=enddate, adjust="")
        stock_hist_df['证券代码'] = stock_code
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


