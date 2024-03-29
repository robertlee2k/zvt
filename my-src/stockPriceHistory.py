import datetime
import os

import akshare as ak
import pandas as pd


class StockPriceHistory:
    stock_price_df = None  # Initialize data attribute at class definition

    def __init__(self):
        pass

    @classmethod
    def initialize_data(cls, auto_fetch_from_ak=False, start_date=None):
        if cls.stock_price_df is None:
            if not os.path.exists('stock/all_stock_hist_df.pkl'):
                if auto_fetch_from_ak:
                    cls.stock_price_df = cls._fetch_and_cache(start_date)
            else:
                cls.stock_price_df = cls.load_from_local('stock/all_stock_hist_df.pkl')
                # 将"日期"列转换为日期类型
                cls.stock_price_df['日期'] = pd.to_datetime(cls.stock_price_df['日期'], format='%Y%m%d')
                if start_date:
                    cls.stock_price_df = cls.stock_price_df[cls.stock_price_df['日期'] >= pd.to_datetime(start_date)]

    @classmethod
    def fetch_stock_close_price(cls, stock_code, trade_date):
        if cls.stock_price_df is None:
            raise ValueError("Data has not been initialized. Call initialize_data first.")
        result = cls.stock_price_df[
            (cls.stock_price_df['证券代码'] == stock_code) & (cls.stock_price_df['日期'] == trade_date)]
        if len(result) == 1:
            return result['收盘'].values[0]
        else:
            return None

    @classmethod
    def _fetch_and_cache(cls, start_date=None):
        if os.path.exists('stock/all_stock_hist_df.pkl'):
            all_stock_hist_df = cls.load_from_local('stock/all_stock_hist_df.pkl')
        else:
            all_stock_hist_df = pd.DataFrame()

        ##TODO
        stock_history_df = pd.read_excel('analyze_summary.xlsx', sheet_name="股票持仓历史", header=0, dtype={'证券代码': str})
        codes = stock_history_df['证券代码'].unique()
        failed_codes = []
        if start_date:
            start_date = pd.to_datetime(start_date).strftime('%Y%m%d')
        else:
            start_date = "20070501"
        # end_date = '20240401' end日期设为今天的后一天
        end_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y%m%d')

        for stock_code in codes:
            market = cls.judge_stock_market(stock_code)
            try:
                if market == 'A股股票':
                    stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date,
                                                       end_date=end_date, adjust="")
                elif market == 'B股股票':
                    stock_hist_df = pd.DataFrame()  # ignore B股 (新浪接口有问题）
                elif market == '港股股票':
                    stock_hist_df = ak.stock_hk_hist(symbol=stock_code, period="daily", start_date=start_date,
                                                     end_date=end_date, adjust="")
                elif market == 'A股新股':
                    stock_hist_df = pd.DataFrame()  # ignore 新股
                else:  # Default to A股股票
                    stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date,
                                                       end_date=end_date, adjust="")
                stock_hist_df['证券代码'] = stock_code
                all_stock_hist_df = pd.concat([all_stock_hist_df, stock_hist_df])
            except Exception as e:
                print(f"Failed to fetch data for stock code: {stock_code}. Error: {e}")
                failed_codes.append(stock_code)

        print(failed_codes)
        # 将"日期"列转换为日期类型
        all_stock_hist_df['日期'] = pd.to_datetime(all_stock_hist_df['日期'], format='%Y%m%d')
        cls.save_to_local(all_stock_hist_df, 'stock/all_stock_hist_df.pkl')
        return all_stock_hist_df

    @classmethod
    def judge_stock_market(cls, code):
        if len(code) == 5:
            return '港股股票'
        elif code.startswith('6') or code.startswith('00') or code.startswith('30'):
            return 'A股股票'
        elif code.startswith('900'):
            return 'B股股票'
        elif code.startswith('5'):
            return 'A股基金'
        elif code.startswith('7'):
            return 'A股新股'
        else:
            return '未知类型'

    @classmethod
    def save_to_local(cls, data_frame, file_name):
        data_frame.to_pickle(file_name)

    @classmethod
    def load_from_local(cls, file_name):
        return pd.read_pickle(file_name)


# Initialize data at the beginning
StockPriceHistory.initialize_data(auto_fetch_from_ak=True)

# Example Usage:
stock_data1 = StockPriceHistory.fetch_stock_close_price('002515', pd.to_datetime('20240320', format='%Y%m%d'))
print(stock_data1)

# In another part of the code or another instance
stock_data2 = StockPriceHistory.fetch_stock_close_price('150172', pd.to_datetime('20240320', format='%Y%m%d'))
print(stock_data2)
