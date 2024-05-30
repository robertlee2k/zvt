import pandas as pd
import numpy as np
import openpyxl
from collections import defaultdict

class StrategyExecutor:
    def __init__(self, aCo=0.3, aRe=0.7, trading_cost=0.01):
        self.aCo = aCo
        self.aRe = aRe
        self.trading_cost = trading_cost


    def get_momentum_signals(self, rets, slow_window=12, fast_window=2):
        slow_mom = rets.rolling(slow_window).mean()
        fast_mom = rets.rolling(fast_window).mean()
        return slow_mom, fast_mom

    def get_market_state(self, slow_mom, fast_mom):
        market_state = np.select([
            (slow_mom >= 0) & (fast_mom >= 0),  # 牛市
            (slow_mom >= 0) & (fast_mom < 0),  # 修正
            (slow_mom < 0) & (fast_mom < 0),  # 熊市
            (slow_mom < 0) & (fast_mom >= 0)  # 反弹
        ], [1, 2, 3, 4], default=0)
        return market_state

    def dynamic_trend_strategy(self, rets, slow_window=12, fast_window=2):
        slow_mom, fast_mom = self.get_momentum_signals(rets, slow_window, fast_window)
        market_state = self.get_market_state(slow_mom, fast_mom)


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

        current_position_df = pd.Series(current_position, index=rets.index)
        # 获取上一期的头寸
        previous_position = current_position_df.shift(1).fillna(0).values

        # 计算策略收益率,扣除交易成本
        strategy_rets = rets * current_position - self.trading_cost * np.abs(current_position - previous_position)

        # 记录每次策略执行的操作
        self.strategy_operations = defaultdict(list)
        cum_strategy_ret = 1
        cum_bench_ret = 1
        for date, prev_pos, curr_pos, ret in zip(rets.index, previous_position, current_position, strategy_rets):
            cum_strategy_ret *= (1 + ret)
            cum_bench_ret *= (1 + rets.loc[pd.Timestamp(date)])

            position_change = curr_pos - prev_pos
            if position_change != 0 or date==rets.index[-1] or date==rets.index[0]:  # 只记录：有操作的日期、开始日期、结束日期
                if position_change > 0:
                    operation_type = "买入"
                elif position_change < 0:
                    operation_type = "卖出"
                else:
                    operation_type = "检查点"
                self.strategy_operations[date.date()].append(
                    (operation_type, position_change, curr_pos, cum_strategy_ret-1, cum_bench_ret-1))

        # 返回策略收益率和头寸序列
        return strategy_rets, pd.Series(current_position, index=rets.index)

    def save_strategy_operations_to_excel(self, benchmark_rets, freq, filename):
        # 创建Excel工作簿
        workbook = openpyxl.Workbook()
        worksheet = workbook.active

        # 设置工作表标题
        if freq == 'daily':
            worksheet.title = "日线策略操作记录"
        elif freq == 'weekly':
            worksheet.title = "周线策略操作记录"
        else:
            worksheet.title = "月线策略操作记录"

        # 写入表头
        worksheet.append(["操作日期", "操作类型", "变化仓位","当前持仓", "累计收益率", "基准收益率"])

        # 记录策略操作
        for date, operations in sorted(self.strategy_operations.items()):
            for operation_type, position_change, current_position, strategy_ret, excess_ret in operations:
                worksheet.append([date, operation_type, position_change, current_position,  f"{strategy_ret:.2f}", f"{excess_ret:.2f}"])

        # 保存Excel文件
        workbook.save(filename)
