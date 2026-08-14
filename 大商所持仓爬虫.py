#!/usr/bin/env python3
"""
大商所持仓数据爬虫 - 简易版本
直接运行即可爬取铁矿石持仓数据
"""

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
from io import StringIO
import json
from pathlib import Path
import time


def crawl_dce_position_data():
    """爬取大商所铁矿石持仓数据"""

    print("=" * 60)
    print("大商所持仓数据爬虫")
    print("=" * 60)

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

        # 访问铁矿石持仓数据页面
        print("\n2. 访问铁矿石持仓数据页面...")
        url = "http://www.dce.com.cn/frontend/dcereport/#/zh/memberDealPosiQuotes?tradeType=1&variety=i"
        print(f"   URL: {url}")

        driver.get(url)
        print("   等待页面加载（15秒）...")
        time.sleep(15)

        print(f"   当前URL: {driver.current_url}")
        print(f"   页面标题: {driver.title}")

        # 查找表格
        print("\n3. 查找数据表格...")
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"   找到 {len(tables)} 个表格")

        # 找到主数据表格
        main_df = None
        for i, table in enumerate(tables):
            try:
                table_html = table.get_attribute('outerHTML')
                dfs = pd.read_html(StringIO(table_html))
                if dfs and len(dfs) > 0:
                    df = dfs[0]
                    if len(df) > 10:  # 主数据表通常有超过10行
                        print(f"\n   ✅ 找到主数据表格 (索引 {i})")
                        print(f"   列数: {len(df.columns)}, 行数: {len(df)}")
                        main_df = df
                        break
            except Exception as e:
                continue

        if main_df is not None:
            print("\n4. 数据预览（前5名）:")
            print(main_df.head(5).to_string(index=False))

            # 保存数据
            print("\n5. 保存数据...")

            result = {
                "品种": "铁矿石",
                "品种代码": "i",
                "爬取时间": time.strftime("%Y-%m-%d %H:%M:%S"),
                "数据来源": url,
                "总记录数": len(main_df),
                "数据": main_df.to_dict('records')
            }

            # 保存JSON
            json_file = output_dir / "铁矿石持仓数据.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"   ✅ JSON数据已保存: {json_file.absolute()}")

            # 保存Excel
            excel_file = output_dir / "铁矿石持仓数据.xlsx"
            main_df.to_excel(excel_file, index=False)
            print(f"   ✅ Excel数据已保存: {excel_file.absolute()}")

            # 截图
            screenshot_file = output_dir / "页面截图.png"
            driver.save_screenshot(str(screenshot_file))
            print(f"   ✅ 截图已保存: {screenshot_file.absolute()}")

            print("\n" + "=" * 60)
            print("✅ 爬取完成！")
            print(f"数据保存在: {output_dir.absolute()}")
            print("=" * 60)

        else:
            print("   ❌ 未找到有效数据表格")

        driver.quit()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    crawl_dce_position_data()
