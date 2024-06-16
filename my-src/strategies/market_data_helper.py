import akshare as ak
import pandas as pd

AK_ADJUST_HFQ = "hfq-factor"  # 后复权模式
AK_ADJUST_NONE = ""  # 不复权


class MarketDataHelper:

    @staticmethod
    def get_trade_dates():
        return pd.read_pickle('../stock/trade_dates.pkl')

    @staticmethod
    def judge_stock_market(code):
        if len(code) == 5:
            return '港股股票'
        elif code.startswith('6'):
            return '上海A股'
        elif code.startswith('00') or code.startswith('30'):
            return '深圳A股'
        elif code.startswith('900'):
            return 'B股股票'
        elif code.startswith('5'):
            return 'A股基金'
        elif code.startswith('7'):
            return 'A股新股'
        else:
            return '未知类型'


    @staticmethod
    def query_index_data(index_code, start_date, end_date):
        price_df = ak.stock_zh_index_daily(symbol=index_code)
        price_df['date'] = pd.to_datetime(price_df['date'])
        price_df = price_df[(price_df['date'] >= start_date) & (price_df['date'] <= end_date)]
        price_df = price_df.sort_values('date').set_index('date')
        price_df = price_df.dropna(subset=['high', 'low', 'close'])  # 删除缺失值
        return price_df

    # 调用akshare接口（东财接口）, exchange_rate_df
    @staticmethod
    def query_akshare(symbol, period, start_date, end_date, adjust=AK_ADJUST_NONE):
        stock_hist_df = None
        market = MarketDataHelper.judge_stock_market(symbol)

        try:
            if market == '上海A股' or market == '深圳A股':
                stock_hist_df = ak.stock_zh_a_hist(symbol=symbol, period=period, start_date=start_date,
                                                   end_date=end_date, adjust=adjust)
            elif market == 'B股股票':
                stock_hist_df = pd.DataFrame()  # ignore B股 (新浪接口有问题）
            elif market == '港股股票':
                stock_hist_df = ak.stock_hk_hist(symbol=symbol, period=period, start_date=start_date,
                                                 end_date=end_date, adjust=adjust)
                # stock_hist_df['日期'] = pd.to_datetime(stock_hist_df['日期'])
                # stock_hist_df = pd.merge(stock_hist_df, exchange_rate_df, how='left', on=['日期'])
                # stock_hist_df['收盘'] = stock_hist_df['收盘'] * stock_hist_df['卖出结算汇兑比率']
                # stock_hist_df = stock_hist_df[
                #     ['日期', '收盘']]  # .drop(['买入结算汇兑比率','卖出结算汇兑比率','货币种类'], axis=1, inplace=True)
                #
            elif market == 'A股新股':
                stock_hist_df = pd.DataFrame()  # ignore 新股
            else:  # Default to A股股票
                stock_hist_df = pd.DataFrame()  # ignore
        except Exception as e:
            print(f"Failed to fetch data for stock code: {symbol}. Error: {e}")
        return stock_hist_df
