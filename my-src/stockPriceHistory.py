import datetime
import os
import akshare as ak
import pandas as pd
from datetime import timedelta
from gxTransData import AccountSummary

ALL_STOCK_HIST_DF_PKL = 'stock/all_stock_hist_df.pkl'  # 所有股票价格
HGT_EXCHANGE_RATE_FILE = 'stock/hgt_exchange_rate.pkl'  # 沪港通结算汇率


class StockPriceHistory:

    def __init__(self):
        self.stock_price_df = None  # Initialize data attribute

    # 从本地存储中，获取股票价格的dataframe
    def get_stock_price_df(self, start_date=None):
        if self.stock_price_df is None:  # 如果数据为空，则从文件中加载
            if os.path.exists(ALL_STOCK_HIST_DF_PKL):  # 如果有历史文件，从历史文件里加载
                self.stock_price_df = self.load_from_local(ALL_STOCK_HIST_DF_PKL)
                if start_date:  # 获取start_date之后的数据
                    self.stock_price_df = self.stock_price_df[self.stock_price_df['日期'] >= start_date]
        return self.stock_price_df

    # 获取某个股票某日的收盘价，一般直接做inner join，而不是用这个函数
    def get_close_price(self, stock_code, trade_date):
        if self.stock_price_df is None:
            raise ValueError("Data has not been initialized. Call get_stock_price_df first.")
        result = self.stock_price_df[
            (self.stock_price_df['证券代码'] == stock_code) & (self.stock_price_df['日期'] == trade_date)]
        if len(result) == 1:
            return result['收盘'].values[0]
        else:
            return None

    # 从akshare获取收盘价
    def fetch_close_price_from_ak(self, start_date=None):
        if os.path.exists(ALL_STOCK_HIST_DF_PKL):
            all_stock_hist_df = self.load_from_local(ALL_STOCK_HIST_DF_PKL)
        else:
            all_stock_hist_df = pd.DataFrame()

        # 再保存港股通结算汇率
        exchange_rate_df = self.cache_exchange_rate_from_ak()

        # 获取持仓股票的收盘价
        # 获取每日持股数据
        stock_trans_df = AccountSummary.load_stockhold_from_file()

        if start_date is None:  # 开始日期为空，则从20070501开始
            start_date = pd.to_datetime("20070501")
        else:
            stock_trans_df = stock_trans_df[stock_trans_df['交收日期'] >= start_date]

        # 结束日期设为今天之后一天
        end_date = (datetime.datetime.now() + datetime.timedelta(days=1))

        # 切分为200日一份，以免冗余数据过多
        date_ranges = self.split_date_ranges(start_date, end_date)
        # 开始循环
        failed_codes = []
        for range_start, range_end in date_ranges:
            stock_df_range = stock_trans_df[
                (stock_trans_df['交收日期'] >= range_start) & (stock_trans_df['交收日期'] <= range_end)]
            codes = stock_df_range['证券代码'].unique()
            print(f"{range_start.strftime('%Y%m%d')}, {range_end.strftime('%Y%m%d'):}")
            print(codes)
            for stock_code in codes:
                stock_hist_df = self.query_akshare(stock_code, range_start, range_end, exchange_rate_df)
                if stock_hist_df is None:
                    failed_codes.append(stock_code)
                else:  # 将查询数据拼接
                    all_stock_hist_df = pd.concat([all_stock_hist_df, stock_hist_df])

        # 只保留需要的三列
        all_stock_hist_df = all_stock_hist_df[['日期', '收盘', '证券代码']]

        # 将"日期"列转换为日期类型
        all_stock_hist_df['日期'] = pd.to_datetime(all_stock_hist_df['日期'])

        # 重新设置index
        all_stock_hist_df.reset_index(drop=True,inplace=True)
        self.save_to_local(all_stock_hist_df, ALL_STOCK_HIST_DF_PKL)

        return all_stock_hist_df, failed_codes

    # 调用akshare接口
    def query_akshare(self, stock_code, from_date, to_date, exchange_rate_df):
        stock_hist_df = None
        market = self.judge_stock_market(stock_code)
        # 转换为akshare所需的字符串形式
        start_date = from_date.strftime('%Y%m%d')
        end_date = to_date.strftime('%Y%m%d')
        try:
            if market == 'A股股票':
                stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date,
                                                   end_date=end_date, adjust="")
            elif market == 'B股股票':
                stock_hist_df = pd.DataFrame()  # ignore B股 (新浪接口有问题）
            elif market == '港股股票':
                stock_hist_df = ak.stock_hk_hist(symbol=stock_code, period="daily", start_date=start_date,
                                                 end_date=end_date, adjust="")
                stock_hist_df['日期'] = pd.to_datetime(stock_hist_df['日期'])
                stock_hist_df = pd.merge(stock_hist_df, exchange_rate_df, how='left', on=['日期'])
                stock_hist_df['收盘'] = stock_hist_df['收盘'] * stock_hist_df['卖出结算汇兑比率']
                stock_hist_df = stock_hist_df[
                    ['日期', '收盘']]  # .drop(['买入结算汇兑比率','卖出结算汇兑比率','货币种类'], axis=1, inplace=True)

            elif market == 'A股新股':
                stock_hist_df = pd.DataFrame()  # ignore 新股
            else:  # Default to A股股票
                stock_hist_df = pd.DataFrame()  # ignore
            stock_hist_df['证券代码'] = stock_code
        except Exception as e:
            print(f"Failed to fetch data for stock code: {stock_code}. Error: {e}")

        return stock_hist_df

    # 将日期区间按照100天间隔切分为左闭右闭的子区间，这样每次批量获取的收盘价数据不至于冗余太多
    @staticmethod
    def split_date_ranges(start_date, end_date):
        date_ranges = []
        current_date = pd.to_datetime(start_date)
        while current_date < pd.to_datetime(end_date):
            next_date = current_date + timedelta(days=100)
            if next_date > pd.to_datetime(end_date):
                next_date = pd.to_datetime(end_date)
            date_ranges.append((current_date, next_date))
            current_date = next_date + timedelta(days=1)  # 调整为左闭右闭区间
        return date_ranges

    @staticmethod
    def judge_stock_market(code):
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

    @staticmethod
    def save_to_local(data_frame, file_name):
        # 检查stock_price_df中的重复数据，并删除
        duplicate_rows = data_frame[data_frame.duplicated()]
        print("删除以下重复数据行:")
        print(duplicate_rows)
        data_frame = data_frame.drop_duplicates()
        data_frame.to_pickle(file_name)

    @staticmethod
    def load_from_local(file_name):
        return pd.read_pickle(file_name)

    @staticmethod
    def cache_exchange_rate_from_ak():
        # 获取所有沪港通结算汇率数据并保存到文件里
        stock_sgt_settlement_exchange_rate_sse_df = ak.stock_sgt_settlement_exchange_rate_sse()
        stock_sgt_settlement_exchange_rate_sse_df.rename(columns={'适用日期': '日期'}, inplace=True)
        stock_sgt_settlement_exchange_rate_sse_df['日期'] = pd.to_datetime(
            stock_sgt_settlement_exchange_rate_sse_df['日期'])
        print(stock_sgt_settlement_exchange_rate_sse_df)
        stock_sgt_settlement_exchange_rate_sse_df.to_pickle(HGT_EXCHANGE_RATE_FILE)
        return stock_sgt_settlement_exchange_rate_sse_df

    @staticmethod
    def load_exchange_rate_df():
        return pd.read_pickle(HGT_EXCHANGE_RATE_FILE)


def run_update_ak():
    start_date = None #pd.to_datetime('20240321', format='%Y%m%d')
    stock_price = StockPriceHistory()
    df, failed = stock_price.fetch_close_price_from_ak(start_date)
    print(df)
    print(f"failed codes: {failed}")


# Example usage
if __name__ == "__main__":
    # 使用示例
    run_update_ak()
