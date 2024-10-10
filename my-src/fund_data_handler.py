from datetime import datetime

import akshare as ak
import pandas as pd


class FundDataHandler:
    # 定义 ETF 基金代码列表为类的常量
    ETF_FUNDS = ['159915', '159919', '510050', '510300', '510500', '513920', '513050']
    # 定义分级基金代码列表为类的常量
    GRADE_FUNDS = [
        '150019', '150152', '150153', '150172', '150181', '150182', '150187', '150194',
        '150204', '150206', '150210', '150218', '150222', '150231', '150235', '502008', '161024'
    ]

    @staticmethod
    def is_etf_fund(code):
        return code in FundDataHandler.ETF_FUNDS

    @staticmethod
    def is_grade_fund(code):
        return code in FundDataHandler.GRADE_FUNDS

    def __init__(self):
        self.fund_codes = FundDataHandler.GRADE_FUNDS.copy()
        self.result_df = pd.DataFrame()

    def refresh_local_storage(self):
        for fund_code in self.fund_codes:
            temp_df = self.get_fund_info(fund_code)
            self.result_df = pd.concat([self.result_df, temp_df], ignore_index=True)

        # 按照日期列升序排序
        self.result_df = self.result_df.sort_values(by='净值日期', ascending=True)
        # 确保收盘价列转换为浮点数
        self.result_df['单位净值'] = self.result_df['单位净值'].astype(float)

        self.result_df.to_pickle('stock/grade_fund.pkl')

    @staticmethod
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

    @staticmethod
    def format_date(date_str, input_format='%Y%m%d', output_format='%Y-%m-%d'):
        """
        将日期字符串从 input_format 转换为 output_format 格式。 因为东财的分级基金需要后者

        :param date_str: 原始日期字符串
        :param input_format: 输入日期字符串的格式，默认为 '%Y%m%d'
        :param output_format: 输出日期字符串的格式，默认为 '%Y-%m-%d'
        :return: 转换后的日期字符串
        """
        date_obj = datetime.strptime(date_str, input_format)
        formatted_date = date_obj.strftime(output_format)
        return formatted_date

    @staticmethod
    def grade_fund_hist(stock_code, start_date, end_date):
        start_date = FundDataHandler.format_date(start_date)
        end_date = FundDataHandler.format_date(end_date)
        # 从pickle文件加载已缓存的数据
        cached_df = pd.read_pickle('stock/grade_fund.pkl')

        # 过滤指定基金代码和日期范围的数据
        filtered_df = cached_df[(cached_df['基金代码'] == stock_code) &
                                (cached_df['净值日期'] >= start_date) &
                                (cached_df['净值日期'] <= end_date)]

        # 将过滤后的数据重新赋值给 cached_df 以免报警告信息
        cached_df = filtered_df
        # 重命名列以匹配需求
        cached_df.rename(columns={'净值日期': '日期', '单位净值': '收盘'}, inplace=True)

        # 返回指定列的数据
        return cached_df[['日期', '收盘']]

    @staticmethod
    def etf_fund_hist(stock_code: str, start_date: str, end_date: str):
        stock_hist_df = ak.fund_etf_fund_info_em(fund=stock_code, start_date=start_date, end_date=end_date)
        stock_hist_df.rename(columns={'净值日期': '日期', '单位净值': '收盘'}, inplace=True)
        stock_hist_df = stock_hist_df[['日期', '收盘']]
        return stock_hist_df


# 使用示例
if __name__ == "__main__":
    # handler = FundDataHandler()
    # handler.refresh_local_storage()

    # 查询示例
    stockcode = '150172'
    startdate = '20150508'
    enddate = '20150806'
    query_result = FundDataHandler.grade_fund_hist(stockcode, startdate, enddate)
    print(query_result)
