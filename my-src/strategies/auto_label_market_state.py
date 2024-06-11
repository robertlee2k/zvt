### 这个是标注牛熊形态的，用了未来数据，不能用于回测！！！

import pandas as pd
from market_data_helper import MarketDataHelper

class LabelMarketState:

    def __init__(self ,frequency, adjust_type, start_date, end_date, stock_code):
        self.frequency = frequency
        self.market_states = None
        self.start_date = None  # 策略开始运行的日期
        self.end_date = None
        self.returns, self.prices=LabelMarketState.prepare_data(frequency, adjust_type, start_date, end_date, stock_code)

    @staticmethod
    def prepare_data(frequency, adjust_type, start_date, end_date, stock_code):
        stock_his = MarketDataHelper.query_akshare(symbol=stock_code, period=frequency,
                                                    start_date=start_date,
                                                    end_date=end_date, adjust=adjust_type)

        stock_his.index = pd.to_datetime(stock_his['日期'])
        stock_his["涨跌幅"] = stock_his["涨跌幅"] / 100
        # 重命名 '涨跌幅' 字段为 '收益率'
        stock_his.rename(columns={'涨跌幅': '收益率'}, inplace=True)
        stock_rets = stock_his[['收益率']]
        stock_prices = stock_his[["开盘", "收盘", "最高", "最低", "成交量"]]
        return stock_rets,stock_prices


    def label_market_trends(self, bull_threshold=0.20, bear_threshold=-0.20, correction_threshold=-0.10):
        """
        标注股票的牛市、熊市、修正、反弹区间
        df: 包含历史日收益率的数据框，假设有一列 `returns` 表示日收益率
        bull_threshold: 牛市阈值
        bear_threshold: 熊市阈值
        correction_threshold: 修正阈值
        返回标注了市场状态的数据框
        """
        df = self.returns
        # 计算累计收益率
        df['cumulative_returns'] = (1 + df['returns']).cumprod() - 1

        # 初始化市场状态列
        df['market_state'] = 'None'

        # 设置初始状态
        current_state = 'None'
        start_index = 0

        # 遍历数据框
        for i in range(1, len(df)):
            # 计算当前累计收益率变化
            cumulative_change = df.loc[i, 'cumulative_returns'] - df.loc[start_index, 'cumulative_returns']

            # 处理牛市
            if current_state == 'None':
                if cumulative_change > bull_threshold:
                    current_state = 'Bull'
                    df.loc[start_index:i, 'market_state'] = 'Bull'
                    start_index = i
                elif cumulative_change < bear_threshold:
                    current_state = 'Bear'
                    df.loc[start_index:i, 'market_state'] = 'Bear'
                    start_index = i
                elif bear_threshold < cumulative_change < correction_threshold:
                    current_state = 'Correction'
                    df.loc[start_index:i, 'market_state'] = 'Correction'
                    start_index = i

            # 处理牛市后的转换
            elif current_state == 'Bull':
                if cumulative_change < correction_threshold:
                    current_state = 'Correction'
                    df.loc[start_index:i, 'market_state'] = 'Correction'
                    start_index = i
                elif cumulative_change < bear_threshold:
                    current_state = 'Bear'
                    df.loc[start_index:i, 'market_state'] = 'Bear'
                    start_index = i

            # 处理熊市
            elif current_state == 'Bear':
                if cumulative_change > -correction_threshold:
                    current_state = 'Rebound'
                    df.loc[start_index:i, 'market_state'] = 'Rebound'
                    start_index = i

            # 处理修正后的转换
            elif current_state == 'Correction':
                if cumulative_change > correction_threshold:
                    current_state = 'Bull'
                    df.loc[start_index:i, 'market_state'] = 'Bull'
                    start_index = i
                elif cumulative_change < bear_threshold:
                    current_state = 'Bear'
                    df.loc[start_index:i, 'market_state'] = 'Bear'
                    start_index = i

            # 处理反弹后的转换
            elif current_state == 'Rebound':
                if cumulative_change > correction_threshold:
                    current_state = 'Bull'
                    df.loc[start_index:i, 'market_state'] = 'Bull'
                    start_index = i
                elif cumulative_change < bear_threshold:
                    current_state = 'Bear'
                    df.loc[start_index:i, 'market_state'] = 'Bear'
                    start_index = i

        # 确保最后一个区间标注正确
        if current_state != 'None':
            df.loc[start_index:, 'market_state'] = current_state

        self.market_states=LabelMarketState.create_market_structure(df,self.stock_code,self.start_date)
        return df

    @staticmethod
    def create_market_structure(data, stock_code, start_date):
        """
        根据标注后的数据创建market结构
        data: 包含标注市场状态的DataFrame
        stock_code: 股票代码
        start_date: 开始日期
        返回market结构列表
        """
        market = []
        for i in range(len(data)):
            market_date = data.index[i]  # 市场状态就是当天
            cur_market = data['market_state'].iloc[i]  # 当前的市场状态
            market.append((market_date, stock_code, cur_market))
        return market

    # 示例数据框
    data = pd.DataFrame({'returns': [0.01, -0.02, 0.03, -0.01, 0.02, -0.03, 0.01]})
    data.index = pd.date_range(start='2023-01-01', periods=len(data), freq='D')

    # 标注市场状态
    labeled_df = label_market_trends(data)

    # 创建market结构
    stock_code = 'AAPL'
    start_date = pd.Timestamp('2023-01-03')
    market_structure = create_market_structure(labeled_df, stock_code, start_date)

    print(market_structure)

def run_labeling():
    stock_code = "01024"
    adjust_type = "hfq"
    start_date = '20230101'
    end_date = '20241231'
    frequency = 'daily'
    labelClass = LabelMarketState(frequency, adjust_type, start_date, end_date, stock_code)
    labelClass.label_market_trends()

if __name__ == "__main__":
    run_labeling()
