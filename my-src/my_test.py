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

# import akshare as ak
#
# qfq_factor_df = ak.stock_zh_a_daily(symbol="sz002515", adjust="hfq-factor")
# print(qfq_factor_df)

import pandas as pd
import plotly.graph_objects as go
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import numpy as np
import datetime

# 生成随机的股票数据
tickers = ['AAPL', 'MSFT', 'AMZN']
start_date = datetime.datetime(2022, 1, 1)
end_date = datetime.datetime(2023, 4, 30)
dates = pd.date_range(start_date, end_date)

data = {}
for ticker in tickers:
    open_prices = np.random.uniform(100, 200, len(dates))
    high_prices = open_prices + np.random.uniform(0, 20, len(dates))
    low_prices = open_prices - np.random.uniform(0, 20, len(dates))
    close_prices = open_prices + np.random.uniform(-10, 10, len(dates))
    df = pd.DataFrame({
        'Date': dates,
        'Open': open_prices,
        'High': high_prices,
        'Low': low_prices,
        'Close': close_prices
    })
    data[ticker] = df

# 使用生成的数据绘制 K 线图
# 您可以在这里继续完成您的 Dash 应用程序

# 创建 Dash 应用程序
app = dash.Dash(__name__)

# 添加下拉菜单供用户选择股票代码
app.layout = html.Div([
    html.H1('股票 K 线图'),
    dcc.Dropdown(
        id='stock-dropdown',
        options=[{'label': i, 'value': i} for i in tickers],
        value='AAPL'
    ),
    dcc.Graph(id='stock-graph')
])

# 更新图表
@app.callback(
    dash.dependencies.Output('stock-graph', 'figure'),
    [dash.dependencies.Input('stock-dropdown', 'value')])
def update_graph(selected_ticker):
    df = data[selected_ticker]
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    )])
    fig.update_layout(title=f"{selected_ticker} 股价走势")
    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
