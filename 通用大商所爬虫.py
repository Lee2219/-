#!/usr/bin/env python3
"""
大商所通用爬虫 - 支持爬取任意页面的表格数据
"""

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
from io import StringIO
import json
from pathlib import Path
import time
import sys


def crawl_dce_page(url, output_name="dce_data"):
    """爬取大商所任意页面的表格数据"""

    print("=" * 60)
    print("大商所通用数据爬虫")
    print("=" * 60)
    print(f"目标URL: {url}")

    # 创建输出目录
    output_dir = Path("dce_data")
    output_dir.mkdir(exist_ok=True)

    try:
        print("\n1. 启动浏览器...")

        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        driver = uc.Chrome(options=options, version_main=151)
        driver.set_window_size(1920, 1080)

        print("   ✅ 浏览器启动成功")

        # 访问目标页面
        print(f"\n2. 访问目标页面...")
        driver.get(url)
        print("   等待页面加载（15秒）...")
        time.sleep(15)

        print(f"   当前URL: {driver.current_url}")
        print(f"   页面标题: {driver.title}")

        # 查找表格
        print("\n3. 查找数据表格...")
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"   找到 {len(tables)} 个表格")

        if not tables:
            print("   ❌ 未找到表格，可能需要调整页面URL")
            driver.quit()
            return

        # 提取所有表格
        print("\n4. 提取表格数据...")
        all_data = []

        for i, table in enumerate(tables):
            try:
                table_html = table.get_attribute('outerHTML')
                dfs = pd.read_html(StringIO(table_html))
                if dfs and len(dfs) > 0:
                    df = dfs[0]
                    print(f"   表格 {i}: {len(df)} 行 x {len(df.columns)} 列")

                    # 保存每个表格
                    table_data = {
                        "table_index": i,
                        "rows": len(df),
                        "columns": len(df.columns),
                        "column_names": list(df.columns),
                        "data": df.to_dict('records')
                    }
                    all_data.append(table_data)
            except Exception as e:
                print(f"   表格 {i} 解析失败: {e}")
                continue

        if not all_data:
            print("   ❌ 未找到有效表格数据")
            driver.quit()
            return

        print(f"\n   ✅ 成功提取 {len(all_data)} 个表格")

        # 保存数据
        print("\n5. 保存数据...")

        result = {
            "爬取时间": time.strftime("%Y-%m-%d %H:%M:%S"),
            "来源URL": url,
            "页面标题": driver.title,
            "表格数量": len(all_data),
            "表格数据": all_data
        }

        # 保存JSON
        json_file = output_dir / f"{output_name}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"   ✅ JSON数据已保存: {json_file.absolute()}")

        # 保存所有表格到Excel
        try:
            excel_file = output_dir / f"{output_name}.xlsx"
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                for i, table_info in enumerate(all_data):
                    df = pd.DataFrame(table_info["data"])
                    df.to_excel(writer, sheet_name=f'表格{i+1}', index=False)
            print(f"   ✅ Excel数据已保存: {excel_file.absolute()}")
        except Exception as e:
            print(f"   ⚠️ Excel保存失败: {e}")

        # 截图
        screenshot_file = output_dir / f"{output_name}_截图.png"
        driver.save_screenshot(str(screenshot_file))
        print(f"   ✅ 截图已保存: {screenshot_file.absolute()}")

        print("\n" + "=" * 60)
        print("✅ 爬取完成！")
        print(f"数据保存在: {output_dir.absolute()}")
        print("=" * 60)

        driver.quit()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # 默认URL
        url = "http://www.dce.com.cn/dce/channel/242.html"  # 限仓参数

    if len(sys.argv) > 2:
        output_name = sys.argv[2]
    else:
        output_name = "持仓限额数据"

    crawl_dce_page(url, output_name)


if __name__ == "__main__":
    main()
