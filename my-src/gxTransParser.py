import pandas as pd

from gxTransData import SummaryClassifier, AccountSummary
from gxTransHistory import StockTransHistory


# 拆分逻辑：根据空格分隔拆分证券名称和证券代码
def split_security(row):
    """
    将交易证券字符串拆分为两部分

    Args:
        row (dict): 包含'交易证券'键的字典

    Returns:
        tuple: 拆分后的两部分,如果无法拆分则返回原字符串和'-'
    """
    security = row['交易证券']

    # 如果以'-'开头且后面是数字,则拆分为'-'和数字部分
    if security.startswith('-') and security[1:].isdigit():
        if len(security[1:]) < 6:
            # 将数字部分补足为6位
            num_part = security[1:].zfill(6)
        else:
            num_part = security[1:]
        return security[0], num_part

    # 否则尝试使用空格拆分
    parts = security.split()
    if len(parts) == 2:
        return parts[0], parts[1]
    # 如果只有一个部分且是数字,则拆分为数字和'-'
    elif len(parts) == 1 and parts[0].isdigit():
        return parts[0], '-'
    # 其他情况(代码里有空格的）,使用' '连接前面的部分,最后一部分单独返回
    else:
        return ' '.join(parts[:-1]), parts[-1]


# 分析交易流水记录并输出到csv文件
def analyze_transactions(start_date=None):
    # 创建一个字典存储每只股票的交易记录
    stock_transactions = {}
    # 加载指定日期开始后的交易数据，如果start_date==None 意味着全量计算
    data = get_transactions(start_date)

    # 初始化每日持股、每日资金余额数据的空DataFrame
    account_summary = AccountSummary()
    # 初始化每日持股数据, 初始化每日资金余额数据:
    init_stockhold, init_balance = account_summary.init_start_holdings(start_date)

    # 记录初始日期的持仓
    today_balance = init_balance.copy()
    today_holdings = init_stockhold.copy()

    # Step 1: Group by '交收日期'
    grouped_by_date = data.groupby('交收日期')

    for trade_date, date_group in grouped_by_date:
        # 设置调试用的断点
        debug_date = pd.to_datetime('20141127', format='%Y%m%d')
        if debug_date == trade_date:
            print("here is the debug point.")

        # copy一份作为新的交易日的空白记录，并初始化新的日期
        today_holdings = today_holdings.copy()
        today_balance = today_balance.copy()
        # 初始化 daily_recorded_balances 字典，用于保存文件里读取的每日资金余额列表
        daily_recorded_balances = {account_type: [] for account_type in today_balance['账户类型']}

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
            for index_inday, row_in_day in code_date_group.iterrows():
                stock_name = row_in_day['证券名称']
                # 获取账户类型
                account_type = SummaryClassifier.get_account_type(row_in_day['货币代码'], row_in_day['融资账户'])
                summary = row_in_day['摘要']
                # 根据摘要设置成交量和成交金额、银行流入流出的正负号
                volume_flag, amount_flag, bank_flag = SummaryClassifier.get_classification(summary)
                trade_quantity = abs(row_in_day['成交数量']) * volume_flag
                trade_amount = row_in_day['发生金额'] * amount_flag
                bank_flow_amount = row_in_day['发生金额'] * bank_flag

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
                                cost = (abs(trade_quantity) / trans_out['持股数量'].values[0]) * \
                                       trans_out['持股成本'].values[0]
                                today_holdings = insert_or_update_holdings(today_holdings, "国信融资账户", trade_date,
                                                                           stock_code,
                                                                           stock_name, -1 * cost, abs(trade_quantity))
                                today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date,
                                                                           stock_code,
                                                                           stock_name, cost, trade_quantity)
                            elif summary == '担保品划出':
                                trans_out = get_record_from_holdings(today_holdings, account_type, stock_code)
                                cost = (abs(trade_quantity) / trans_out['持股数量'].values[0]) * \
                                       trans_out['持股成本'].values[0]
                                today_holdings = insert_or_update_holdings(today_holdings, "国信账户", trade_date,
                                                                           stock_code,
                                                                           stock_name, -1 * cost, abs(trade_quantity))
                                today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date,
                                                                           stock_code,
                                                                           stock_name, cost, trade_quantity)
                            else:  # 需要特殊处理的code但属于其他交易类型
                                cost = trade_amount
                                # 融资借款 和融资还款这种只有发生金额没有成交价格的在持股成本计算时要忽略
                                if summary in (
                                        SummaryClassifier.RONGZI_CASHFLOW_SUMMARY | SummaryClassifier.FROZEN_CASHFLOW_SUMMARY):
                                    cost = 0
                                today_holdings = insert_or_update_holdings(today_holdings, account_type, trade_date,
                                                                           stock_code,
                                                                           stock_name, cost, trade_quantity)
                    else:  # 不是成对出现的交易，不需要特殊处理的
                        if summary == '股份转出' or summary == '股份转入':
                            pass  # 这个本质上相当于临时冻结股票（特殊情况的融资，或者要约收购），忽略，否则市值计算有问题
                        else:
                            cost = trade_amount
                            # 融资借款 和融资还款这种只有发生金额没有成交价格的在持股成本计算时要忽略
                            if summary in (
                                    SummaryClassifier.RONGZI_CASHFLOW_SUMMARY | SummaryClassifier.FROZEN_CASHFLOW_SUMMARY):
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
                balance_index = today_balance[today_balance['账户类型'] == account_type].index
                today_balance.loc[balance_index, '资金余额'] += trade_amount
                today_balance.loc[balance_index, '累计净转入资金'] += bank_flow_amount

                # 如果一天中有多条交易记录，因为其不保证有序，我们不知道哪一条的’资金余额‘是正确的，我们先保存下来后面再选择
                daily_recorded_balances[account_type].append(row_in_day['资金余额'])

                # 计算当天融资账户借款余额
                if summary in SummaryClassifier.RONGZI_CASHFLOW_SUMMARY:
                    today_balance.loc[balance_index, '融资借款'] += trade_amount

                # 计算当天被冻结的资金余额
                if summary in SummaryClassifier.FROZEN_CASHFLOW_SUMMARY:
                    today_balance.loc[balance_index, '冻结资金'] += trade_amount

            # end loop : for index, row in code_date_group:
        # end loop : for stock_code, code_date_group in grouped_by_code:

        # 每个交易日结束，用该日最接近的recorded_balance比较更新数据
        for index_in_day, row_in_day in today_balance.iterrows():
            account_type = row_in_day['账户类型']
            if not daily_recorded_balances[account_type]:
                continue  # 跳过空列表
            # 计算当日资金余额 减去冻结资金（因为新股我们忽略了），然后与记录的余额比较，取最接近的
            available_balance = row_in_day['资金余额']
            closest_balance = min(daily_recorded_balances[account_type], key=lambda x: abs(x - available_balance))
            today_balance.loc[index_in_day, '记录账户余额'] = closest_balance
            today_balance.loc[index_in_day, '校验差异'] = available_balance - closest_balance

        # 将差异和融资余额等计算项 小于0.01的值设置为0
        today_balance.loc[abs(today_balance['校验差异']) < 0.01, '校验差异'] = 0
        today_balance.loc[abs(today_balance['融资借款']) < 0.01, '融资借款'] = 0

        # 新的一天，将之前一天的记录更新追加到history里
        # 将上一交易日的记录加入历史记录df中
        account_summary.add_to_history(today_balance, today_holdings)
    # end loop : for trade_date, date_group in grouped_by_date

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
    account_summary.save_account_history(start_date)

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


def get_transactions(start_date):
    data = StockTransHistory.load_stock_transactions(start_date)
    # 分拆证券代码和证券名称
    data[['证券名称', '证券代码']] = data.apply(split_security, axis=1, result_type='expand')
    return data


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


# 从当前analyze_summary.xls文件最新的日子接着分析
def analyze_incrementally():
    # 从目前持仓文件的下一天开始分析
    stock_holding_records = AccountSummary.load_stockhold_from_file()
    if stock_holding_records is None:
        continue_from_date = None
    else:
        continue_from_date = stock_holding_records['交收日期'].max()
    # continue_from_date = continue_from_date + datetime.timedelta(days=1)  # 从下一天开始
    print(f"从{continue_from_date}开始继续更新股票持仓数据")
    analyze_transactions(continue_from_date)


if __name__ == "__main__":
    # analyze_incrementally()

    # analyze_transactions(start_date=pd.to_datetime('20240325', format='%Y%m%d'))
    analyze_transactions()
