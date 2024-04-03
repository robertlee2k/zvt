import time
from datetime import datetime
from datetime import timedelta
from io import StringIO

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as expect_conditions
from selenium.webdriver.support.ui import WebDriverWait

GX_WEB_URL = "https://trade2.guosen.com.cn/trade/views/index.html#/stk/zjlscx"
CHROMEDRIVER_EXE = "C:/standalone tools/webdrivers/chromedriver.exe"
CHECKPOINT_FILE = "stock/crawler_last_completed_date.txt"


class StockTransHistory:
    TRANSACTION_ALL_DATA_CSV = 'stock/stock-transaction-all-data.csv'
    DATACRAWLER_RESULT_CSV = 'stock/guoxin_datacrawler.csv'

    def __init__(self):
        pass

    @classmethod
    def load_stock_transactions(cls, start_date=None):
        # 读取CSV文件
        data = pd.read_csv(cls.TRANSACTION_ALL_DATA_CSV, encoding='GBK')
        if not pd.api.types.is_datetime64_any_dtype(data['交收日期']):
            # 将“交收日期”列转换为日期类型
            data['交收日期'] = pd.to_datetime(data['交收日期'])  # , format='%Y%m%d')
        if start_date:
            data = data[data['交收日期'] >= pd.to_datetime(start_date)]
        return data

    @classmethod
    def generate_month_ranges(cls, begin_year, end_year, end_month=None, continue_date=None):
        ranges = []
        for year in range(begin_year, end_year + 1):
            for month in range(1, 13):
                if end_month is not None:
                    if year == end_year and month >= end_month:
                        print(f"stop at {year} {month}")
                        break
                start_date = datetime(year, month, 1)
                end_date = datetime(year, month + 1, 1) - timedelta(days=1) \
                    if month < 12 else datetime(year, 12, 31)
                if continue_date is not None:  # 从断点日期之后继续开始工作
                    if start_date <= continue_date:
                        if end_date <= continue_date:  # 结束日也没到断点日，忽略
                            continue
                        else:  # 开始日在断点日之前，结束日在断点日之后
                            start_date = continue_date
                ranges.append((start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")))
        return ranges

    @classmethod
    def wait_for_user_trigger(cls):
        input("请登录好进入资金流水页面后，按回车键开始自动化程序...")

    @classmethod
    def scrape_data(cls, driver, start_date, end_date):
        try:
            driver.find_element(By.CSS_SELECTOR, '[ng-model="strdate"]').clear()
            driver.find_element(By.CSS_SELECTOR, '[ng-model="strdate"]').send_keys(start_date)
            driver.find_element(By.CSS_SELECTOR, '[ng-model="enddate"]').clear()
            driver.find_element(By.CSS_SELECTOR, '[ng-model="enddate"]').send_keys(end_date)
            driver.find_element(By.CSS_SELECTOR, '[ng-click="refresh();"]').click()
            time.sleep(5)  # 增加等待时间以确保数据加载

            # 检查是否有“暂无查询记录”的提示
            no_record_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '暂无查询记录')]")
            if no_record_elements and any(elem.is_displayed() for elem in no_record_elements):
                print(f"No records for {start_date} to {end_date}")
                return None

            # 处理“加载更多”
            while True:
                try:
                    # 等待直到“加载更多”按钮可见
                    load_more_button = WebDriverWait(driver, 10).until(
                        expect_conditions.visibility_of_element_located((By.XPATH, "//div[contains(text(),'加载更多')]"))
                    )
                    load_more_button.click()
                    time.sleep(2)  # 等待页面加载
                except TimeoutException:
                    # 如果超时，可能已经没有更多内容加载
                    break
                except NoSuchElementException:
                    # 如果找不到元素，稍后重试
                    time.sleep(2)
                    continue

            # 抓取表格数据
            table_html = driver.find_element(By.CSS_SELECTOR, 'table.table-striped').get_attribute('outerHTML')

            # 使用StringIO对象包装HTML字符串
            html_buffer = StringIO(table_html)

            # 通过read_html读取数据
            data = pd.read_html(html_buffer)[0]

            return data

        except Exception as e:
            print(f"Error during scraping for {start_date} to {end_date}: {e}")
            return None

    @classmethod
    def read_last_completed_date(cls):
        try:
            with open(CHECKPOINT_FILE, "r") as file:
                last_date = file.readline()
                return datetime.strptime(last_date, "%Y-%m-%d") if last_date else None
        except FileNotFoundError:
            return None

    @classmethod
    def write_last_completed_date(cls, date_str):
        with open(CHECKPOINT_FILE, "w") as file:
            file.write(date_str)

    @classmethod
    def crawler(cls, guoxin_data_file, from_year, end_year, end_month, last_completed_date=None):
        all_data = pd.DataFrame()
        if last_completed_date is None:  # 如果没有从外界传入，尝试从文件里读取（断点续传的情形）
            last_completed_date = cls.read_last_completed_date()
            if last_completed_date is not None:
                all_data = pd.read_csv(guoxin_data_file, encoding='GBK')

        last_completed_date += + timedelta(days=1)  # 从下一天开始
        date_ranges = cls.generate_month_ranges(from_year, end_year, end_month, last_completed_date)
        print(date_ranges)
        # 初始化 Chrome WebDriver
        # 指定Chrome驱动程序的路径
        driver_path = CHROMEDRIVER_EXE
        # 启动Chrome浏览器并指定驱动程序路径
        driver = webdriver.Chrome(service=Service(driver_path))
        driver.get(GX_WEB_URL)  # 目标网页的 URL

        cls.wait_for_user_trigger()

        # 遍历每个月份，并抓取数据
        for start_date, end_date in date_ranges:
            df = cls.scrape_data(driver, start_date, end_date)
            if df is not None:
                # 删除“交收日期”为“暂无查询记录”的行
                df = df[df['交收日期'] != '暂无查询记录']

                print(df)  # 打印部分表格 HTML 以供检查
                all_data = pd.concat([all_data, df], ignore_index=True)
                all_data.to_csv(guoxin_data_file, index=False, encoding='GBK')
                cls.write_last_completed_date(end_date)
        # 关闭 WebDriver
        driver.quit()
        # 合并所有 DataFrame 并保存为 CSV
        all_data.sort_values(by='交收日期', inplace=True)
        all_data.to_csv(guoxin_data_file, index=False, encoding='GBK')
        print(f"Data scraping completed and saved to {guoxin_data_file}")

    @classmethod
    def get_data_from_web(cls):
        data_file = cls.DATACRAWLER_RESULT_CSV

        all_transaction_df = StockTransHistory.load_stock_transactions()
        # 获取目前文件中交收日期最晚的日期
        latest_day = all_transaction_df['交收日期'].max()
        print("目前文件中交收日期最近的日子:", latest_day.strftime('%Y-%m-%d'))
        start_year = latest_day.year
        # 抓取结束日期设为今天之后的31天
        end_day = datetime.today() + timedelta(days=31)

        cls.crawler(data_file, start_year, end_day.year, end_day.month, latest_day)

    @classmethod
    def append_fetched_data_to_all(cls):
        """
        将 DATA_DRAWLER_RESULT_CSV 文件中的数据追加到 TRANSACTION_ALL_DATA_CSV 文件中。
        """
        try:
            # 读取 DATA_DRAWLER_RESULT_CSV 文件
            new_data = pd.read_csv(cls.DATACRAWLER_RESULT_CSV, encoding='GBK')
            # 将“交收日期”列转换为日期类型
            new_data['交收日期'] = pd.to_datetime(new_data['交收日期'], format='%Y%m%d')

            # 读取 TRANSACTION_ALL_DATA_CSV 文件
            all_data = cls.load_stock_transactions()

            old_data_end_date = all_data['交收日期'].max()
            new_data_begin_date = new_data['交收日期'].min()
            print(f"新数据开始于{new_data_begin_date}, 旧数据结束于{old_data_end_date}")
            # 检查新数据和所有数据是否有重叠
            if new_data_begin_date < old_data_end_date:
                # 删除重叠日期记录
                all_data = all_data[all_data['交收日期'] <= new_data_begin_date]
                print("重叠日期记录已删除，以防止重复")

            # 将新数据追加到 all_data 中
            all_data = pd.concat([all_data, new_data], ignore_index=True)

            # 保存更新后的数据到 TRANSACTION_ALL_DATA_CSV 文件
            all_data.to_csv(cls.TRANSACTION_ALL_DATA_CSV, index=False, encoding='GBK')
            print(f"Data appended to {cls.TRANSACTION_ALL_DATA_CSV}")
        except FileNotFoundError:
            print(f"Error: {cls.DATACRAWLER_RESULT_CSV} file not found.")
        except Exception as e:
            print(f"Error appending data: {e}")


if __name__ == "__main__":
    #StockTransHistory.get_data_from_web()

    StockTransHistory.append_fetched_data_to_all()

    # # 测试函数
    # for start, end in generate_month_ranges(2023, 2024, 4, datetime(2023, 11, 24)):
    #     print(f"Start Date: {start}, End Date: {end}")
