import pandas as pd

from gx_summary import SummaryClassifier, AccountSummary


# 拆分逻辑：根据空格分隔拆分证券名称和证券代码
def split_security(row):
    parts = row['交易证券'].split()
    if len(parts) == 2:
        return parts[0], parts[1]
    elif len(parts) == 1 and parts[0].isdigit() and len(parts[0]) == 6:
        return parts[0], '-'
    else:
        return '-'.join(parts[:-1]), parts[-1]


# 分析交易流水记录并输出到csv文件
def analyze_transactions():
    # 创建一个字典存储每只股票的交易记录
    stock_transactions = {}
    # 读取CSV文件
    data = pd.read_csv('stock/stock-transaction-all-data.csv', encoding='GBK')
    # 将“交收日期”列转换为日期类型
    data['交收日期'] = pd.to_datetime(data['交收日期'], format='%Y%m%d')

    # 分拆证券代码和证券名称
    # data['证券代码'] = data['交易证券'].str.extract(r'(\d{6})').fillna('-')
    # data['证券名称'] = data['交易证券'].str.replace(r'\d', '', regex=True).str.strip().fillna('-')
    # 应用拆分逻辑
    data[['证券名称', '证券代码']] = data.apply(split_security, axis=1, result_type='expand')

    # 初始化每日持股、每日资金余额数据DataFrame
    account_summary = AccountSummary()
    # 初始化每日持股数据:
    stockhold_summary = account_summary.stockhold_record
    # 初始化每日资金余额数据:
    balance_summary = account_summary.balance_record

    # 记录初始日期的持仓
    today_balance = balance_summary.copy()
    today_holdings = stockhold_summary.copy()

    # Step 1: Group by '交收日期'
    grouped_by_date = data.groupby('交收日期')

    for trade_date, date_group in grouped_by_date:
        # 设置调试用的断点
        debug_date = pd.to_datetime('20231120', format='%Y%m%d')
        if debug_date == trade_date:
            print("here is the debug point.")

        # 新的一天，将之前一天的记录更新追加到history里，并初始化新的日期
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

        # Step 2: Group by '股票代码'，不要改变原始顺序
        grouped_by_code = date_group.groupby('证券代码', sort=False)
        for stock_code, code_date_group in grouped_by_code:
            # 把某一天对于某一只股票的操作全部集合起来（用于判断转入转出到底是股份冻结，还是融资与普通账户直接的转入转出）
            summary_set = code_date_group['摘要'].unique()
            transaction_pair = False
            # 针对这些特殊的交易格式
            if any(item in summary_set for item in ['担保品划入', '股份转出', '股份转入', '担保品划出']):
                # 使用集合操作来判断‘担保品划入’和'股份转出'是否成对出现
                if {'担保品划入', '股份转出'}.issubset(summary_set):
                    transaction_pair = True
                elif {'股份转入', '担保品划出'}.issubset(summary_set):
                    transaction_pair = True
                else:
                    transaction_pair = False

            # 处理每一笔交易
            for index, row in code_date_group.iterrows():
                stock_name = row['证券名称']
                # 获取账户类型
                account_type = SummaryClassifier.get_account_type(row['货币代码'], row['融资账户'])
                summary = row['摘要']
                # 根据摘要设置成交量和成交金额、银行流入流出的正负号
                volume_flag, amount_flag, bank_flag = SummaryClassifier.get_classification(summary)
                trade_quantity = abs(row['成交数量']) * volume_flag
                trade_amount = row['发生金额'] * amount_flag
                bank_flow_amount=row['发生金额'] * bank_flag

                transaction = {'summary': summary, 'quantity': trade_quantity, 'amount': trade_amount}

                # 是否是第一次交易这个股票
                if stock_code not in stock_transactions:
                    stock_transactions[stock_code] = {'name': stock_name, 'buy': [], 'sell': [], 'profit': 0}

                # 对于用当日所有的股票买卖动作更新持仓today_holdings的股票数量及股票成本
                # 找到对应的持仓记录
                if stock_code.isdigit() and stock_name != '-':
                    if transaction_pair:  # 只有需要特殊处理的才这样处理
                        # 特别处理 ： '担保品划入'，'股份转入' 忽略。'股份转出'，'担保品划出'时直接对对方账户操作
                        if summary == '担保品划入' or summary == '股份转入':
                            pass
                        else:
                            if summary == '股份转出':
                                # 要单独计算成本
                                trans_out = get_record_from_holdings(today_holdings, account_type, stock_code)
                                cost = (abs(trade_quantity) / trans_out['持股数量'].values[0]) * trans_out['持股成本'].values[0]
                                today_holdings = insert_or_update_holdings(today_holdings, "国信融资账户", trade_date,
                                                                           stock_code,
                                                                           stock_name, -1 * cost, abs(trade_quantity))
                                today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date,
                                                                           stock_code,
                                                                           stock_name, cost, trade_quantity)
                            elif summary == '担保品划出':
                                trans_out = get_record_from_holdings(today_holdings, account_type, stock_code)
                                cost = (abs(trade_quantity) / trans_out['持股数量'].values[0]) * trans_out['持股成本'].values[0]
                                today_holdings = insert_or_update_holdings(today_holdings, "国信账户", trade_date,
                                                                           stock_code,
                                                                           stock_name, -1 * cost, abs(trade_quantity))
                                today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date,
                                                                           stock_code,
                                                                           stock_name, cost, trade_quantity)
                            else:  # 需要特殊处理的code但属于其他交易类型
                                cost = trade_amount
                                # 融资借款 和融资还款这种只有发生金额没有成交价格的在持股成本计算时要忽略
                                if summary == '融资借款' or summary == '融资还款':
                                    cost = 0
                                today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date,
                                                                           stock_code,
                                                                           stock_name, cost, trade_quantity)
                    else:  # 不需要特殊处理的
                        cost = trade_amount
                        # 融资借款 和融资还款这种只有发生金额没有成交价格的在持股成本计算时要忽略
                        if summary == '融资借款' or summary == '融资还款':
                            cost = 0
                        today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date,
                                                                   stock_code,
                                                                   stock_name, cost, trade_quantity)

                if volume_flag == 1:
                    stock_transactions[stock_code]['buy'].append(transaction)
                elif volume_flag == -1:
                    stock_transactions[stock_code]['sell'].append(transaction)

                stock_transactions[stock_code]['profit'] += trade_amount

                # 用最新的trade_amount加上该账户的最近一个交易日的账户余额，追加到balance_summary
                balance_index=today_balance[today_balance['账户类型'] == account_type].index
                today_balance.loc[balance_index, '资金余额'] += trade_amount
                today_balance.loc[balance_index, '累计净转入资金'] += bank_flow_amount
                recorded_balance = row['资金余额']
                today_balance.loc[balance_index, '记录账户余额'] = recorded_balance
            # end loop : for index, row in code_date_group:
        # end loop : for stock_code, code_date_group in grouped_by_code:

        # 每个交易日结束，用最后的recorded_balance比较更新数据
        today_balance['校验差异'] = today_balance['资金余额'] - today_balance['记录账户余额']
        # 将差异小于0.01的值设置为0
        today_balance.loc[abs(today_balance['校验差异']) < 0.01, '校验差异'] = 0
    # end loop : for trade_date, date_group in grouped_by_date
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
    writer.close()


def get_record_from_holdings(today_holdings, account_type, stock_code):
    stock_holding_index = today_holdings[
        (today_holdings['账户类型'] == account_type) & (today_holdings['证券代码'] == stock_code)].index
    # 如果该股票有持仓记录
    if not stock_holding_index.empty:
        return today_holdings.loc[stock_holding_index]
    else:
        print("转入转出错误：", account_type, stock_code)
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
