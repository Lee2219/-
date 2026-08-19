#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大商所涨跌停板公告爬虫 - 表格内容完整提取版
确保完整获取表格所有内容，特别是产品名称和合约代码
"""

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
from pathlib import Path
import time
import json
import re
from datetime import datetime


class DceZhetinCrawler:
    """大商所涨跌停板公告爬虫 - 完整提取版"""

    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None
        self.output_dir = Path(__file__).parent / "最终爬取结果_输出数据"
        self.output_dir.mkdir(parents=True, exist_ok=True)

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

    def crawl_zhetin_announcements(self, max_pages=10):
        """爬取涨跌停板相关公告"""
        print("=" * 60)
        print("📋 大商所涨跌停板调整公告爬虫（完整提取版）")
        print(f"📖 爬取页数: {max_pages}页")
        print("=" * 60)

        try:
            self._start_browser()

            all_announcements = []
            zhetin_announcements = []

            for page in range(1, max_pages + 1):
                print(f"\n📖 第 {page} 页...")

                if page == 1:
                    url = "http://www.dce.com.cn/dce/channel/list/239.html"
                else:
                    url = f"http://www.dce.com.cn/dce/channel/list/239_{page}.html"

                print(f"   📍 正在访问: {url}")
                self.driver.get(url)
                time.sleep(10)

                announcements = self._extract_announcements()

                if not announcements:
                    break

                # 过滤涨跌停板相关公告
                exclude_keywords = [
                    '企业风险管理计划', '产融基地', '龙头', '一对一', '产业基地',
                    '合约停板查询', '停板查询', '查询', '计算器', '参数查询'
                ]
                include_keywords = ['涨跌停板', '涨跌停', '停板', '交易保证金']

                page_zhetin = []
                for item in announcements:
                    title = item.get('title', '')
                    should_exclude = any(exclude_kw in title for exclude_kw in exclude_keywords)
                    if should_exclude:
                        continue

                    has_keyword = any(include_kw in title for include_kw in include_keywords)
                    if has_keyword:
                        page_zhetin.append(item)
                        zhetin_announcements.append(item)

                if page_zhetin:
                    print(f"   🎯 找到 {len(page_zhetin)} 条符合条件的公告")

                all_announcements.extend(announcements)

            # 爬取详情
            if zhetin_announcements:
                print(f"\n🔍 爬取 {len(zhetin_announcements)} 条公告详情...")
                zhetin_with_details = self._crawl_zhetin_details(zhetin_announcements)

                # 二次过滤
                valid_details = []
                for detail in zhetin_with_details:
                    content = detail.get('content', '')
                    if content and len(content) > 50:
                        if any(kw in content for kw in ['涨跌停板', '停板幅度', '交易保证金', '保证金水平']):
                            valid_details.append(detail)
                        else:
                            print(f"   ⚠️  排除: {detail.get('title', '')[:30]}... (内容不匹配)")

                self._save_final_data(valid_details)

                print("\n" + "=" * 60)
                print(f"✅ 爬取完成！")
                print(f"   符合条件: {len(valid_details)} 条")
                print(f"📁 数据位置: {self.output_dir}")
                print("=" * 60)

                return valid_details
            else:
                print("\n⚠️  未找到符合条件的公告")
                return []

        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            return []

        finally:
            self._close_browser()

    def _extract_announcements(self):
        """提取公告列表"""
        announcements = []

        try:
            time.sleep(2)
            all_links = self.driver.find_elements(By.TAG_NAME, "a")

            js_result = self.driver.execute_script("""
                var items = [];
                var links = document.querySelectorAll('a');

                links.forEach(function(link) {
                    var text = link.textContent ? link.textContent.trim() : '';
                    var href = link.href || '';

                    if (text.length > 5 && text.length < 500 && href) {
                        var dateMatch = text.match(/(\\d{4}-\\d{2}-\\d{2})/) ||
                                       text.match(/(\\d{4})年(\\d{1,2})月(\\d{1,2})日/);

                        var date = '';
                        if (dateMatch) {
                            if (dateMatch[1].length === 10) {
                                date = dateMatch[1];
                            } else {
                                date = dateMatch[1] + '-' + String(dateMatch[2]).padStart(2, '0') + '-' + String(dateMatch[3]).padStart(2, '0');
                            }
                        }

                        var cleanTitle = text.replace(/\\s*\\d{4}-\\d{2}-\\d{2}.*/, '').trim();
                        cleanTitle = cleanTitle.replace(/\\s*\\d{4}年\\d{1,2}月\\d{1,2}日.*/, '').trim();

                        items.push({
                            title: cleanTitle || text,
                            link: href,
                            list_date: date
                        });
                    }
                });

                return items;
            """)

            if js_result:
                for item in js_result:
                    announcements.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "list_date": item.get("list_date", "")
                    })

        except Exception as e:
            print(f"   ⚠️  提取公告出错: {e}")

        # 去重
        seen = set()
        unique = []
        for item in announcements:
            link = item.get('link', '')
            if link and link not in seen:
                seen.add(link)
                unique.append(item)

        return unique

    def _crawl_zhetin_details(self, zhetin_announcements):
        """爬取公告详情"""
        details = []

        print(f"🔍 开始爬取 {len(zhetin_announcements)} 条公告详情...")

        for i, item in enumerate(zhetin_announcements, 1):
            title = item.get('title', '')
            print(f"\n📄 [{i}/{len(zhetin_announcements)}] {title[:40]}...")

            try:
                self.driver.get(item['link'])
                time.sleep(3)

                # 提取发布日期
                real_date = self._extract_publish_date()
                print(f"   ✅ 发布日期: {real_date}")

                # 提取正文内容（包含表格）
                main_content = self._extract_main_content()
                print(f"   ✅ 正文长度: {len(main_content)} 字符")

                detail_data = {
                    "title": title,
                    "date": real_date,
                    "link": item['link'],
                    "content": main_content.strip(),
                    "content_length": len(main_content),
                    "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                details.append(detail_data)
                time.sleep(1)

            except Exception as e:
                print(f"   ❌ 公告{i}爬取失败: {e}")

        print(f"\n✅ 爬取完成，共 {len(details)} 条公告")
        return details

    def _extract_publish_date(self):
        """从详情页提取发布日期"""
        try:
            date = self.driver.execute_script("""
                var allElements = document.querySelectorAll('*');
                var foundDates = [];

                for (var i = 0; i < allElements.length; i++) {
                    var elem = allElements[i];
                    var text = elem.textContent || elem.innerText || '';

                    if (text.indexOf('大连商品交易所') !== -1) {
                        var parentText = elem.textContent || elem.innerText || '';
                        var cnDateMatch = parentText.match(/(\\d{4})年(\\d{1,2})月(\\d{1,2})日/);
                        if (cnDateMatch) {
                            foundDates.push({
                                date: cnDateMatch[1] + '-' + String(cnDateMatch[2]).padStart(2, '0') + '-' + String(cnDateMatch[3]).padStart(2, '0')
                            });
                        } else {
                            var dateMatch = parentText.match(/(\\d{4})-(\\d{1,2})-(\\d{1,2})/);
                            if (dateMatch) {
                                foundDates.push({
                                    date: dateMatch[1] + '-' + String(dateMatch[2]).padStart(2, '0') + '-' + String(dateMatch[3]).padStart(2, '0')
                                });
                            }
                        }
                    }
                }

                if (foundDates.length > 0) {
                    return foundDates[foundDates.length - 1].date;
                }

                return '';
            """)

            if date:
                return date

            url = self.driver.current_url
            url_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
            if url_match:
                return f"{url_match.group(1)}-{url_match.group(2)}-{url_match.group(3)}"

            return ""

        except Exception as e:
            return ""

    def _extract_main_content(self):
        """提取正文内容，包含表格数据"""
        try:
            print("   🔍 开始提取正文内容...")

            # 检测页面中是否有表格
            all_tables = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"   📊 检测到 {len(all_tables)} 个表格")

            if len(all_tables) == 0:
                return self._extract_text_content()

            # 尝试找到主要内容容器
            content_elem = self._find_main_content_element()

            if content_elem:
                tables = content_elem.find_elements(By.TAG_NAME, "table")
                print(f"   📊 在内容容器中找到 {len(tables)} 个表格")

                # 提取文本内容
                content_text = self._extract_text_from_element(content_elem)

                # 爬取表格数据
                if tables:
                    for i, table in enumerate(tables):
                        try:
                            table_data = self._extract_table_data(table, i+1)
                            if table_data:
                                content_text += '\n\n' + table_data + '\n\n'
                                print(f"   ✅ 表格{i+1}数据爬取成功")
                        except Exception as e:
                            print(f"   ⚠️  表格{i+1}数据爬取出错: {e}")

                return content_text if len(content_text) > 50 else ""
            else:
                # 备用方法：使用全局表格
                content_text = self._extract_text_content()
                for i, table in enumerate(all_tables):
                    try:
                        table_data = self._extract_table_data(table, i+1)
                        if table_data:
                            content_text += '\n\n' + table_data + '\n\n'
                            print(f"   ✅ 全局表格{i+1}数据爬取成功")
                    except Exception as e:
                        print(f"   ⚠️  全局表格{i+1}数据爬取出错: {e}")

                return content_text

        except Exception as e:
            print(f"   ⚠️  内容提取出错: {e}")
            return ""

    def _find_main_content_element(self):
        """查找主要内容元素"""
        content_selectors = [
            '.article-content', '.news-content', '.content', '.main-content',
            '#content', '.text-content', '.detail-content', 'article',
            '.article', '.news-article', '#main-content', '#article-content'
        ]

        for selector in content_selectors:
            try:
                elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                if elem and elem.text.strip():
                    print(f"   📍 找到内容容器: {selector}")
                    return elem
            except:
                continue

        return None

    def _extract_text_from_element(self, element):
        """从元素中提取文本内容"""
        start_markers = [
            '各会员单位', '各结算会员', '各指定交割仓库', '各产业企业',
            '根据《大连商品交易所风险管理办法》', '经研究决定', '现将'
        ]
        end_markers = ['特此通知', '特此公告', '特此函告']

        content_parts = []
        started = False

        paragraphs = element.find_elements(By.TAG_NAME, "p")

        for p in paragraphs:
            try:
                text = p.text.strip()
                if not text or len(text) < 5:
                    continue

                if not started:
                    for marker in start_markers:
                        if text.startswith(marker) or marker in text[:20]:
                            started = True
                            print(f"   📝 开始提取内容，起始标记: {marker[:10]}...")
                            break

                if started:
                    ended = False
                    for marker in end_markers:
                        if text.startswith(marker) and len(text) < 50:
                            ended = True
                            print(f"   📝 结束提取内容，结束标记: {marker}")
                            break

                    if ended:
                        content_parts.append(text)
                        break

                    content_parts.append(text)
            except:
                continue

        return '\n\n'.join(content_parts) if content_parts else ""

    def _extract_text_content(self):
        """纯文本提取备用方法"""
        start_markers = [
            '各会员单位', '各结算会员', '各指定交割仓库', '各产业企业',
            '根据《大连商品交易所风险管理办法》', '经研究决定', '现将'
        ]
        end_markers = ['特此通知', '特此公告', '特此函告']

        paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
        content_parts = []
        started = False

        for p in paragraphs:
            text = p.text.strip()
            if not text or len(text) < 5:
                continue

            if not started:
                for marker in start_markers:
                    if text.startswith(marker) or marker in text[:20]:
                        started = True
                        break

            if started:
                ended = False
                for marker in end_markers:
                    if text.startswith(marker) and len(text) < 50:
                        ended = True
                        break

                if ended:
                    content_parts.append(text)
                    break

                content_parts.append(text)

        return '\n\n'.join(content_parts) if content_parts else ""

    def _extract_table_data(self, table_element, table_num=1):
        """爬取表格数据并格式化为文本表格 - 完整内容提取版"""
        try:
            print(f"   📊 开始爬取表格{table_num}数据...")

            # 使用JavaScript提取表格数据 - 改进版，确保完整提取所有内容
            table_data = self.driver.execute_script("""
                var table = arguments[0];
                var rows = [];

                for (var i = 0; i < table.rows.length; i++) {
                    var row = [];
                    var cells = table.rows[i].cells;

                    for (var j = 0; j < cells.length; j++) {
                        var cell = cells[j];

                        // 改进的文本提取方法 - 确保获取完整内容
                        var text = '';

                        // 方法1：使用innerText，保留换行和格式
                        if (cell.innerText) {
                            text = cell.innerText;
                        }

                        // 方法2：使用textContent作为备用
                        if (!text && cell.textContent) {
                            text = cell.textContent;
                        }

                        // 清理文本：去除多余空白，但保留有用内容
                        text = text.trim()
                                      .replace(/\\s+/g, ' ')        // 多个空白字符替换为单个空格
                                      .replace(/\\n+/g, ' ')         // 多个换行替换为单个空格
                                      .replace(/\\r+/g, ' ')         // 去除回车
                                      .trim();

                        // 获取colspan和rowspan
                        var colspan = cell.colSpan || 1;
                        var rowspan = cell.rowSpan || 1;

                        row.push({
                            text: text,
                            colspan: colspan,
                            rowspan: rowspan
                        });
                    }
                    rows.push(row);
                }

                return rows;
            """, table_element)

            if not table_data:
                return None

            # 调试输出：显示前几行数据
            print(f"   📋 表格预览（前3行）:")
            for i, row in enumerate(table_data[:3]):
                row_texts = [f"'{cell.get('text', '')[:20]}...({cell.get('colspan', 1)}x{cell.get('rowspan', 1)})'" for cell in row]
                print(f"      行{i}: {', '.join(row_texts)}")

            # 格式化表格为文本
            formatted_table = self._format_table_as_text(table_data)

            print(f"   ✅ 表格{table_num}爬取完成: {len(table_data)}行")
            return formatted_table

        except Exception as e:
            print(f"   ⚠️  表格数据爬取失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _format_table_as_text(self, table_data):
        """将表格数据格式化为文本表格 - 终极对齐算法"""
        try:
            if not table_data:
                return ""

            # 第一步：计算实际列数
            max_cols = 0
            for row in table_data:
                row_cols = sum(cell.get('colspan', 1) for cell in row)
                max_cols = max(max_cols, row_cols)

            num_rows = len(table_data)

            # 第二步：创建表格布局矩阵
            layout = [[None for _ in range(max_cols)] for _ in range(num_rows)]

            for row_idx, row in enumerate(table_data):
                col_idx = 0

                for cell in row:
                    colspan = cell.get('colspan', 1)
                    rowspan = cell.get('rowspan', 1)
                    text = cell.get('text', '')

                    # 找到下一个空位
                    while col_idx < max_cols and layout[row_idx][col_idx] is not None:
                        col_idx += 1

                    if col_idx >= max_cols:
                        break

                    # 在布局中标记这个单元格占据的所有位置
                    for i in range(rowspan):
                        for j in range(colspan):
                            target_row = row_idx + i
                            target_col = col_idx + j
                            if target_row < num_rows and target_col < max_cols:
                                layout[target_row][target_col] = {
                                    'text': text,
                                    'colspan': colspan,
                                    'rowspan': rowspan,
                                    'origin_row': row_idx,
                                    'origin_col': col_idx,
                                    'is_origin': (i == 0 and j == 0)
                                }

                    col_idx += colspan

            # 第三步：计算每列的最佳宽度 - 改进版，确保完整显示内容
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

                # 第一列设置更大的最小宽度，确保能显示完整的产品名称
                if col_idx == 0:
                    max_width = max(max_width, 18)  # 第一列最小18字符，能容纳"线型低密度聚乙烯"
                else:
                    max_width = max(max_width, 8)   # 其他列最小8字符

                # 只设置合理的上限，确保长内容不被截断
                col_widths.append(max_width)  # 移除max限制，确保完整显示

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
                        # 这是被rowspan/colspan占据的位置，添加占位符
                        line_parts.append("|" + " " * col_widths[col_idx])
                        col_idx += 1

                if line_parts:
                    line = "".join(line_parts) + "|"
                    lines.append(line)
                    lines.append(create_separator())

            return "\n".join(lines)

        except Exception as e:
            print(f"   ⚠️  表格格式化失败: {e}")
            # 备用：简单格式
            return self._simple_table_format(table_data)

    def _simple_table_format(self, table_data):
        """简单表格格式备用方法"""
        try:
            lines = []
            for row in table_data:
                cells = []
                for cell in row:
                    text = cell.get('text', '')
                    cells.append(text)
                lines.append(" | ".join(cells))
            return "\n".join(lines)
        except:
            return "表格格式化失败"

    def _save_final_data(self, valid_details):
        """保存数据到文件"""
        import pandas as pd

        # JSON
        json_file = self.output_dir / "zhetin_optimized.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(valid_details, f, ensure_ascii=False, indent=2)
        print(f"   💾 JSON文件: {json_file}")

        # Excel
        df = pd.DataFrame(valid_details)
        excel_file = self.output_dir / "zhetin_optimized.xlsx"
        df.to_excel(excel_file, index=False)
        print(f"   💾 Excel文件: {excel_file}")

        # 纯文本
        text_file = self.output_dir / "zhetin_optimized.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            for i, item in enumerate(valid_details, 1):
                f.write(f"{'='*80}\n")
                f.write(f"【公告{i}】{item.get('title', '')}\n")
                f.write(f"发布日期：{item.get('date', '')}\n")
                f.write(f"链接：{item.get('link', '')}\n")
                f.write(f"{'='*80}\n\n")
                f.write(item.get('content', ''))
                f.write(f"\n\n{'='*80}\n\n\n")
        print(f"   💾 纯文本文件: {text_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='大商所涨跌停板调整公告爬虫（完整提取版）')
    parser.add_argument('-p', '--pages', type=int, default=10, help='爬取页数，默认10页')
    parser.add_argument('--headless', action='store_true', help='无头模式')

    args = parser.parse_args()

    crawler = DceZhetinCrawler(headless=args.headless)
    crawler.crawl_zhetin_announcements(max_pages=args.pages)
