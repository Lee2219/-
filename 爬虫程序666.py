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

    def crawl_zhetin_announcements(self, max_pages=5):
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

            except Exception as e:
                print(f"   ❌ 公告{i}爬取失败: {e}")
                import traceback
                traceback.print_exc()

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
            print(f"   ⚠️  日期提取失败: {e}")
            return ""

    def _extract_main_content(self):
        """提取正文内容，遇到表格时截图"""
        try:
            print("   🔍 开始提取正文内容...")
            start_markers = [
                '各会员单位', '各结算会员', '各指定交割仓库', '各产业企业',
                '根据《大连商品交易所风险管理办法》', '经研究决定', '现将'
            ]

            end_markers = ['特此通知', '特此公告', '特此函告']

            # 获取正文内容
            result = self.driver.execute_script("""
                var startMarkers = ['各会员单位', '各结算会员', '各指定交割仓库',
                                    '根据《大连商品交易所风险管理办法》', '经研究决定', '现将'];
                var endMarkers = ['特此通知', '特此公告', '特此函告'];

                var contentSelectors = ['.article-content', '.news-content', '.content', '.main-content',
                                        '#content', '.text-content', '.detail-content', 'article'];

                var bestContent = '';
                var bestSelector = '';
                var maxTables = 0;

                contentSelectors.forEach(function(selector) {
                    try {
                        var elem = document.querySelector(selector);
                        if (elem) {
                            var contentText = '';
                            var started = false;
                            var tableCount = 0;

                            var children = elem.children;
                            for (var i = 0; i < children.length; i++) {
                                var child = children[i];
                                var tagName = child.tagName.toLowerCase();

                                if (tagName === 'p') {
                                    var text = child.textContent ? child.textContent.trim() : '';
                                    if (!text || text.length < 5) continue;

                                    if (!started) {
                                        for (var j = 0; j < startMarkers.length; j++) {
                                            if (text.indexOf(startMarkers[j]) === 0) {
                                                started = true;
                                                break;
                                            }
                                        }
                                    }

                                    if (started) {
                                        var ended = false;
                                        for (var k = 0; k < endMarkers.length; k++) {
                                            if (text.indexOf(endMarkers[k]) === 0 && text.length < 50) {
                                                ended = true;
                                                break;
                                            }
                                        }

                                        if (ended) break;

                                        contentText += text + '\\n\\n';
                                    }
                                }
                                else if (tagName === 'table' && started) {
                                    tableCount++;
                                    contentText += '\\n【表格】\\n';
                                }
                            }

                            if (tableCount > maxTables && contentText.length > bestContent.length) {
                                bestContent = contentText;
                                bestSelector = selector;
                                maxTables = tableCount;
                            }
                        }
                    } catch(e) {}
                });

                return { content: bestContent, selector: bestSelector, tableCount: maxTables };
            """)

            if result:
                content_text = result.get('content', '')
                selector = result.get('selector', '')
                table_count = result.get('tableCount', 0)

                print(f"   📊 内容选择器: {selector}, 检测到 {table_count} 个表格")

                # 在Python层面查找并截图表格
                if selector and table_count > 0:
                    try:
                        print(f"   🔧 开始查找表格元素...")
                        content_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                        tables = content_elem.find_elements(By.TAG_NAME, "table")

                        print(f"   📸 实际找到 {len(tables)} 个表格元素，开始截图...")

                        if tables:
                            for i, table in enumerate(tables):
                                try:
                                    screenshot_path = self._screenshot_table(table, i)
                                    # 替换原来的【表格】标记
                                    table_marker = f'\n【表格】\n'
                                    if table_marker in content_text:
                                        content_text = content_text.replace(table_marker, f'\n【表格截图{i+1}】{screenshot_path}\n', 1)
                                    else:
                                        content_text += f'\n【表格截图{i+1}】{screenshot_path}\n'
                                except Exception as e:
                                    print(f"   ⚠️  表格{i+1}截图失败: {e}")
                                    content_text += '\n【表格】(截图失败)\n'
                    except Exception as e:
                        print(f"   ⚠️  查找表格元素失败: {e}")
                        import traceback
                        traceback.print_exc()

                print(f"   ✅ 正文内容长度: {len(content_text)} 字符")
                if content_text and len(content_text) > 50:
                    return content_text

            # 备用方法
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
                        break

                    content_parts.append(text)

            return '\n\n'.join(content_parts)

        except Exception as e:
            print(f"   ⚠️  内容提取出错: {e}")
            return ""

    def _screenshot_table(self, table_element, index=0):
        """对表格进行截图（使用element.screenshot()方法）"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = str(self.output_dir / f"table_{index}_{timestamp}.png")

            # 滚动到表格位置，确保表格可见
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", table_element)
            time.sleep(0.5)

            # 使用element.screenshot()方法直接对表格元素截图
            table_element.screenshot(screenshot_path)

            print(f"   📸 表格截图已保存: {screenshot_path}")
            return screenshot_path

        except Exception as e:
            print(f"   ⚠️  表格截图出错: {e}")
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
