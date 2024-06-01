import pandas as pd
import numpy as np

class TraderSimulator:
    stock_dtypes = {
        '证券代码': str,
        '证券名称': str,
        '证券数量': int,
        '库存数量': int,
        '可卖数量': int,
        '买入数量': int,
        '参考成本价': float,
        '买入均价': float,
        '参考盈亏成本价': float,
        '当前价': float,
        '最新市值': float,
        '参考浮动盈亏': float,
        '盈亏比例(%)': float,
        '在途买入': int,
        '在途卖出': int,
        '股东代码': str
    }
    zhijing_columns = '余额|可用|参考市值|资产|盈亏'
    chengjiao_columns = "成交日期|成交时间|证券代码|证券名称|买0卖1|买卖标志|委托价格|委托数量|委托编号|成交价格|成交数量|成交金额|成交编号|股东代码|状态数字标识|状态说明"

    def __init__(self, initial_cash, trading_cost=0.01, stock_code='600000'):
        self.cash_position = initial_cash
        self.shares_position = 0
        self.portfolio_value = initial_cash
        self.trading_cost = trading_cost
        self.stock_code = stock_code
        self.trades = []
        self.cash_flows = []

        self.df_ChengJiao = pd.DataFrame(columns=self.chengjiao_columns.split('|'), dtype=object)
        self.df_stock = pd.DataFrame(self.stock_dtypes, index=[0])
        self.df_zhijing = pd.DataFrame(np.array([initial_cash, initial_cash, 0, initial_cash, 0])).T
        self.df_zhijing.columns = self.zhijing_columns.split('|')
        self.portfolio_values = pd.Series()

    def _T1(self, date):
        """经过了一天， 重置stock表可卖数量"""
        if len(self.df_ChengJiao) == 0:
            return
        last_date = self.df_ChengJiao['成交日期'].iloc[-1]
        cur_date = date.date().strftime('%Y-%m-%d')
        if cur_date != last_date:
            for i in range(len(self.df_stock)):
                self.df_stock.at[i, '证券数量'] = self.df_stock.iloc[i]['库存数量']
                self.df_stock.at[i, '可卖数量'] = self.df_stock.iloc[i]['证券数量']
                if self.df_stock.iloc[i]['库存数量'] == 0:
                    self.df_stock.at[i, '买入数量'] = 0

    def _insert_chengjiao_record(self, price, num, date, is_sell):
        row = {}
        for k in self.chengjiao_columns.split('|'):
            row[k] = ''
        row['成交日期'] = date.date().strftime('%Y-%m-%d')
        row['成交时间'] = date.time().strftime('%H:%M:%S')
        row['证券代码'] = self.stock_code
        row['买0卖1'] = str(int(is_sell))
        row['买卖标志'] = is_sell and '证券卖出' or '证券买入'
        row['委托价格'] = row['成交价格'] = price
        row['委托数量'] = row['成交数量'] = num
        row['成交金额'] = float("%.2f" % (num * price))
        row['状态说明'] = '已成'
        self.df_ChengJiao.loc[len(self.df_ChengJiao)] = row
        self.df_ChengJiao.index = pd.DatetimeIndex(list(self.df_ChengJiao.index[:-1]) + [date])

    def _update_stock_chengben(self, price, num, is_sell):
        index = self.df_stock[self.df_stock['证券代码'] == self.stock_code].index[0]
        org_num = self.df_stock.iloc[index]['库存数量']
        buy_num = self.df_stock.iloc[index]['买入均价']
        buy_avg_price = self.df_stock.iloc[index]['买入均价']
        num *= is_sell and -1 or 1
        if not is_sell:
            new_price = (buy_num * buy_avg_price + price * num) / (buy_num + num)
            self.df_stock.at[index, '买入均价'] = new_price
        if org_num + num > 0:
            new_price = (org_num * buy_avg_price + price * num + price * abs(num) * self.trading_cost) / (org_num + num)
            yinkui_ratio = float('%.2f' % ((price - new_price) / new_price * 100))
        else:
            new_price = 0
            yinkui_ratio = 0
        self.df_stock.at[index, '参考成本价'] = new_price
        self.df_stock.at[index, '参考盈亏成本价'] = new_price
        self.df_stock.at[index, '盈亏比例(%)'] = yinkui_ratio
        self.df_stock.at[index, '当前价'] = price

    def _insert_zhijing(self, price, num, is_sell, date):
        m = price * num
        if is_sell:
            self.cash_position += m * (1 - self.trading_cost)
        else:
            self.cash_position -= m * self.trading_cost
            self.cash_position -= m
        row = self.df_zhijing.iloc[-1].tolist()
        row[1] = self.cash_position
        stock_quantity = self.df_stock.loc[self.df_stock['证券代码'] == self.stock_code, '库存数量'].iloc[0]
        row[2] = stock_quantity * price
        row[3] = row[2] + row[1]
        self.df_zhijing.loc[len(self.df_zhijing)] = row
        self.df_zhijing.index = pd.DatetimeIndex(list(self.df_zhijing.index[:-1]) + [date])

    def _buy(self, price, num, date):
        self._T1(date)

        money = price * num
        if self.cash_position < money:
            num = int(self.cash_position / price // 100 * 100)
        if num == 0:
            return
        is_sell = False
        self._insert_chengjiao_record(price, num, date, is_sell)
        # 初始化一条空记录
        row = dict.fromkeys(self.stock_dtypes.keys(), '')
        row['证券代码'] = self.stock_code
        for col in '证券数量|库存数量'.split('|'):
            row[col] = num
        row['可卖数量'] = 0
        row['买入数量'] = num
        for col in '买入均价|当前价|参考成本价|参考盈亏成本价'.split('|'):
            row[col] = price
        row['盈亏比例(%)'] = 0
        if (self.df_stock['证券代码'] == self.stock_code).any():
            index = self.df_stock[self.df_stock['证券代码'] == self.stock_code].index[0]
            self._update_stock_chengben(price, num, is_sell)
            self.df_stock.at[index, '库存数量'] = self.df_stock.iloc[index]['库存数量'] + num
            self.df_stock.at[index, '买入数量'] = self.df_stock.iloc[index]['买入数量'] + num
        else:
            self.df_stock.loc[len(self.df_stock)] = row
        self._insert_zhijing(price, num, is_sell, date)
        self.shares_position += num
        self.portfolio_value = self.cash_position + self.shares_position * price
        if not self.portfolio_values.empty:
            self.portfolio_values = pd.concat([self.portfolio_values, pd.Series(self.portfolio_value, index=[date])])
        else:
            self.portfolio_values = pd.Series(self.portfolio_value, index=[date])

    def _sell(self, price, num, date):
        self._T1(date)

        if (self.df_stock['证券代码'] == self.stock_code).any():
            is_sell = True
            can_sell_num = self.df_stock.loc[self.df_stock['证券代码'] == self.stock_code, '可卖数量'].iloc[0]
            num = min(num, can_sell_num)
            if num <= 0:
                return
            self._insert_chengjiao_record(price, num, date, is_sell)
            index = self.df_stock[self.df_stock['证券代码'] == self.stock_code].index[0]
            self._update_stock_chengben(price, num, is_sell)
            self.df_stock.at[index, '可卖数量'] = self.df_stock.iloc[index]['可卖数量'] - num
            self.df_stock.at[index, '库存数量'] = self.df_stock.iloc[index]['库存数量'] - num
            self._insert_zhijing(price, num, is_sell, date)

            stock_quantity = self.df_stock.loc[self.df_stock['证券代码'] == self.stock_code, '库存数量'].iloc[0]
            if stock_quantity == 0:
                self.df_stock = self.df_stock[self.df_stock['证券代码'] != self.stock_code]
        self.shares_position -= num
        self.portfolio_value = self.cash_position + self.shares_position * price
        if not self.portfolio_values.empty:
            self.portfolio_values = pd.concat([self.portfolio_values, pd.Series(self.portfolio_value, index=[date])])
        else:
            self.portfolio_values = pd.Series(self.portfolio_value, index=[date])

    def execute_trade(self, date, position, price):
        position_change = position - self.shares_position
        if position_change == 0:
            return
        elif position_change > 0:
            self._buy(price, position_change, date)
        elif position_change < 0:
            self._sell(price, abs(position_change), date)
        self.trades.append((date, (position_change, price, self.trading_cost * abs(position_change))))
        self.cash_flows.append((date, self.cash_position, self.shares_position, self.portfolio_value))

    def simulate_trading(self, trading_operations, prices):
        # 对trading_operations和prices进行日期升序排序
        trading_operations = sorted(trading_operations, key=lambda x: x[0])
        prices = prices.sort_index()

        for date, position in trading_operations:
            price = prices.loc[date]
            target_shares = int(position * self.portfolio_value / price // 100 * 100)
            self.execute_trade(date, target_shares, price)

        # 计算每日收益率
        self.daily_returns = []
        prev_cash_balance = self.portfolio_value
        prev_stock_quantity = 0
        for date in prices.index:
            try:
                last_record = self.df_zhijing.loc[date]
                cash_balance = last_record['余额']
                stock_quantity = self.df_stock.loc[self.df_stock['证券代码'] == self.stock_code, '库存数量'].iloc[0]
            except (IndexError, KeyError):
                cash_balance = prev_cash_balance
                stock_quantity = prev_stock_quantity
            portfolio_value = cash_balance + stock_quantity * prices.loc[date]
            if date == prices.index[0]:
                prev_portfolio_value = portfolio_value
            else:
                prev_portfolio_value = self.daily_returns[-1][1]
            daily_return = (portfolio_value - prev_portfolio_value) / prev_portfolio_value
            self.daily_returns.append((date, portfolio_value, daily_return))
            prev_cash_balance = cash_balance
            prev_stock_quantity = stock_quantity

        self.daily_returns = pd.DataFrame(self.daily_returns, columns=['date', 'portfolio_value', 'daily_return'])
        self.daily_returns.set_index('date', inplace=True)
        return self.daily_returns['daily_return']



