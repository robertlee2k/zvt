import akshare as ak
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def get_momentum_signals(rets, slow_window=12, fast_window=2):
    slow_mom = rets.rolling(slow_window).mean()
    fast_mom = rets.rolling(fast_window).mean()
    return slow_mom, fast_mom


def get_market_state(slow_mom, fast_mom):
    market_state = np.select([
        (slow_mom >= 0) & (fast_mom >= 0),  # 牛市
        (slow_mom >= 0) & (fast_mom < 0),  # 修正
        (slow_mom < 0) & (fast_mom < 0),  # 熊市
        (slow_mom < 0) & (fast_mom >= 0)  # 反弹
    ], [1, 2, 3, 4], default=0)
    return market_state


def dynamic_trend_strategy(rets, slow_window=12, fast_window=2, aCo=0.3, aRe=0.7, trading_cost=0.01):
    slow_mom, fast_mom = get_momentum_signals(rets, slow_window, fast_window)
    market_state = get_market_state(slow_mom, fast_mom)

    # 计算上一期的头寸
    # Convert market_state to a pandas Series
    market_state_series = pd.Series(market_state, index=rets.index)

    # Calculate previous_position
    previous_position = np.select([
        market_state_series.shift(1) == 1,  # 上期为牛市
        market_state_series.shift(1) == 2,  # 上期为修正
        market_state_series.shift(1) == 3,  # 上期为熊市
        market_state_series.shift(1) == 4  # 上期为反弹
    ], [
        (slow_mom.shift(1) >= 0).astype(int),  # 按慢速信号持仓
        (1 - aCo) * (slow_mom.shift(1) >= 0).astype(int) + aCo * (fast_mom.shift(1) >= 0).astype(int),  # 混合慢快信号持仓
        0,  # 不持仓
        np.maximum(0, (1 - aRe) * (slow_mom.shift(1) >= 0).astype(int) + aRe * (fast_mom.shift(1) >= 0).astype(int))
        # 最多持有0仓位
    ], default=0)

    # 计算本期头寸
    current_position = np.select([
        market_state == 1,  # 本期为牛市
        market_state == 2,  # 本期为修正
        market_state == 3,  # 本期为熊市
        market_state == 4  # 本期为反弹
    ], [
        (slow_mom >= 0).astype(int),  # 按慢速信号持仓
        (1 - aCo) * (slow_mom >= 0).astype(int) + aCo * (fast_mom >= 0).astype(int),  # 混合慢快信号持仓
        0,  # 不持仓
        np.maximum(0, (1 - aRe) * (slow_mom >= 0).astype(int) + aRe * (fast_mom >= 0).astype(int))  # 最多持有0仓位
    ], default=0)

    # 计算策略收益率,扣除交易成本
    strategy_rets = rets * current_position - trading_cost * np.abs(current_position - previous_position)

    return strategy_rets,current_position


def visualize_strategy_returns(strategy_rets, positions, benchmark_rets, title, ylabel):
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


# 获取恒生科技指数数据
stock_code = "01024"
adjust_type = "hfq"
start_date = '20230101'
end_date = '20231201'

# 日线数据
hstech_daily = ak.stock_hk_hist(symbol=stock_code, period="daily", start_date=start_date,
                                end_date=end_date, adjust=adjust_type)
# 周线数据
hstech_weekly = ak.stock_hk_hist(symbol=stock_code, period="weekly", start_date=start_date,
                                 end_date=end_date, adjust=adjust_type)
# 月线数据
hstech_monthly = ak.stock_hk_hist(symbol=stock_code, period="monthly", start_date=start_date,
                                  end_date=end_date, adjust=adjust_type)

# 回测日线数据
# 日线数据
hstech_daily_rets = hstech_daily["涨跌幅"]/100

# 回测日线数据
aCo = 0.3
aRe = 0.7
daily_strategy_rets, daily_positions = dynamic_trend_strategy(hstech_daily_rets, aCo=aCo, aRe=aRe)
daily_strategy_rets = pd.Series(daily_strategy_rets, index=hstech_daily_rets.index)
daily_positions = pd.Series(daily_positions, index=hstech_daily_rets.index)

# 可视化日线数据
#visualize_strategy_returns(daily_strategy_rets, daily_positions, hstech_daily_rets, 'Dynamic Trend Strategy Daily Returns', 'Returns')

# 周线数据
hstech_weekly_rets = hstech_weekly["涨跌幅"]/100

# 回测周线数据
weekly_strategy_rets, weekly_positions = dynamic_trend_strategy(hstech_weekly_rets, aCo=aCo, aRe=aRe)
weekly_strategy_rets = pd.Series(weekly_strategy_rets, index=hstech_weekly_rets.index)
weekly_positions = pd.Series(weekly_positions, index=hstech_weekly_rets.index)

# 可视化周线数据
#visualize_strategy_returns(weekly_strategy_rets, weekly_positions, hstech_weekly_rets, 'Dynamic Trend Strategy Weekly Returns', 'Returns')

# 月线数据
hstech_monthly_rets = hstech_monthly["涨跌幅"]/100

# 回测月线数据
monthly_strategy_rets, monthly_positions = dynamic_trend_strategy(hstech_monthly_rets, aCo=aCo, aRe=aRe)
monthly_strategy_rets = pd.Series(monthly_strategy_rets, index=hstech_monthly_rets.index)
monthly_positions = pd.Series(monthly_positions, index=hstech_monthly_rets.index)

# 可视化月线数据
#visualize_strategy_returns(monthly_strategy_rets, monthly_positions, hstech_monthly_rets, 'Dynamic Trend Strategy Monthly Returns', 'Returns')


def calculate_strategy_performance(strategy_rets, benchmark_rets, freq):
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
# 调用函数并传入freq参数
calculate_strategy_performance(daily_strategy_rets, hstech_daily_rets, 'daily')
calculate_strategy_performance(weekly_strategy_rets, hstech_weekly_rets, 'weekly')
calculate_strategy_performance(monthly_strategy_rets, hstech_monthly_rets, 'monthly')


