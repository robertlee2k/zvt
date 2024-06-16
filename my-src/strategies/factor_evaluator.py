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