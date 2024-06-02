import numpy as np
import openpyxl


# ***** 需要特别注意 *******
# 在回测和实际操作中，我们通常需要在日结束后（例如，收盘后）计算出策略信号，并在下一个交易日开盘前执行操作。
# 因此，为了避免使用未来数据，策略信号计算应该基于前一天的数据，而不是当日的数据。
# 生成批量计划时， 我们采用的是current_position[i-1]: 这样，我们在生成交易操作时使用的是前一天的头寸，
# 这样可以模拟我们是确保在每个交易日开盘前做出决策，而不使用未来的数据。


class StrategyPlanner:
    def __init__(self, aCo=0.3, aRe=0.7):
        self.aCo = aCo
        self.aRe = aRe
        self.market_states = None
        self.plan = None

    def get_market_states(self):
        return self.market_states

    def get_trading_operations(self):
        return self.plan

    def _momentum_signals(self, rets, slow_window=12, fast_window=2):
        slow_mom = rets.rolling(slow_window).mean()
        fast_mom = rets.rolling(fast_window).mean()
        return slow_mom, fast_mom

    def _market_state(self, slow_mom, fast_mom):
        market_state = np.select([
            (slow_mom >= 0) & (fast_mom >= 0),  # 牛市
            (slow_mom >= 0) & (fast_mom < 0),  # 修正
            (slow_mom < 0) & (fast_mom < 0),  # 熊市
            (slow_mom < 0) & (fast_mom >= 0)  # 反弹
        ], [1, 2, 3, 4], default=0)
        return market_state

    def generate_trading_operations(self, stock_code, rets, slow_window=12, fast_window=2):
        slow_mom, fast_mom = self._momentum_signals(rets, slow_window, fast_window)
        market_state = self._market_state(slow_mom, fast_mom)

        # 计算本期头寸
        current_position = np.select([
            market_state == 1,  # 本期为牛市
            market_state == 2,  # 本期为修正
            market_state == 3,  # 本期为熊市
            market_state == 4  # 本期为反弹
        ], [
            (slow_mom >= 0).astype(int),  # 按慢速信号持仓
            (1 - self.aCo) * (slow_mom >= 0).astype(int) + self.aCo * (fast_mom >= 0).astype(int),  # 混合慢快信号持仓
            0,  # 不持仓
            np.maximum(0, (1 - self.aRe) * (slow_mom >= 0).astype(int) + self.aRe * (fast_mom >= 0).astype(int))
            # 最多持有0仓位
        ], default=0)

        # 记录每次策略执行的操作，并将执行日期往后推一个周期
        trading_operations = []
        market = []
        for i in range(len(rets) - 1):
            execute_date = rets.index[i + 1]  # 将执行日期推后一天
            curr_pos = current_position[i]  # 当前的头寸
            trading_operations.append((execute_date, stock_code, curr_pos))

            market_date = rets.index[i] # 市场状态就是当天,不用后推一天
            cur_market = market_state[i] # 当前的市场状态
            market.append((market_date,stock_code, cur_market))


        self.plan = trading_operations
        self.market_states = market
        self.save_strategy_plan()
        return trading_operations

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
        workbook.save("strategy_plan.xlsx")
