import pandas as pd

# 读取新股数据
new_stock_df = pd.read_pickle('stock/新股数据.pkl')

# 读取需要更新的CSV文件
missing_price_df = pd.read_csv('stock/missing_price.csv')
# 将 '证券代码' 列转换为字符串，并补充前导零至 6 位
def pad_security_code(code):
    return str(code).zfill(6)

missing_price_df['证券代码'] = missing_price_df['证券代码'].apply(pad_security_code)

# 初始化一个新的列
missing_price_df['分类'] = None
missing_price_df['价格'] = 0.0
# 确保 '证券代码' 和 '申购代码' 都是字符串类型
missing_price_df['证券代码'] = missing_price_df['证券代码'].astype(str)
new_stock_df['申购代码'] = new_stock_df['申购代码'].astype(str)

# 使用左连接（left join）并将 '证券代码' 与 '申购代码' 进行匹配
merged_df = missing_price_df.merge(new_stock_df[['申购代码', '发行价格']],
                                   left_on='证券代码', right_on='申购代码', how='left')

# 检查 '证券代码' 在 missing_price_df 中是否唯一出现
# 找出唯一出现的证券代码
unique_codes = missing_price_df['证券代码'].duplicated(keep=False)  # 保持所有行
unique_codes_dict = {code: not is_duplicated for code, is_duplicated in
                         zip(missing_price_df['证券代码'], unique_codes)}
# 设置分类和价格
merged_df['分类'] = merged_df.apply(
#    lambda row: '新股' if (not pd.isna(row['发行价格']) and unique_codes_dict.get(row['证券代码'], False)) else '',
    lambda row: '新股' if not pd.isna(row['发行价格']) else '',
    axis=1
)
merged_df['价格'] = merged_df.apply(
#    lambda row: row['发行价格'] if (not pd.isna(row['发行价格']) and unique_codes_dict.get(row['证券代码'], False)) else 0.0,
    lambda row: row['发行价格'] if not pd.isna(row['发行价格'])  else 0.0,
    axis=1
)
# 选择只保留需要的列
missing_price_df = merged_df[['日期','证券代码','证券名称', '分类', '价格']]

# 输出结果或保存到新的CSV文件
print(missing_price_df)
missing_price_df.to_csv('updated_missing_price.csv', index=False)