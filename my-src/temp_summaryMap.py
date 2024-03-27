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
# with open('stock-transaction-all-data.csv', 'r') as file:
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

import pandas as pd

# 读取CSV文件
df = pd.read_csv('stock-all-data200705-2023-updated.csv', header=0, delimiter=',',encoding='GBK')
#
# # 定义分类函数
# def classify_transaction(buy_sell_flag):
#     if buy_sell_flag == 1:
#         return 'buy'
#     elif buy_sell_flag == -1:
#         return 'sell'
#     else:
#         return 'no_count'
#
# def classify_fund(fund_change_flag):
#     if fund_change_flag == 1:
#         return 'change_fund'
#     else:
#         return 'no_change'
#
# # 应用分类函数
# df['buy_sell'] = df['成交数量标志'].apply(classify_transaction)
# df['fund_change'] = df['发生金额标志'].apply(classify_fund)
#
# # 摘要、buy_sell和fund_change列
# summary_df = df[['摘要', 'buy_sell', 'fund_change']].copy()

# Create a dictionary mapping each summary to its classifications
summary_df = df.groupby('摘要').apply(lambda x: x.iloc[0][['成交数量标志', '发生金额标志']]).to_dict('index')
# # 去重
# summary_df.drop_duplicates(inplace=True)

# Print the dictionary in a format that can be copied as a constant
print("SUMMARY_CLASSIFICATION = {")
for summary, classifications in summary_df.items():
    print(f"    '{summary}': {classifications},")
print("}")

#
# # 分别按buy_sell和fund_change分组输出对应的摘要
# print("Grouped by buy_sell:")
# for name, group in summary_df.groupby('buy_sell'):
#     print(f"\n{name} transactions:")
#     print(group['摘要'].unique())
#
# print("\nGrouped by fund_change:")
# for name, group in summary_df.groupby('fund_change'):
#     print(f"\n{name} transactions:")
#     print(group['摘要'].unique())