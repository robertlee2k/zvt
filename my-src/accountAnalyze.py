# import csv
# from collections import defaultdict
#
# # 创建默认字典存储每个组合及其对应的"摘要"值
# category_summaries = defaultdict(list)
#
# # 所有可能的组合
# all_categories = [
#     ("发生金额大于0", "成交数量大于0", "成交价格大于0"),
#     ("发生金额大于0", "成交数量大于0", "成交价格等于0"),
#     ("发生金额大于0", "成交数量等于0", "成交价格大于0"),
#     ("发生金额大于0", "成交数量等于0", "成交价格等于0"),
#     ("发生金额等于0", "成交数量大于0", "成交价格大于0"),
#     ("发生金额等于0", "成交数量大于0", "成交价格等于0"),
#     ("发生金额等于0", "成交数量等于0", "成交价格大于0"),
#     ("发生金额等于0", "成交数量等于0", "成交价格等于0"),
#     ("发生金额小于0", "成交数量大于0", "成交价格大于0"),
#     ("发生金额小于0", "成交数量大于0", "成交价格等于0"),
#     ("发生金额小于0", "成交数量等于0", "成交价格大于0"),
#     ("发生金额小于0", "成交数量等于0", "成交价格等于0")
# ]
#
# # 打开CSV文件并读取数据
# with open('stock-transaction-data200705-2023.csv', 'r') as file:
#     reader = csv.reader(file)
#     # 跳过第一行标题
#     next(reader)
#
#     for row in reader:
#         # 获取相关字段
#         summary = row[2]
#         trade_amount = float(row[3])
#         trade_quantity = float(row[4])
#         trade_price = float(row[5])
#
#         # 根据发生金额、成交数量和成交价格的大小确定类别
#         category = (
#             "发生金额大于0" if trade_amount > 0 else ("发生金额等于0" if trade_amount == 0 else "发生金额小于0"),
#             "成交数量大于0" if trade_quantity > 0 else "成交数量等于0",
#             "成交价格大于0" if trade_price > 0 else "成交价格等于0"
#         )
#
#         # 将"摘要"值添加到对应类别的列表中
#         category_summaries[category].append(summary)
#
# # 打印每个类别及其对应的"摘要"值
# for category in all_categories:
#     print(f"类别: {', '.join(category)}")
#     summaries = category_summaries[category]
#     if summaries:
#         print("摘要值:")
#         for summary in set(summaries):
#             print(f"  {summary}")
#     else:
#         print("没有数据")
#     print()

import csv

def classify_transaction(transaction):
    buy_sell = transaction[13] ##['成交数量标志']
    if buy_sell == '1':
        return 'buy'
    elif buy_sell == '2':
        return 'sell'
    else:
        return 'no_count'

def classify_fund(transaction):
    fund_change = transaction[15]#['发生金额标志']
    if fund_change == '1':
        return 'change_fund'
    else:
        return 'no_change'

def process_transaction(transaction):
    buy_sell = classify_transaction(transaction)
    fund_change = classify_fund(transaction)
    return buy_sell, fund_change

def main():
    with open('stock-transaction-data200705-2023 - 副本.csv', 'r') as file:
        reader = csv.reader(file, delimiter=',')
        unique_types = set()  # Create a set to store unique types
        for row in reader:
            transaction = row
            buy_sell, fund_change = process_transaction(transaction)
            if transaction[2] not in unique_types:
                unique_types.add(transaction[2])
                print(transaction[2],buy_sell, fund_change)  # Add the tuple of types to the set
        for types in unique_types:  # Iterate over the unique types and print them
            print(types)
if __name__ == '__main__':
    main()