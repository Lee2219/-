#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表格数据爬取调试脚本 - 终极修复版本，正确处理rowspan
"""

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time


def test_table_extraction(url):
    """测试单个页面的表格爬取，终极修复版本"""
    print("=" * 60)
    print("📋 表格数据爬取调试工具（终极修复版本）")
    print("=" * 60)

    # 启动浏览器
    print("\n🌐 启动浏览器...")
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')

    driver = uc.Chrome(options=options, version_main=151)
    driver.set_page_load_timeout(60)

    try:
        # 访问页面
        print(f"📍 访问页面: {url}")
        driver.get(url)
        time.sleep(5)

        # 查找表格
        all_tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"📊 找到 {len(all_tables)} 个表格")

        if all_tables:
            table = all_tables[0]
            print("\n🔍 开始爬取表格...")

            # 提取表格数据
            table_data = extract_table_data(driver, table)

            print(f"✅ 表格数据爬取完成: {len(table_data)} 行")

            # 终极修复重建表格
            formatted = create_ultimate_table(table_data)
            print(f"\n📋 重建表格:")
            print(formatted)

            # 保存到文件
            output_file = "/Users/tony/Desktop/爬虫程序/测试表格_ultimate.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"测试页面: {url}\n\n")
                f.write(f"表格行数: {len(table_data)}\n\n")
                f.write("终极修复重建表格:\n\n")
                f.write(formatted)

            print(f"\n💾 表格数据已保存到: {output_file}")

        else:
            print("❌ 未找到表格")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        driver.quit()
        print("\n🔒 浏览器已关闭")


def extract_table_data(driver, table_element):
    """提取表格数据，保持完整的colspan和rowspan信息"""
    return driver.execute_script("""
        var table = arguments[0];
        var result = [];

        for (var i = 0; i < table.rows.length; i++) {
            var row = table.rows[i];
            var rowData = {
                rowIndex: i,
                cells: []
            };

            for (var j = 0; j < row.cells.length; j++) {
                var cell = row.cells[j];
                rowData.cells.push({
                    text: cell.textContent ? cell.textContent.trim() : '',
                    colspan: cell.colSpan || 1,
                    rowspan: cell.rowSpan || 1,
                    index: j
                });
            }

            result.push(rowData);
        }

        return result;
    """, table_element)


def create_ultimate_table(table_data):
    """创建终极修复的表格"""
    if not table_data:
        return "空表格"

    # 第一步：计算实际列数
    max_cols = 0
    for row in table_data:
        row_cols = sum(cell['colspan'] for cell in row['cells'])
        max_cols = max(max_cols, row_cols)

    print(f"  📐 表格总列数: {max_cols}")
    num_rows = len(table_data)

    # 第二步：创建表格布局矩阵
    layout = [[None for _ in range(max_cols)] for _ in range(num_rows)]

    for row_data in table_data:
        row_idx = row_data['rowIndex']
        col_idx = 0

        for cell in row_data['cells']:
            # 找到下一个空位
            while col_idx < max_cols and layout[row_idx][col_idx] is not None:
                col_idx += 1

            if col_idx >= max_cols:
                break

            colspan = cell['colspan']
            rowspan = cell['rowspan']

            # 在布局中标记这个单元格占据的所有位置
            for i in range(rowspan):
                for j in range(colspan):
                    target_row = row_idx + i
                    target_col = col_idx + j
                    if target_row < num_rows and target_col < max_cols:
                        layout[target_row][target_col] = {
                            'text': cell['text'],
                            'colspan': colspan,
                            'rowspan': rowspan,
                            'origin_row': row_idx,
                            'origin_col': col_idx,
                            'is_origin': (i == 0 and j == 0)
                        }

            col_idx += colspan

    # 第三步：计算每列的最佳宽度
    col_widths = []
    for col_idx in range(max_cols):
        max_width = 6  # 最小宽度
        for row_idx in range(num_rows):
            cell = layout[row_idx][col_idx]
            if cell and cell['is_origin']:
                # 计算文本显示宽度（中文字符为2个字符）
                text_width = sum(2 if '一' <= char <= '鿿' else 1 for char in cell['text'])

                # 如果单元格跨越多列，平均分配宽度
                if cell['colspan'] > 1:
                    text_width = (text_width // cell['colspan']) + 2

                max_width = max(max_width, text_width)

        # 限制最大宽度
        col_widths.append(min(max_width, 12))

    print(f"  📐 列宽: {col_widths}")

    # 第四步：构建表格字符串
    lines = []

    def create_separator():
        """创建分隔线"""
        parts = []
        for width in col_widths:
            parts.append("-" * width)
        return "+" + "+".join(parts) + "+"

    # 添加顶部分隔线
    lines.append(create_separator())

    # 处理每一行
    for row_idx in range(num_rows):
        row = layout[row_idx]
        line_parts = []
        col_idx = 0

        while col_idx < max_cols:
            cell = row[col_idx]

            if cell is None:
                # 空单元格，添加占位符
                line_parts.append("|" + " " * col_widths[col_idx])
                col_idx += 1
            elif cell['is_origin']:
                # 这是原始单元格，需要渲染
                text = cell['text']
                colspan = cell['colspan']

                # 计算总宽度
                if colspan == 1:
                    total_width = col_widths[col_idx]
                else:
                    # 跨多列，累加宽度并加上分隔符
                    total_width = sum(col_widths[col_idx:col_idx + colspan]) + (colspan - 1)

                # 截断过长的文本
                text_width = sum(2 if '一' <= char <= '鿿' else 1 for char in text)
                if text_width > total_width:
                    # 按字符宽度截断
                    current_width = 0
                    truncated_text = ""
                    for char in text:
                        char_width = 2 if '一' <= char <= '鿿' else 1
                        if current_width + char_width > total_width - 3:
                            break
                        truncated_text += char
                        current_width += char_width
                    text = truncated_text + "..."

                # 居中对齐
                centered_text = text.center(total_width)
                line_parts.append("|" + centered_text)
                col_idx += colspan
            else:
                # 这是被rowspan/colspan占据的位置，添加占位符（但不要跳过）
                line_parts.append("|" + " " * col_widths[col_idx])
                col_idx += 1

        if line_parts:
            line = "".join(line_parts) + "|"
            lines.append(line)
            lines.append(create_separator())

    return "\n".join(lines)


if __name__ == "__main__":
    # 测试URL
    test_url = "http://www.dce.com.cn/dce/content/2026/ywggytz/18627594.html"

    print("📋 表格数据爬取调试工具（终极修复版本）")
    print(f"📍 测试页面: {test_url}")
    print()

    test_table_extraction(test_url)

    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60)
