import pandas as pd

# 创建一个字典存储每只股票的交易记录
stock_transactions = {}

# 读取CSV文件
data = pd.read_csv('stock-transaction-data200705-2023.csv',encoding='GBK')
# 将“交收日期”列转换为日期类型
data['交收日期'] = pd.to_datetime(data['交收日期'], format='%Y%m%d')

# 处理每一行数据
for index, row in data.iterrows():
    stock_code = row['证券代码']
    summary = row['摘要']
    trade_amount = row['发生金额']
    trade_quantity = row['成交数量']

    if stock_code:
        if stock_code not in stock_transactions:
            stock_transactions[stock_code] = {'buy': [], 'sell': [], 'profit': 0}

        transaction = {'summary': summary, 'quantity': trade_quantity, 'amount': trade_amount}
        if trade_amount > 0:
            stock_transactions[stock_code]['sell'].append(transaction)
            stock_transactions[stock_code]['profit'] += trade_amount
        else:
            stock_transactions[stock_code]['buy'].append(transaction)
            stock_transactions[stock_code]['profit'] -= trade_amount

# 创建结果列表
result = []
for stock_code, transactions in stock_transactions.items():
    buy_df = pd.DataFrame(transactions['buy'])
    sell_df = pd.DataFrame(transactions['sell'])

    buy_total = buy_df['quantity'].sum() if not buy_df.empty else 0
    sell_total = sell_df['quantity'].sum() if not sell_df.empty else 0

    buy_details = buy_df.groupby('summary')['quantity'].sum().reset_index() if not buy_df.empty else pd.DataFrame(columns=['summary', 'quantity'])
    sell_details = sell_df.groupby('summary')['quantity'].sum().reset_index() if not sell_df.empty else pd.DataFrame(columns=['summary', 'quantity'])

    result.append({
        '证券代码': stock_code,
        '买入数量': buy_total,
        '卖出数量': sell_total,
        '累计盈利': transactions['profit']
    })

    result[-1]['买入明细'] = buy_details.set_index('summary')['quantity'].to_dict()
    result[-1]['卖出明细'] = sell_details.set_index('summary')['quantity'].to_dict()

# 将结果输出到Excel文件
result_df = pd.DataFrame(result)
writer = pd.ExcelWriter('stock_transactions_summary.xlsx', engine='xlsxwriter')
result_df.to_excel(writer, sheet_name='Sheet1', index=False)

workbook = writer.book
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

def calculate_initial_holdings(data):
    # Filter out the stock transactions data for the year 2007
    #data_2007 = data[data['交收日期'].dt.year == 2007]

    # Create a DataFrame to store initial holdings
    initial_holdings = pd.DataFrame(columns=['证券代码', '持仓数量'])

    # Dictionary to store cumulative trade quantities for each stock code
    stock_quantities = {}

    # Calculate the initial holdings
    for index, row in data.iterrows():
        stock_code = row['证券代码']
        trade_amount = row['发生金额']
        trade_quantity = row['成交数量']

        if stock_code:
            if stock_code not in stock_quantities:
                stock_quantities[stock_code] = 0

            if trade_amount < 0:  # Sell transaction
                stock_quantities[stock_code] -= trade_quantity
            else:  # Buy transaction
                stock_quantities[stock_code] += trade_quantity

    # Convert the dictionary to a DataFrame
    initial_holdings = pd.DataFrame(list(stock_quantities.items()), columns=['证券代码', '持仓数量'])
    # Filter out rows where the initial holding quantity is not 0
    initial_holdings = initial_holdings[initial_holdings['持仓数量'] != 0]
    return initial_holdings

# 使用该函数来计算2007年的初始持仓
initial_holdings_2007 = calculate_initial_holdings(data)
print(initial_holdings_2007)
