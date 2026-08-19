#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大商所今日所有品种交易参数爬虫
爬取所有合约的日交易参数数据
"""

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
from pathlib import Path
import time
from datetime import datetime
import sys


class AllProductsCrawler:
    """所有品种交易参数爬虫"""

    def __init__(self, headless=False):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.headless = headless
        self.driver = None
        self.output_dir = Path(f"/home/liyuexuan/下载/{self.today}_所有品种交易参数")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 所有品种：中文名称和对应代码（统一使用小写）
        self.all_products = {
            "豆一": "a",
            "豆二": "b",
            "豆粕": "m",
            "豆油": "y",
            "棕榈油": "p",
            "玉米": "c",
            "玉米淀粉": "cs",
            "粳米": "rr",
            "鸡蛋": "jd",
            "生猪": "lh",
            "纤维板": "fb",
            "胶合板": "bb",
            "原木": "lg",  # 修正为lg
            "焦煤": "jm",
            "焦炭": "j",
            "铁矿石": "i",
            "聚乙烯": "l",
            "聚氯乙烯": "v",
            "聚丙烯": "pp",
            "乙二醇": "eg",
            "苯乙烯": "eb",
            "液化石油气": "pg",
            "纯苯": "b",  # 新增
            "聚乙烯月均价": "lldpe",  # 新增
            "聚氯乙烯月均价": "pvc",  # 新增
            "聚丙烯月均价": "ppavg"  # 新增
        }

    def _start_browser(self):
        """启动浏览器"""
        print("🌐 启动浏览器...")
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')

        if self.headless:
            options.add_argument('--headless=new')

        self.driver = uc.Chrome(options=options, version_main=151)
        self.driver.set_page_load_timeout(60)
        print("   ✅ 浏览器启动成功")

    def _close_browser(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("🔒 浏览器已关闭")

    def crawl_all_products(self):
        """爬取所有品种数据"""
        print("=" * 70)
        print("📋 大商所今日所有品种交易参数爬虫")
        print(f"📅 当前日期: {self.today}")
        print(f"📦 产品数量: {len(self.all_products)} 个品种")
        print(f"📦 产品列表: {', '.join(self.all_products.keys())}")
        print("=" * 70)

        try:
            self._start_browser()

            all_data = {}
            failed_products = []

            # 分别访问每个品种
            for i, (product_name, product_code) in enumerate(self.all_products.items(), 1):
                print(f"\n📦 [{i}/{len(self.all_products)}] 爬取品种: {product_name} ({product_code})")

                try:
                    # 访问该品种的页面
                    url = f"http://www.dce.com.cn/frontend/dcereport/#/zh/queryDayTradPara?variety={product_code}&tradeType=1"
                    print(f"   📍 访问: {url}")
                    self.driver.get(url)

                    # 等待数据加载
                    time.sleep(10)

                    # 检查页面是否正常（不是暂无数据）
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if "暂无数据" in page_text or "无数据" in page_text:
                        print(f"   ⚠️  页面显示暂无数据")
                        failed_products.append(product_name)
                        time.sleep(2)
                        continue

                    # 尝试等待和验证数据加载
                    data_loaded = self._wait_for_data_load(product_code)
                    print(f"   {'✅' if data_loaded else '⚠️'} 数据加载{'成功' if data_loaded else '超时'}")

                    # 提取数据
                    data = self._extract_product_data(product_name, product_code)
                    if data is not None and not data.empty:
                        all_data[product_name] = data
                        print(f"   ✅ {product_name}: {len(data)} 条记录")
                    else:
                        print(f"   ⚠️  {product_name}: 无数据")
                        failed_products.append(product_name)

                    # 避免请求过快 - 增加等待时间
                    time.sleep(3)

                    # 每10个品种休息一下，避免被反爬虫检测
                    if i % 10 == 0:
                        print(f"   🔄 已完成{i}个品种，休息10秒...")
                        time.sleep(10)

                except Exception as e:
                    print(f"   ❌ {product_name} 爬取失败: {e}")
                    failed_products.append(product_name)
                    continue

            # 合并并保存数据
            if all_data:
                combined_df = pd.concat(all_data.values(), ignore_index=True)
                self._save_data(combined_df)

                print("\n" + "=" * 70)
                print(f"✅ 爬取完成！")
                print(f"   成功: {len(all_data)} 个产品")
                print(f"   失败: {len(failed_products)} 个产品")
                print(f"   总记录: {len(combined_df)} 条")
                print(f"📁 数据位置: {self.output_dir}")

                if failed_products:
                    print(f"⚠️  失败的产品: {', '.join(failed_products)}")

                print("=" * 70)

                return combined_df
            else:
                print("\n⚠️ 未能获取任何数据")
                return None

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            self._close_browser()

    def _wait_for_data_load(self, product_code, timeout=45):
        """等待数据加载完成"""
        try:
            print(f"   ⏳ 等待数据加载...")
            waited = 0
            check_interval = 5

            while waited < timeout:
                time.sleep(check_interval)
                waited += check_interval

                # 检查页面是否有对应品种的合约代码
                has_target_contracts = self.driver.execute_script(f"""
                    var targetCode = arguments[0];
                    var body = document.body;
                    var bodyText = body.textContent || body.innerText || '';

                    // 检查是否包含目标品种的合约代码
                    var pattern = targetCode + '2[5679]\\\\d';
                    var regex = new RegExp(pattern, 'i');
                    return regex.test(bodyText);
                """, product_code)

                if has_target_contracts:
                    print(f"   ✅ 检测到品种{product_code}的合约代码")
                    return True

                # 每20秒检查一次数据加载状态
                if waited % 20 == 0 and waited > 0:
                    tbody_count = len(self.driver.find_elements(By.TAG_NAME, "tbody"))
                    print(f"      等待中... {waited}s, tbody数量: {tbody_count}")

            return False

        except Exception as e:
            return False

    def _extract_product_data(self, product_name, product_code):
        """提取单个产品的数据"""
        try:
            print(f"   🔍 提取 {product_name} 数据...")

            # 查找tbody元素
            tbodies = self.driver.find_elements(By.TAG_NAME, "tbody")

            for tbody_idx, tbody in enumerate(tbodies):
                try:
                    tbody_data = self._extract_from_tbody(tbody)
                    if tbody_data and len(tbody_data) > 2:
                        # 检查是否包含目标品种的合约
                        has_target = any(
                            row and row[0] and row[0].startswith(product_code)
                            for row in tbody_data if row
                        )

                        if has_target and len(tbody_data) >= 3:
                            # 使用正确的列名
                            correct_columns = ['合约', '交易保证金(投机)比例', '交易保证金(投机)金额(元/手)',
                                             '交易保证金(套保)比例', '交易保证金(套保)金额(元/手)',
                                             '涨跌停板涨跌停板比例', '涨跌停板涨停板价位(元)', '涨跌停板跌停板价位(元)',
                                             '持仓限额(手)限仓模式', '持仓限额(手)非期货公司会员', '持仓限额(手)客户',
                                             '交易限额(手)品种限额', '交易限额(手)合约限额']

                            num_cols = len(tbody_data[0]) if tbody_data else len(correct_columns)

                            # 检查第一行是否是表头
                            first_row_text = ' '.join(tbody_data[0])
                            is_header = '合约' in first_row_text
                            data_rows = tbody_data[1:] if is_header else tbody_data

                            df = pd.DataFrame(data_rows, columns=correct_columns[:num_cols])
                            df = df.dropna(how='all')
                            df = df.reset_index(drop=True)

                            # 只保留目标品种的合约
                            df = df[df['合约'].astype(str).str.startswith(product_code)]

                            if not df.empty:
                                # 添加元数据
                                df['品种'] = product_name
                                df['查询日期'] = self.today
                                df['爬取日期'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                return df
                except:
                    continue

            return None

        except Exception as e:
            return None

    def _extract_from_tbody(self, tbody_element):
        """从tbody元素提取数据"""
        try:
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
            return None

    def _save_data(self, combined_df):
        """保存数据"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Excel文件
            excel_file = self.output_dir / f"所有品种交易参数_{timestamp}.xlsx"
            combined_df.to_excel(excel_file, index=False, engine='openpyxl')
            print(f"   💾 Excel: {excel_file}")

            # CSV文件
            csv_file = self.output_dir / f"所有品种交易参数_{timestamp}.csv"
            combined_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"   💾 CSV: {csv_file}")

            # 按品种分别保存
            print(f"   💾 保存分品种文件...")
            for product in combined_df['品种'].unique():
                product_df = combined_df[combined_df['品种'] == product]
                product_excel = self.output_dir / f"{product}_交易参数_{timestamp}.xlsx"
                product_df.to_excel(product_excel, index=False, engine='openpyxl')
                print(f"      - {product}: {product_excel}")

        except Exception as e:
            print(f"   ⚠️  保存数据失败: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='大商所所有品种交易参数爬虫')
    parser.add_argument('--headless', action='store_true', help='无头模式')

    args = parser.parse_args()

    crawler = AllProductsCrawler(headless=args.headless)
    crawler.crawl_all_products()
