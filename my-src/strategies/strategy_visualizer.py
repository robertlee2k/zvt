import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from strategy_planner import StrategyPlanner


class StrategyVisualizer:
    def visualize_strategy_returns(self, daily_returns, benchmark_rets, title, ylabel):

        strategy_rets = daily_returns['daily_return']
        positions = daily_returns['position_ratio']
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

        # 绘制策略持仓百分比
        ax_twin = axs[0].twinx()
        ax_twin.plot(positions.index, positions.values, color='g', label='Position Percentage')
        ax_twin.axhline(y=0, color='k', linestyle='--')
        ax_twin.axhline(y=1, color='k', linestyle='--')
        ax_twin.set_ylim(-1.1, 1.1)
        ax_twin.legend(loc='upper left')

        plt.tight_layout()
        plt.show()

    def calculate_strategy_performance(self, strategy_rets, benchmark_rets, freq):
        strategy_rets = strategy_rets.dropna()
        benchmark_rets = benchmark_rets.dropna()

        if freq == StrategyPlanner.DAILY:
            periods_per_year = 252
        elif freq == StrategyPlanner.WEEKLY:
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
        annualized_excess_return = annualized_return - benchmark_annualized_return

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

    # Function to draw a segment
    def _draw_segment(self, ax, start_idx, end_idx, state, hstech_his_price, colors, labels, font_colors):
        ax.axvspan(start_idx, end_idx, color=colors[state], alpha=0.3)
        mid_idx = (start_idx + end_idx) // 2
        ax.text(mid_idx, hstech_his_price['high'].max() * 1.05, labels[state],
                color=font_colors[state], fontsize=10, ha='center')

    def visualize_plan(self, strategy_planner: StrategyPlanner, hstech_his_price):
        # 绘制K线图和标记
        fig, ax = plt.subplots(figsize=(12, 8))
        # 重命名列名
        hstech_his_price = hstech_his_price.rename(columns={
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume"
        })

        hstech_his_price.index = pd.to_datetime(hstech_his_price.index)

        # 自定义样式
        mc = mpf.make_marketcolors(up='red', down='green', wick={'up': 'red', 'down': 'green'},
                                   edge={'up': 'red', 'down': 'green'})
        s = mpf.make_mpf_style(marketcolors=mc)
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
        plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
        mpf.plot(hstech_his_price, type='candle', ax=ax, style=s, volume=False)

        # 标记市场状态
        # 牛市(Bull Market): 使用 # FF9999 (较深的淡红)
        # 修正(Correction): 使用  # B0E57C (浅绿)
        # 熊市(Bear Market): 使用  # 90EE90 (浅绿)
        # 反弹(Rebound): 使用    # FFC1C1 (淡红色)
        colors = ['gray', '#FF9999', '#B0E57C', '#90EE90', '#FFC1C1']
        labels = StrategyPlanner.MARKET_STAGES  # ['未定义', '牛市', '修正', '熊市', '反弹']
        font_colors = ['black', 'red', 'green', 'green', 'red']
        market_states = strategy_planner.get_market_states()
        start_idx = None
        end_idx = None
        current_state = None

        # Iterate over market states
        for i, market_state in enumerate(market_states):
            date, stock, state_str = market_state

            # Check if date exists in hstech_his_price
            if date in hstech_his_price.index:
                idx = hstech_his_price.index.get_loc(date)
                state = StrategyPlanner.MARKET_STAGES.index(state_str)

                if current_state is None:
                    # Initialize the first state
                    start_idx = idx
                    current_state = state
                elif state != current_state:
                    # State has changed, draw the previous state segment
                    self._draw_segment(ax, start_idx, idx, current_state, hstech_his_price, colors, labels, font_colors)
                    # Update to the new state
                    start_idx = idx
                    current_state = state

        # Draw the last segment if the loop finished with an open state
        if current_state is not None and start_idx is not None:
            self._draw_segment(ax, start_idx, len(hstech_his_price) - 1, current_state, hstech_his_price, colors,
                               labels,
                               font_colors)

        # 标记交易计划
        previous_position = None
        dates = []
        positions = []

        for operation in strategy_planner.get_trading_operations():
            date, stock, position = operation
            idx = hstech_his_price.index.get_loc(date)
            dates.append(idx)
            positions.append(position)

            if previous_position is not None:
                change = round(position - previous_position, 2)
                if change > 0:
                    ax.annotate(f'↑ {change:.2f}', xy=(idx, hstech_his_price.loc[date, 'open']),
                                xytext=(idx, hstech_his_price.loc[date, 'open'] - 2),
                                arrowprops=dict(facecolor='red', shrink=0.05),
                                fontsize=8, color='black', ha='center', va='top')
                elif change < 0:
                    ax.annotate(f'↓ {change:.2f}', xy=(idx, hstech_his_price.loc[date, 'open']),
                                xytext=(idx, hstech_his_price.loc[date, 'open'] + 2),
                                arrowprops=dict(facecolor='green', shrink=0.05),
                                fontsize=8, color='black', ha='center', va='bottom')
            previous_position = position

        # 绘制实际仓位的背景线
        ax2 = ax.twinx()
        ax2.plot(dates, positions, color='blue', linestyle='-', linewidth=0.5, alpha=0.3)
        ax2.set_ylabel('仓位')
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.2f}'))
        ax2.grid(False)  # 隐藏背景线的网格
        ax2.set_yticks([])  # 隐藏背景线的Y轴刻度

        plt.title('市场状态与交易计划')
        plt.show()
