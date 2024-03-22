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
    # 创建一个字典存储每只股票的交易记录
    stock_transactions = {}
    # 读取CSV文件
    data = pd.read_csv('stock-transaction-data200705-2023.csv', encoding='GBK')
    # 将“交收日期”列转换为日期类型
    data['交收日期'] = pd.to_datetime(data['交收日期'], format='%Y%m%d')
    # 获取校验数据
    verification_results = get_verification_data(data)

    # 初始化每日持股、每日资金余额数据DataFrame
    account_summary = AccountSummary()
    # 初始化每日持股数据:
    stockhold_summary = account_summary.stockhold_record
    # 初始化每日资金余额数据:
    balance_summary = account_summary.balance_record

    # 记录当天的持仓
    today_balance = balance_summary.copy()
    today_holdings = stockhold_summary.copy()

    # 用于判断新的trade_date要不要插入到history里
    last_trade_date = pd.to_datetime('20070501', format='%Y%m%d')

    # 处理每一行数据
    for index, row in data.iterrows():
        stock_code = row['证券代码']
        stock_name = row['证券名称']
        trade_date = row['交收日期']
        currency = row['货币代码']
        # 获取账户类型
        account_type = SummaryClassifier.get_account_type(row['货币代码'], row['融资账户'])

        # 新的一天，将之前一天的记录更新追加到history里，并初始化新的日期
        if trade_date != last_trade_date:
            last_trade_date = trade_date
            # 将上一交易日的记录加入历史记录df中
            account_summary.add_to_history(today_balance, today_holdings)
            # copy一份作为新的交易日的空白记录
            today_holdings = today_holdings.copy()
            today_balance = today_balance.copy()
            # Check if the stock quantity is zero after the trade
            zero_quantity_index = today_holdings[today_holdings['持股数量'] == 0].index
            if not zero_quantity_index.empty:
                # 将实现盈亏的数据加入到历史记录中
                account_summary.add_to_stock_profit_history(today_holdings.loc[zero_quantity_index])
                # Remove records for stocks with zero quantity
                today_holdings = today_holdings.drop(zero_quantity_index)
            # 新交易日的日期设定
            today_holdings['交收日期'] = trade_date
            today_balance['交收日期'] = trade_date

        if stock_code:
            if stock_code not in stock_transactions:
                stock_transactions[stock_code] = {'name': stock_name, 'buy': [], 'sell': [], 'profit': 0}

            summary = row['摘要']
            volume_flag, amount_flag = SummaryClassifier.get_classification(summary)
            trade_amount = row['发生金额'] * amount_flag
            trade_quantity = abs(row['成交数量']) * volume_flag

            transaction = {'summary': summary, 'quantity': trade_quantity, 'amount': trade_amount}

            # 对于用当日所有的股票买卖动作更新持仓today_holdings
            # 找到对应的持仓记录
            if stock_code.isdigit() :
                # 特别处理 ： '担保品划入'，'股份转入' 忽略。'股份转出'，'担保品划出'时直接对对方账户操作
                if summary == '担保品划入' or summary == '股份转入':
                    pass
                else:
                    if summary == '股份转出':
                        # 要单独计算成本
                        trans_out = get_record_from_holdings(today_holdings, account_type, stock_code)
                        cost = (abs(trade_quantity) / trans_out['持股数量'].values[0]) * trans_out['持股成本'].values[0]
                        today_holdings = insert_or_update_holdings(today_holdings, "国信融资账户", trade_date, stock_code,
                                                                   stock_name, -1*cost, abs(trade_quantity))
                        today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date, stock_code,
                                                               stock_name, cost, trade_quantity)
                    elif summary == '担保品划出':
                        trans_out = get_record_from_holdings(today_holdings, account_type, stock_code)
                        cost = (abs(trade_quantity) / trans_out['持股数量'].values[0]) * trans_out['持股成本'].values[0]
                        today_holdings = insert_or_update_holdings(today_holdings, "国信账户", trade_date, stock_code,
                                                                   stock_name, -1*cost, abs(trade_quantity))
                        today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date, stock_code,
                                                               stock_name, cost, trade_quantity)
                    else:
                        today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date, stock_code,
                                                               stock_name, trade_amount, trade_quantity)

            if volume_flag == 1:
                stock_transactions[stock_code]['buy'].append(transaction)
            elif volume_flag == -1:
                stock_transactions[stock_code]['sell'].append(transaction)

            stock_transactions[stock_code]['profit'] += trade_amount

            # 用最新的trade_amount加上该账户的最近一个交易日的账户余额，追加到balance_summary
            today_balance.loc[today_balance['账户类型'] == account_type, '资金余额'] += trade_amount
            calculated_balance = today_balance.loc[today_balance['账户类型'] == account_type, '资金余额'].values[0]

            # 校验特定交易日的资金余额
            verification_results = verify_account_balance(trade_date, currency, calculated_balance,
                                                          verification_results)
    # 处理最后一天的数据
    account_summary.add_to_history(today_balance, today_holdings)

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

    # 输出每日持仓结果
    account_summary.save_account_history()

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


def get_record_from_holdings(today_holdings, account_type, stock_code):
    stock_holding_index = today_holdings[
        (today_holdings['账户类型'] == account_type) & (today_holdings['证券代码'] == stock_code)].index
    # 如果该股票有持仓记录
    if not stock_holding_index.empty:
        return today_holdings.loc[stock_holding_index]
    else:
        print("转入转出错误：",account_type,stock_code)
        print(today_holdings)
        return None


def insert_or_update_holdings(today_holdings, account_type, trade_date, stock_code, stock_name, trade_amount,
                              trade_quantity):
    stock_holding_index = today_holdings[
        (today_holdings['账户类型'] == account_type) & (today_holdings['证券代码'] == stock_code)].index
    # 如果该股票有持仓记录
    if not stock_holding_index.empty:
        today_holdings.loc[stock_holding_index, '持股数量'] += trade_quantity
        today_holdings.loc[stock_holding_index, '持股成本'] -= trade_amount
    else:
        one_holding = pd.DataFrame([{
            '交收日期': pd.to_datetime(trade_date, format='%Y%m%d'),
            '账户类型': account_type,
            '证券代码': stock_code,
            '证券名称': stock_name,
            '持股数量': trade_quantity,
            '持股成本': trade_amount * -1
        }])
        today_holdings = pd.concat([today_holdings, one_holding], ignore_index=True)
    return today_holdings


if __name__ == "__main__":
    analyze_transactions()
