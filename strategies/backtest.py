import akshare as ak
from strategy_executor import StrategyExecutor
from strategy_visualizer import StrategyVisualizer
import pandas as pd

# 获取恒生科技指数数据
stock_code = "01024"
adjust_type = "hfq"
start_date = '20220101'
end_date = '20241231'

# 日线数据
hstech_daily = ak.stock_hk_hist(symbol=stock_code, period="daily", start_date=start_date,
                                end_date=end_date, adjust=adjust_type)
# 周线数据
hstech_weekly = ak.stock_hk_hist(symbol=stock_code, period="weekly", start_date=start_date,
                                 end_date=end_date, adjust=adjust_type)
# 月线数据
hstech_monthly = ak.stock_hk_hist(symbol=stock_code, period="monthly", start_date=start_date,
                                  end_date=end_date, adjust=adjust_type)

# 重设日线数据索引为日期
hstech_daily.index = pd.to_datetime(hstech_daily['日期'])
# 重设周线数据索引为日期
hstech_weekly.index = pd.to_datetime(hstech_weekly['日期'])
# 重设月线数据索引为日期
hstech_monthly.index = pd.to_datetime(hstech_monthly['日期'])
# 回测日线数据
hstech_daily_rets = hstech_daily["涨跌幅"]/100

# 回测周线数据
hstech_weekly_rets = hstech_weekly["涨跌幅"]/100

# 回测月线数据
hstech_monthly_rets = hstech_monthly["涨跌幅"]/100

# 创建策略执行器和可视化器实例
strategy_executor = StrategyExecutor(aCo=0.3, aRe=0.7)
strategy_visualizer = StrategyVisualizer()

# 执行日线策略
daily_strategy_rets, positions = strategy_executor.dynamic_trend_strategy(hstech_daily_rets)
daily_strategy_rets = pd.Series(daily_strategy_rets, index=hstech_daily_rets.index)

# 可视化日线策略
strategy_visualizer.visualize_strategy_returns(daily_strategy_rets, positions, hstech_daily_rets, 'Dynamic Trend Strategy Daily Returns', 'Returns')

# 计算日线策略指标
strategy_visualizer.calculate_strategy_performance(daily_strategy_rets, hstech_daily_rets, 'daily')

# 保存日线策略操作记录
strategy_executor.save_strategy_operations_to_excel(hstech_daily_rets, 'daily', '日线策略操作记录.xlsx')

# 执行周线策略
weekly_strategy_rets, positions = strategy_executor.dynamic_trend_strategy(hstech_weekly_rets)
weekly_strategy_rets = pd.Series(weekly_strategy_rets, index=hstech_weekly_rets.index)

# 可视化周线策略
strategy_visualizer.visualize_strategy_returns(weekly_strategy_rets, positions, hstech_weekly_rets, 'Dynamic Trend Strategy Weekly Returns', 'Returns')

# 计算周线策略指标
strategy_visualizer.calculate_strategy_performance(weekly_strategy_rets, hstech_weekly_rets, 'weekly')

# 保存周线策略操作记录
strategy_executor.save_strategy_operations_to_excel(hstech_weekly_rets, 'weekly', '周线策略操作记录.xlsx')

# 执行月线策略
monthly_strategy_rets, positions = strategy_executor.dynamic_trend_strategy(hstech_monthly_rets)
monthly_strategy_rets = pd.Series(monthly_strategy_rets, index=hstech_monthly_rets.index)

# 可视化月线策略
strategy_visualizer.visualize_strategy_returns(monthly_strategy_rets, positions, hstech_monthly_rets, 'Dynamic Trend Strategy Monthly Returns', 'Returns')

# 计算月线策略指标
strategy_visualizer.calculate_strategy_performance(monthly_strategy_rets, hstech_monthly_rets, 'monthly')

# 保存月线策略操作记录
strategy_executor.save_strategy_operations_to_excel(hstech_monthly_rets, 'monthly', '月线策略操作记录.xlsx')
