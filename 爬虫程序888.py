#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大商所239页面爬虫 - 涨跌停板专题（简化版）
遇到表格时直接截图（使用element.screenshot()方法）
修改：将DolphinDB的parquet格式改为JSON，避免依赖问题
"""

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
from pathlib import Path
import time
import json
import re
import base64
from datetime import datetime


class Dce239ZhetinCrawler:
    """大商所239页面涨跌停板爬虫 - 简化版"""

    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None
        self.output_dir = Path(__file__).parent / "爬取结果"
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
        self.driver.set_script_timeout(30)
        self.driver.set_window_size(1920, 1080)
        print("   ✅ 浏览器启动成功")

    def _close_browser(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("🔒 浏览器已关闭")

    def crawl_zhetin_announcements(self, max_pages=10):
        """爬取涨跌停板相关公告"""
        print("=" * 60)
        print("📋 大商所涨跌停板调整公告爬虫（简化版）")
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
            print(f"   🔗 链接: {item.get('link', '')}")

            try:
                print(f"   🌐 正在访问页面...")
                self.driver.get(item['link'])
                time.sleep(3)

                print(f"   📅 提取发布日期...")
                real_date = self._extract_publish_date()
                print(f"   ✅ 发布日期: {real_date}")

                print(f"   📝 提取正文内容...")
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

                if main_content:
                    print(f"   ✅ 公告{i}处理完成: 日期={real_date}, 正文={len(main_content)}字符")
                else:
                    print(f"   ⚠️  公告{i}正文为空")

                time.sleep(1)

                # 最后一个公告处理完成后增加额外延迟，确保截图完成
                if i == len(zhetin_announcements):
                    print(f"   ⏳ 最后一个公告处理完成，等待2秒确保所有截图保存...")
                    time.sleep(2)

            except Exception as e:
                print(f"   ❌ 公告{i}爬取失败: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n✅ 爬取完成，共 {len(details)} 条公告")
        # 在返回前再增加延迟，确保所有操作完成
        time.sleep(1)
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
            print(f"   ⚠️  日期提取失败: {e}")
            return ""

    def _extract_main_content(self):
        """提取正文内容，遇到表格时截图"""
        try:
            print("   🔍 开始提取正文内容...")

            # 第一步：全局检测页面中是否有表格
            all_tables = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"   📊 全局检测到 {len(all_tables)} 个表格元素")

            if len(all_tables) == 0:
                print("   ℹ️  页面中没有表格，使用纯文本提取")
                return self._extract_text_content()

            # 第二步：尝试找到包含正文的主要容器
            content_elem = self._find_main_content_element()

            if content_elem:
                # 在找到的内容容器中查找表格
                tables = content_elem.find_elements(By.TAG_NAME, "table")
                print(f"   📊 在内容容器中找到 {len(tables)} 个表格")

                # 提取文本内容
                content_text = self._extract_text_from_element(content_elem)

                # 对表格进行截图
                if tables:
                    for i, table in enumerate(tables):
                        is_last = (i == len(tables) - 1)  # 判断是否是最后一个表格
                        try:
                            screenshot_path = self._screenshot_table(table, i, is_last_table=is_last)
                            table_marker = '\n【表格】\n'
                            if table_marker in content_text:
                                content_text = content_text.replace(table_marker, f'\n【表格截图{i+1}】{screenshot_path}\n', 1)
                            else:
                                content_text += f'\n【表格截图{i+1}】{screenshot_path}\n'
                            print(f"   ✅ 表格{i+1}截图成功")
                        except Exception as e:
                            print(f"   ⚠️  表格{i+1}截图失败: {e}")
                            content_text += '\n【表格】(截图失败)\n'

                print(f"   ✅ 正文内容长度: {len(content_text)} 字符")
                return content_text if len(content_text) > 50 else ""
            else:
                # 备用方法：直接使用所有表格
                print("   ⚠️  未找到主要内容容器，使用全局表格")
                content_text = self._extract_text_content()

                # 对所有表格进行截图
                for i, table in enumerate(all_tables):
                    try:
                        screenshot_path = self._screenshot_table(table, i)
                        content_text += f'\n【表格截图{i+1}】{screenshot_path}\n'
                        print(f"   ✅ 全局表格{i+1}截图成功")
                    except Exception as e:
                        print(f"   ⚠️  全局表格{i+1}截图失败: {e}")
                        content_text += '\n【表格】(截图失败)\n'

                return content_text

        except Exception as e:
            print(f"   ⚠️  内容提取出错: {e}")
            import traceback
            traceback.print_exc()
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

        print("   ⚠️  未找到内容容器")
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

        # 获取所有段落和文本节点
        all_paragraphs = element.find_elements(By.XPATH, ".//p | .//text()")

        for node in all_paragraphs:
            try:
                if node.tag_name == 'p':
                    text = node.text.strip()
                else:
                    text = node.strip()

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
                        content_parts.append(text)  # 包含结束标记
                        break

                    content_parts.append(text)

            except Exception as e:
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
                    content_parts.append(text)  # 包含结束标记
                    break

                content_parts.append(text)

        return '\n\n'.join(content_parts) if content_parts else ""

    def _screenshot_table(self, table_element, index=0, is_last_table=False):
        """对表格进行完整截图，使用滚动拼接方法确保完全截取"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = str(self.output_dir / f"table_{index}_{timestamp}.png")

            print(f"   📸 开始处理表格{index+1}{'(最后一个表格)' if is_last_table else ''}")

            # 移除表格和父容器的样式限制
            self.driver.execute_script("""
                var table = arguments[0];
                table.style.maxHeight = 'none';
                table.style.maxWidth = 'none';
                table.style.overflow = 'visible';
                table.style.height = 'auto';

                // 移除父容器的限制
                var parent = table.parentElement;
                var count = 0;
                while (parent && parent !== document.body && count < 10) {
                    var computedStyle = window.getComputedStyle(parent);
                    var originalOverflow = parent.style.overflow;
                    var originalMaxHeight = parent.style.maxHeight;

                    parent.style.overflow = 'visible';
                    parent.style.maxHeight = 'none';

                    // 如果父容器有固定高度，移除它
                    if (computedStyle.maxHeight !== 'none') {
                        parent.style.maxHeight = 'none';
                    }

                    parent = parent.parentElement;
                    count++;
                }
            """, table_element)

            time.sleep(0.5)  # 增加等待时间让样式生效

            # 获取表格的完整尺寸信息
            table_info = self.driver.execute_script("""
                var table = arguments[0];
                var rect = table.getBoundingClientRect();

                return {
                    scrollHeight: table.scrollHeight,
                    scrollWidth: table.scrollWidth,
                    offsetTop: rect.top + window.pageYOffset,
                    offsetLeft: rect.left + window.pageXOffset,
                    viewportHeight: window.innerHeight,
                    viewportWidth: window.innerWidth,
                    rectTop: rect.top,
                    rectBottom: rect.bottom,
                    rectHeight: rect.height
                };
            """, table_element)

            table_height = table_info.get('scrollHeight', 0)
            table_width = table_info.get('scrollWidth', 0)
            viewport_height = table_info.get('viewportHeight', 0)
            rect_top = table_info.get('rectTop', 0)
            rect_bottom = table_info.get('rectBottom', 0)

            print(f"   📏 表格尺寸: {table_width}x{table_height}px, 视口: {viewport_height}px")
            print(f"   📊 表格位置: top={rect_top}, bottom={rect_bottom}")

            # 调整窗口宽度以适应表格宽度（如果需要）
            max_window_width = 2560  # 设置合理的最大宽度
            if table_width > viewport_height:  # 这里应该是比较宽度
                needed_width = min(max_window_width, table_width + 100)
                current_width = self.driver.execute_script("return window.innerWidth")
                if needed_width > current_width:
                    print(f"   🔧 调整窗口宽度: {needed_width}px")
                    self.driver.set_window_size(needed_width, 1080)
                    time.sleep(0.3)

            # 使用滚动截图方法，传递是否是最后一个表格的信息
            return self._scroll_and_screenshot(table_element, screenshot_path, table_info, is_last_table)

        except Exception as e:
            print(f"   ⚠️  表格截图出错: {e}")
            import traceback
            traceback.print_exc()

            # 备用方法：直接尝试element.screenshot
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                fallback_path = str(self.output_dir / f"table_{index}_fallback_{timestamp}.png")
                table_element.screenshot(fallback_path)
                print(f"   📸 备用截图已保存: {fallback_path}")
                return fallback_path
            except:
                return ""

    def _scroll_and_screenshot(self, table_element, screenshot_path, table_info, is_last_table=False):
        """调整浏览器窗口大小来适应表格，避免滚动拼接"""
        try:
            table_height = table_info.get('scrollHeight', 0)
            table_width = table_info.get('scrollWidth', 0)
            offset_top = table_info.get('offsetTop', 0)
            viewport_height = table_info.get('viewportHeight', 0)
            viewport_width = table_info.get('viewportWidth', 0)

            print(f"   📏 表格尺寸: {table_width}x{table_height}px")
            print(f"   🖥️  当前视口: {viewport_width}x{viewport_height}px")

            # 如果表格在当前视口内完全可见，直接截图
            if table_height <= viewport_height:
                print(f"   📸 表格完全可见，直接截图")
                self._scroll_to_table_safely(table_element, offset_top)
                time.sleep(0.3)
                table_element.screenshot(screenshot_path)
                print(f"   📸 表格截图已保存: {screenshot_path}")
                return screenshot_path

            # 表格超出视口，需要调整窗口大小
            print(f"   🔧 表格超出视口，调整窗口大小")

            # 计算需要的窗口尺寸（设置合理上限）
            max_window_width = 3840
            max_window_height = 10800  # 大幅增加最大高度限制

            # 计算需要的宽度和高度
            needed_width = min(max_window_width, max(table_width + 100, viewport_width))
            needed_height = min(max_window_height, table_height + 300)  # 增加更多边距

            print(f"   🔧 调整窗口大小: {needed_width}x{needed_height}px")

            # 调整浏览器窗口大小
            self.driver.set_window_size(needed_width, needed_height)
            time.sleep(0.5)

            # 重新获取视口信息
            new_viewport = self.driver.execute_script("""
                return {
                    width: window.innerWidth,
                    height: window.innerHeight
                };
            """)

            print(f"   🖥️  新视口尺寸: {new_viewport.get('width')}x{new_viewport.get('height')}px")

            # 滚动到表格位置，确保表格完全可见
            self._scroll_to_table_safely(table_element, offset_top)
            time.sleep(0.5)

            # 再次检查表格是否完全可见
            final_check = self.driver.execute_script("""
                var table = arguments[0];
                var rect = table.getBoundingClientRect();

                return {
                    isFullyVisible: rect.top >= 0 &&
                                   rect.bottom <= window.innerHeight &&
                                   rect.left >= 0 &&
                                   rect.right <= window.innerWidth,
                    rectTop: rect.top,
                    rectBottom: rect.bottom,
                    rectLeft: rect.left,
                    rectRight: rect.right,
                    viewportHeight: window.innerHeight,
                    viewportWidth: window.innerWidth
                };
            """, table_element)

            is_fully_visible = final_check.get('isFullyVisible', False)
            print(f"   🔍 表格完全可见: {is_fully_visible}")

            if not is_fully_visible:
                print(f"   📊 位置信息: top={final_check.get('rectTop')}, bottom={final_check.get('rectBottom')}")
                print(f"   📊 视口信息: height={final_check.get('viewportHeight')}")

            # 对表格元素进行截图
            table_element.screenshot(screenshot_path)
            print(f"   📸 表格截图已保存: {screenshot_path}")

            # 对最后一个表格进行额外的验证和处理
            if is_last_table:
                print(f"   🔍 最后表格验证，检查是否完整...")
                time.sleep(1)  # 给额外时间确保截图保存

                # 检查文件是否存在且大小合理
                import os
                if os.path.exists(screenshot_path):
                    file_size = os.path.getsize(screenshot_path)
                    print(f"   📁 截图文件大小: {file_size} bytes")

                    # 如果文件太小，可能是截图失败，尝试备用方法
                    if file_size < 10000:  # 小于10KB可能是失败
                        print(f"   ⚠️  截图文件过小，尝试备用方法")
                        return self._fallback_screenshot(table_element, screenshot_path, table_info)
                else:
                    print(f"   ⚠️  截图文件不存在，尝试备用方法")
                    return self._fallback_screenshot(table_element, screenshot_path, table_info)

            # 恢复原始窗口大小
            print(f"   🔧 恢复原始窗口大小: 1920x1080")
            self.driver.set_window_size(1920, 1080)
            time.sleep(0.5)  # 增加延迟

            return screenshot_path

        except Exception as e:
            print(f"   ⚠️  调整窗口方法出错: {e}")
            import traceback
            traceback.print_exc()

            # 最后的备用方法：使用全页截图
            try:
                print(f"   🔧 使用全页截图备用方法")
                self._scroll_to_table_safely(table_element, table_info.get('offsetTop', 0))
                time.sleep(0.3)

                # 获取表格位置信息，用于裁剪
                table_rect = self.driver.execute_script("""
                    var table = arguments[0];
                    var rect = table.getBoundingClientRect();

                    return {
                        top: rect.top + window.pageYOffset,
                        left: rect.left + window.pageXOffset,
                        width: rect.width,
                        height: rect.height
                    };
                """, table_element)

                # 全页截图
                full_page_screenshot = str(self.output_dir / f"temp_full_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                self.driver.save_screenshot(full_page_screenshot)

                # 如果有PIL，裁剪出表格部分
                try:
                    from PIL import Image
                    img = Image.open(full_page_screenshot)

                    # 计算裁剪区域
                    crop_left = int(table_rect.get('left', 0))
                    crop_top = int(table_rect.get('top', 0))
                    crop_width = int(table_rect.get('width', 0))
                    crop_height = int(table_rect.get('height', 0))

                    # 确保不超出图片边界
                    img_width, img_height = img.size
                    crop_left = max(0, min(crop_left, img_width - crop_width))
                    crop_top = max(0, min(crop_top, img_height - crop_height))

                    # 裁剪图片
                    cropped = img.crop((crop_left, crop_top, crop_left + crop_width, crop_top + crop_height))
                    cropped.save(screenshot_path)

                    # 删除临时全页截图
                    import os
                    os.remove(full_page_screenshot)

                    print(f"   📸 裁剪截图已保存: {screenshot_path}")
                    return screenshot_path

                except ImportError:
                    # 没有PIL，直接使用全页截图
                    import shutil
                    shutil.copy(full_page_screenshot, screenshot_path)
                    import os
                    os.remove(full_page_screenshot)
                    print(f"   📸 全页截图已保存: {screenshot_path}")
                    return screenshot_path

            except Exception as fallback_error:
                print(f"   ⚠️  备用方法也失败: {fallback_error}")
                return ""

    def _scroll_to_table_safely(self, table_element, offset_top):
        """安全地滚动到表格位置"""
        try:
            # 计算理想的滚动位置（让表格在视口中居中偏上）
            viewport_height = self.driver.execute_script("return window.innerHeight")

            # 滚动到表格位置，留出顶部空间
            scroll_position = max(0, offset_top - 200)
            self.driver.execute_script(f"window.scrollTo(0, {scroll_position});")
            time.sleep(0.3)

        except Exception as e:
            print(f"   ⚠️  滚动出错: {e}")
            # 基础滚动备用方法
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", table_element)

    def _fallback_screenshot(self, table_element, screenshot_path, table_info):
        """最后一个表格的备用截图方法"""
        try:
            print(f"   🔄 使用最后一个表格的备用截图方法")

            # 确保滚动到表格可见区域
            offset_top = table_info.get('offsetTop', 0)
            self.driver.execute_script(f"window.scrollTo(0, {max(0, offset_top - 300)});")
            time.sleep(1)

            # 尝试使用全页截图然后裁剪
            full_page_path = str(self.output_dir / f"temp_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            self.driver.save_screenshot(full_page_path)

            try:
                from PIL import Image
                img = Image.open(full_page_path)

                # 获取表格在页面中的精确位置
                table_rect = self.driver.execute_script("""
                    var table = arguments[0];
                    var rect = table.getBoundingClientRect();

                    return {
                        top: rect.top + window.pageYOffset,
                        left: rect.left + window.pageXOffset,
                        width: table.scrollWidth,
                        height: table.scrollHeight,
                        rectTop: rect.top,
                        rectBottom: rect.bottom
                    };
                """, table_element)

                crop_top = int(table_rect.get('top', 0))
                crop_left = int(table_rect.get('left', 0))
                crop_width = int(table_rect.get('width', 0))
                crop_height = int(table_rect.get('height', 0))

                print(f"   ✂️  裁剪区域: top={crop_top}, left={crop_left}, width={crop_width}, height={crop_height}")

                # 确保裁剪区域合理
                img_width, img_height = img.size
                crop_width = min(crop_width, img_width - crop_left)
                crop_height = min(crop_height, img_height - crop_top)

                if crop_width > 0 and crop_height > 0:
                    # 增加一些边距确保完整
                    margin = 50
                    crop_top = max(0, crop_top - margin)
                    crop_left = max(0, crop_left - margin//2)
                    crop_width = min(crop_width + margin, img_width - crop_left)
                    crop_height = min(crop_height + margin*2, img_height - crop_top)

                    cropped = img.crop((crop_left, crop_top, crop_left + crop_width, crop_top + crop_height))
                    cropped.save(screenshot_path)
                    print(f"   ✅ 备用截图已保存: {screenshot_path}")

                    # 删除临时文件
                    import os
                    os.remove(full_page_path)
                    return screenshot_path
                else:
                    raise Exception("裁剪区域无效")

            except ImportError:
                # 没有PIL，直接使用全页截图
                import shutil
                shutil.copy(full_page_path, screenshot_path)
                import os
                os.remove(full_page_path)
                print(f"   ✅ 全页截图已保存: {screenshot_path}")
                return screenshot_path

        except Exception as e:
            print(f"   ⚠️  备用截图方法失败: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def _save_final_data(self, valid_details):
        """保存数据到文件和DolphinDB"""
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

        # DolphinDB结构化数据（改为JSON格式，避免依赖问题）
        print(f"   📊 解析数据用于DolphinDB存储...")
        dolphindb_data = self._parse_for_dolphindb(valid_details)

        if dolphindb_data:
            dolphindb_df = pd.DataFrame(dolphindb_data)
            dolphindb_file = self.output_dir / "zhetin_dolphindb.json"
            dolphindb_df.to_json(dolphindb_file, orient='records', force_ascii=False, indent=2)
            print(f"   💾 DolphinDB数据文件: {dolphindb_file}")
            print(f"   📊 解析到 {len(dolphindb_data)} 条结构化记录")

            # 保存DolphinDB建表脚本
            script_file = self.output_dir / "dolphindb_schema.txt"
            with open(script_file, 'w', encoding='utf-8') as f:
                f.write(self._generate_dolphindb_schema())
            print(f"   💾 DolphinDB建表脚本: {script_file}")
        else:
            print(f"   ⚠️  未解析到结构化数据")

    def _parse_for_dolphindb(self, announcements):
        """解析公告数据为DolphinDB格式"""
        import hashlib
        import re

        parsed_records = []

        for announcement in announcements:
            try:
                title = announcement.get('title', '')
                content = announcement.get('content', '')
                date_str = announcement.get('date', '')
                link = announcement.get('link', '')

                # 解析基本信息
                announcement_type = self._determine_type(title)
                publish_date = self._parse_date(date_str)
                effective_date = self._extract_effective_date(content)

                # 解析品种参数
                varieties = self._extract_varieties(content)

                for variety_data in varieties:
                    record = {
                        'announcement_id': self._generate_id(link, variety_data['variety']),
                        'publish_date': publish_date,
                        'effective_date': effective_date,
                        'title': title,
                        'announcement_type': announcement_type,
                        'variety': variety_data['variety'],
                        'contract_specific': variety_data.get('contract_specific', ''),
                        'limit_before': variety_data.get('limit_before'),
                        'limit_after': variety_data.get('limit_after'),
                        'margin_speculator_before': variety_data.get('margin_speculator_before'),
                        'margin_speculator_after': variety_data.get('margin_speculator_after'),
                        'margin_hedger_before': variety_data.get('margin_hedger_before'),
                        'margin_hedger_after': variety_data.get('margin_hedger_after'),
                        'is_holiday_adjustment': 1 if '假期' in title or '劳动节' in title or '春节' in title else 0,
                        'link': link,
                        'content': content,
                        'crawl_time': announcement.get('crawl_time', '')
                    }
                    parsed_records.append(record)

            except Exception as e:
                print(f"   ⚠️  解析公告失败: {e}")
                continue

        return parsed_records

    def _determine_type(self, title):
        """判断公告类型"""
        if '假期' in title or '春节' in title or '劳动节' in title or '国庆节' in title:
            return '假期调整'
        elif '涨跌停板' in title and '交易保证金' in title:
            return '涨跌停板和保证金'
        elif '涨跌停板' in title:
            return '涨跌停板'
        elif '交易保证金' in title:
            return '交易保证金'
        else:
            return '其他'

    def _parse_date(self, date_str):
        """解析日期字符串"""
        try:
            if date_str:
                return pd.to_datetime(date_str).date()
        except:
            pass
        return None

    def _extract_effective_date(self, content):
        """提取生效日期"""
        patterns = [
            r'自(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'自(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{4})年(\d{1,2})月(\d{1,2})日.*?结算时起'
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    year, month, day = match.groups()
                    return pd.to_datetime(f"{year}-{month.zfill(2)}-{day.zfill(2)}").date()
                except:
                    continue
        return None

    def _extract_varieties(self, content):
        """提取品种和参数"""
        varieties = []

        variety_list = [
            '铁矿石', '焦炭', '焦煤', '黄大豆1号', '黄大豆2号', '豆粕', '豆油',
            '棕榈油', '玉米', '玉米淀粉', '粳米', '鸡蛋', '生猪', '线型低密度聚乙烯',
            '聚丙烯', '聚氯乙烯', '乙二醇', '纯苯', '苯乙烯', '液化石油气', '原木',
            '纤维板', '胶合板'
        ]

        for variety in variety_list:
            if variety in content:
                params = self._extract_single_variety_params(content, variety)
                if params:
                    varieties.extend(params)

        return varieties

    def _extract_single_variety_params(self, content, variety):
        """提取单个品种的参数"""
        params = []

        # 简化的参数提取逻辑
        try:
            # 查找品种后的涨跌停板调整
            limit_pattern = rf'{re.escape(variety)}.*?涨跌停板.*?由(\d+)%调整为(\d+)%'
            limit_match = re.search(limit_pattern, content)

            # 查找品种后的保证金调整
            margin_pattern = rf'{re.escape(variety)}.*?交易保证金.*?由(\d+)%调整为(\d+)%'
            margin_match = re.search(margin_pattern, content)

            param = {'variety': variety, 'contract_specific': ''}

            if limit_match:
                param['limit_before'] = float(limit_match.group(1)) / 100
                param['limit_after'] = float(limit_match.group(2)) / 100

            if margin_match:
                # 尝试分别提取投机和保值保证金
                margin_text = margin_match.group(0)
                if '投机' in margin_text and '保值' in margin_text:
                    # 需要更复杂的解析
                    speculator_pattern = r'投机.*?由(\d+)%.*?调整为(\d+)%'
                    hedger_pattern = r'保值.*?由(\d+)%.*?调整为(\d+)%'

                    speculator_match = re.search(speculator_pattern, margin_text)
                    hedger_match = re.search(hedger_pattern, margin_text)

                    if speculator_match:
                        param['margin_speculator_before'] = float(speculator_match.group(1)) / 100
                        param['margin_speculator_after'] = float(speculator_match.group(2)) / 100
                    if hedger_match:
                        param['margin_hedger_before'] = float(hedger_match.group(1)) / 100
                        param['margin_hedger_after'] = float(hedger_match.group(2)) / 100
                else:
                    param['margin_speculator_before'] = float(margin_match.group(1)) / 100
                    param['margin_speculator_after'] = float(margin_match.group(2)) / 100

            # 只添加有数据的参数
            if any(v for k, v in param.items() if k != 'variety' and k != 'contract_specific' and v is not None):
                params.append(param)

        except Exception as e:
            print(f"   ⚠️  解析{variety}参数失败: {e}")

        return params

    def _generate_id(self, link, variety):
        """生成唯一ID"""
        import hashlib
        hash_str = f"{link}_{variety}"
        return abs(int(hashlib.md5(hash_str.encode()).hexdigest(), 16)) % (10**10)

    def _generate_dolphindb_schema(self):
        """生成DolphinDB建表脚本"""
        return """
// DolphinDB 建表脚本
// 连接数据库: login("admin", "123456")

// 创建数据库
db = database("dfs://dce_zhetin", RANGE, `effective_date)

// 创建表结构
schema = table(
    100:0,
    `announcement_id`publish_date`effective_date`title`announcement_type`variety`contract_specific
    `limit_before`limit_after`margin_speculator_before`margin_speculator_after
    `margin_hedger_before`margin_hedger_after`is_holiday_adjustment`link`content`crawl_time,
    [LONG, DATE, DATE, STRING, STRING, STRING, STRING,
     DOUBLE, DOUBLE, DOUBLE, DOUBLE, DOUBLE, DOUBLE, INT, STRING, STRING, TIMESTAMP]
)

// 创建分区表
pt = db.createPartitionedTable(schema, `zhetin_announcements, `effective_date,
                                sortColumns=`announcement_id`effective_date, keepDuplicates=LAST)

// 创建索引
pt.createIndex("variety_idx", `variety)
pt.createIndex("date_idx", `effective_date)
pt.createIndex("type_idx", `announcement_type)

print("✅ 数据库和表创建成功")
"""

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='大商所涨跌停板调整公告爬虫（简化版）')
    parser.add_argument('-p', '--pages', type=int, default=10, help='爬取页数，默认10页')
    parser.add_argument('--headless', action='store_true', help='无头模式')

    args = parser.parse_args()

    crawler = Dce239ZhetinCrawler(headless=args.headless)
    crawler.crawl_zhetin_announcements(max_pages=args.pages)
