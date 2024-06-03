import numpy as np
import pandas as pd
import akshare as ak

# 这里我们生成一些模拟数据
DAILY = 'daily'
WEEKLY = 'weekly'
MONTHLY = 'monthly'
# 获取恒生科技指数数据
stock_code = "01024"
adjust_type = "hfq"
start_date = '20200101'
end_date = '20241231'
frequency = WEEKLY

# k线数据
hstech_his = ak.stock_hk_hist(symbol=stock_code, period=frequency, start_date=start_date,
                              end_date=end_date, adjust=adjust_type)
hstech_his.index = pd.to_datetime(hstech_his['日期'])
hstech_his["涨跌幅"] = hstech_his["涨跌幅"] / 100
data = hstech_his[['涨跌幅']]
# 重命名 '涨跌幅' 字段为 '收益率'
data.rename(columns={'涨跌幅': '收益率'}, inplace=True)

# 定义动量信号计算
def calculate_momentum(data, window):
    return data.rolling(window=window).mean()


def get_market_state(momentum_slow, momentum_fast):
    market_state = pd.DataFrame(index=momentum_slow.index)
    conditions = [
        (momentum_slow>= 0) & (momentum_fast >= 0),
        (momentum_slow < 0) & (momentum_fast < 0),
        (momentum_slow >= 0) & (momentum_fast < 0),
        (momentum_slow < 0) & (momentum_fast >= 0)
    ]
    choices = ['Bull', 'Bear', 'Correction', 'Rebound']
    market_state['市场状态'] = np.select(conditions, choices, default='Unknown')
    return market_state


# 计算慢速和快速动量信号
slow_window = 12
fast_window = 2
momentum_slow = calculate_momentum(data, slow_window)
momentum_fast = calculate_momentum(data, fast_window)

# 获取市场状态
market_state = get_market_state(momentum_slow, momentum_fast)
# 将市场状态拼接到原始数据中
data['市场状态'] = market_state
#window = 30  # 使用过去30个月的数据


# 计算归一化因子 C
def calculate_normalization_factor(returns, lookback_months):
    # 确保数据量足够进行计算
    if len(returns) < lookback_months:
        return np.nan

    # 取最近 lookback_months 的数据
    past_returns = returns.iloc[-lookback_months:]
    past_market_state = returns.iloc[-lookback_months:]['市场状态']

    # 计算频率
    freq_bu = np.sum(past_market_state == 'Bull') / lookback_months
    freq_be = np.sum(past_market_state == 'Bear') / lookback_months
    freq_bu_or_be = freq_bu + freq_be

    # 计算平均回报率
    avg_return_bu = past_returns[past_returns['市场状态'] == 'Bull']['收益率'].mean()
    avg_return_be = past_returns[past_returns['市场状态'] == 'Bear']['收益率'].mean()

    # 计算平均平方回报率
    avg_return_square_bu_or_be = (past_returns[past_returns['市场状态'].isin(['Bull', 'Bear'])]['收益率'] ** 2).mean()

    if freq_bu_or_be == 0 or avg_return_square_bu_or_be == 0:
        return np.nan
    else:
        C = (freq_bu / freq_bu_or_be) * (avg_return_bu / avg_return_square_bu_or_be) - \
            (freq_be / freq_bu_or_be) * (avg_return_be / avg_return_square_bu_or_be)
        return C


# 计算 aCo 和 aRe
def calculate_aCo_aRe(returns):
    C_series = pd.Series(index=returns.index)
    aCo_series = pd.Series(index=returns.index)
    aRe_series = pd.Series(index=returns.index)
    # 计算C用
    lookback_months = 30

    for date in returns.index:
        # 先算C
        returns_before_the_date = returns.loc[:date]
        C = calculate_normalization_factor(returns_before_the_date, lookback_months)
        C_series[date] = C

        # 再算aCo
        returns_co = returns[returns['市场状态'] == 'Correction'].loc[:date]
        avg_return_co = returns_co['收益率'].mean()
        avg_return_square_co = (returns_co['收益率'] ** 2).mean()
        a_co = 0.5 * (1 - (1 / C) * (avg_return_co / avg_return_square_co))
        aCo_series[date] = a_co

        returns_re = returns[returns['市场状态']== 'Rebound'].loc[:date]
        avg_return_re = returns_re['收益率'].mean()
        avg_return_square_re = (returns_re['收益率'] ** 2).mean()
        a_re = 0.5 * (1 - (1 / C) * (avg_return_re / avg_return_square_re))
        aRe_series[date] = a_re
    return aCo_series, aRe_series, C_series


aCo, aRe, C = calculate_aCo_aRe(data)
print(aCo,aRe,C)

# 计算动态趋势策略仓位
def calculate_dynamic_positions(data, aCo, aRe, momentum_slow, momentum_fast):
    dynamic_positions = pd.DataFrame(index=data.index, columns=['仓位'])
    for date in data.index:
        state = data.loc[date]['市场状态']
        slow_mom = momentum_slow.loc[date]['收益率']
        if slow_mom >= 0:
            slow_mom = 1
        else:
            slow_mom = -1
        fast_mom = momentum_fast.loc[date]['收益率']
        if fast_mom >= 0:
            fast_mom = 1
        else:
            fast_mom = -1
        if state == 'Bull':
            dynamic_positions.loc[date] = 1
        elif state == 'Bear':
            dynamic_positions.loc[date] = -1
        elif state == 'Correction':
            dynamic_positions.loc[date] = (1 - aCo.loc[date]) * slow_mom + aCo.loc[
                date] * fast_mom
        elif state == 'Rebound':
            dynamic_positions.loc[date] = (1 - aRe.loc[date]) * slow_mom + aRe.loc[
                date] * fast_mom
    return dynamic_positions


dynamic_positions = calculate_dynamic_positions(data, aCo, aRe, momentum_slow, momentum_fast)


# 归一化到目标波动率
def normalize_to_target_volatility(positions, returns, target_vol=0.10, window=12):
    realized_vol = returns.rolling(window=window).std() * np.sqrt(12)
    scaling_factor = target_vol / realized_vol
    normalized_positions = positions.multiply(scaling_factor, axis=0)
    return normalized_positions


# # 将仓位与回报匹配计算目标波动率
# normalized_positions = normalize_to_target_volatility(dynamic_positions, data)

print(dynamic_positions)
