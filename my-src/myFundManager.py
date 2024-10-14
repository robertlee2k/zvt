import pandas as pd

class FundManager:
    def __init__(self, initial_fund_total_assets, initial_fund_units, analyze_summary_file, start_date):
        self.fund_total_assets = initial_fund_total_assets  # 基金总资产
        self.fund_units = initial_fund_units  # 基金总份额
        self.fund_data_history = []  # 保存每日基金的历史记录
        self.user_units = {}  # 每个用户持有的基金份额
        self.analyze_summary_file = analyze_summary_file  # 分析报告文件路径
        self.start_date = pd.to_datetime(start_date)  # 开始计算的日期
        self.daily_assets = {}  # 存储每日基金净资产
        self.user_units["波"] = initial_fund_units  # 默认份额都属于波

    def get_nav(self):
        """计算基金净值: 基金总资产 / 基金总份额"""
        if self.fund_units == 0:
            return 0
        return self.fund_total_assets / self.fund_units

    def process_transaction(self, user_id, amount, date, last_fund_assets, last_fund_units):
        """
        处理用户申购或赎回请求
        :param user_id: 用户ID
        :param amount: 交易金额（正值为申购，负值为赎回）
        :param date: 交易日期
        """
        last_fund_nav = last_fund_assets/last_fund_units
        if last_fund_nav == 0:
            raise ValueError(f"{date} 无法处理交易，上一交易日基金净值为0")

        if user_id != "临时调拨":   # 忽略内部临时调拨
            units_change = int(amount / last_fund_nav)  # 计算份额变化，取整

            if user_id not in self.user_units:
                self.user_units[user_id] = 0

            if units_change < 0 and self.user_units[user_id] + units_change < 0:
                # 用户份额不足的情况下，将差额由“波”来承担
                shortfall = abs(self.user_units[user_id] + units_change)
                print(f"{date} 用户 {user_id} 的份额 {self.user_units[user_id]} 不足，差额由 '波' 承担 {shortfall} 份 * 前日净值 {last_fund_nav}")

                # 先用该用户的剩余份额进行交易，然后由“波”承担剩余部分
                self.user_units[user_id] = 0
                self.user_units["波"] += units_change + shortfall  # “波”承担不足的份额
            else:
                self.user_units[user_id] += units_change  # 更新用户份额

            if self.user_units[user_id] == 0:
                del self.user_units[user_id]
            self.fund_units += units_change  # 更新基金总份额


    def calculate_daily_assets(self):
        """
        预计算每日基金总资产并存储
        """
        analyze_summary = pd.read_excel(self.analyze_summary_file)

        # # 读取交易 CSV 文件并转换交易日期为 datetime 类型
        # transactions = pd.read_csv(csv_file_path, encoding='GBK')
        # transactions = transactions[(transactions['用户名'] == '临时调拨') & (transactions['金额']<0)]
        # transactions['交易日期'] = pd.to_datetime(transactions['交易日期'])

        for date in analyze_summary['交收日期'].unique():
            date = pd.to_datetime(date)

            if date < self.start_date:
                continue

            daily_summary = analyze_summary[analyze_summary['交收日期'] == date]

            guoxin_accounts = daily_summary[daily_summary['账户类型'].isin(['国信账户', '国信融资账户'])]
            total_assets = guoxin_accounts['资产净值'].sum()

            self.daily_assets[date] = total_assets
            # if (date in transactions['交易日期'].unique()):
            #     for index, row in transactions[transactions['交易日期'] == date].iterrows():
            #         self.daily_assets[date] -= row['金额']
            #         print(f"{date} 回充 {row['用户名']} 金额 {row['金额']}")



    def calculate_user_balances(self, date):
        """
        计算每个用户的资产余额和基金占比，并输出基金净值
        :param date: 当前日期
        """
        nav = self.get_nav()  # 获取当日净值
        total_assets = self.fund_total_assets
        balances = []

        for user_id, units in self.user_units.items():
            user_balance = round(units * nav, 2)  # 用户资产余额，保留两位小数
            ownership = round((user_balance / total_assets) * 100, 2) if total_assets > 0 else 0  # 用户的基金占比，百分数表示且保留两位小数
            balances.append({
                'Date': date.strftime('%Y-%m-%d'),  # 输出仅有日期
                'User': user_id,
                'Units': f"{units:,}",  # 份额带有逗号分隔，不带小数
                'Balance': f"{user_balance:,.2f}",  # 资产净值带逗号分隔，保留两位小数
                'Ownership Percentage': f"{ownership}%",  # 百分比，保留两位小数
                'Fund NAV': f"{nav:,.2f}"  # 基金净值，带逗号分隔，保留两位小数
            })

        # 添加当天的基金状态到历史记录
        self.fund_data_history.append({
            'Date': date.strftime('%Y-%m-%d'),
            'Fund Total Units': f"{self.fund_units:,}",
            'Fund Total Assets': f"{self.fund_total_assets:,.2f}",
            'Fund NAV': f"{nav:,.2f}"
        })

        return balances

    def process_csv_and_generate_report(self, csv_file_path, output_file):
        """
        处理CSV中的申购赎回记录，并计算每日资产余额及基金占比
        :param csv_file_path: CSV文件路径
        :param output_file: 输出Excel文件路径
        """
        # 读取 CSV 文件并转换交易日期为 datetime 类型
        transactions = pd.read_csv(csv_file_path, encoding='GBK')
        transactions['交易日期'] = pd.to_datetime(transactions['交易日期'])

        # 预先计算每日的基金资产
        self.calculate_daily_assets()

        all_balances = pd.DataFrame()

        # 获取所有交易日并按顺序排序
        unique_dates = sorted(self.daily_assets.keys())

        # 遍历所有交易日
        for i, date in enumerate(unique_dates):
            if i > 0:
                base_date = unique_dates[i - 1]
            else:
                base_date = unique_dates[0]

            # 在变更当日数据之前，计算存储前一天的基金净值，用于计算申购赎回的净值基础
            last_fund_assets = self.daily_assets[base_date]
            last_fund_units = self.fund_units
            # 更新当天的基金资产
            self.fund_total_assets = self.daily_assets[unique_dates[i]]

            # 筛选出当天的所有交易
            daily_transactions = transactions[transactions['交易日期'] == date]

            # 合并同一用户的所有交易
            aggregated_transactions = daily_transactions.groupby('用户名')['金额'].sum().reset_index()

            # 处理合并后的每个用户的交易
            for _, transaction in aggregated_transactions.iterrows():
                user_id = transaction['用户名']
                amount = transaction['金额']
                if amount != 0:
                    self.process_transaction(user_id=user_id, amount=amount, date=date, last_fund_assets=last_fund_assets, last_fund_units=last_fund_units)

            # 计算当天每个用户的资产余额和占比
            daily_balances = self.calculate_user_balances(date)
            # 将当天的结果添加到总记录中
            all_balances = pd.concat([all_balances, pd.DataFrame(daily_balances)], ignore_index=True)

        # 将基金历史数据转换为 DataFrame
        fund_assets_report = pd.DataFrame(self.fund_data_history)

        # 使用 ExcelWriter 输出多个 sheet
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            all_balances.to_excel(writer, sheet_name='Fund Balances', index=False)
            fund_assets_report.to_excel(writer, sheet_name='基金资产净值', index=False)

        print(f"每日资产余额及基金占比已输出至 {output_file}")


# 示例用法
analyze_summary_file = 'analyze_summary.xlsx'
start_date = '2015-07-01'

fund = FundManager(initial_fund_total_assets=2203414.09, initial_fund_units=2203500,
                   analyze_summary_file=analyze_summary_file, start_date=start_date)

csv_file_path = 'stock/fund_cashflow.csv'

output_file = 'fund_balances.xlsx'

fund.process_csv_and_generate_report(csv_file_path, output_file)
