#!/usr/bin/env python3
"""
大商所持仓数据爬虫
使用undetected-chromedriver获取大连商品交易所的期货持仓数据
"""

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
from io import StringIO
import json
from pathlib import Path
import time
import argparse
from typing import Dict, List, Optional


class DCEPositionCrawler:
    """大商所持仓数据爬虫类"""

    def __init__(self, output_dir: str = "data/dce", headless: bool = False):
        """
        初始化爬虫

        Args:
            output_dir: 数据输出目录
            headless: 是否使用无头模式
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.driver = None

        # 品种代码映射
        self.variety_codes = {
            "铁矿石": "i",
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
            "原木": "lg",
            "焦煤": "jm",
            "焦炭": "j",
            "聚乙烯": "l",
            "聚氯乙烯": "v",
            "聚丙烯": "pp",
            "乙二醇": "eg",
            "苯乙烯": "eb",
            "液化石油气": "pg",
        }

    def _init_driver(self):
        """初始化浏览器驱动"""
        if self.driver is None:
            options = Options()
            if self.headless:
                options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')

            self.driver = uc.Chrome(options=options, version_main=151)
            self.driver.set_window_size(1920, 1080)

    def _parse_table_data(self, table_html: str) -> Optional[pd.DataFrame]:
        """
        解析表格HTML数据

        Args:
            table_html: 表格HTML字符串

        Returns:
            DataFrame对象或None
        """
        try:
            dfs = pd.read_html(StringIO(table_html))
            if dfs and len(dfs) > 0:
                return dfs[0]
        except Exception as e:
            print(f"   解析表格出错: {e}")
        return None

    def crawl_position_data(self, variety_name: str, variety_code: str) -> Optional[Dict]:
        """
        爬取指定品种的持仓数据

        Args:
            variety_name: 品种名称
            variety_code: 品种代码

        Returns:
            包含持仓数据的字典或None
        """
        self._init_driver()

        url = f"http://www.dce.com.cn/frontend/dcereport/#/zh/memberDealPosiQuotes?tradeType=1&variety={variety_code}"

        print(f"\n{'='*60}")
        print(f"开始爬取 {variety_name} ({variety_code}) 持仓数据")
        print(f"{'='*60}")
        print(f"URL: {url}")

        try:
            self.driver.get(url)
            time.sleep(15)  # 等待页面加载

            # 查找所有表格
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"找到 {len(tables)} 个表格")

            if not tables:
                print("   ❌ 未找到表格数据")
                return None

            # 分析表格，找到主要数据表格
            main_data = None
            for i, table in enumerate(tables):
                try:
                    table_html = table.get_attribute('outerHTML')
                    df = self._parse_table_data(table_html)

                    if df is not None and len(df) > 10:  # 主要数据表通常有超过10行
                        print(f"   ✅ 找到主数据表格 (索引 {i})")
                        print(f"   列名: {list(df.columns)}")
                        print(f"   行数: {len(df)}")

                        # 处理列名
                        if list(df.columns) == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
                            # 如果列名是数字，重新命名
                            df.columns = ['排名1', '会员1', '成交量', '成交增减',
                                         '排名2', '会员2', '持买单量', '买单增减',
                                         '排名3', '会员3', '持卖单量', '卖单增减']

                        print(f"\n   数据预览（前5行）:")
                        print(df.head(5).to_string(index=False))

                        main_data = {
                            "variety": variety_name,
                            "variety_code": variety_code,
                            "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "url": url,
                            "total_records": len(df),
                            "columns": list(df.columns),
                            "records": df.to_dict('records')
                        }
                        break
                except Exception as e:
                    print(f"   处理表格 {i} 出错: {e}")
                    continue

            if main_data:
                # 保存数据
                filename = self.output_dir / f"dce_{variety_code}_position_data.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(main_data, f, ensure_ascii=False, indent=2)

                print(f"\n   ✅ 数据已保存: {filename}")

                # 截图
                screenshot_path = self.output_dir / f"dce_{variety_code}_screenshot.png"
                self.driver.save_screenshot(str(screenshot_path))
                print(f"   截图已保存: {screenshot_path}")

                return main_data
            else:
                print("   ❌ 未找到有效数据")
                return None

        except Exception as e:
            print(f"   ❌ 爬取出错: {e}")
            import traceback
            traceback.print_exc()
            return None

    def crawl_multiple_varieties(self, varieties: List[str]) -> Dict[str, Dict]:
        """
        批量爬取多个品种的持仓数据

        Args:
            varieties: 品种名称列表

        Returns:
            包含所有品种数据的字典
        """
        results = {}

        for variety in varieties:
            variety_code = self.variety_codes.get(variety)
            if not variety_code:
                print(f"   ⚠️ 未知品种: {variety}")
                continue

            data = self.crawl_position_data(variety, variety_code)
            if data:
                results[variety] = data

            # 品种间等待一下，避免请求过于频繁
            time.sleep(3)

        return results

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='大商所持仓数据爬虫')
    parser.add_argument('--variety', '-v', type=str, default='铁矿石',
                        help='品种名称（默认：铁矿石）')
    parser.add_argument('--output-dir', '-o', type=str, default='data/dce',
                        help='输出目录（默认：data/dce）')
    parser.add_argument('--headless', action='store_true',
                        help='使用无头模式')
    parser.add_argument('--list', action='store_true',
                        help='列出所有可用品种')

    args = parser.parse_args()

    # 创建爬虫实例
    with DCEPositionCrawler(output_dir=args.output_dir, headless=args.headless) as crawler:
        if args.list:
            # 列出所有可用品种
            print("可用品种列表：")
            print("-" * 40)
            for name, code in crawler.variety_codes.items():
                print(f"{name:12s} : {code}")
            return

        # 爬取指定品种数据
        variety_code = crawler.variety_codes.get(args.variety)
        if not variety_code:
            print(f"❌ 未知品种: {args.variety}")
            print("使用 --list 查看可用品种")
            return

        result = crawler.crawl_position_data(args.variety, variety_code)

        if result:
            print(f"\n{'='*60}")
            print(f"✅ 爬取完成！")
            print(f"品种: {result['variety']}")
            print(f"记录数: {result['total_records']}")
            print(f"数据已保存到: {args.output_dir}")
            print(f"{'='*60}")
        else:
            print(f"\n❌ 爬取失败")


if __name__ == "__main__":
    main()
