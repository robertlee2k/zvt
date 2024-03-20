import pandas as pd

from gx_summary import SummaryClassifier, AccountSummary



# 从交易记录中过滤出当天该账户只有一条交易的记录，用于后续资金余额的校验
def get_verification_data(data):
    # 过滤出当天仅有一条交易记录的记录
    currency_daily_counts = data.groupby(['交收日期', '货币代码']).size().reset_index(name='counts')
    single_transaction_mask = currency_daily_counts['counts'] == 1
    single_transaction_tuples = [tuple(x) for x in
                                 currency_daily_counts.loc[single_transaction_mask, ['交收日期', '货币代码']].values]
    single_transaction_records = data[data[['交收日期', '货币代码']].apply(tuple, axis=1).isin(single_transaction_tuples)]
    # 保留需要的字段并添加新字段
    verification_results = single_transaction_records[['交收日期', '货币代码', '资金余额', '融资账户']].copy()
    verification_results = verification_results.rename(columns={'货币代码': '货币', '资金余额': '文件记录余额'})
    verification_results['计算余额'] = 0
    verification_results['差异'] = 0
    return verification_results


# 校验特定交易日的资金余额并记录
def verify_account_balance(trade_date, currency, calculated_balance, verification_results):
    # 获取当天该币种的交易次数
    # 从文件中读取的资金余额
    # 找到verification_results中对应的行索引
    checkpoint_index = verification_results[
        (verification_results['交收日期'] == trade_date) & (verification_results['货币'] == currency)].index
    # 如果当天需要验证（该币种只有一笔交易），则进行验证
    if not checkpoint_index.empty:
        recorded_balance = verification_results.loc[checkpoint_index, '文件记录余额'].values[0]

        # 如果计算余额与文件记录余额不一致，记录到验证结果DataFrame中
        verification_results.loc[checkpoint_index, '计算余额'] = calculated_balance
        diff = calculated_balance - recorded_balance
        if abs(diff) < 0.001:  # 忽略特别小的
            diff = 0
        verification_results.loc[checkpoint_index, '差异'] = diff
    return verification_results


# 分析交易流水记录并输出到csv文件
def analyze_transactions():

    # 初始化每日持股、每日资金余额数据DataFrame
    account_summary = AccountSummary()
    # 初始化每日持股数据:
    stockhold_summary = account_summary.stockhold_summary
    # 初始化每日资金余额数据:
    balance_summary=account_summary.balance_summary

    # 创建一个字典存储每只股票的交易记录
    stock_transactions = {}
    # 读取CSV文件
    data = pd.read_csv('stock-transaction-data200705-2023.csv', encoding='GBK')
    # 将“交收日期”列转换为日期类型
    data['交收日期'] = pd.to_datetime(data['交收日期'], format='%Y%m%d')

    # 处理每一行数据
    for index, row in data.iterrows():
        stock_code = row['证券代码']
        stock_name = row['证券名称']
        trade_date = row['交收日期']
        currency = row['货币代码']
        # 获取账户类型
        account_type=SummaryClassifier.get_account_type(row['货币代码'],row['融资账户'])

        if stock_code:
            if stock_code not in stock_transactions:
                stock_transactions[stock_code] = {'name': stock_name, 'buy': [], 'sell': [], 'profit': 0}

            summary = row['摘要']
            volume_flag, amount_flag = SummaryClassifier.get_classification(summary)
            trade_amount = row['发生金额'] * amount_flag
            trade_quantity = abs(row['成交数量']) * volume_flag

            transaction = {'summary': summary, 'quantity': trade_quantity, 'amount': trade_amount}

            # 用当日所有的股票买卖动作更新持仓stockhold_summary，如果该股票持仓为0，则不记录
            ## TODO
            if volume_flag == 1:
                stock_transactions[stock_code]['buy'].append(transaction)
            elif volume_flag == -1:
                stock_transactions[stock_code]['sell'].append(transaction)

            stock_transactions[stock_code]['profit'] += trade_amount

            # 用最新的trade_amount加上该账户的最近一个交易日的账户余额，追加到balance_summary
            ## Todo
            last_balance=account_summary.get_closest_balance(account_type,trade_date)
            last_balance['交收日期']
            if is_margin_account:
                margin_account_balance += trade_amount
                calculated_balance = margin_account_balance
            else:
                account_balance[currency] += trade_amount
                calculated_balance = account_balance[currency]

            # 先根据成交数量标志来判断是买入还是卖出
            if volume_flag == 1:
                stock_transactions[stock_code]['buy'].append(transaction)
            elif volume_flag == -1:
                stock_transactions[stock_code]['sell'].append(transaction)
            #        else: # 如果成交数量标志位0
            # print("ignore summary:", summary)

            # trade_amount已自带正负号
            stock_transactions[stock_code]['profit'] += trade_amount

            # 校验特定交易日的资金余额
            if verification_results is None:
                verification_results = get_verification_data(data)
            verification_results = verify_account_balance(trade_date, currency, calculated_balance,
                                                          verification_results)

    # 创建结果列表
    result = []
    for stock_code, transactions in stock_transactions.items():
        buy_df = pd.DataFrame(transactions['buy'])
        sell_df = pd.DataFrame(transactions['sell'])

        buy_total = buy_df['quantity'].sum() if not buy_df.empty else 0
        sell_total = sell_df['quantity'].sum() if not sell_df.empty else 0
        # 当前持仓数量（自带正负号）
        current_holdings = buy_total + sell_total

        buy_details = buy_df.groupby('summary')['amount'].sum().reset_index() if not buy_df.empty else pd.DataFrame(
            columns=['summary', 'amount'])
        sell_details = sell_df.groupby('summary')['amount'].sum().reset_index() if not sell_df.empty else pd.DataFrame(
            columns=['summary', 'amount'])

        # 累计买入花费
        buy_amount_total = buy_df['amount'].sum() * -1 if not buy_df.empty else 0
        # 利润率
        if buy_amount_total == 0:
            profit_rate = 0
        else:
            profit_rate = transactions['profit'] / buy_amount_total

        result.append({
            '证券代码': stock_code,
            '证券名称': transactions['name'],
            '买入数量': buy_total,
            '卖出数量': sell_total,
            '当前持仓股数': current_holdings,
            '累计买入花费': buy_amount_total,
            '累计盈利': transactions['profit'],
            '整体盈利率': profit_rate
        })

        result[-1]['买入明细'] = buy_details.set_index('summary')['amount'].to_dict()
        result[-1]['卖出明细'] = sell_details.set_index('summary')['amount'].to_dict()

    # 将验证结果输出到CSV文件
    verification_results.to_csv('verification_results.csv', index=False, encoding='GBK')

    # 将交易结果输出到Excel文件
    result_df = pd.DataFrame(result)
    writer = pd.ExcelWriter('stock_transactions_summary.xlsx', engine='xlsxwriter')
    result_df.to_excel(writer, sheet_name='Sheet1', index=False)
    worksheet = writer.sheets['Sheet1']
    for idx, col in enumerate(result_df.columns):
        if col in ['买入明细', '卖出明细']:
            worksheet.set_column(idx, idx, 40)
        else:
            series = result_df[col]
            max_len = max((
                series.astype(str).map(len).max(),
                len(str(series.name))
            ))
            max_len = min(max_len, 40)
            worksheet.set_column(idx, idx, max_len)
    writer.save()


if __name__ == "__main__":
    analyze_transactions()
