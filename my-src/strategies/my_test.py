import numpy as np
import pandas as pd

# 示例数据
dates = pd.date_range(start='2022-01-01', periods=10, freq='D')
data = pd.DataFrame({
    '市场状态': ['Bull', 'Bear', 'Correction', 'Rebound', 'Bull', 'Correction', 'Bear', 'Rebound', 'Bull',
                 'Correction'],
    '收益率': np.random.randn(10)
}, index=dates)

momentum_slow = pd.Series(np.random.randn(10), index=dates)
momentum_fast = pd.Series(np.random.randn(10), index=dates)
aCo = pd.Series(np.random.rand(10), index=dates)
aRe = pd.Series(np.random.rand(10), index=dates)


# 原始方法
def original_cal_dynamic_positions(data, aCo, aRe, momentum_slow, momentum_fast):
    dynamic_positions = pd.DataFrame(index=data.index, columns=['仓位'])
    for date in data.index:
        state = data.loc[date]['市场状态']
        slow_mom = momentum_slow.loc[date]
        if slow_mom >= 0:
            slow_mom = 1
        else:
            slow_mom = -1
        fast_mom = momentum_fast.loc[date]
        if fast_mom >= 0:
            fast_mom = 1
        else:
            fast_mom = -1
        if state == 'Bull':
            dynamic_positions.loc[date] = 1
        elif state == 'Bear':
            dynamic_positions.loc[date] = -1
        elif state == 'Correction':
            dynamic_positions.loc[date] = (1 - aCo.loc[date]) * slow_mom + aCo.loc[date] * fast_mom
        elif state == 'Rebound':
            dynamic_positions.loc[date] = (1 - aRe.loc[date]) * slow_mom + aRe.loc[date] * fast_mom
    return dynamic_positions


# 改进方法
def improved_cal_dynamic_positions(data, aCo, aRe, momentum_slow, momentum_fast):
    # 计算慢速和快速动量信号的方向
    slow_mom = np.sign(momentum_slow)
    fast_mom = np.sign(momentum_fast)

    # 计算 Correction 和 Rebound 状态下的仓位
    correction_positions = (1 - aCo) * slow_mom + aCo * fast_mom
    rebound_positions = (1 - aRe) * slow_mom + aRe * fast_mom

    # 根据市场状态设置仓位
    positions = np.where(
        data['市场状态'] == 'Bull', 1,
        np.where(data['市场状态'] == 'Bear', -1,
                 np.where(data['市场状态'] == 'Correction',
                          correction_positions,
                          rebound_positions
                          )
                 )
    )

    dynamic_positions = pd.DataFrame(data=positions, index=data.index, columns=['仓位'])

    return dynamic_positions


# 比较结果
original_positions = original_cal_dynamic_positions(data, aCo, aRe, momentum_slow, momentum_fast)
improved_positions = improved_cal_dynamic_positions(data, aCo, aRe, momentum_slow, momentum_fast)

print("Original Positions:")
print(original_positions)
print("\nImproved Positions:")
print(improved_positions)

# 将所有值转换为浮点数
original_positions['仓位'] = original_positions['仓位'].astype(float)
improved_positions['仓位'] = improved_positions['仓位'].astype(float)

# 验证两个结果是否相同
tolerance = 1e-6
positions_equal = np.allclose(original_positions['仓位'].values, improved_positions['仓位'].values, atol=tolerance)

assert positions_equal, "The results are not equivalent!"
print("The results are equivalent!")
