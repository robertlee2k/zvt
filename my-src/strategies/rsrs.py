import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import ParameterGrid, TimeSeriesSplit
import time
from market_data_helper import MarketDataHelper


class RSRSStrategy:
    def __init__(self, index_code, start_date, end_date, window_N=16, window_M=300, n_splits=5):
        self.index_code = index_code
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        self.window_N = window_N
        self.window_M = window_M
        self.n_splits = n_splits
        self.price_df = self._get_data()
        self.optimal_params = {}
        self.skipped_months = []

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
        # TODO 如果是当日，要再减一
        nearest_end_index = df_trade_dates['trade_date'].searchsorted(end_date)
        end_date = df_trade_dates.iloc[nearest_end_index]['trade_date']

        start_idx = max(0, nearest_end_index - num_periods)
        start_date = df_trade_dates.iloc[start_idx]['trade_date']
        return self.warmup_df[start_date:end_date]


    def optimize_parameters(self):
        param_grid = {
            'window_N': range(10, 31, 5),
            'window_M': range(100, 401, 50)
        }

        tscv = TimeSeriesSplit(n_splits=self.n_splits)

        for end_month in pd.date_range(self.start_date, self.end_date, freq='MS'):
            monthly_df = self.price_df[(self.price_df.index >= self.start_date) & (self.price_df.index <= end_month)]

            best_score = -np.inf
            best_params = None
            start_time = time.time()

            for params in ParameterGrid(param_grid):
                window_n = params['window_N']
                window_m = params['window_M']
                scores = []

                # 如果 用于n折计算的monthly_df 中 warmup 数据不够，从 warmup_df 中获取并拼接
                warmup_nsplit_needed = self.n_splits * window_n
                if len(monthly_df) < warmup_nsplit_needed:
                    warmup_data_needed = warmup_nsplit_needed - len(monthly_df)
                    warmup_df = self.get_warmup_data(monthly_df.index.min(),warmup_data_needed)
                    monthly_df = pd.concat([warmup_df, monthly_df])

                print(f"Processing month: {end_month.strftime('%Y-%m')} ")
                print(f"    with monthly data: {monthly_df.shape} (min date: {monthly_df.index.min().strftime('%Y-%m-%d')}, max date: {monthly_df.index.max().strftime('%Y-%m-%d')}) ")

                for train_idx, val_idx in tscv.split(monthly_df):
                    train_df = monthly_df.iloc[train_idx].copy()
                    val_df = monthly_df.iloc[val_idx].copy()
                    print(
                        f"    with Train data: {train_df.shape} (min date: {train_df.index.min().strftime('%Y-%m-%d')}, max date: {train_df.index.max().strftime('%Y-%m-%d')}) ")

                    print(
                        f"    with Val data: {val_df.shape} (min date: {val_df.index.min().strftime('%Y-%m-%d')}, max date: {val_df.index.max().strftime('%Y-%m-%d')}) ")

                    # 用于计算滚动均值和标准差的 warmup 数据
                    rolling_df = monthly_df[monthly_df.index < train_df.index.min()]
                    if len(rolling_df) < window_m:
                        warmup_needed = window_m - len(rolling_df)
                        rolling_warmup_df = self.get_warmup_data(train_df.index.min(),warmup_needed)
                        rolling_df = pd.concat([rolling_warmup_df, rolling_df])
                    print(
                        f"    with rolling data: {rolling_df.shape} (min date: {rolling_df.index.min().strftime('%Y-%m-%d')}, max date: {rolling_df.index.max().strftime('%Y-%m-%d')})")

                    beta = np.full(train_df.shape[0], np.nan)
                    r_squared = np.full(train_df.shape[0], np.nan)

                    for i in range(window_n - 1, len(train_df)):
                        y = train_df['high'].iloc[i - window_n + 1:i + 1].values
                        X = np.c_[np.ones(window_n), train_df['low'].iloc[i - window_n + 1:i + 1].values]
                        if np.isnan(y).any() or np.isnan(X).any():
                            print(f"NaN detected in train data at window: {i}")
                            continue  # 跳过包含NaN值的窗口
                        model = LinearRegression()
                        model.fit(X, y)
                        beta[i] = model.coef_[1]
                        r_squared[i] = model.score(X, y)

                    train_df['rsrs_beta'] = beta
                    train_df['r_squared'] = r_squared

                    # 计算滚动均值和标准差
                    full_rolling_df = pd.concat([rolling_df, train_df])
                    rolling_mean = full_rolling_df['rsrs_beta'].rolling(window=window_m, min_periods=1).mean()
                    rolling_std = full_rolling_df['rsrs_beta'].rolling(window=window_m, min_periods=1).std()

                    train_df['rsrs_zscore'] = (train_df['rsrs_beta'] - rolling_mean[-len(train_df):]) / rolling_std[
                                                                                                        -len(train_df):]
                    train_df['rsrs_zscore_r2'] = train_df['rsrs_zscore'] * train_df['r_squared']
                    train_df['rsrs_zscore_positive'] = train_df['rsrs_zscore_r2'] * train_df['rsrs_beta']

                    val_df.loc[:, 'rsrs_beta'] = np.nan
                    val_df.loc[:, 'r_squared'] = np.nan
                    for i in range(window_n - 1, len(val_df)):
                        if i < len(train_df):
                            y = val_df['high'].iloc[i - window_n + 1:i + 1].values
                            X = np.c_[np.ones(window_n), val_df['low'].iloc[i - window_n + 1:i + 1].values]
                            if np.isnan(y).any() or np.isnan(X).any():
                                print(f"NaN detected in val data at window: {i}")
                                continue  # 跳过包含NaN值的窗口
                            model = LinearRegression()
                            model.fit(X, y)
                            val_df.loc[val_df.index[i], 'rsrs_beta'] = model.coef_[1]
                            val_df.loc[val_df.index[i], 'r_squared'] = model.score(X, y)

                    # 计算验证集的滚动均值和标准差
                    full_rolling_df = pd.concat([rolling_df, train_df, val_df])
                    rolling_mean_val = full_rolling_df['rsrs_beta'].rolling(window=window_m, min_periods=1).mean()
                    rolling_std_val = full_rolling_df['rsrs_beta'].rolling(window=window_m, min_periods=1).std()
                    val_df['rsrs_zscore'] = (val_df['rsrs_beta'] - rolling_mean_val[-len(val_df):]) / rolling_std_val[-len(val_df):]
                    val_df['rsrs_zscore_r2'] = val_df['rsrs_zscore'] * val_df['r_squared']
                    val_df['rsrs_zscore_positive'] = val_df['rsrs_zscore_r2'] * val_df['rsrs_beta']
                    val_df['returns'] = val_df['close'].pct_change().shift(-1).fillna(0)

                    # 确保 val_df 中没有 NaN 值
                    if val_df[['rsrs_zscore_r2', 'returns']].isnull().values.any():
                        print(f"NaN detected in val_df for params: {params}")
                        continue

                    signals = val_df[['rsrs_zscore_r2']]
                    evaluator = FactorEvaluator(signals, val_df['returns'])
                    evaluation = evaluator.evaluate()

                    # 检查 evaluation 结果是否有 NaN 值
                    if np.isnan(evaluation['rsrs_zscore_r2']['Sharpe Ratio']):
                        print(f"NaN detected in evaluation for params: {params}")

                    scores.append(evaluation['rsrs_zscore_r2']['Sharpe Ratio'])

                avg_score = np.nanmean(scores)  # 使用np.nanmean忽略NaN值
                if avg_score > best_score:
                    best_score = avg_score
                    best_params = (window_n, window_m)

            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Month: {end_month.strftime('%Y-%m')} - Elapsed time: {elapsed_time:.2f} seconds")

            self.optimal_params[end_month] = {
                'params': best_params,
                'elapsed_time': elapsed_time
            }

        # 保存最优参数到文件
        # with open('optimal_params.json', 'w') as f:
        #     json.dump(self.optimal_params, f, indent=4)
        # # 保存被跳过的月份到文件
        # with open('skipped_months.json', 'w') as f:
        #     json.dump(self.skipped_months, f, indent=4)
        print("最优参数：")
        print(self.optimal_params)
        print("跳过的月份：")
        print(self.skipped_months)

    def calculate_rsrs(self):
        self.optimize_parameters()

        beta = np.full(self.price_df.shape[0], np.nan)
        r_squared = np.full(self.price_df.shape[0], np.nan)

        for i in range(len(self.price_df)):
            current_date = self.price_df.index[i]
            current_month_start = pd.to_datetime(f"{current_date.year}-{current_date.month}-01")
            if current_month_start not in self.optimal_params:
                continue

            window_N, window_M = self.optimal_params[current_month_start]['params']

            if i >= window_N - 1:
                y = self.price_df['high'].iloc[i - window_N + 1:i + 1].values
                X = np.c_[np.ones(window_N), self.price_df['low'].iloc[i - window_N + 1:i + 1].values]
                model = LinearRegression()
                model.fit(X, y)
                beta[i] = model.coef_[1]
                r_squared[i] = model.score(X, y)

        self.price_df['rsrs_beta'] = beta
        self.price_df['r_squared'] = r_squared

        rolling_mean = self.price_df['rsrs_beta'].rolling(window=self.window_M, min_periods=1).mean()
        rolling_std = self.price_df['rsrs_beta'].rolling(window=self.window_M, min_periods=1).std()
        self.price_df['rsrs_zscore'] = (self.price_df['rsrs_beta'] - rolling_mean) / rolling_std
        self.price_df['rsrs_zscore_r2'] = self.price_df['rsrs_zscore'] * self.price_df['r_squared']
        self.price_df['rsrs_zscore_positive'] = self.price_df['rsrs_zscore_r2'] * self.price_df['rsrs_beta']
        self.price_df['returns'] = self.price_df['close'].pct_change().shift(-1).fillna(0)

        # 保存因子计算结果到文件
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
