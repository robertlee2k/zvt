import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import ParameterGrid
from market_data_helper import MarketDataHelper
from joblib import Parallel, delayed


class RSRSStrategy:
    def __init__(self, index_code, start_date, end_date, n_jobs=-1):
        self.index_code = index_code
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.price_df = self._get_data()
        self.optimal_params = {}
        self.skipped_months = []
        self.n_jobs = n_jobs

        self._prepare_warmup_data()

    def _get_data(self):
        price_df = MarketDataHelper.query_index_data(self.index_code, self.start_date, self.end_date)
        print(f"Data loaded with shape: {price_df.shape}")
        return price_df

    def _prepare_warmup_data(self):
        # 获取所有交易日期
        df_trade_dates = MarketDataHelper.get_trade_dates()
        # 找到 start_date 最近的交易日索引
        nearest_index = df_trade_dates['trade_date'].searchsorted(self.start_date)
        self.start_date = df_trade_dates.iloc[nearest_index]['trade_date']

        # 计算 warmup_start_date
        warmup_period = 550
        warmup_index = max(0, nearest_index - warmup_period)
        self.warmup_start_date = df_trade_dates.iloc[warmup_index]['trade_date']

        # 获取 warmup 数据
        self.warmup_df = MarketDataHelper.query_index_data(self.index_code, self.warmup_start_date, self.start_date)

    def get_warmup_data(self, end_date, num_periods):
        # 获取所有交易日期
        df_trade_dates = MarketDataHelper.get_trade_dates()
        # 找到 end_date 最近的交易日索引
        nearest_end_index = df_trade_dates['trade_date'].searchsorted(end_date)
        end_date = df_trade_dates.iloc[nearest_end_index]['trade_date']

        start_idx = max(0, nearest_end_index - num_periods)
        start_date = df_trade_dates.iloc[start_idx]['trade_date']
        return self.warmup_df[start_date:end_date]

    def optimize_parameters_for_month(self, end_month, param_grid):
        monthly_df = self.price_df[(self.price_df.index >= self.start_date) & (self.price_df.index <= end_month)].copy()
        best_score = -np.inf
        best_params = None

        for params in ParameterGrid(param_grid):
            window_n = params['window_N']
            window_m = params['window_M']

            # 如果用于计算的monthly_df中warmup数据不够，从warmup_df中获取并拼接
            warmup_period_needed = window_n + window_m + 1
            if len(monthly_df) < warmup_period_needed:
                warmup_data_needed = warmup_period_needed - len(monthly_df)
                warmup_df = self.get_warmup_data(monthly_df.index.min(), warmup_data_needed)
                monthly_df = pd.concat([warmup_df, monthly_df])

            print(f"Processing month: {end_month.strftime('%Y-%m')} with window_n={window_n} and window_m={window_m}")
            print(
                f"    with monthly data: {monthly_df.shape} (min date: {monthly_df.index.min().strftime('%Y-%m-%d')}, max date: {monthly_df.index.max().strftime('%Y-%m-%d')}) ")

            beta, r_squared = self.calculate_rsrs_parameters(monthly_df, window_n)

            # 只保留train_df的部分
            monthly_df['rsrs_beta'] = beta
            monthly_df['r_squared'] = r_squared

            # 计算滚动均值和标准差
            rolling_mean = monthly_df['rsrs_beta'].rolling(window=window_m, min_periods=1).mean()
            rolling_std = monthly_df['rsrs_beta'].rolling(window=window_m, min_periods=1).std()

            monthly_df['rsrs_zscore'] = (monthly_df['rsrs_beta'] - rolling_mean) / rolling_std
            monthly_df['rsrs_zscore_r2'] = monthly_df['rsrs_zscore'] * monthly_df['r_squared']
            monthly_df['rsrs_zscore_positive'] = monthly_df['rsrs_zscore_r2'] * monthly_df['rsrs_beta']
            monthly_df['returns'] = monthly_df['close'].pct_change().shift(-1).fillna(0)

            # 评估参数
            evaluation_score = self.evaluate_params(monthly_df, end_month)
            if evaluation_score > best_score:
                best_score = evaluation_score
                best_params = (window_n, window_m)

        return end_month, best_params, best_score

    def optimize_parameters(self):
        param_grid = {
            'window_N': range(10, 31, 5),
            'window_M': range(100, 401, 50)
        }

        results = Parallel(n_jobs=self.n_jobs)(
            delayed(self.optimize_parameters_for_month)(end_month, param_grid)
            for end_month in pd.date_range(self.start_date, self.end_date, freq='MS')
        )

        for end_month, best_params, best_score in results:
            if best_params:
                self.optimal_params[end_month] = {'params': best_params, 'score': best_score}

        print("最优参数：")
        print(self.optimal_params)
        print("跳过的月份：")
        print(self.skipped_months)

    def calculate_rsrs_parameters(self, df, window_n):
        beta = np.full(df.shape[0], np.nan)
        r_squared = np.full(df.shape[0], np.nan)

        for i in range(window_n - 1, len(df)):
            y = df['high'].iloc[i - window_n + 1:i + 1].values
            X = np.c_[np.ones(window_n), df['low'].iloc[i - window_n + 1:i + 1].values]
            if np.isnan(y).any() or np.isnan(X).any():
                print(f"NaN detected in train data at window: {i}")
                continue  # 跳过包含NaN值的窗口
            model = LinearRegression()
            model.fit(X, y)
            beta[i] = model.coef_[1]
            r_squared[i] = model.score(X, y)

        return beta, r_squared

    def evaluate_params(self, df, end_month):
        eval_start_date = end_month - pd.DateOffset(months=3)  # 看最近3个月的ic表现
        eval_df = df[(df.index >= eval_start_date) & (df.index < end_month)].copy()

        if len(eval_df) == 0:
            return -np.inf

        return self.calculate_ic(eval_df['rsrs_zscore_r2'], eval_df['returns'])

    def calculate_ic(self, factor, returns):
        return factor.corr(returns)

    def calculate_rsrs(self):
        self.optimize_parameters()

        beta = np.full(self.price_df.shape[0], np.nan)
        r_squared = np.full(self.price_df.shape[0], np.nan)

        for end_month in pd.date_range(self.start_date, self.end_date, freq='MS'):
            current_month_start = end_month
            if current_month_start not in self.optimal_params:
                continue

            window_N, window_M = self.optimal_params[current_month_start]['params']
            monthly_df = self.price_df[(self.price_df.index >= self.start_date) & (self.price_df.index < end_month)].copy()

            beta, r_squared = self.calculate_rsrs_parameters(monthly_df, window_N)

            self.price_df.loc[monthly_df.index, 'rsrs_beta'] = beta[-len(monthly_df):]
            self.price_df.loc[monthly_df.index, 'r_squared'] = r_squared[-len(monthly_df):]

            rolling_mean = self.price_df['rsrs_beta'].rolling(window=window_M, min_periods=1).mean()
            rolling_std = self.price_df['rsrs_beta'].rolling(window=window_M, min_periods=1).std()
            self.price_df.loc[monthly_df.index, 'rsrs_zscore'] = (self.price_df['rsrs_beta'] - rolling_mean) / rolling_std
            self.price_df.loc[monthly_df.index, 'rsrs_zscore_r2'] = self.price_df['rsrs_zscore'] * self.price_df['r_squared']
            self.price_df.loc[monthly_df.index, 'rsrs_zscore_positive'] = self.price_df['rsrs_zscore_r2'] * self.price_df['rsrs_beta']
            self.price_df.loc[monthly_df.index, 'returns'] = self.price_df['close'].pct_change().shift(-1).fillna(0)

        self.price_df.to_csv('rsrs_results.csv')
    def get_signals(self):
        return self.price_df[['rsrs_zscore', 'rsrs_zscore_r2', 'rsrs_zscore_positive', 'returns']]


from factor_evaluator import FactorEvaluator

# 使用示例
rsrs_strategy = RSRSStrategy(index_code='sh000300', start_date='2020-01-01', end_date='2024-12-31')
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
