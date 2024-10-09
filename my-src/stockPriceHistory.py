import datetime
import os
import akshare as ak
import pandas as pd
from datetime import timedelta
from gxTransData import AccountSummary
import gxTransParser
from fund_data_handler import FundDataHandler

ALL_STOCK_HIST_DF_PKL = 'stock/all_stock_hist_df.pkl'  # 所有股票价格
HGT_EXCHANGE_RATE_FILE = 'stock/hgt_exchange_rate.pkl'  # 沪港通结算汇率
TRADE_DATES = 'stock/trade_dates.pkl'  # 交易日
ALL_HFQ_FACTORS_PKL = 'stock/all_hfq_factors.pkl'

AK_ADJUST_HFQ = "hfq-factor"  # 后复权模式
AK_ADJUST_NONE = ""  # 不复权


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

    # 从akshare获取收盘价，增量更新模式，在原有数据文件基础上继续加载数据（最后会去重）
    # 这里需要两类数据： 1. 获取持仓股票的收盘价。 2. 获取爬取交易流水数据的收盘价
    def fetch_close_price_from_ak(self, start_date=None):
        # 1. 获取持仓股票的收盘价
        stock_hold_df = AccountSummary.load_stockhold_from_file()

        if start_date is None:  # 开始日期为空，则从20070501开始
            start_date = pd.to_datetime("20070501")
        else:
            # 找到离 start_date 最近的交收日期对应的行索引
            prev_date_idx = stock_hold_df['交收日期'].sub(start_date).abs().idxmin()
            # 找到离 start_date 最近的交收日期(可以是当天）
            prev_date = stock_hold_df.loc[prev_date_idx]['交收日期']
            print(f'最近持仓日期{prev_date}')
            stock_hold_df = stock_hold_df[stock_hold_df['交收日期'] >= prev_date]
            # 根据最接近的持仓股票的交收日期修改start_date（因为在下面的代码里这个日期如果小于start_date会被过滤掉）
            if prev_date < start_date:
                start_date = prev_date

        stock_hold_df = stock_hold_df[["交收日期", "证券代码"]]

        # 2. 获取爬取交易流水数据的收盘价
        stock_trans_df = gxTransParser.get_transactions(start_date=start_date)
        stock_trans_df = stock_trans_df[["交收日期", "证券代码"]]

        stock_df = pd.concat([stock_hold_df, stock_trans_df], ignore_index=True)

        # 结束日期设为今天之后一天
        end_date = (datetime.datetime.now() + datetime.timedelta(days=1))

        all_stock_hist_df, failed_codes = self.query_ak_for_stocks(stock_df, start_date,
                                                                   end_date)

        return all_stock_hist_df, failed_codes

    @staticmethod
    # 将一段时间的不复权价格转换为以特定日期为基准的后复权价格
    # 为了模拟评估模式：从akshare为持仓数据获取从某日开始后复权的收盘价，不保存本地
    def cal_hfq_price(stock_price_df, hfq_data, base_date=None):
        # 这段代码的主要步骤如下:
        # 不复权价格: stock_price_df
        # 后复权因子数据: hfq_data。
        # 设置后复权基准日期为base_date。
        # 创建一个新的列hfq_factor来存储每个交易日的后复权因子。初始值为1.0
        # 遍历hfq_data中的每个后复权因子, 并根据对应的时间范围, 将stock_data中的hfq_factor列更新为该因子除以基准日期的因子。这样可以确保后复权价格是以基准日期为基准的。
        # 最后, 我们计算adj_close列, 即后复权价格, 方法是将close列乘以hfq_factor列。

        # 对hfq_data按日期排序
        hfq_data = hfq_data.sort_values('日期')

        # 设置基准日期base_date
        if base_date is None:
            base_date = stock_price_df['日期'].min()
        base_date = pd.to_datetime(base_date)

        # 找到base_date在hfq_data中最近的日期
        base_date_idx = hfq_data['日期'].searchsorted(base_date, side='right')
        if base_date_idx > 0:
            base_date = hfq_data['日期'].iloc[base_date_idx - 1]

        # 过滤掉hfq_data中小于base_date的数据
        hfq_data = hfq_data.loc[hfq_data['日期'] >= base_date]

        # 将hfq_data['hfq_factor']转换为数值类型
        hfq_data['hfq_factor'] = hfq_data['hfq_factor'].astype(float)

        # 在原始DataFrame中插入'后复权因子'和'后复权收盘'两列
        stock_price_df.insert(len(stock_price_df.columns), '后复权因子', 1.0)
        stock_price_df.insert(len(stock_price_df.columns), '后复权收盘', stock_price_df['收盘'])

        # 计算每个交易日的后复权因子
        for i in range(len(hfq_data)):
            start_date = hfq_data['日期'].iloc[i]
            if i == len(hfq_data) - 1:
                # 对于最后一次除权数据之后的日期，不设end_date的限制
                stock_price_df.loc[stock_price_df['日期'] >= start_date, '后复权因子'] = \
                    hfq_data['hfq_factor'].iloc[i] / hfq_data['hfq_factor'].loc[hfq_data['日期'] == base_date].values[
                        0]
            else:
                end_date = hfq_data['日期'].iloc[i + 1]
                stock_price_df.loc[
                    (stock_price_df['日期'] >= start_date) & (stock_price_df['日期'] < end_date), '后复权因子'] = \
                    hfq_data['hfq_factor'].iloc[i] / hfq_data['hfq_factor'].loc[hfq_data['日期'] == base_date].values[
                        0]

        # 计算后复权价格
        stock_price_df.loc[:, '后复权收盘'] = stock_price_df['收盘'] * stock_price_df['后复权因子']

        # 以后复权方式获取价格
        stock_price_df = StockPriceHistory.remove_duplicates(stock_price_df)

        return stock_price_df

    # 从akshare查询持仓列表的股价（对于入参stock_trans其实没有特别要求，只需要有["交收日期","证券代码"]即可）
    def query_ak_for_stocks(self, stock_trans_df, start_date, end_date, adjust_type=AK_ADJUST_NONE):
        stock_price_df = pd.DataFrame()
        # 保存港股通结算汇率
        exchange_rate_df = self.cache_exchange_rate_from_ak()
        # 切分为100日一份，以免冗余数据过多
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
                stock_hist_df = self.query_akshare(stock_code, range_start, range_end, exchange_rate_df, adjust_type)
                if stock_hist_df is None:
                    failed_codes.append(stock_code)
                else:  # 将查询数据拼接
                    stock_price_df = pd.concat([stock_price_df, stock_hist_df])
        # 只保留需要的三列
        stock_price_df = stock_price_df[['日期', '收盘', '证券代码']]
        # 将"日期"列转换为日期类型
        stock_price_df['日期'] = pd.to_datetime(stock_price_df['日期'])

        # 如果磁盘上有缓存文件，先把缓存加载（最后会删除去重）
        if os.path.exists(ALL_STOCK_HIST_DF_PKL):
            all_stock_hist_df = self.load_from_local(ALL_STOCK_HIST_DF_PKL)
            all_stock_hist_df = pd.concat([all_stock_hist_df, stock_price_df])
        else:
            all_stock_hist_df = stock_price_df

        all_stock_hist_df = self.remove_duplicates(all_stock_hist_df)
        # 保存到本地
        self.save_to_local(all_stock_hist_df, ALL_STOCK_HIST_DF_PKL)

        return all_stock_hist_df, failed_codes

    @staticmethod
    # 检查stock_price_df中的重复数据，和收盘价格为NA的数据，并删除
    def remove_duplicates(stock_price_df):
        print("删除以下收盘价格为NA的记录行：")
        # 打印出 '收盘' 字段为 NA 的记录
        na_records = stock_price_df[stock_price_df['收盘'].isna()]
        print(na_records)
        # 删除 '收盘' 字段为 NA 的记录
        stock_price_df = stock_price_df[~stock_price_df['收盘'].isna()]

        # 删除重复行
        duplicate_rows = stock_price_df[stock_price_df.duplicated()]
        print("删除以下重复数据行:")
        print(duplicate_rows)
        stock_price_df = stock_price_df.drop_duplicates()

        # 重新设置index
        stock_price_df.reset_index(drop=True, inplace=True)
        return stock_price_df

    # 调用akshare接口（东财接口）
    def query_akshare(self, stock_code, from_date, to_date, exchange_rate_df, adjust_type=AK_ADJUST_NONE):
        stock_hist_df = None
        market = self.judge_stock_market(stock_code)
        # 转换为akshare所需的字符串形式
        start_date = from_date.strftime('%Y%m%d')
        end_date = to_date.strftime('%Y%m%d')
        try:
            if market == '上海A股' or market == '深圳A股':
                stock_hist_df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", start_date=start_date,
                                                   end_date=end_date, adjust=adjust_type)
            elif market == '分级基金':
                stock_hist_df = FundDataHandler.grade_fund_hist(stock_code=stock_code, start_date=start_date,end_date=end_date)
            elif market == 'ETF基金':
                stock_hist_df = FundDataHandler.etf_fund_hist(stock_code=stock_code, start_date=start_date,end_date=end_date)
            elif market == 'B股股票':
                stock_hist_df = ak.stock_zh_b_daily(symbol='sh' + stock_code, start_date=start_date,
                                                    end_date=end_date, adjust=adjust_type)
                stock_hist_df.rename(columns={'date': '日期', 'close': '收盘'}, inplace=True)
                stock_hist_df = stock_hist_df[['日期', '收盘']]
            elif market == '港股股票':
                stock_hist_df = ak.stock_hk_hist(symbol=stock_code, period="daily", start_date=start_date,
                                                 end_date=end_date, adjust=adjust_type)
                stock_hist_df['日期'] = pd.to_datetime(stock_hist_df['日期'])
                stock_hist_df = pd.merge(stock_hist_df, exchange_rate_df, how='left', on=['日期'])
                stock_hist_df['收盘'] = stock_hist_df['收盘'] * stock_hist_df['卖出结算汇兑比率']
                stock_hist_df = stock_hist_df[['日期', '收盘']]
                # .drop(['买入结算汇兑比率','卖出结算汇兑比率','货币种类'], axis=1, inplace=True)
            elif market == 'A股新股':
                stock_hist_df = pd.DataFrame()  # ignore 新股
            else:  # Default to A股股票
                stock_hist_df = pd.DataFrame()  # ignore
        except Exception as e:
            print(f"Failed to fetch data for stock code: {stock_code}. Error: {e}")
        stock_hist_df['证券代码'] = stock_code
        return stock_hist_df

    # 将日期区间按照bin_size(缺省100天)间隔切分为左闭右闭的子区间，这样每次批量获取的收盘价数据不至于冗余太多
    @staticmethod
    def split_date_ranges(start_date, end_date, bin_size=100):
        date_ranges = []
        current_date = pd.to_datetime(start_date)
        while current_date < pd.to_datetime(end_date):
            next_date = current_date + timedelta(days=bin_size)
            if next_date > pd.to_datetime(end_date):
                next_date = pd.to_datetime(end_date)
            date_ranges.append((current_date, next_date))
            current_date = next_date + timedelta(days=1)  # 调整为左闭右闭区间
        return date_ranges

    @staticmethod
    def judge_stock_market(code):
        if not isinstance(code, str) or len(code) < 1:
            raise ValueError("Invalid input: code must be a non-empty string")

        if FundDataHandler.is_etf_fund(code):
            return 'ETF基金'
        if FundDataHandler.is_grade_fund(code):
            return '分级基金'

        if len(code) < 5:
            return '未知类型'

        if len(code) == 5:
            return '港股股票'
        elif code.startswith('6'):
            return '上海A股'
        elif code.startswith('00') or code.startswith('30'):
            return '深圳A股'
        elif code.startswith('900'):
            return 'B股股票'
        elif code.startswith('7'):
            return 'A股新股'
        else:
            return '未知类型'


    # 调用akshare接口（新浪接口）获取目标股票的后复权因子
    @staticmethod
    def cache_hfq_factors(stockcodes):
        all_hfq_factors = pd.DataFrame()
        df_hfq_factors = None
        for stock_code in stockcodes:
            market = StockPriceHistory.judge_stock_market(stock_code)
            try:
                if market == '上海A股':
                    df_hfq_factors = ak.stock_zh_a_daily(symbol='sh' + stock_code, adjust=AK_ADJUST_HFQ)
                if market == '深圳A股':
                    df_hfq_factors = ak.stock_zh_a_daily(symbol='sz' + stock_code, adjust=AK_ADJUST_HFQ)
                elif market == 'B股股票':
                    df_hfq_factors = ak.stock_zh_b_daily(symbol='sh' + stock_code, adjust=AK_ADJUST_HFQ)
                elif market == '港股股票':
                    df_hfq_factors = ak.stock_hk_daily(symbol=stock_code, adjust=AK_ADJUST_HFQ)
                elif market == 'A股新股':
                    df_hfq_factors = pd.DataFrame()  # ignore 新股
                else:  # Default to A股股票
                    df_hfq_factors = pd.DataFrame()  # ignore
            except Exception as e:
                print(f"Failed to fetch data for stock code: {stock_code}. Error: {e}")
            df_hfq_factors['证券代码'] = stock_code
            all_hfq_factors = pd.concat([all_hfq_factors, df_hfq_factors])
        # 数据格式为： date hfq_factor   cash  ，先改名
        all_hfq_factors.rename(columns={'date': '日期'}, inplace=True)
        # 将日期格式更新
        all_hfq_factors['日期'] = pd.to_datetime(all_hfq_factors['日期'])

        # 如果磁盘上有缓存文件，先把缓存加载（最后会删除去重）
        if os.path.exists(ALL_HFQ_FACTORS_PKL):
            history_df = pd.read_pickle(ALL_HFQ_FACTORS_PKL)
            all_hfq_factors = pd.concat([all_hfq_factors, history_df])

        all_hfq_factors = StockPriceHistory.remove_duplicates(all_hfq_factors)

        # 保存到本地
        all_hfq_factors.to_pickle(ALL_HFQ_FACTORS_PKL)
        return all_hfq_factors

    @staticmethod
    def save_to_local(data_frame, file_name):
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

    @staticmethod
    def cache_trade_dates():
        tool_trade_date_hist_sina_df = ak.tool_trade_date_hist_sina()
        tool_trade_date_hist_sina_df['trade_date'] = pd.to_datetime(tool_trade_date_hist_sina_df['trade_date'])
        print(tool_trade_date_hist_sina_df)
        tool_trade_date_hist_sina_df.to_pickle(TRADE_DATES)

    @staticmethod
    def load_trade_dates():
        return pd.read_pickle(TRADE_DATES)


