import time
from datetime import datetime, timedelta
from io import StringIO
import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service


def generate_month_ranges(start_year, end_year, end_month=None, last_finished_date=None):
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if end_month is not None:
                if year==end_year and month>=end_month:
                    print(f"stop at {year} {month}")
                    break;
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month + 1, 1) - timedelta(days=1) if month < 12 else datetime(year, 12, 31)
            if last_finished_date is not None:  # 从断点日期之后继续开始工作
                if start_date <= last_finished_date:
                    if end_date <= last_finished_date: #结束日也没到断点日，忽略
                        continue
                    else: # 开始日在断点日之前，结束日在断点日之后
                        start_date=last_finished_date
            yield start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def wait_for_user_trigger():
    input("请登录好进入资金流水页面后，按回车键开始自动化程序...")


def scrape_data(driver, start_date, end_date):
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
                    EC.visibility_of_element_located((By.XPATH, "//div[contains(text(),'加载更多')]"))
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


def read_last_completed_date():
    try:
        with open("stock/crawler_last_completed_date.txt", "r") as file:
            last_date = file.readline()
            return datetime.strptime(last_date, "%Y-%m-%d") if last_date else None
    except FileNotFoundError:
        return None


def write_last_completed_date(date_str):
    with open("stock/crawler_last_completed_date.txt", "w") as file:
        file.write(date_str)


def crawler(guoxin_data_file,from_year,end_year,end_month,last_completed_date=None):


    all_data = pd.DataFrame()
    if last_completed_date is None: #如果没有从外界传入，尝试从文件里读取（断点续传的情形）
        last_completed_date = read_last_completed_date()
        if last_completed_date is not None:
            all_data = pd.read_csv(guoxin_data_file, encoding='GBK')

    # 初始化 Chrome WebDriver
    # 指定Chrome驱动程序的路径
    driver_path = "C:/standalone tools/webdrivers/chromedriver.exe"
    # 启动Chrome浏览器并指定驱动程序路径
    driver = webdriver.Chrome(service=Service(driver_path))
    driver.get("https://trade2.guosen.com.cn/trade/views/index.html#/stk/zjlscx")  # 替换为目标网页的 URL

    wait_for_user_trigger()

    # 遍历每个月份，并抓取数据
    for start_date, end_date in generate_month_ranges(2023, 2024, end_month=4, last_finished_date=last_completed_date):
        df = scrape_data(driver, start_date, end_date)
        if df is not None:
            print(df)  # 打印部分表格 HTML 以供检查
            df['Start Date'] = start_date
            df['End Date'] = end_date
            all_data = pd.concat([all_data, df], ignore_index=True)
            all_data.to_csv(guoxin_data_file, index=False, encoding='GBK')
            write_last_completed_date(end_date)
    # 关闭 WebDriver
    driver.quit()
    # 合并所有 DataFrame 并保存为 CSV
    all_data.sort_values(by='交收日期', inplace=True)
    all_data.to_csv(guoxin_data_file, index=False, encoding='GBK')
    print(f"Data scraping completed and saved to {guoxin_data_file}")

if __name__ == "__main__":
    guoxin_data_file = 'stock/guoxin_datacrawler.csv'
    from_year=2023
    end_year=2024
    end_month=4
    last_completed_date=datetime(2023, 11, 24)
    crawler(guoxin_data_file,from_year,end_year,end_month, last_completed_date)

# # 测试函数
# for start, end in generate_month_ranges(2023, 2024, 4, datetime(2023, 11, 24)):
#     print(f"Start Date: {start}, End Date: {end}")