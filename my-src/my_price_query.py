import pandas as pd
import akshare as ak

# 定义基金代码列表
gradefunds = ['150019', '150152', '150153', '150172', '150181', '150182', '150187', '150194',
              '150204', '150206', '150210', '150218', '150222', '150231', '150235', '502008', '161024']

# 函数用于获取基金信息并处理结果
def get_fund_info(fund_code):
    try:
        fund_graded_fund_info_em_df = ak.fund_graded_fund_info_em(fund=fund_code)
        if fund_graded_fund_info_em_df.empty:
            print(f"Error: No data found for fund {fund_code}")
            return pd.DataFrame()
        else:
            print(f"已获取 {fund_code} 交易数据：{len(fund_graded_fund_info_em_df)}")
            fund_graded_fund_info_em_df['基金代码'] = fund_code
            return fund_graded_fund_info_em_df
    except Exception as e:
        print(f"Error processing fund {fund_code}: {e}")
        return pd.DataFrame()

# 初始化一个空的DataFrame用于拼接结果
result_df = pd.DataFrame()

# 循环处理每个基金代码
for fund_code in gradefunds:
    temp_df = get_fund_info(fund_code)
    result_df = pd.concat([result_df, temp_df], ignore_index=True)

# 按照日期列升序排序
result_df = result_df.sort_values(by='净值日期', ascending=True)
result_df.to_pickle('stock/grade_fund.pkl')
print(result_df)