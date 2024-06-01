import numpy as np
import matplotlib.pyplot as plt

class StrategyVisualizer:
    def visualize_strategy_returns(self, strategy_rets, benchmark_rets, title, ylabel):
        fig, axs = plt.subplots(2, 1, figsize=(16, 9), sharex=True, gridspec_kw={'height_ratios': [3, 1]})

        # 绘制单期收益率
        axs[0].plot(strategy_rets.index, strategy_rets.values, label='Strategy Returns')
        axs[0].legend()
        axs[0].set_title(title)
        axs[0].set_ylabel(ylabel)

        # 绘制累计收益率
        cum_strategy_rets = (1 + strategy_rets).cumprod()
        cum_benchmark_rets = (1 + benchmark_rets).cumprod()
        axs[1].plot(cum_strategy_rets.index, cum_strategy_rets.values, label='Cumulative Strategy Returns')
        axs[1].plot(cum_benchmark_rets.index, cum_benchmark_rets.values, label='Cumulative Benchmark Returns')
        axs[1].axhline(y=1, color='k', linestyle='--', label='Initial Capital')
        axs[1].legend()
        axs[1].set_xlabel('Date')
        axs[1].set_ylabel('Cumulative Returns')

        # # 绘制策略持仓百分比
        # ax_twin = axs[0].twinx()
        # ax_twin.plot(positions.index, positions.values, color='g', label='Position Percentage')
        # ax_twin.axhline(y=0, color='k', linestyle='--')
        # ax_twin.axhline(y=1, color='k', linestyle='--')
        # ax_twin.set_ylim(-1.1, 1.1)
        # ax_twin.legend(loc='upper left')

        plt.tight_layout()
        plt.show()

    def calculate_strategy_performance(self, strategy_rets, benchmark_rets, freq):
        strategy_rets = strategy_rets.dropna()
        benchmark_rets = benchmark_rets.dropna()

        if freq == 'daily':
            periods_per_year = 252
        elif freq == 'weekly':
            periods_per_year = 52
        else:
            periods_per_year = 12

        annualized_return = (1 + strategy_rets).prod() ** (periods_per_year / len(strategy_rets)) - 1
        benchmark_annualized_return = (1 + benchmark_rets).prod() ** (periods_per_year / len(benchmark_rets)) - 1

        annualized_volatility = strategy_rets.std() * np.sqrt(periods_per_year)
        benchmark_annualized_volatility = benchmark_rets.std() * np.sqrt(periods_per_year)

        risk_free_rate = 0  # 假设无风险利率为0
        annualized_excess_return = annualized_return - risk_free_rate
        # 处理年化波动率为0的情况
        if annualized_volatility == 0:
             sharpe_ratio = np.nan
        else:
            sharpe_ratio = annualized_excess_return / annualized_volatility

        cum_rets = (1 + strategy_rets).cumprod()
        cum_max = cum_rets.cummax()
        drawdowns = (cum_max - cum_rets) / cum_max
        max_drawdown = drawdowns.max()

        benchmark_cum_rets = (1 + benchmark_rets).cumprod()
        benchmark_cum_max = benchmark_cum_rets.cummax()
        benchmark_drawdowns = (benchmark_cum_max - benchmark_cum_rets) / benchmark_cum_max
        benchmark_max_drawdown = benchmark_drawdowns.max()

        excess_returns = strategy_rets - benchmark_rets
        annualized_excess_return= annualized_return - benchmark_annualized_return

        if freq == 'daily':
            print("日线数据回测结果:")
        elif freq == 'weekly':
            print("周线数据回测结果:")
        else:
            print("月线数据回测结果:")

        print("-" * 30)
        print("{:<20}{:<20}{:<20}".format('指标', '策略', '基准'))
        print("-" * 30)
        print("{:<20}{:<20.2%}{:<20.2%}".format('年化收益率', annualized_return, benchmark_annualized_return))
        print("{:<20}{:<20.2%}{:<20.2%}".format('年化波动率', annualized_volatility, benchmark_annualized_volatility))
        print("{:<20}{:<20.2f}{:<20.2f}".format('夏普比率', sharpe_ratio, (
                    benchmark_annualized_return - risk_free_rate) / benchmark_annualized_volatility))
        print("{:<20}{:<20.2%}{:<20.2%}".format('最大回撤', max_drawdown, benchmark_max_drawdown))
        print("{:<20}{:<20.2%}".format('年化超额收益率', annualized_excess_return))
        print("-" * 30)

        return annualized_return, annualized_volatility, sharpe_ratio, max_drawdown, annualized_excess_return
