from stockPriceHistory import StockPriceHistory
import pandas as pd
import numpy as np


# 实例化历史数据处理类
stockPriceHandler = StockPriceHistory()

# 设置股票和 ETF 代码、时间区间
stock_code = '03690'
etf_code = '513050'
from_date = pd.to_datetime('20240101')
to_date = pd.to_datetime('20241231')

adjust = 'hfq'

# 获取港股通结算汇率
exchange_rate_df = StockPriceHistory.cache_exchange_rate_from_ak()

# 获取股票和 ETF 的价格数据
stock_price_df = stockPriceHandler.query_akshare(stock_code, from_date, to_date, exchange_rate_df, adjust)
etf_price_df = stockPriceHandler.query_akshare(etf_code, from_date, to_date, None, adjust)

# 计算日收益率
stock_returns = stock_price_df['收盘'].pct_change(fill_method=None).dropna()
etf_returns = etf_price_df['收盘'].pct_change(fill_method=None).dropna()

# 对齐日期
common_dates = stock_returns.index.intersection(etf_returns.index)
stock_returns = stock_returns.loc[common_dates]
etf_returns = etf_returns.loc[common_dates]

# 设置无风险利率（假设为年化 2%）
risk_free_rate = 0.02 / 252  # 每个交易日的无风险收益率


# 滑动窗口长度（可以设定为 30 天或其他时长）
window_size = 30

# 创建一个 DataFrame 来存储每日的 Alpha 和 Beta 以及其他指标
alpha_beta_df = pd.DataFrame(index=common_dates)

# 计算每日的 Alpha 和 Beta，并存储解读
interpretations = []  # 用来存储每个日期的解读

for i in range(window_size, len(common_dates)):
    rolling_stock_returns = stock_returns.iloc[i - window_size:i]
    rolling_etf_returns = etf_returns.iloc[i - window_size:i]

    # 计算协方差和 ETF 的方差
    covariance = np.cov(rolling_stock_returns, rolling_etf_returns)[0][1]
    variance = np.var(rolling_etf_returns)

    # 计算 Beta
    beta = covariance / variance

    # 计算 Alpha
    alpha = rolling_stock_returns.mean() - (risk_free_rate + beta * (rolling_etf_returns.mean() - risk_free_rate))

    # 计算夏普比率
    sharpe_ratio = (rolling_stock_returns.mean() - risk_free_rate) / rolling_stock_returns.std()

    # 超额收益率
    excess_returns = rolling_stock_returns - rolling_etf_returns

    # 计算信息比率
    tracking_error = excess_returns.std()
    information_ratio = excess_returns.mean() / tracking_error

    # 计算市场回报的均值
    market_mean_return = rolling_etf_returns.mean()

    # 筛选出市场下跌和上涨的回报
    down_market = rolling_etf_returns[rolling_etf_returns < market_mean_return]
    up_market = rolling_etf_returns[rolling_etf_returns > market_mean_return]

    # 筛选出相应的股票回报
    down_stock_returns = rolling_stock_returns.loc[down_market.index]
    up_stock_returns = rolling_stock_returns.loc[up_market.index]

    # 计算下行 Beta
    cov_down = np.cov(down_stock_returns, down_market)[0][1]
    var_down = np.var(down_market)
    downside_beta = cov_down / var_down

    # 计算上行 Beta
    cov_up = np.cov(up_stock_returns, up_market)[0][1]
    var_up = np.var(up_market)
    upside_beta = cov_up / var_up


    # 存储计算结果
    alpha_beta_df.loc[common_dates[i], 'Alpha'] = alpha
    alpha_beta_df.loc[common_dates[i], 'Beta'] = beta
    alpha_beta_df.loc[common_dates[i], '上行Beta'] = upside_beta
    alpha_beta_df.loc[common_dates[i], '下行Beta'] = downside_beta
    alpha_beta_df.loc[common_dates[i], 'Sharpe Ratio'] = sharpe_ratio
    alpha_beta_df.loc[common_dates[i], 'Information Ratio'] = information_ratio



    # 生成解读信息
    analysis = []

    # Alpha 分析
    if alpha > 0:
        analysis.append(f" 股票在风险调整后跑赢了市场。")
    else:
        analysis.append(f" 股票在风险调整后未跑赢市场。")

    # Beta 分析
    if beta > 1:
        analysis.append(f"股票波动性大于市场。")
    elif beta == 1:
        analysis.append(f"股票波动性与市场相同。")
    else:
        analysis.append(f"股票波动性小于市场。")

    # 夏普比率分析
    if sharpe_ratio > 1:
        analysis.append(f"股票表现优异，风险调整后的回报率较高。")
    elif sharpe_ratio > 0:
        analysis.append(f"股票表现尚可，回报率与风险相平衡。")
    else:
        analysis.append(f"股票表现不佳，风险高且回报率低。")

    # 信息比率分析
    if information_ratio > 0.5:
        analysis.append(f"股票相对于基准的超额收益稳定且优异。")
    elif information_ratio > 0:
        analysis.append(f"股票相对于基准的超额收益表现一般。")
    else:
        analysis.append(f"股票相对于基准的表现不佳，超额收益为负。")

    # 将解读合并为单条字符串
    interpretations= "\n".join(analysis)
    # 将解读信息存储到 DataFrame
    alpha_beta_df.loc[common_dates[i], '解读'] = interpretations

# 将结果保存为 Excel 文件
output_file = "alpha_beta_analysis.xlsx"

# 使用 Pandas 的 ExcelWriter 和 xlsxwriter 写入 Excel 文件，并设置格式
with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    alpha_beta_df.to_excel(writer, sheet_name='Analysis',index=False)

    # 获取工作簿和工作表对象
    workbook = writer.book
    worksheet = writer.sheets['Analysis']

    # 设置列宽和自动换行
    worksheet.set_column('H:H', 50)  # F 列为 "解读" 列，设置宽度为 50
    wrap_format = workbook.add_format({'text_wrap': True})  # 创建自动换行格式
    worksheet.set_column('H:H', 50, wrap_format)  # 应用格式到解读列


print(f"分析结果已保存到 {output_file}")
