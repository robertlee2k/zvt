import numpy as np
import pandas as pd
import openpyxl


# ***** 需要特别注意 *******
# 在回测和实际操作中，我们通常需要在日结束后（例如，收盘后）计算出策略信号，并在下一个交易日开盘前执行操作。
# 因此，为了避免使用未来数据，策略信号计算应该基于前一天的数据，而不是当日的数据。
# 生成批量计划时， 我们采用的是current_position[i-1]: 这样，我们在生成交易操作时使用的是前一天的头寸，
# 这样可以模拟我们是确保在每个交易日开盘前做出决策，而不使用未来的数据。


class StrategyPlanner:
    MARKET_STAGES = ['Unknown', 'Bull', 'Correction', 'Bear', 'Rebound']
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'

    def __init__(self, frequency):
        self.lookback_periods, self.slow_window, self.fast_window = self._define_window_periods(frequency)
        self.aCo_Series = None
        self.aRe_Series = None
        self.market_states = None
        self.plan = None

    @staticmethod
    def _define_window_periods(frequency):

        if frequency == StrategyPlanner.DAILY:
            lookback_periods = 200
            slow_window = 60
            fast_window = 10
        elif frequency == StrategyPlanner.WEEKLY:
            lookback_periods = 52
            slow_window = 24
            fast_window = 4
        elif frequency == StrategyPlanner.MONTHLY:
            lookback_periods = 12
            slow_window = 12
            fast_window = 2
        else:
            lookback_periods = 200
            slow_window = 12
            fast_window = 2
        return lookback_periods, slow_window, fast_window

    def get_market_states(self):
        return self.market_states

    def get_trading_operations(self):
        return self.plan

    # 定义动量信号计算
    @staticmethod
    def _cal_momentum(data, window):
        return data.rolling(window=window).mean()

    @staticmethod
    def _market_state(momentum_slow, momentum_fast):
        market_state = pd.DataFrame(index=momentum_slow.index)
        conditions = [
            (momentum_slow >= 0) & (momentum_fast >= 0),
            (momentum_slow >= 0) & (momentum_fast < 0),
            (momentum_slow < 0) & (momentum_fast < 0),
            (momentum_slow < 0) & (momentum_fast >= 0)
        ]
        choices = StrategyPlanner.MARKET_STAGES[1:]
        market_state['市场状态'] = np.select(conditions, choices, default=StrategyPlanner.MARKET_STAGES[0])
        return market_state

    @staticmethod
    def _cal_normalization_factor(past_returns):
        """
        参数：
        past_returns: pandas.Series，资产过去m个周期的的回报率数据和市场状态数据
        返回值：
        归一化因子（标量）
        """
        past_market_state = past_returns['市场状态']
        lookback_periods = len(past_returns)

        # 计算频率
        freq_bu = np.sum(past_market_state == 'Bull') / lookback_periods
        freq_be = np.sum(past_market_state == 'Bear') / lookback_periods
        freq_bu_or_be = freq_bu + freq_be

        # 计算平均回报率
        avg_return_bu = past_returns[past_returns['市场状态'] == 'Bull']['收益率'].mean()
        avg_return_be = past_returns[past_returns['市场状态'] == 'Bear']['收益率'].mean()

        # 计算平均平方回报率
        avg_return_square_bu_or_be = (
                past_returns[past_returns['市场状态'].isin(['Bull', 'Bear'])]['收益率'] ** 2).mean()

        if freq_bu_or_be == 0 or avg_return_square_bu_or_be == 0:
            return np.nan
        else:
            C = (freq_bu / freq_bu_or_be) * (avg_return_bu / avg_return_square_bu_or_be) - \
                (freq_be / freq_bu_or_be) * (avg_return_be / avg_return_square_bu_or_be)
            return C

    # 计算 aCo 和 aRe
    def _cal_aCo_aRe(self, returns):
        C_series = pd.Series(index=returns.index, name='ConstC')
        aCo_series = pd.Series(index=returns.index, name='aCorrection')
        aRe_series = pd.Series(index=returns.index, name='aRebound')

        for date in returns.index:
            # 先算C
            returns_before_the_date = returns.loc[:date]
            # 计算归一化因子。确保有足够的数据，如果不够，则使用现有的数据。
            # lookback_periods: int，回溯期长度（这是用历史统计数据来看股票的长短趋势，按直觉判断，日线应该用250，周线用52，年线用12）
            # 如果数据量不足，使用已有全部的数据
            if len(returns_before_the_date) > self.lookback_periods:
                # 取最近 lookback_periods 的数据
                returns_before_the_date = returns_before_the_date.iloc[- self.lookback_periods:]

            C = self._cal_normalization_factor(returns_before_the_date)
            C_series[date] = C

            # 再算aCo
            returns_co = returns_before_the_date[returns_before_the_date['市场状态'] == 'Correction']
            avg_return_co = returns_co['收益率'].mean()
            avg_return_square_co = (returns_co['收益率'] ** 2).mean()
            a_co = 0.5 * (1 - (1 / C) * (avg_return_co / avg_return_square_co))
            aCo_series[date] = a_co

            returns_re = returns_before_the_date[returns_before_the_date['市场状态'] == 'Rebound']
            avg_return_re = returns_re['收益率'].mean()
            avg_return_square_re = (returns_re['收益率'] ** 2).mean()
            a_re = 0.5 * (1 - (1 / C) * (avg_return_re / avg_return_square_re))
            aRe_series[date] = a_re
        aRe_series = aRe_series.clip(0, 1)
        aCo_series = aCo_series.clip(0, 1)
        return aCo_series, aRe_series, C_series

    # 计算动态趋势策略仓位
    @staticmethod
    def _cal_dynamic_positions(data, aCo, aRe, momentum_slow, momentum_fast):
        dynamic_positions = pd.DataFrame(index=data.index, columns=['仓位'])
        for date in data.index:
            state = data.loc[date]['市场状态']
            slow_mom = momentum_slow.loc[date]
            if slow_mom >= 0:
                slow_mom = 1
            else:
                slow_mom = -1
            fast_mom = momentum_fast.loc[date]
            if fast_mom >= 0:
                fast_mom = 1
            else:
                fast_mom = -1
            if state == 'Bull':
                dynamic_positions.loc[date] = 1
            elif state == 'Bear':
                dynamic_positions.loc[date] = -1
            elif state == 'Correction':
                dynamic_positions.loc[date] = (1 - aCo.loc[date]) * slow_mom + aCo.loc[
                    date] * fast_mom
            elif state == 'Rebound':
                dynamic_positions.loc[date] = (1 - aRe.loc[date]) * slow_mom + aRe.loc[
                    date] * fast_mom
        return dynamic_positions

    def generate_trading_operations(self, stock_code, data):
        # 计算慢速和快速动量信号
        momentum_slow = self._cal_momentum(data['收益率'], self.slow_window)
        momentum_slow = momentum_slow.rename('长期收益率')
        momentum_fast = self._cal_momentum(data['收益率'], self.fast_window)
        momentum_fast = momentum_fast.rename('短期收益率')

        # 获取市场状态
        market_state = self._market_state(momentum_slow, momentum_fast)
        # 将市场状态拼接到原始数据中
        data = pd.concat([data, market_state], axis=1)
        self.aCo_Series, self.aRe_Series, C = self._cal_aCo_aRe(data)
        current_positions = self._cal_dynamic_positions(data, self.aCo_Series, self.aRe_Series, momentum_slow,
                                                        momentum_fast)

        self.write_internal_status(C, current_positions, data, momentum_slow, momentum_fast)

        # 明确数据类型以避免 FutureWarning
        current_positions['仓位'] = current_positions['仓位'].infer_objects(copy=False)
        # 将所有的 NaN 值转换为 0
        current_positions['仓位'] = current_positions['仓位'].fillna(0)
        # 将所有小于 0 的值设为 0 (因为我们不做空）
        current_positions['仓位'] = current_positions['仓位'].apply(lambda x: max(x, 0))

        # 记录每次策略执行的操作，并将执行日期往后推一个周期
        trading_operations = []
        market = []
        # 将执行日期往后推一个周期
        shifted_dates = self._shift_date_by_one(current_positions.index)
        for i, execute_date in enumerate(shifted_dates):
            curr_pos = current_positions['仓位'].iloc[i]  # 当前的头寸
            trading_operations.append((execute_date, stock_code, curr_pos))

            market_date = data.index[i]  # 市场状态就是当天,不用后推一天
            cur_market = data['市场状态'].iloc[i]  # 当前的市场状态
            market.append((market_date, stock_code, cur_market))

        self.plan = trading_operations
        self.market_states = market
        self.save_strategy_plan()
        return trading_operations

    def write_internal_status(self, C, current_positions, data, momentum_slow, momentum_fast):
        filename = '../output-files/strategy_internal_status.xlsx'
        # 拼接成一个 DataFrame
        combined_df = pd.concat(
            [current_positions, data, momentum_slow, momentum_fast, self.aCo_Series, self.aRe_Series, C], axis=1)
        combined_df.to_excel(filename)

        print(f"数据已成功导出到 {filename}")

    @staticmethod
    def _shift_date_by_one(date_index):
        return date_index[1:]

    def save_strategy_plan(self):
        # 保存交易记录和收益率到Excel文件
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.title = "策略计划"
        # 写入表头
        worksheet.append(["交易日期", "目标代码", "目标仓位"])
        # 记录交易操作
        for date, stock, target_position in self.plan:
            worksheet.append([date, stock, target_position])
        # 保存Excel文件
        workbook.save("../output-files/strategy_plan.xlsx")