def run_update_ak():
    stock_price = StockPriceHistory()

    start_date = pd.to_datetime('20070501', format='%Y%m%d')
    # 如果磁盘上有缓存文件，先把缓存加载，用于确定继续的start_date
    if os.path.exists(ALL_STOCK_HIST_DF_PKL):
        all_stock_hist_df = stock_price.load_from_local(ALL_STOCK_HIST_DF_PKL)
        start_date = all_stock_hist_df['日期'].max()

    df, failed = stock_price.fetch_close_price_from_ak(start_date)
    print(df)
    print(f"failed codes: {failed}")


# 纯粹测试函数
def get_hfq_prices():
    stock_price = StockPriceHistory()
    start_date = pd.to_datetime('20191124', format='%Y%m%d')
    stock_price_df = stock_price.get_stock_price_df(start_date)
    stock_price_df = stock_price_df[stock_price_df['证券代码'] == '002515']
    hfq_df = pd.read_pickle(ALL_HFQ_FACTORS_PKL)
    hfq_df = hfq_df[hfq_df['证券代码'] == '002515']
    result = stock_price.cal_hfq_price(stock_price_df, hfq_df, start_date)
    print(result)


# Example usage
if __name__ == "__main__":
    run_update_ak()
    # StockPriceHistory.cache_trade_dates() # 获取交易日的函数不用经常调用，每年调一次即可

# StockPriceHistory.cache_hfq_factors(['002515','01024'])
# get_hfq_prices()
