import akshare as ak
import pandas as pd
from strategy_planner import StrategyPlanner
from trade_simulator import TraderSimulator
from strategy_visualizer import StrategyVisualizer

# 获取恒生科技指数数据
stock_code = "01024"
adjust_type = "hfq"
start_date = '20230101'
end_date = '20231231'

# 日线数据
hstech_daily = ak.stock_hk_hist(symbol=stock_code, period="daily", start_date=start_date,
                                end_date=end_date, adjust=adjust_type)
hstech_daily.index = pd.to_datetime(hstech_daily['日期'])
hstech_daily_rets = hstech_daily["涨跌幅"] / 100
hstech_daily_prices = hstech_daily["收盘"]

# 创建策略规划器和交易模拟器实例
strategy_planner = StrategyPlanner(aCo=0.3, aRe=0.7)
trader_simulator = TraderSimulator(start_date=start_date, initial_cash=1000000, stock_code=stock_code)

# 生成交易操作记录
trading_operations = strategy_planner.generate_trading_operations(stock_code, hstech_daily_rets)

# 模拟交易过程
strategy_rets = trader_simulator.simulate_trading(trading_operations, hstech_daily_prices)
print(strategy_rets)


# 可视化策略表现
strategy_visualizer = StrategyVisualizer()
strategy_visualizer.visualize_strategy_returns(strategy_rets,hstech_daily_rets, 'Dynamic Trend Strategy Daily Returns', 'Returns')
strategy_visualizer.calculate_strategy_performance(strategy_rets['daily_return'], hstech_daily_rets, 'daily')