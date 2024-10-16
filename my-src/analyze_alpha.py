from stockPriceHistory import StockPriceHistory
import pandas as pd
import numpy as np

class StockAnalyzer:
    def __init__(self, stock_code, etf_code, from_date, to_date, adjust='hfq'):
        self.stock_code = stock_code
        self.etf_code = etf_code
        self.from_date = pd.to_datetime(from_date)
        self.to_date = pd.to_datetime(to_date)
        self.adjust = adjust
        self.stock_price_handler = StockPriceHistory()

    def get_exchange_rate(self):
        return StockPriceHistory.cache_exchange_rate_from_ak()

    def get_price_data(self, code):
        exchange_rate_df = self.get_exchange_rate()
        return self.stock_price_handler.query_akshare(code, self.from_date, self.to_date, exchange_rate_df, self.adjust)

    def calculate_daily_returns(self, price_df):
        daily_returns = price_df['收盘'].pct_change(fill_method=None).dropna()
        price_df['daily_return'] = daily_returns
        return price_df

    def align_dates(self, stock_returns, index_returns):
        # 确保日期列为 datetime 类型，并处理空值
        stock_returns['日期'] = pd.to_datetime(stock_returns['日期'], errors='coerce')
        index_returns['日期'] = pd.to_datetime(index_returns['日期'], errors='coerce')

        # 获取两个 DataFrame 的日期列的交集
        try:
            common_dates = stock_returns['日期'].intersection(index_returns['日期'])
        except Exception as e:
            print(f"Error finding common dates: {e}")
            return None, None

        # 如果交集为空，则返回空 DataFrame
        if len(common_dates) == 0:
            return pd.DataFrame(), pd.DataFrame()

        # 根据交集筛选数据
        stock_returns_aligned = stock_returns.set_index('日期').loc[common_dates].reset_index()
        index_returns_aligned = index_returns.set_index('日期').loc[common_dates].reset_index()

        return stock_returns_aligned, index_returns_aligned

    def calculate_risk_free_rate(self):
        return 0.02 / 252  # 每个交易日的无风险收益率

    def calculate_metrics(self, stock_returns, index_returns, window_size=30):
        alpha_beta_df = pd.DataFrame(index=stock_returns.index)
        risk_free_rate = self.calculate_risk_free_rate()

        for i in range(window_size, len(stock_returns.index)):
            rolling_stock_returns = stock_returns['daily_return'].iloc[i - window_size:i]
            rolling_index_returns = index_returns['daily_return'].iloc[i - window_size:i]

            covariance = np.cov(rolling_stock_returns, rolling_index_returns)[0][1]
            variance = np.var(rolling_index_returns)
            beta = covariance / variance
            alpha = rolling_stock_returns.mean() - (risk_free_rate + beta * (rolling_index_returns.mean() - risk_free_rate))
            sharpe_ratio = (rolling_stock_returns.mean() - risk_free_rate) / rolling_stock_returns.std()
            excess_returns = rolling_stock_returns - rolling_index_returns
            tracking_error = excess_returns.std()
            information_ratio = excess_returns.mean() / tracking_error

            # 计算上行和下行Beta
            market_mean_return = rolling_index_returns.mean()
            down_market = rolling_index_returns[rolling_index_returns < market_mean_return]
            up_market = rolling_index_returns[rolling_index_returns > market_mean_return]
            down_stock_returns = rolling_stock_returns.loc[down_market.index]
            up_stock_returns = rolling_stock_returns.loc[up_market.index]

            cov_down = np.cov(down_stock_returns, down_market)[0][1]
            var_down = np.var(down_market)
            downside_beta = cov_down / var_down

            cov_up = np.cov(up_stock_returns, up_market)[0][1]
            var_up = np.var(up_market)
            upside_beta = cov_up / var_up

            alpha_beta_df.loc[stock_returns.index[i], 'Alpha'] = alpha
            alpha_beta_df.loc[stock_returns.index[i], 'Beta'] = beta
            alpha_beta_df.loc[stock_returns.index[i], '上行Beta'] = upside_beta
            alpha_beta_df.loc[stock_returns.index[i], '下行Beta'] = downside_beta
            alpha_beta_df.loc[stock_returns.index[i], 'Sharpe Ratio'] = sharpe_ratio
            alpha_beta_df.loc[stock_returns.index[i], 'Information Ratio'] = information_ratio

            # 生成解读信息
            analysis = []
            if alpha > 0:
                analysis.append("股票在风险调整后跑赢了市场。")
            else:
                analysis.append("股票在风险调整后未跑赢市场。")

            if beta > 1:
                analysis.append("股票波动性大于市场。")
            elif beta == 1:
                analysis.append("股票波动性与市场相同。")
            else:
                analysis.append("股票波动性小于市场。")

            if sharpe_ratio > 1:
                analysis.append("股票表现优异，风险调整后的回报率较高。")
            elif sharpe_ratio > 0:
                analysis.append("股票表现尚可，回报率与风险相平衡。")
            else:
                analysis.append("股票表现不佳，风险高且回报率低。")

            if information_ratio > 0.5:
                analysis.append("股票相对于基准的超额收益稳定且优异。")
            elif information_ratio > 0:
                analysis.append("股票相对于基准的超额收益表现一般。")
            else:
                analysis.append("股票相对于基准的表现不佳，超额收益为负。")

            alpha_beta_df.loc[stock_returns.index[i], '解读'] = "\n".join(analysis)

        # 创建一个新的DataFrame，包含日期、股票收益率、ETF收益率
        result_df = pd.DataFrame({
            '日期': stock_returns['日期'],
            '股票收益率': stock_returns['daily_return'],
            '指数收益率': index_returns['daily_return']
        })

        # 合并两个DataFrame
        result_df = result_df.join(alpha_beta_df, how='inner')

        return result_df

    def save_to_excel(self, df, output_file):
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Analysis', index=False)
            workbook = writer.book
            worksheet = writer.sheets['Analysis']
            worksheet.set_column('J:J', 50)
            wrap_format = workbook.add_format({'text_wrap': True})
            worksheet.set_column('J:J', 50, wrap_format)
        print(f"分析结果已保存到 {output_file}")

def main():
    stock_code = '03690'
    index_code = 'HSTECH'
    from_date = pd.to_datetime('20240101')
    to_date = pd.to_datetime('20241231')

    analyzer = StockAnalyzer(stock_code, index_code, from_date, to_date)
    stock_price_df = analyzer.get_price_data(stock_code)
    index_price_df = analyzer.get_price_data(index_code)
    stock_returns = analyzer.calculate_daily_returns(stock_price_df)
    index_returns = analyzer.calculate_daily_returns(index_price_df)
    stock_returns, index_returns = analyzer.align_dates(stock_returns, index_returns)
    alpha_beta_df = analyzer.calculate_metrics(stock_returns, index_returns)
    output_file = "alpha_beta_analysis.xlsx"
    analyzer.save_to_excel(alpha_beta_df, output_file)

if __name__ == '__main__':
    main()
