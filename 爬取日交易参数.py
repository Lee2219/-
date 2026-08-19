#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大商所日交易参数爬虫
根据截图中的页面结构，直接访问日交易参数页面并提取表格数据
"""

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import pandas as pd
from pathlib import Path
import time
import json
from datetime import datetime
import re
import os
import requests


class DceDailyParamsCrawler:
    """大商所日交易参数爬虫"""

    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None
        # 输出到下载文件夹
        self.output_dir = Path("/home/liyuexuan/下载/日交易参数_输出数据")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir = Path("/home/liyuexuan/下载")
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # 品种按钮映射
        self.products = ["全部品种", "豆一", "豆二", "豆粕", "豆油", "棕榈油", "玉米",
                        "玉米淀粉", "粳米", "鸡蛋", "生猪", "纤维板", "胶合板", "原木",
                        "焦煤", "焦炭", "铁矿石", "聚乙烯", "聚氯乙烯", "聚丙烯",
                        "乙二醇", "苯乙烯", "液化石油气", "纯苯"]

    def _start_browser(self):
        """启动浏览器"""
        print("🌐 启动浏览器...")
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')

        # 设置下载目录
        prefs = {
            "download.default_directory": str(self.download_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)

        if self.headless:
            options.add_argument('--headless=new')

        self.driver = uc.Chrome(options=options, version_main=151)
        self.driver.set_page_load_timeout(60)

        # 启用性能日志来监听网络请求
        self.driver.execute_cdp_cmd('Performance.enable', {})
        self.driver.execute_cdp_cmd('Network.enable', {})

        print("   ✅ 浏览器启动成功")

    def _close_browser(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("🔒 浏览器已关闭")

    def crawl_daily_params(self, target_date=None, product="全部品种", export_excel=False):
        """
        爬取日交易参数
        :param target_date: 目标日期，格式 YYYYMMDD 或 YYYY-MM-DD，默认为当天
        :param product: 品种名称，默认"全部品种"
        :param export_excel: 是否尝试点击"导出表格"按钮
        """
        print("=" * 60)
        print("📋 大商所日交易参数爬虫")
        print(f"📅 目标日期: {target_date or '当天'}")
        print(f"📦 产品: {product}")
        print("=" * 60)

        try:
            self._start_browser()

            # 使用正确的日交易参数前端URL
            url = "http://www.dce.com.cn/frontend/dcereport/#/zh/queryDayTradPara?variety=all&tradeType=1"
            print(f"\n📍 访问日交易参数页面: {url}")
            self.driver.set_page_load_timeout(30)
            self.driver.get(url)
            time.sleep(10)

            # 检查页面是否加载成功
            page_title = self.driver.title
            current_url = self.driver.current_url
            print(f"   📄 页面标题: {page_title}")
            print(f"   🔗 当前URL: {current_url}")

            # 选择品种
            if product != "全部品种":
                print(f"\n🔍 选择品种: {product}")
                self._select_product(product)
                time.sleep(3)

            # 获取页面日期
            page_date = self._get_page_date()
            print(f"📅 页面日期: {page_date}")

            # 如果需要导出Excel，尝试点击导出按钮
            if export_excel:
                print("\n🔍 尝试点击'导出表格'按钮...")
                downloaded_file = self._click_export_button()
                if downloaded_file:
                    print(f"   ✅ 导出成功: {downloaded_file}")
                    # 读取导出的文件
                    data = self._read_exported_file(downloaded_file)
                    if data is not None:
                        self._save_data(data, product, page_date)
                        return data
                else:
                    print("   ⚠️  导出失败，将提取页面表格数据")

            # 提取表格数据
            table_data = self._extract_table_data()

            if table_data is not None and not table_data.empty:
                # 添加元数据
                table_data['爬取日期'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                table_data['查询日期'] = page_date
                table_data['品种'] = product

                # 保存数据
                self._save_data(table_data, product, page_date)

                print("\n" + "=" * 60)
                print(f"✅ 爬取完成！共 {len(table_data)} 条记录")
                print(f"📁 数据位置: {self.output_dir}")
                print("=" * 60)

                return table_data
            else:
                print("\n⚠️ 未能提取到表格数据")
                return None

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            self._close_browser()

    def _get_page_date(self):
        """获取页面显示的查询日期"""
        try:
            # 页面上显示的日期格式：查询日期：20260819
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # 查找日期模式
            date_match = re.search(r'查询日期[：:]\s*(\d{8})', page_text)
            if date_match:
                date_str = date_match.group(1)
                # 转换为 YYYY-MM-DD 格式
                return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            return datetime.now().strftime("%Y-%m-%d")
        except:
            return datetime.now().strftime("%Y-%m-%d")

    def _select_product(self, product_name):
        """选择品种按钮"""
        try:
            # 使用JavaScript查找并点击品种按钮
            result = self.driver.execute_script("""
                var targetName = arguments[0];
                var buttons = document.querySelectorAll('button, a, li, span, div');
                var found = null;

                for (var i = 0; i < buttons.length; i++) {
                    var text = buttons[i].textContent ? buttons[i].textContent.trim() : '';
                    if (text === targetName) {
                        found = buttons[i];
                        break;
                    }
                }

                if (found) {
                    found.click();
                    return true;
                }
                return false;
            """, product_name)

            if result:
                print(f"   ✅ 已点击品种按钮: {product_name}")
                return True
            else:
                print(f"   ⚠️  未找到品种按钮: {product_name}")
                return False

        except Exception as e:
            print(f"   ⚠️  选择品种失败: {e}")
            return False

    def _click_export_button(self):
        """点击导出表格按钮"""
        try:
            # 查找"导出表格"按钮
            result = self.driver.execute_script("""
                var buttons = document.querySelectorAll('button, a, span, div');
                var exportBtn = null;

                for (var i = 0; i < buttons.length; i++) {
                    var text = buttons[i].textContent ? buttons[i].textContent.trim() : '';
                    if (text === '导出表格' || text === '导出') {
                        exportBtn = buttons[i];
                        break;
                    }
                }

                if (exportBtn) {
                    exportBtn.click();
                    return true;
                }
                return false;
            """)

            if result:
                print("   📍 已点击'导出表格'按钮")
                time.sleep(5)
                # 检查下载目录
                return self._wait_for_download()
            else:
                print("   ⚠️  未找到'导出表格'按钮")
                return None

        except Exception as e:
            print(f"   ⚠️  点击导出按钮失败: {e}")
            return None

    def _wait_for_download(self):
        """等待文件下载"""
        try:
            max_wait = 20
            wait_time = 0

            while wait_time < max_wait:
                files = list(self.download_dir.glob("*"))
                valid_files = [f for f in files if not f.name.startswith('crdownload')
                              and not f.name.startswith('.')
                              and f.suffix in ['.xls', '.xlsx', '.csv']]

                if valid_files:
                    latest_file = max(valid_files, key=os.path.getmtime)
                    file_age = time.time() - os.path.getmtime(latest_file)
                    if file_age < 60:
                        return latest_file

                time.sleep(2)
                wait_time += 2

            return None

        except:
            return None

    def _read_exported_file(self, file_path):
        """读取导出的文件"""
        try:
            file_ext = file_path.suffix.lower()

            if file_ext == '.csv':
                for encoding in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312']:
                    try:
                        return pd.read_csv(file_path, encoding=encoding)
                    except:
                        continue
                try:
                    return pd.read_csv(file_path, engine='python')
                except:
                    pass

            elif file_ext in ['.xlsx', '.xls']:
                return pd.read_excel(file_path, engine='openpyxl' if file_ext == '.xlsx' else 'xlrd')

            return None

        except Exception as e:
            print(f"   ⚠️  读取文件失败: {e}")
            return None

    def _extract_table_data(self):
        """提取表格数据"""
        try:
            print("\n🔍 开始提取表格数据...")

            # 等待表格加载 - 前端应用需要更长时间
            print("   ⏳ 等待前端应用加载表格数据...")
            time.sleep(60)  # 增加等待时间到60秒

            # 尝试滚动页面并等待以触发数据加载
            print("   📜 滚动页面并等待以触发懒加载...")
            for scroll_wait in [(0.25, 5), (0.5, 5), (0.75, 5), (1.0, 10)]:
                scroll_pos, wait_time = scroll_wait
                self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_pos});")
                print(f"      滚动到 {scroll_pos*100}% 位置，等待 {wait_time} 秒...")
                time.sleep(wait_time)

            # 最后回到顶部并等待
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(10)

            # 保存页面HTML源码用于分析
            html_file = self.output_dir / "page_source.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"   💾 页面HTML源码已保存: {html_file}")

            # 查找包含合约代码的元素
            print("   🔍 查找合约代码元素...")
            contract_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'a26') or contains(text(), 'm26') or contains(text(), 'c26')]")
            print(f"   📍 找到 {len(contract_elements)} 个包含合约代码的元素")

            # 尝试查找tbody而不是table
            print("   🔍 尝试查找tbody元素...")
            tbodies = self.driver.find_elements(By.TAG_NAME, "tbody")
            print(f"   📍 找到 {len(tbodies)} 个tbody元素")

            # 尝试从网络日志中找到API请求
            print("   🔍 查找数据API请求...")
            api_data = self._find_api_requests()
            if api_data:
                print("   ✅ 找到API数据！")
                return self._process_api_data(api_data)

            # 查找所有表格
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"   📊 检测到 {len(tables)} 个表格")

            # 尝试查找tbody元素（数据可能在tbody中）
            all_tbodies = self.driver.find_elements(By.TAG_NAME, "tbody")
            print(f"   📊 检测到 {len(all_tbodies)} 个tbody元素")

            # 优先尝试从tbody提取数据
            if all_tbodies:
                print(f"   🔍 尝试从tbody提取数据...")
                for tbody_idx, tbody in enumerate(all_tbodies):
                    try:
                        tbody_data = self._extract_from_tbody(tbody)
                        if tbody_data and len(tbody_data) > 2:  # 至少要有数据行
                            print(f"   ✅ 从tbody {tbody_idx+1} 提取到 {len(tbody_data)} 行数据")
                            print(f"   📋 第一行内容: {tbody_data[0]}")

                            # 检查是否是数据表格（包含合约代码）
                            first_row_text = ' '.join(tbody_data[0])
                            if '合约' in first_row_text or (len(tbody_data) > 10 and any('a' in str(cell) or 'b' in str(cell) or 'm' in str(cell) for row in tbody_data for cell in row)):
                                print(f"   ✅ tbody {tbody_idx+1} 包含数据表格")

                                # 使用正确的列名
                                correct_columns = ['合约', '交易保证金(投机)比例', '交易保证金(投机)金额(元/手)',
                                                 '交易保证金(套保)比例', '交易保证金(套保)金额(元/手)',
                                                 '涨跌停板涨跌停板比例', '涨跌停板涨停板价位(元)', '涨跌停板跌停板价位(元)',
                                                 '持仓限额(手)限仓模式', '持仓限额(手)非期货公司会员', '持仓限额(手)客户',
                                                 '交易限额(手)品种限额', '交易限额(手)合约限额']

                                # 确保列数匹配
                                num_cols = len(tbody_data[0]) if tbody_data else len(correct_columns)
                                df = pd.DataFrame(tbody_data, columns=correct_columns[:num_cols])
                                df = self._clean_dataframe(df)
                                return df
                            else:
                                print(f"   ⏭️  tbody {tbody_idx+1} 不是数据表格，跳过")
                    except Exception as e:
                        print(f"   ⚠️  tbody {tbody_idx+1} 提取失败: {e}")
                        continue

            # 如果没有表格，打印页面结构用于调试
            if len(tables) == 0:
                print("   🔍 未检测到表格，检查页面结构...")
                page_text = self.driver.find_element(By.TAG_NAME, "body").text[:500]
                print(f"   📄 页面文本预览: {page_text}")

                # 保存HTML用于调试
                debug_html = self.output_dir.parent / f"debug_page_{int(time.time())}.html"
                with open(debug_html, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                print(f"   💾 调试HTML已保存: {debug_html}")

            for i, table in enumerate(tables):
                try:
                    # 使用JavaScript提取表格数据 - 直接获取所有tr元素
                    table_data = self.driver.execute_script("""
                        var table = arguments[0];
                        var rows = [];
                        var allRows = table.querySelectorAll('tr');
                        var debugInfo = {totalRows: allRows.length};

                        for (var i = 0; i < allRows.length; i++) {
                            var row = [];
                            var cells = allRows[i].querySelectorAll('td, th');

                            for (var j = 0; j < cells.length; j++) {
                                var cell = cells[j];
                                var text = '';

                                if (cell.innerText) {
                                    text = cell.innerText;
                                } else if (cell.textContent) {
                                    text = cell.textContent;
                                }

                                text = text.trim()
                                    .replace(/\\s+/g, ' ')
                                    .replace(/\\n+/g, ' ')
                                    .trim();

                                row.push(text);
                            }
                            rows.push(row);
                        }

                        return {data: rows, debug: debugInfo};
                    """, table)

                    # 处理新的返回格式
                    if isinstance(table_data, dict) and 'data' in table_data:
                        debug_info = table_data.get('debug', {})
                        table_rows = table_data.get('data', [])
                        print(f"   🔍 调试信息: 总行数={debug_info.get('totalRows', 'unknown')}")

                        # 显示前几行的调试信息
                        for i in range(min(3, len(table_rows))):
                            print(f"      行{i}: {len(table_rows[i])}个单元格, 内容: {[cell[:15] for cell in table_rows[i][:3]]}")
                    else:
                        table_rows = table_data

                    if not table_rows or len(table_rows) < 2:
                        continue

                    # 检查是否是目标表格
                    first_row = table_rows[0]
                    if any('合约' in str(cell) for cell in first_row):
                        print(f"   ✅ 找到目标表格（第{i+1}个表格）")

                        # 处理多层表头 - 跳过前2行表头，第3行开始是真实数据
                        if len(table_rows) > 3:
                            print(f"   📊 检测到多层表头，跳过前2行")
                            # 从第3行开始获取数据（索引2）
                            data_rows = table_rows[2:]  # 跳过前2行
                            headers = table_rows[0]  # 使用第一行作为基本列名

                            # 处理列数不匹配问题
                            max_cols = max(len(row) for row in data_rows) if data_rows else len(headers)
                            print(f"   📊 数据行数: {len(data_rows)}, 最大列数: {max_cols}")

                            # 标准化所有行的列数
                            normalized_data = []
                            for row in data_rows:
                                if len(row) < max_cols:
                                    row.extend([''] * (max_cols - len(row)))
                                elif len(row) > max_cols:
                                    row = row[:max_cols]
                                normalized_data.append(row)

                            # 确保列名数量正确
                            while len(headers) < max_cols:
                                headers.append(f'列{len(headers)+1}')

                            df = pd.DataFrame(normalized_data, columns=headers[:max_cols])
                        else:
                            # 如果数据行数很少，使用原来的逻辑
                            max_cols = max(len(row) for row in table_rows)
                            print(f"   📊 表格最大列数: {max_cols}")

                            normalized_data = []
                            for row in table_rows:
                                if len(row) < max_cols:
                                    row.extend([''] * (max_cols - len(row)))
                                elif len(row) > max_cols:
                                    row = row[:max_cols]
                                normalized_data.append(row)

                            df = pd.DataFrame(normalized_data[1:], columns=normalized_data[0])

                        # 清理数据
                        df = self._clean_dataframe(df)

                        print(f"   📊 提取到 {len(df)} 行数据")
                        print(f"   📋 列名: {list(df.columns)}")

                        # 显示前几行
                        if len(df) > 0:
                            print(f"   📄 前3行数据预览:")
                            for idx, row in df.head(3).iterrows():
                                print(f"      {dict(row)}")

                        return df

                except Exception as e:
                    print(f"   ⚠️  表格{i+1}提取失败: {e}")
                    continue

            print("   ⚠️  未找到目标表格")
            return None

        except Exception as e:
            print(f"   ❌ 表格数据提取出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _clean_dataframe(self, df):
        """清理DataFrame数据"""
        try:
            # 删除空行
            df = df.dropna(how='all')

            # 重置索引
            df = df.reset_index(drop=True)

            # 删除全是空值的列
            df = df.dropna(axis=1, how='all')

            return df
        except:
            return df

    def _find_api_requests(self):
        """从网络日志中查找API请求"""
        try:
            # 获取网络日志
            logs = self.driver.get_log('performance')

            for entry in logs:
                try:
                    log = json.loads(entry['message'])['message']

                    # 查找网络请求
                    if log['method'] == 'Network.requestWillBeSent':
                        request = log['params']['request']
                        url = request.get('url', '')

                        # 查找包含数据相关的API请求
                        if any(keyword in url for keyword in ['queryDayTradPara', 'dayTradingParams', 'dailyParams', 'api']):
                            print(f"   📍 找到API请求: {url}")

                            # 尝试直接请求这个API
                            try:
                                response = requests.get(url, timeout=10)
                                if response.status_code == 200:
                                    data = response.json()
                                    print(f"   ✅ API返回数据成功！")
                                    return data
                            except:
                                continue

                except:
                    continue

            return None

        except Exception as e:
            print(f"   ⚠️  获取网络日志失败: {e}")
            return None

    def _extract_from_tbody(self, tbody_element):
        """专门从tbody元素提取数据"""
        try:
            # 使用JavaScript提取tbody中的所有tr
            tbody_data = self.driver.execute_script("""
                var tbody = arguments[0];
                var rows = [];
                var trs = tbody.querySelectorAll('tr');

                for (var i = 0; i < trs.length; i++) {
                    var row = [];
                    var cells = trs[i].querySelectorAll('td, th');

                    for (var j = 0; j < cells.length; j++) {
                        var cell = cells[j];
                        var text = '';

                        if (cell.innerText) {
                            text = cell.innerText;
                        } else if (cell.textContent) {
                            text = cell.textContent;
                        }

                        text = text.trim()
                            .replace(/\\s+/g, ' ')
                            .replace(/\\n+/g, ' ')
                            .trim();

                        row.push(text);
                    }
                    rows.push(row);
                }

                return rows;
            """, tbody_element)

            return tbody_data

        except Exception as e:
            print(f"   ⚠️  tbody数据提取失败: {e}")
            return None

    def _process_api_data(self, api_data):
        """处理API返回的数据"""
        try:
            print("   🔍 处理API数据...")

            # 尝试从API数据中提取表格数据
            if 'data' in api_data:
                data_list = api_data['data']

                # 如果是列表，直接转换为DataFrame
                if isinstance(data_list, list) and len(data_list) > 0:
                    df = pd.DataFrame(data_list)
                    print(f"   ✅ API数据处理完成，共 {len(df)} 行")
                    return df

            # 尝试其他可能的数据结构
            if 'rows' in api_data:
                df = pd.DataFrame(api_data['rows'])
                return df

            if 'result' in api_data:
                result = api_data['result']
                if isinstance(result, list):
                    df = pd.DataFrame(result)
                    return df

            print("   ⚠️  无法从API数据中提取表格")
            return None

        except Exception as e:
            print(f"   ⚠️  处理API数据失败: {e}")
            return None

    def _save_data(self, data, product_name, query_date):
        """保存数据到文件"""
        try:
            print(f"\n💾 保存数据...")

            safe_name = product_name.replace('/', '_').replace(' ', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 如果data是DataFrame，直接保存
            if isinstance(data, pd.DataFrame):
                # CSV
                csv_file = self.output_dir / f"{safe_name}_日交易参数_{query_date}_{timestamp}.csv"
                data.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"   💾 CSV: {csv_file}")

                # Excel
                excel_file = self.output_dir / f"{safe_name}_日交易参数_{query_date}_{timestamp}.xlsx"
                data.to_excel(excel_file, index=False, engine='openpyxl')
                print(f"   💾 Excel: {excel_file}")

                # JSON
                json_file = self.output_dir / f"{safe_name}_日交易参数_{query_date}_{timestamp}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data.to_dict('records'), f, ensure_ascii=False, indent=2)
                print(f"   💾 JSON: {json_file}")

            print(f"   ✅ 数据保存完成")

        except Exception as e:
            print(f"   ⚠️  保存数据出错: {e}")

    def crawl_all_products(self, target_date=None):
        """爬取所有品种的数据"""
        print("=" * 60)
        print("📋 大商所日交易参数爬虫 - 全部品种")
        print("=" * 60)

        all_data = {}
        failed_products = []

        for i, product in enumerate(self.products[1:], 1):  # 跳过"全部品种"
            print(f"\n📦 [{i}/{len(self.products)-1}] 爬取品种: {product}")

            try:
                # 重新启动浏览器以确保每次都是干净的会话
                if self.driver:
                    self._close_browser()
                self._start_browser()

                data = self.crawl_daily_params(target_date=target_date, product=product)
                if data is not None and not data.empty:
                    all_data[product] = data
                else:
                    failed_products.append(product)
                    print(f"   ⚠️  品种 {product} 未获取到数据")

                # 避免请求过快
                time.sleep(3)

            except Exception as e:
                failed_products.append(product)
                print(f"   ❌ 品种 {product} 爬取失败: {e}")
                continue

        # 合并所有数据
        if all_data:
            combined_df = pd.concat(all_data.values(), ignore_index=True)

            # 保存合并数据
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            combined_file = self.output_dir / f"全部品种_日交易参数_{timestamp}.xlsx"
            combined_df.to_excel(combined_file, index=False, engine='openpyxl')
            print(f"\n💾 合并数据已保存: {combined_file}")

            if failed_products:
                print(f"\n⚠️  以下品种爬取失败: {', '.join(failed_products)}")

            return combined_df
        else:
            print("\n⚠️ 未能获取任何数据")
            return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='大商所日交易参数爬虫')
    parser.add_argument('-d', '--date', type=str, default=None,
                       help='目标日期，格式YYYYMMDD或YYYY-MM-DD，默认为当天')
    parser.add_argument('-p', '--product', type=str, default='全部品种',
                       help='品种名称，如"豆一"、"豆粕"等，默认"全部品种"')
    parser.add_argument('-a', '--all', action='store_true',
                       help='爬取所有品种')
    parser.add_argument('-e', '--export', action='store_true',
                       help='尝试点击"导出表格"按钮')
    parser.add_argument('--headless', action='store_true', help='无头模式')

    args = parser.parse_args()

    crawler = DceDailyParamsCrawler(headless=args.headless)

    if args.all:
        crawler.crawl_all_products(target_date=args.date)
    else:
        crawler.crawl_daily_params(target_date=args.date, product=args.product, export_excel=args.export)
