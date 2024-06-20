import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import ParameterGrid
from tqdm import tqdm

from factor_evaluator import FactorEvaluator
from market_data_helper import MarketDataHelper


class RSRSStrategy:
    def __init__(self, index_code, start_date, end_date, n_jobs=1):
        self.index_code = index_code
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.price_df = self._get_data()
        self.n_jobs = n_jobs

        self._prepare_warmup_data()

    def _get_data(self):
        price_df = MarketDataHelper.query_index_data(self.index_code, self.start_date, self.end_date)
        self.start_date = price_df.index.min()
        self.end_date = price_df.index.max()
        print(f"Data loaded with shape: {price_df.shape}, from {self.start_date.date()} to {self.end_date.date()}")
        return price_df

    def _prepare_warmup_data(self):
        df_trade_dates = MarketDataHelper.get_trade_dates()
        nearest_index = df_trade_dates['trade_date'].searchsorted(self.start_date)
        self.start_date = df_trade_dates.iloc[nearest_index]['trade_date']

        warmup_period = 550
        warmup_index = max(0, nearest_index - warmup_period)
        self.warmup_start_date = df_trade_dates.iloc[warmup_index]['trade_date']

        self.warmup_df = MarketDataHelper.query_index_data(self.index_code, self.warmup_start_date, self.start_date)

    @staticmethod
    # 生成日期区段中的所有月初日期列表
    def get_month_starts(start_date, end_date):
        # 生成从start_date的下一个月的第一天到end_date的月的第一天的月初日期范围
        next_month_start = start_date + pd.DateOffset(days=-start_date.day + 1, months=1)
        month_starts = pd.date_range(next_month_start, end_date, freq='MS')

        # 将start_date作为列表的第一个元素
        return [start_date] + list(month_starts)

    def get_warmup_data(self, month_start, num_periods):
        df_trade_dates = MarketDataHelper.get_trade_dates()
        nearest_end_index = df_trade_dates['trade_date'].searchsorted(month_start)
        month_start = df_trade_dates.iloc[nearest_end_index]['trade_date']

        start_idx = max(0, nearest_end_index - num_periods)
        start_date = df_trade_dates.iloc[start_idx]['trade_date']
        return self.warmup_df[start_date:month_start]

    def optimize_parameters_for_month(self, month_start, param_grid):
        monthly_df = self.price_df[
            (self.price_df.index >= self.start_date) & (self.price_df.index < month_start)].copy()
        best_score = -np.inf
        best_params = None

        month_results = []

        for params in ParameterGrid(param_grid):
            window_n = params['window_N']
            window_m = params['window_M']

            monthly_df = self.add_warmup_data_if_needed(self.start_date, monthly_df, window_m, window_n)

            beta, r_squared = self.calculate_rsrs_parameters(monthly_df, window_n)
            print(
                f"finish prams {params} for month: {month_start.date()}"
                f" from {monthly_df.index.min().date()}"
                f" to {monthly_df.index.max().date()}")

            monthly_df['rsrs_beta'] = beta
            monthly_df['r_squared'] = r_squared

            rolling_mean = monthly_df['rsrs_beta'].rolling(window=window_m, min_periods=1).mean()
            rolling_std = monthly_df['rsrs_beta'].rolling(window=window_m, min_periods=1).std()

            monthly_df['rsrs_zscore'] = (monthly_df['rsrs_beta'] - rolling_mean) / rolling_std
            monthly_df['rsrs_zscore_r2'] = monthly_df['rsrs_zscore'] * monthly_df['r_squared']
            monthly_df['rsrs_zscore_positive'] = monthly_df['rsrs_zscore_r2'] * monthly_df['rsrs_beta']
            monthly_df['returns'] = monthly_df['close'].pct_change().shift(-1).fillna(0)

            evaluation_score = self.evaluate_params(monthly_df, month_start)
            month_results.append({
                'month_start': month_start.strftime('%Y-%m-%d'),
                'window_N': window_n,
                'window_M': window_m,
                'ic_score': evaluation_score,
                'is_optimal': 0
            })

            if evaluation_score > best_score:
                best_score = evaluation_score
                best_params = (window_n, window_m)

        for result in month_results:
            if result['window_N'] == best_params[0] and result['window_M'] == best_params[1]:
                result['is_optimal'] = 1

        # 返回 month_start 和 monthly_df 中第一个不是 NA 的开始数据（first_valid_index）的 DataFrame。
        first_valid_index = monthly_df['rsrs_beta'].first_valid_index()
        filtered_monthly_df = monthly_df.loc[first_valid_index:].copy()
        filtered_monthly_df['month_start'] = month_start
        filtered_monthly_df['window_N'] = window_n
        filtered_monthly_df['window_M'] = window_m
        return month_results, filtered_monthly_df

    def optimize_parameters(self):
        param_grid = {
            'window_N': range(10, 61, 5),
            'window_M': range(100, 201, 50)
        }

        results = Parallel(n_jobs=self.n_jobs)(
            delayed(self.optimize_parameters_for_month)(month_start, param_grid)
            for month_start in RSRSStrategy.get_month_starts(self.start_date, self.end_date)
        )

        all_params_list = []
        all_details_df = None
        for eval_scores, eval_details in results:
            for month_results in eval_scores:
                all_params_list.append(month_results)
            # 将每个月的详细计算结果拼接到总的 DataFrame 中
            all_details_df = pd.concat([all_details_df, eval_details])

        all_params_df = pd.DataFrame(all_params_list)
        self.save_params_to_csv(all_params_df, all_details_df)
        all_params_df['month_start'] = pd.to_datetime(all_params_df['month_start'])
        return all_params_df

    def save_params_to_csv(self, all_params_df, all_details_df):
        post_fix = f'{self.index_code}_{self.start_date.date()}-{self.end_date.date()}.csv'
        file_name = f'all_params_{post_fix}'
        all_params_df.to_csv(file_name, index=False)
        detail_file_name = f'all_details_{post_fix}'
        all_details_df.to_csv(detail_file_name, index=False)

    def load_params_from_csv(self):
        file_path = f'all_params_{self.index_code}_{self.start_date.date()}-{self.end_date.date()}.csv'
        if os.path.exists(file_path):
            params_df = pd.read_csv(file_path)
            params_df['month_start'] = pd.to_datetime(params_df['month_start'])
        else:
            params_df = pd.DataFrame()
        return params_df

    @staticmethod
    def calculate_rsrs_parameters(df, window_n):
        beta = np.full(df.shape[0], np.nan)
        r_squared = np.full(df.shape[0], np.nan)

        for i in range(window_n - 1, len(df)):
            y = df['high'].iloc[i - window_n + 1:i + 1].values
            X = np.c_[np.ones(window_n), df['low'].iloc[i - window_n + 1:i + 1].values]
            if np.isnan(y).any() or np.isnan(X).any():
                continue
            model = LinearRegression()
            model.fit(X, y)
            beta[i] = model.coef_[1]
            r_squared[i] = model.score(X, y)

        return beta, r_squared

    def evaluate_params(self, df, month_start):
        eval_start_date = month_start - pd.DateOffset(months=3)
        eval_df = df[(df.index >= eval_start_date) & (df.index < month_start)].copy()

        if len(eval_df) == 0:
            return -np.inf

        return self.calculate_ic(eval_df['rsrs_zscore_r2'], eval_df['returns'])

    @staticmethod
    def calculate_ic(factor, returns):
        return factor.corr(returns)

    def calculate_rsrs(self):
        params_df = self.load_params_from_csv()

        if params_df.empty:
            params_df = self.optimize_parameters()
        optimal_params_df = params_df[params_df['is_optimal'] == 1]

        for month_start in tqdm(RSRSStrategy.get_month_starts(self.start_date, self.end_date),
                                desc="Processing months"):
            current_month_start = pd.to_datetime(month_start)
            optimal_params = optimal_params_df[optimal_params_df['month_start'] == current_month_start]

            if optimal_params.empty:
                continue

            window_n = optimal_params['window_N'].values[0]
            window_m = optimal_params['window_M'].values[0]

            # 计算和评估最佳参数组合不同之处在于，我们需要获取这个月的完整数据，而不仅仅这个月之前的数据就行
            month_end = month_start + pd.offsets.MonthEnd(0)
            monthly_df = self.price_df[
                (self.price_df.index >= self.start_date) & (self.price_df.index <= month_end)].copy()

            # 如有需要补上warmup数据
            monthly_df = self.add_warmup_data_if_needed(self.start_date, monthly_df, window_m, window_n)

            beta, r_squared = self.calculate_rsrs_parameters(monthly_df, window_n)

            monthly_df['rsrs_beta'] = beta
            monthly_df['r_squared'] = r_squared

            rolling_mean = monthly_df['rsrs_beta'].rolling(window=window_m, min_periods=1).mean()
            rolling_std = monthly_df['rsrs_beta'].rolling(window=window_m, min_periods=1).std()

            monthly_df['rsrs_zscore'] = (monthly_df['rsrs_beta'] - rolling_mean) / rolling_std
            monthly_df['rsrs_zscore_r2'] = monthly_df['rsrs_zscore'] * monthly_df['r_squared']
            monthly_df['rsrs_zscore_positive'] = monthly_df['rsrs_zscore_r2'] * monthly_df['rsrs_beta']

            # 截取该月数据（去掉warmup的部分）
            monthly_df = monthly_df.loc[monthly_df.index >= month_start]
            rsrs_columns = ['rsrs_beta', 'r_squared', 'rsrs_zscore', 'rsrs_zscore_r2', 'rsrs_zscore_positive']
            # 遍历 monthly_df 上面计算出来的每一列，并将其追加到完整的 price_df 中
            for column in rsrs_columns:
                self.price_df.loc[monthly_df.index, column] = monthly_df[column]

        # 把次日回报率整体算出来，为后续评估ic计算准备
        self.price_df['returns'] = self.price_df['close'].pct_change().shift(-1).fillna(0)

        self.price_df.to_csv('rsrs_results.csv')

    def add_warmup_data_if_needed(self, start_date, monthly_df, window_m, window_n):
        warmup_period_needed = window_n + window_m + 1
        if len(monthly_df) < warmup_period_needed:
            warmup_data_needed = warmup_period_needed - len(monthly_df)
            if monthly_df.empty:
                min_date = start_date
            else:
                min_date = monthly_df.index.min()
            warmup_df = self.get_warmup_data(min_date, warmup_data_needed)
            monthly_df = pd.concat([warmup_df, monthly_df])
        return monthly_df

    def get_signals(self):

        # 根据RSRS择时
        rsrs_list = ['rsrs_zscore', 'rsrs_zscore_r2', 'rsrs_zscore_positive']
        rsrs_name = ['标准分RSRS', '修正标准分RSRS', '右偏标准分RSRS']
        s = 0.7  # RSRS的阈值

        # 计算择时信号:RSRS值高于s时开仓，RSRS值低于-s时清仓，RSRS值在-s和s之间时维持先前的仓位
        timing_df = pd.DataFrame()
        for i in range(len(rsrs_list)):
            rsrs = rsrs_list[i]
            timing_df[f'{rsrs_name[i]}择时'] = (self.price_df[rsrs] >= s) * 1. + (self.price_df[rsrs] <= -s) * -1.
        timing_df = timing_df.replace(0, np.nan)  # 先将0替换为NA
        timing_df = timing_df.ffill()  # 使用前值填充NA
        timing_df[timing_df < 0] = 0
        timing_df['不择时'] = 1.
        timing_df['returns'] = self.price_df['returns']
        timing_df.to_csv('signals.csv', index=True)

        return timing_df

    def analyze_param_distributions(self):
        all_params_df = self.load_params_from_csv()

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        axes[0].hist(all_params_df['window_N'], bins=range(10, 35, 5), edgecolor='black')
        axes[0].set_title('Distribution of Window N')
        axes[1].hist(all_params_df['window_M'], bins=range(100, 450, 50), edgecolor='black')
        axes[1].set_title('Distribution of Window M')
        axes[2].hist(all_params_df['ic_score'], bins=20, edgecolor='black')
        axes[2].set_title('Distribution of Scores')
        plt.tight_layout()
        plt.show()

        mean_score = all_params_df['ic_score'].mean()
        std_score = all_params_df['ic_score'].std()
        best_scores = all_params_df[all_params_df['is_optimal'] == 1]['ic_score']
        best_mean_score = best_scores.mean()

        print(f"Average Score: {mean_score:.4f}")
        print(f"Standard Deviation of Scores: {std_score:.4f}")
        print(f"Average Best Score: {best_mean_score:.4f}")

        # 置信区间
        ci_low = mean_score - 1.96 * std_score / np.sqrt(len(all_params_df))
        ci_high = mean_score + 1.96 * std_score / np.sqrt(len(all_params_df))
        print(f"95% Confidence Interval of the Mean Score: ({ci_low:.4f}, {ci_high:.4f})")

        # 检查最优得分是否在置信区间内
        if ci_low <= best_mean_score <= ci_high:
            print("The factor is robust across different parameter combinations.")
        else:
            print("The factor is not robust across different parameter combinations.")


# 使用示例
rsrs_strategy = RSRSStrategy(index_code='sh000300', start_date='2020-01-01', end_date='2024-12-31')
rsrs_strategy.calculate_rsrs()
signals = rsrs_strategy.get_signals()

# 评估ic等指标
signals_except_returns = signals.loc[:, signals.columns != 'returns']
evaluator = FactorEvaluator(signals_except_returns, signals['returns'])
evaluation = evaluator.evaluate()
interpretations = evaluator.interpret_metrics(evaluation)
# 打印结果
for key, value in interpretations.items():
    print(f"{key}:")
    for metric, interpretation in value.items():
        print(f"  {metric}: {interpretation}")

# 可视化收益率
# 计算择时后的每日收益率
timing_ret = signals_except_returns.mul(signals['returns'], axis=0).dropna()
# 计算择时后的累计收益率
cumul_ret = (1 + timing_ret.fillna(0)).cumprod() - 1.
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
# 可视化输出
cumul_ret.plot(figsize=(10, 6), title='RSRS择时')

# 分析参数分布
rsrs_strategy.analyze_param_distributions()
