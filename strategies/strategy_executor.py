import pandas as pd
import numpy as np

class StrategyExecutor:
    def __init__(self, aCo=0.3, aRe=0.7):
        self.aCo = aCo
        self.aRe = aRe

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

    def generate_trading_operations(self, rets, slow_window=12, fast_window=2):
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
            np.maximum(0, (1 - self.aRe) * (slow_mom >= 0).astype(int) + self.aRe * (fast_mom >= 0).astype(int))  # 最多持有0仓位
        ], default=0)

        # 记录每次策略执行的操作
        trading_operations = []
        for date, curr_pos in zip(rets.index, current_position):
            trading_operations.append((date, curr_pos))

        return trading_operations