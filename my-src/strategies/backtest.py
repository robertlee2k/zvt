import akshare as ak
import pandas as pd
from strategy_planner import StrategyPlanner
from trade_simulator import TraderSimulator
from strategy_visualizer import StrategyVisualizer


def run_backtest():
    # 获取恒生科技指数数据
    stock_code = "01024"
    adjust_type = "hfq"
    start_date = '20200101'
    end_date = '20241231'
    frequency = StrategyPlanner.WEEKLY
    # k线数据
    hstech_his = ak.stock_hk_hist(symbol=stock_code, period=frequency, start_date=start_date,
                                  end_date=end_date, adjust=adjust_type)
    hstech_his.index = pd.to_datetime(hstech_his['日期'])
    hstech_his["涨跌幅"] = hstech_his["涨跌幅"] / 100
    # 重命名 '涨跌幅' 字段为 '收益率'
    hstech_his.rename(columns={'涨跌幅': '收益率'}, inplace=True)
    hstech_his_rets = hstech_his[['收益率']]
    hstech_his_prices = hstech_his[["开盘", "收盘", "最高", "最低", "成交量"]]
    # 创建策略规划器
    strategy_planner = StrategyPlanner(frequency)
    strategy_planner.generate_trading_operations(stock_code, hstech_his_rets)
    # 生成交易操作记录
    trading_operations = strategy_planner.get_trading_operations()
    # 创建交易模拟器实例
    trader_simulator = TraderSimulator(start_date=start_date, initial_cash=1000000, stock_code=stock_code)
    # 模拟交易过程
    strategy_rets = trader_simulator.simulate_trading(trading_operations, hstech_his_prices)
    # 可视化策略表现
    strategy_visualizer = StrategyVisualizer()
    strategy_visualizer.visualize_plan(strategy_planner, hstech_his_prices)
    strategy_visualizer.visualize_strategy_returns(strategy_rets, hstech_his_rets,
                                                   'Dynamic Trend Strategy Daily Returns', 'Returns')
    strategy_visualizer.calculate_strategy_performance(strategy_rets['daily_return'], hstech_his_rets['收益率'],
                                                       frequency)


if __name__ == "__main__":
    run_backtest()
