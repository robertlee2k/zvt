import pandas as pd
import csv

# 创建一个字典存储每只股票的交易记录
stock_transactions = {}

# 打开CSV文件并读取数据
with open('stock-transaction-data200705-2023.csv', 'r') as file:
    reader = csv.reader(file)
    # 跳过第一行标题
    next(reader)

    for row in reader:
        # 获取相关字段
        stock_code = row[11]
        summary = row[2]
        trade_amount = float(row[3])
        trade_quantity = float(row[4])

        # 如果"交易证券"列不为空,则处理该记录
        if stock_code:
            if stock_code not in stock_transactions:
                stock_transactions[stock_code] = {'buy': [], 'sell': [], 'profit': 0}

            # 根据"发生金额"的正负判断是买入还是卖出
            transaction = {'summary': summary, 'quantity': trade_quantity, 'amount': trade_amount}
            if trade_amount > 0:
                stock_transactions[stock_code]['sell'].append(transaction)
                stock_transactions[stock_code]['profit'] += trade_amount
            else:
                stock_transactions[stock_code]['buy'].append(transaction)
                stock_transactions[stock_code]['profit'] -= trade_amount

# 创建一个列表存储结果
result = []
for stock_code, transactions in stock_transactions.items():
    buy_df = pd.DataFrame(transactions['buy'])
    sell_df = pd.DataFrame(transactions['sell'])

    # 计算买入数量总和,如果买入数据框为空,则设置为0
    buy_total = buy_df['quantity'].sum() if not buy_df.empty else 0

    # 计算卖出数量总和,如果卖出数据框为空,则设置为0
    sell_total = sell_df['quantity'].sum() if not sell_df.empty else 0

    # 按"摘要"分组计算买入明细
    buy_details = buy_df.groupby('summary')['quantity'].sum().reset_index() if not buy_df.empty else pd.DataFrame(
        columns=['summary', 'quantity'])

    # 按"摘要"分组计算卖出明细
    sell_details = sell_df.groupby('summary')['quantity'].sum().reset_index() if not sell_df.empty else pd.DataFrame(
        columns=['summary', 'quantity'])

    # 将结果添加到result列表中
    result.append({
        '证券代码': stock_code,
        '买入数量': buy_total,
        '卖出数量': sell_total,
        '累计盈利': transactions['profit']
    })

    # 将买入明细和卖出明细作为子DataFrame添加到result中
    result[-1]['买入明细'] = buy_details.set_index('summary')['quantity'].to_dict()
    result[-1]['卖出明细'] = sell_details.set_index('summary')['quantity'].to_dict()

# 将结果转换为DataFrame并输出到Excel文件
result_df = pd.DataFrame(result)
writer = pd.ExcelWriter('stock_transactions_summary.xlsx', engine='xlsxwriter')
result_df.to_excel(writer, sheet_name='Sheet1', index=False)

# 调整列宽以适应内容
workbook = writer.book
worksheet = writer.sheets['Sheet1']
for idx, col in enumerate(result_df.columns):
    if col in ['买入明细', '卖出明细']:
        # 对于字典列,设置较大的列宽
        worksheet.set_column(idx, idx, 40)
    else:
        series = result_df[col]
        max_len = max((
            series.astype(str).map(len).max(),
            len(str(series.name))
        ))
        max_len = min(max_len, 40)  # 限制最大列宽为40
        worksheet.set_column(idx, idx, max_len)

writer.save()