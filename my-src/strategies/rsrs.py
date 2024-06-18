import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import ParameterGrid
from market_data_helper import MarketDataHelper
from joblib import Parallel, delayed
import os
import matplotlib.pyplot as plt


class RSRSStrategy:
    def __init__(self, index_code, start_date, end_date, n_jobs=1):
        self.index_code = index_code
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.price_df = self._get_data()
        self.optimal_params_df = None
        self.skipped_months = []
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

    def get_warmup_data(self, end_date, num_periods):
        df_trade_dates = MarketDataHelper.get_trade_dates()
        nearest_end_index = df_trade_dates['trade_date'].searchsorted(end_date)
        end_date = df_trade_dates.iloc[nearest_end_index]['trade_date']

        start_idx = max(0, nearest_end_index - num_periods)
        start_date = df_trade_dates.iloc[start_idx]['trade_date']
        return self.warmup_df[start_date:end_date]

    def optimize_parameters_for_month(self, month_start, param_grid):
        monthly_df = self.price_df[
            (self.price_df.index >= self.start_date) & (self.price_df.index < month_start)].copy()
        best_score = -np.inf
        best_params = None

        month_results = []

        for params in ParameterGrid(param_grid):
            window_n = params['window_N']
            window_m = params['window_M']

            warmup_period_needed = window_n + window_m + 1
            if len(monthly_df) < warmup_period_needed:
                warmup_data_needed = warmup_period_needed - len(monthly_df)
                warmup_df = self.get_warmup_data(monthly_df.index.min(), warmup_data_needed)
                monthly_df = pd.concat([warmup_df, monthly_df])

            beta, r_squared = self.calculate_rsrs_parameters(monthly_df, window_n)
            print(
                f"finish prams {params} for month: {month_start.date()} from {monthly_df.index.min().date()} to {monthly_df.index.max().date()}")

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
                'score': evaluation_score,
                'is_optimal': 0
            })

            if evaluation_score > best_score:
                best_score = evaluation_score
                best_params = (window_n, window_m)

        for result in month_results:
            if result['window_N'] == best_params[0] and result['window_M'] == best_params[1]:
                result['is_optimal'] = 1

        return month_results

    def optimize_parameters(self):
        param_grid = {
            'window_N': range(10, 31, 5),
            'window_M': range(100, 401, 50)
        }

        results = Parallel(n_jobs=self.n_jobs)(
            delayed(self.optimize_parameters_for_month)(month_start, param_grid)
            for month_start in pd.date_range(self.start_date, self.end_date, freq='MS')
        )

        all_params_list = []
        optimal_params_list = []
        for month_results in results:
            all_params_list.extend(month_results)
            for result in month_results:
                if result['is_optimal']:
                    optimal_params_list.append(result)

        self.all_params_df = pd.DataFrame(all_params_list)
        self.optimal_params_df = pd.DataFrame(optimal_params_list)
        self.save_params_to_csv()

    def save_params_to_csv(self):
        self.optimal_params_df.to_csv(f'optimal_params_{self.index_code}.csv', index=False)
        self.all_params_df.to_csv(f'all_params_{self.index_code}.csv', index=False)

    def load_optimal_params_from_csv(self):
        file_path = f'optimal_params_{self.index_code}.csv'
        if os.path.exists(file_path):
            self.optimal_params_df = pd.read_csv(file_path)
        else:
            self.optimal_params_df = pd.DataFrame(columns=['month_start', 'window_N', 'window_M', 'score'])

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
        self.load_optimal_params_from_csv()

        if self.optimal_params_df.empty:
            self.optimize_parameters()

        for month_start in pd.date_range(self.start_date, self.end_date, freq='MS'):
            current_month_start = month_start.strftime('%Y-%m-%d')
            optimal_params = self.optimal_params_df[self.optimal_params_df['month_start'] == current_month_start]

            if optimal_params.empty:
                continue

            window_N = optimal_params['window_N'].values[0]
            window_M = optimal_params['window_M'].values[0]
            monthly_df = self.price_df[
                (self.price_df.index >= self.start_date) & (self.price_df.index < month_start)].copy()

            beta, r_squared = self.calculate_rsrs_parameters(monthly_df, window_N)

            self.price_df.loc[monthly_df.index, 'rsrs_beta'] = beta[-len(monthly_df):]
            self.price_df.loc[monthly_df.index, 'r_squared'] = r_squared[-len(monthly_df):]

            rolling_mean = self.price_df['rsrs_beta'].rolling(window=window_M, min_periods=1).mean()
            rolling_std = self.price_df['rsrs_beta'].rolling(window=window_M, min_periods=1).std()
            self.price_df.loc[monthly_df.index, 'rsrs_zscore'] = (self.price_df[
                                                                      'rsrs_beta'] - rolling_mean) / rolling_std
            self.price_df.loc[monthly_df.index, 'rsrs_zscore_r2'] = self.price_df['rsrs_zscore'] * self.price_df[
                'r_squared']
            self.price_df.loc[monthly_df.index, 'rsrs_zscore_positive'] = self.price_df['rsrs_zscore_r2'] * \
                                                                          self.price_df['rsrs_beta']
            self.price_df.loc[monthly_df.index, 'returns'] = self.price_df['close'].pct_change().shift(-1).fillna(0)

        self.price_df.to_csv('rsrs_results.csv')

    def get_signals(self):
        return self.price_df[['rsrs_zscore', 'rsrs_zscore_r2', 'rsrs_zscore_positive', 'returns']]

    def analyze_param_distributions(self):
        all_params_path = f'all_params_{self.index_code}.csv'
        if not os.path.exists(all_params_path):
            print("No parameter data to analyze.")
            return

        all_params_df = pd.read_csv(all_params_path)

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        axes[0].hist(all_params_df['window_N'], bins=range(10, 35, 5), edgecolor='black')
        axes[0].set_title('Distribution of Window N')
        axes[1].hist(all_params_df['window_M'], bins=range(100, 450, 50), edgecolor='black')
        axes[1].set_title('Distribution of Window M')
        axes[2].hist(all_params_df['score'], bins=20, edgecolor='black')
        axes[2].set_title('Distribution of Scores')
        plt.tight_layout()
        plt.show()

        mean_score = all_params_df['score'].mean()
        std_score = all_params_df['score'].std()
        best_scores = all_params_df[all_params_df['is_optimal'] == 1]['score']
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


from factor_evaluator import FactorEvaluator

# 使用示例
rsrs_strategy = RSRSStrategy(index_code='sh000300', start_date='2014-01-01', end_date='2024-12-31')
rsrs_strategy.calculate_rsrs()
signals = rsrs_strategy.get_signals()

evaluator = FactorEvaluator(signals[['rsrs_zscore', 'rsrs_zscore_r2', 'rsrs_zscore_positive']], signals['returns'])
evaluation = evaluator.evaluate()
interpretations = evaluator.interpret_metrics(evaluation)

# 打印结果
for key, value in interpretations.items():
    print(f"{key}:")
    for metric, interpretation in value.items():
        print(f"  {metric}: {interpretation}")

# 分析参数分布
rsrs_strategy.analyze_param_distributions()
