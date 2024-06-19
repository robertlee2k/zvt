import math

import numpy as np
import pandas as pd


class FactorEvaluator:
    def __init__(self, signals, returns):
        self.signals = signals
        self.returns = returns

    def calc_ic(self, signal):
        valid_idx = ~np.isnan(signal)
        signal = signal[valid_idx]
        returns = self.returns[valid_idx]
        if len(signal) == 0 or len(returns) == 0:
            return np.nan
        ic = np.corrcoef(signal, returns)[0, 1]
        return ic

    def hit_rate(self, signal):
        valid_idx = ~np.isnan(signal)
        signal = signal[valid_idx]
        returns = self.returns[valid_idx]
        if len(signal) == 0 or len(returns) == 0:
            return np.nan
        hit_rate = np.mean((signal > 0) == (returns > 0))
        return hit_rate

    def sharpe_ratio(self, signal, risk_free_rate=0.0):
        valid_idx = ~np.isnan(signal)
        returns = self.returns[valid_idx]
        if len(returns) == 0:
            return np.nan
        excess_returns = returns - risk_free_rate
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)

    def cumulative_return(self, signal):
        valid_idx = ~np.isnan(signal)
        returns = self.returns[valid_idx]
        if len(returns) == 0:
            return pd.Series([np.nan])
        return (1 + returns).cumprod() - 1

    def evaluate(self):
        results = {}
        for signal_name in self.signals.columns:
            signal = self.signals[signal_name]
            ic = self.calc_ic(signal)
            hit_rate = self.hit_rate(signal)
            sharpe_ratio = self.sharpe_ratio(signal)
            cumulative_returns = self.cumulative_return(signal)

            if not cumulative_returns.isna().all():
                cumulative_return_value = cumulative_returns.iloc[-1]
            else:
                cumulative_return_value = np.nan

            results[signal_name] = {
                'IC': ic,
                'Hit Rate': hit_rate,
                'Sharpe Ratio': sharpe_ratio,
                'Cumulative Returns': cumulative_return_value
            }

        return results

    def interpret_metrics(self, evaluation):
        interpretations = {}

        for factor, metrics in evaluation.items():
            ic = metrics['IC']
            hit_rate = metrics['Hit Rate']
            sharpe_ratio = metrics['Sharpe Ratio']

            interpretations[factor] = {}

            # 解释IC值
            if ic > 0.2:
                interpretations[factor][
                    'IC'] = f"IC值为 {ic:.4f}，表示因子具有较强的预测能力。一般来说，IC值大于0.2是较好的指标。"
            elif ic > 0:
                interpretations[factor][
                    'IC'] = f"IC值为 {ic:.4f}，表示因子具有一定的预测能力。一般来说，IC值在0到0.2之间表示中等预测能力。"
            else:
                interpretations[factor][
                    'IC'] = f"IC值为 {ic:.4f}，表示因子的预测能力较弱或无预测能力。一般来说，IC值小于等于0表示预测能力较差。"

            # 解释命中率
            if hit_rate > 0.6:
                interpretations[factor][
                    '命中率'] = f"命中率为 {hit_rate:.4f}，表示因子的预测准确率较高。一般来说，命中率高于0.6是较好的。"
            elif hit_rate > 0.5:
                interpretations[factor][
                    '命中率'] = f"命中率为 {hit_rate:.4f}，表示因子具有一定的预测准确率。一般来说，命中率在0.5到0.6之间表示中等预测准确率。"
            else:
                interpretations[factor][
                    '命中率'] = f"命中率为 {hit_rate:.4f}，表示因子的预测准确率较低。一般来说，命中率低于0.5表示预测准确率较差。"

            # 解释夏普比率
            if sharpe_ratio > 1:
                interpretations[factor][
                    '夏普比率'] = f"夏普比率为 {sharpe_ratio:.4f}，表示因子具有较好的风险调整后收益。一般来说，夏普比率高于1是较好的。"
            elif sharpe_ratio > 0:
                interpretations[factor][
                    '夏普比率'] = f"夏普比率为 {sharpe_ratio:.4f}，表示因子具有一定的风险调整后收益。一般来说，夏普比率在0到1之间表示中等的风险调整后收益。"
            else:
                interpretations[factor][
                    '夏普比率'] = f"夏普比率为 {sharpe_ratio:.4f}，表示因子的风险调整后收益较差或为负。一般来说，夏普比率小于等于0表示收益较差。"

        return interpretations

    def calculate_statistics(self, df):
        '''
        输入：
        DataFrame类型，包含价格数据和仓位、开平仓标志
            position列：仓位标志位，0表示空仓，1表示持有标的
            flag列：买入卖出标志位，1表示在该时刻买入，-1表示在该时刻卖出
            close列：日收盘价

        输出：dict类型，包含夏普比率、最大回撤等策略结果的统计数据
        '''
        # 净值序列
        df['net_asset_pct_chg'] = df.net_asset_value.pct_change(1).fillna(0)

        # 总收益率与年化收益率
        total_return = (df['net_asset_value'][df.shape[0] - 1] - 1)
        annual_return = (total_return) ** (1 / (df.shape[0] / 252)) - 1
        total_return = total_return * 100
        annual_return = annual_return * 100
        # 夏普比率
        df['ex_pct_chg'] = df['net_asset_pct_chg']
        sharp_ratio = df['ex_pct_chg'].mean() * math.sqrt(252) / df['ex_pct_chg'].std()

        # 回撤
        df['high_level'] = (
            df['net_asset_value'].rolling(
                min_periods=1, window=len(df), center=False).max()
        )
        df['draw_down'] = df['net_asset_value'] - df['high_level']
        df['draw_down_percent'] = df["draw_down"] / df["high_level"] * 100
        max_draw_down = df["draw_down"].min()
        max_draw_percent = df["draw_down_percent"].min()

        # 持仓总天数
        hold_days = df['position'].sum()

        # 交易次数
        trade_count = df[df['flag'] != 0].shape[0] / 2

        # 平均持仓天数
        avg_hold_days = int(hold_days / trade_count)

        # 获利天数
        profit_days = df[df['net_asset_pct_chg'] > 0].shape[0]
        # 亏损天数
        loss_days = df[df['net_asset_pct_chg'] < 0].shape[0]

        # 胜率(按天)
        winrate_by_day = profit_days / (profit_days + loss_days) * 100
        # 平均盈利率(按天)
        avg_profit_rate_day = df[df['net_asset_pct_chg'] > 0]['net_asset_pct_chg'].mean() * 100
        # 平均亏损率(按天)
        avg_loss_rate_day = df[df['net_asset_pct_chg'] < 0]['net_asset_pct_chg'].mean() * 100
        # 平均盈亏比(按天)
        avg_profit_loss_ratio_day = avg_profit_rate_day / abs(avg_loss_rate_day)

        # 每一次交易情况
        buy_trades = df[df['flag'] == 1].reset_index()
        sell_trades = df[df['flag'] == -1].reset_index()
        result_by_trade = {
            'buy': buy_trades['close'],
            'sell': sell_trades['close'],
            'pct_chg': (sell_trades['close'] - buy_trades['close']) / buy_trades['close']
        }
        result_by_trade = pd.DataFrame(result_by_trade)
        # 盈利次数
        profit_trades = result_by_trade[result_by_trade['pct_chg'] > 0].shape[0]
        # 亏损次数
        loss_trades = result_by_trade[result_by_trade['pct_chg'] < 0].shape[0]
        # 单次最大盈利
        max_profit_trade = result_by_trade['pct_chg'].max() * 100
        # 单次最大亏损
        max_loss_trade = result_by_trade['pct_chg'].min() * 100
        # 胜率(按次)
        winrate_by_trade = profit_trades / (profit_trades + loss_trades) * 100
        # 平均盈利率(按次)
        avg_profit_rate_trade = result_by_trade[result_by_trade['pct_chg'] > 0]['pct_chg'].mean() * 100
        # 平均亏损率(按次)
        avg_loss_rate_trade = result_by_trade[result_by_trade['pct_chg'] < 0]['pct_chg'].mean() * 100
        # 平均盈亏比(按次)
        avg_profit_loss_ratio_trade = avg_profit_rate_trade / abs(avg_loss_rate_trade)

        statistics_result = {
            'net_asset_value': df['net_asset_value'][df.shape[0] - 1],  # 最终净值
            'total_return': total_return,  # 收益率
            'annual_return': annual_return,  # 年化收益率
            'sharp_ratio': sharp_ratio,  # 夏普比率
            'max_draw_percent': max_draw_percent,  # 最大回撤
            'hold_days': hold_days,  # 持仓天数
            'trade_count': trade_count,  # 交易次数
            'avg_hold_days': avg_hold_days,  # 平均持仓天数
            'profit_days': profit_days,  # 盈利天数
            'loss_days': loss_days,  # 亏损天数
            'winrate_by_day': winrate_by_day,  # 胜率（按天）
            'avg_profit_rate_day': avg_profit_rate_day,  # 平均盈利率（按天）
            'avg_loss_rate_day': avg_loss_rate_day,  # 平均亏损率（按天）
            'avg_profit_loss_ratio_day': avg_profit_loss_ratio_day,  # 平均盈亏比（按天）
            'profit_trades': profit_trades,  # 盈利次数
            'loss_trades': loss_trades,  # 亏损次数
            'max_profit_trade': max_profit_trade,  # 单次最大盈利
            'max_loss_trade': max_loss_trade,  # 单次最大亏损
            'winrate_by_trade': winrate_by_trade,  # 胜率（按次）
            'avg_profit_rate_trade': avg_profit_rate_trade,  # 平均盈利率（按次）
            'avg_loss_rate_trade': avg_loss_rate_trade,  # 平均亏损率（按次）
            'avg_profit_loss_ratio_trade': avg_profit_loss_ratio_trade  # 平均盈亏比（按次）
        }
        return statistics_result
