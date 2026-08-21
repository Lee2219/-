#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能版万能表格解析整合器 v3.0
完全基于最终爬取结果数据，精确提取个体参数

核心特点：
1. ✅ 只从最终爬取结果文件夹获取数据（JSON + TXT）
2. ✅ 根据数据时间范围自动确定合约范围
3. ✅ 精确提取个体参数变化（涨跌停板、投机保证金、套保保证金）
4. ✅ 不依赖其他已存在的基础数据目录
5. ✅ 支持任意假期和任意格式的表格数据整合
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import platform


class SmartTableIntegrator:
    """智能版表格解析整合器 - 完全基于爬取结果数据，精确提取参数"""

    def __init__(self, data_dir, output_dir):
        """
        Args:
            data_dir: 最终爬取结果数据目录，包含JSON和TXT文件
            output_dir: 输出结果目录
        """
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)

        # 数据文件
        self.json_file = self.data_dir / "zhetin_optimized.json"
        self.txt_file = self.data_dir / "zhetin_optimized.txt"

        # 产品代码映射
        self.product_codes = {
            '纯苯': 'BZ', '焦炭': 'J', '焦煤': 'JM', '铁矿石': 'I',
            '黄大豆1号': 'A', '黄大豆2号': 'B', '豆粕': 'M', '豆油': 'Y',
            '棕榈油': 'P', '玉米': 'C', '玉米淀粉': 'CS', '粳米': 'RR',
            '鸡蛋': 'JD', '生猪': 'LH', '线型低密度聚乙烯': 'L',
            '聚丙烯': 'PP', '聚氯乙烯': 'V', '乙二醇': 'EG',
            '苯乙烯': 'EB', '液化石油气': 'PG', '原木': 'LG',
            '纤维板': 'FB', '胶合板': 'BB'
        }

        # 有效交易月份（包含所有月份）
        self.valid_months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']

        # 存储解析后的数据
        self.json_data = []
        self.txt_data = []
        self.smart_contract_range = None
        self.earliest_effective_date = None

        # 合约交割日（每月第10日）
        self.delivery_day = 10

    def load_json_data(self):
        """加载JSON公告数据"""
        if not self.json_file.exists():
            print(f"⚠️ JSON文件不存在: {self.json_file}")
            return

        with open(self.json_file, 'r', encoding='utf-8') as f:
            self.json_data = json.load(f)
        print(f"✅ 加载JSON数据: {len(self.json_data)} 条公告")

    def load_txt_data(self):
        """加载TXT公告数据"""
        if not self.txt_file.exists():
            print(f"⚠️ TXT文件不存在: {self.txt_file}")
            return

        with open(self.txt_file, 'r', encoding='utf-8') as f:
            txt_content = f.read()

        # 解析TXT文件中的各个公告
        self.txt_data = self._parse_txt_announcements(txt_content)
        print(f"✅ 加载TXT数据: {len(self.txt_data)} 条公告")

    def _parse_txt_announcements(self, content: str) -> List[Dict]:
        """解析TXT文件中的各个公告"""
        announcements = []

        # 按照公告分隔符分割
        pattern = r'={80,}\s*\【公告(\d+)\】([^\n]+)\s+发布日期：([^\n]+)\s+链接：([^\n]+)'
        parts = re.split(pattern, content)

        # 跳过第一个空部分
        parts = parts[1:] if parts else []

        # 重组公告数据
        for i in range(0, len(parts), 4):
            if i + 3 < len(parts):
                announcement = {
                    'number': parts[i],
                    'title': parts[i+1].strip(),
                    'date': parts[i+2].strip(),
                    'url': parts[i+3].strip(),
                    'content': ''  # 稍后填充
                }
                announcements.append(announcement)

        # 填充公告内容
        for i, announcement in enumerate(announcements):
            # 找到公告开始位置
            start_pattern = f"【公告{announcement['number']}】"
            start_idx = content.find(start_pattern)

            # 找到下一个公告开始位置
            if i + 1 < len(announcements):
                next_pattern = f"【公告{announcements[i+1]['number']}】"
                end_idx = content.find(next_pattern)
            else:
                end_idx = len(content)

            if start_idx != -1 and end_idx != -1:
                # 提取公告内容（从URL行之后到下一个公告之前）
                url_end = content.find('\n\n', start_idx)
                if url_end != -1:
                    announcement['content'] = content[url_end+2:end_idx].strip()

        return announcements

    def extract_products_from_data(self) -> List[str]:
        """从数据中提取所有产品名称"""
        products = set()

        # 从JSON数据中提取产品
        for item in self.json_data:
            content = item.get('content', '')
            # 尝试匹配产品名称模式
            for product in self.product_codes.keys():
                if product in content:
                    products.add(product)

        # 从TXT数据中提取产品
        for item in self.txt_data:
            content = item.get('content', '')
            for product in self.product_codes.keys():
                if product in content:
                    products.add(product)

        return sorted(list(products))

    def analyze_data_time_range(self):
        """分析数据时间范围，确定合约范围"""
        all_dates = []

        # 从JSON数据中提取日期
        for item in self.json_data:
            content = item.get('content', '')
            pattern = r'自(\d{4})年(\d{1,2})月(\d{1,2})日[^\n]+?结算时起'
            matches = re.findall(pattern, content)
            for match in matches:
                year, month, day = match
                date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                all_dates.append(date_str)

        # 从TXT数据中提取日期
        for item in self.txt_data:
            content = item.get('content', '')
            pattern = r'自(\d{4})年(\d{1,2})月(\d{1,2})日[^\n]+?结算时起'
            matches = re.findall(pattern, content)
            for match in matches:
                year, month, day = match
                date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                all_dates.append(date_str)

        if not all_dates:
            print("⚠️ 无法提取任何日期，使用默认合约范围: 2603-2703")
            self.smart_contract_range = ("2603", "2703")
            self.earliest_effective_date = datetime(2026, 1, 1)
            return

        # 排序并找到最早日期
        unique_dates = sorted(set(all_dates))
        earliest_date_str = unique_dates[0]
        latest_date_str = unique_dates[-1]

        earliest_date = datetime.strptime(earliest_date_str, '%Y-%m-%d')
        self.earliest_effective_date = earliest_date

        print(f"📅 数据时间范围: {earliest_date_str} 到 {latest_date_str}")

        # 计算智能合约范围
        start_contract, end_contract = self._determine_contract_range(earliest_date)
        self.smart_contract_range = (start_contract, end_contract)

        print(f"🎯 智能合约范围: {start_contract} 到 {end_contract}")

    def _determine_contract_range(self, earliest_date: datetime) -> tuple:
        """根据数据起始时间确定合约范围"""

        # 起始合约：数据开始月份的下个月
        start_year = earliest_date.year
        start_month = earliest_date.month + 1

        # 处理月份溢出
        if start_month > 12:
            start_month = 1
            start_year += 1

        # 结束合约：起始合约 + 1.5年（18个月）
        end_year = start_year + (start_month + 17) // 12
        end_month = (start_month + 17) % 12
        if end_month == 0:
            end_month = 12
            end_year -= 1

        # 生成合约代码
        start_contract = f"{str(start_year)[-2:]}{str(start_month).zfill(2)}"
        end_contract = f"{str(end_year)[-2:]}{str(end_month).zfill(2)}"

        # 调整到有效交易月份（现在包含所有月份）
        start_contract = self._adjust_to_valid_month(start_contract, is_start=True)
        end_contract = self._adjust_to_valid_month(end_contract, is_start=False)

        return (start_contract, end_contract)

    def _adjust_to_valid_month(self, contract_code: str, is_start: bool = True) -> str:
        """调整合约代码到有效的交易月份"""
        year_suffix = contract_code[:2]
        month = contract_code[2:]
        month_int = int(month)

        if is_start:
            # 起始合约：向前找最近的有效月份
            for i in range(len(self.valid_months) - 1, -1, -1):
                if int(self.valid_months[i]) <= month_int:
                    return f"{year_suffix}{self.valid_months[i]}"
            # 如果没找到，使用前一年的11月
            return f"{str(int(year_suffix) - 1).zfill(2)}11"
        else:
            # 结束合约：向后找最近的有效月份
            for valid_month in self.valid_months:
                if int(valid_month) >= month_int:
                    return f"{year_suffix}{valid_month}"
            # 如果没找到，使用下一年的1月
            return f"{str(int(year_suffix) + 1).zfill(2)}01"

    def generate_contracts_for_product(self, product_name: str) -> List[str]:
        """为指定产品生成合约列表"""
        if product_name not in self.product_codes:
            return []

        product_code = self.product_codes[product_name]
        start_code, end_code = self.smart_contract_range

        # 解析起始和结束年月
        start_year = int(start_code[:2])
        start_month = int(start_code[2:])
        end_year = int(end_code[:2])
        end_month = int(end_code[2:])

        contracts = []

        # 生成所有合约
        current_year = start_year
        current_month = start_month

        while True:
            # 检查是否超出范围
            if current_year > end_year or (current_year == end_year and current_month > end_month):
                break

            # 生成所有月份的合约
            month_str = str(current_month).zfill(2)
            contract = f"{product_code}{str(current_year).zfill(2)}{month_str}"
            contracts.append(contract)

            # 移动到下一个月
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return contracts

    def parse_contract_expiry(self, contract: str) -> Optional[datetime]:
        """解析合约到期日期"""
        try:
            # 提取年月部分
            match = re.search(r'(\d{4})$', contract)
            if not match:
                return None

            ym = match.group(1)  # 如 '2508'
            year = 2000 + int(ym[:2])  # 25 -> 2025
            month = int(ym[2:])  # 08 -> 8

            # 使用每月第10日作为估算的到期日
            return datetime(year, month, self.delivery_day)

        except Exception as e:
            print(f"解析合约到期日期失败: {contract}, 错误: {e}")
            return None

    def is_change_valid_for_contract(self, change_date_str: str, contract_expiry: datetime) -> bool:
        """判断参数变化是否对合约有效"""
        try:
            change_date = datetime.strptime(change_date_str, '%Y-%m-%d')
            # 变化必须在合约到期日之前才有效
            return change_date <= contract_expiry
        except:
            return True  # 如果日期解析失败，保守返回True

    # 🎯 精确参数提取方法（从参考程序中移植）

    def parse_simple_table_line(self, line):
        """解析简单表格单行数据"""
        pattern = r'\|\s*([^\|]+?)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|'
        match = re.search(pattern, line)
        if match:
            product_name = match.group(1).strip()
            return {
                'product': product_name,
                'current_standard': {
                    'limit': match.group(2),
                    'margin_spec': match.group(3),
                    'margin_hedge': match.group(4)
                },
                'holiday_standard': {
                    'limit': match.group(5),
                    'margin_spec': match.group(6),
                    'margin_hedge': match.group(7)
                },
                'post_holiday_standard': {
                    'limit': match.group(8),
                    'margin_spec': match.group(9),
                    'margin_hedge': match.group(10)
                }
            }
        return None

    def parse_contract_table_line(self, line):
        """解析分合约表格单行数据"""
        contract_pattern = r'\|\s*([^\（]+)\（([^\）]+)\）\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|\s*(\d+%)\s*\|'

        match = re.search(contract_pattern, line)
        if match:
            product_name = match.group(1).strip()
            contract_info = match.group(2).strip()
            return {
                'product': product_name,
                'contract_info': contract_info,
                'current_standard': {
                    'limit': match.group(3),
                    'margin_spec': match.group(4),
                    'margin_hedge': match.group(5)
                },
                'holiday_standard': {
                    'limit': match.group(6),
                    'margin_spec': match.group(7),
                    'margin_hedge': match.group(8)
                },
                'post_holiday_standard': {
                    'limit': match.group(9),
                    'margin_spec': match.group(10),
                    'margin_hedge': match.group(11)
                }
            }
        return None

    def contract_matches_table_info(self, contract, contract_info):
        """判断合约是否匹配表格中的合约信息"""
        if '其他' in contract_info:
            return True  # 其他合约匹配所有
        else:
            # 提取合约信息中的年月
            contract_months = re.findall(r'(\d{4})', contract_info)
            if not contract_months:
                return True

            # 检查合约是否在列表中
            contract_ym = contract[-4:]  # 提取年月，如2607
            return contract_ym in contract_months

    def _extract_recovery_date(self, content: str, default_date: str = None) -> str:
        """🎯 从公告内容中提取恢复日期

        常见格式：
        - "2026年1月5日（星期一）恢复交易后"
        - "1月5日恢复交易后"
        """
        # 模式1：明确提到"X年X月X日恢复交易后"
        recovery_pattern1 = r'(\d{4})年(\d{1,2})月(\d{1,2})日[^\n]*?恢复交易后'
        match1 = re.search(recovery_pattern1, content)
        if match1:
            year, month, day = match1.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # 模式2：提到"X月X日恢复交易后"（同年）
        recovery_pattern2 = r'(\d{1,2})月(\d{1,2})日[^\n]*?恢复交易后'
        match2 = re.search(recovery_pattern2, content)
        if match2:
            # 从生效日期中提取年份
            if default_date:
                year = default_date.split('-')[0]
                month, day = match2.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        # 如果没有找到，使用默认日期（通常是生效日期的下周）
        return default_date

    def parse_table_from_content(self, content, is_labor_day=False):
        """从内容中解析表格数据"""
        table_data = {}
        lines = content.split('\n')

        for line in lines:
            if is_labor_day:
                # 劳动节表格：先尝试分合约格式
                parsed = self.parse_contract_table_line(line)
                if not parsed:
                    # 如果不匹配分合约格式，尝试简单格式
                    parsed = self.parse_simple_table_line(line)
            else:
                # 春节表格：使用简单格式
                parsed = self.parse_simple_table_line(line)

            if parsed:
                product_name = parsed['product']
                if product_name not in table_data:
                    table_data[product_name] = []

                table_data[product_name].append(parsed)

        return table_data

    def extract_params_from_content(self, content: str, product_name: str) -> Dict:
        """🎯 精确从公告内容中提取特定产品的参数变化"""
        params = {
            'limit': None,
            'margin_spec': None,
            'margin_hedge': None,
            'description': ''
        }

        # 查找包含产品名称的段落
        lines = content.split('\n')
        product_section = []
        found_product = False

        for i, line in enumerate(lines):
            if product_name in line:
                found_product = True
                # 收集产品相关的段落（包含参数信息）
                product_section.append(line)
                # 继续收集接下来的几行
                for j in range(i+1, min(i+10, len(lines))):
                    if '涨跌停板' in lines[j] or '保证金' in lines[j] or '%' in lines[j]:
                        product_section.append(lines[j])
                    elif lines[j].strip() and '。' in lines[j]:
                        break
                break

        if not product_section:
            return None

        product_text = ' '.join(product_section)

        # 精确提取参数
        # 模式1：涨跌停板幅度调整为X%
        limit_pattern = rf'{product_name}[^。]*?涨跌停板[幅度]*[^。]*?(\d+%)'
        limit_match = re.search(limit_pattern, product_text)
        if limit_match:
            params['limit'] = limit_match.group(1)

        # 模式2：投机保证金/交易保证金调整为X%
        margin_patterns = [
            rf'{product_name}[^。]*?投机.*?保证金[^。]*?(\d+%)',
            rf'{product_name}[^。]*?交易保证金[^。]*?(\d+%)',
        ]
        for pattern in margin_patterns:
            match = re.search(pattern, product_text)
            if match:
                params['margin_spec'] = match.group(1)
                break

        # 模式3：套期保值保证金调整为X%
        hedge_pattern = rf'{product_name}[^。]*?套期保值.*?保证金[^。]*?(\d+%)'
        hedge_match = re.search(hedge_pattern, product_text)
        if hedge_match:
            params['margin_hedge'] = hedge_match.group(1)

        # 如果没有精确提取到，尝试通用模式
        if not params['limit'] or not params['margin_spec']:
            all_percentages = re.findall(r'(\d+%)', product_text)
            if len(all_percentages) >= 2:
                if not params['limit']:
                    params['limit'] = all_percentages[0]
                if not params['margin_spec']:
                    params['margin_spec'] = all_percentages[1] if len(all_percentages) > 1 else all_percentages[0]
                if not params['margin_hedge']:
                    params['margin_hedge'] = all_percentages[2] if len(all_percentages) > 2 else all_percentages[1]

        # 生成描述
        if params['limit'] or params['margin_spec'] or params['margin_hedge']:
            desc_parts = []
            if params['limit']:
                desc_parts.append(f"涨跌停板幅度调整为{params['limit']}")
            if params['margin_spec']:
                desc_parts.append(f"投机交易保证金调整为{params['margin_spec']}")
            if params['margin_hedge']:
                desc_parts.append(f"套期保值交易保证金调整为{params['margin_hedge']}")
            params['description'] = '；'.join(desc_parts)
        else:
            params['description'] = "参数维持不变"

        return params if any([params['limit'], params['margin_spec'], params['margin_hedge']]) else None

    def extract_table_params_for_contract(self, product_name: str, contract: str) -> List[Dict]:
        """🎯 从表格数据中精确提取合约参数变化"""
        changes = []

        # 从所有公告内容中提取表格数据
        all_announcements = self.json_data + self.txt_data

        for announcement in all_announcements:
            content = announcement.get('content', '')
            title = announcement.get('title', announcement.get('title', ''))

            # 解析表格数据
            is_labor_day = '劳动节' in title or '4月' in title
            table_data = self.parse_table_from_content(content, is_labor_day)

            if product_name not in table_data:
                continue

            for item in table_data[product_name]:
                # 检查合约是否匹配
                if 'contract_info' in item:
                    if not self.contract_matches_table_info(contract, item['contract_info']):
                        continue

                # 提取生效日期
                pattern = r'自(\d{4})年(\d{1,2})月(\d{1,2})日[^\n]+?结算时起'
                matches = re.findall(pattern, content)
                if not matches:
                    continue

                effective_date = f"{matches[0][0]}-{matches[0][1].zfill(2)}-{matches[0][2].zfill(2)}"

                # 检查是否对合约有效
                contract_expiry = self.parse_contract_expiry(contract)
                if contract_expiry and not self.is_change_valid_for_contract(effective_date, contract_expiry):
                    continue

                # 生成精确的参数变化描述
                current = item['current_standard']
                holiday = item['holiday_standard']

                # 假期前变化
                before_params = f"涨跌停板幅度从{current['limit']}变为{holiday['limit']}，投机交易保证金从{current['margin_spec']}变为{holiday['margin_spec']}，套期保值交易保证金从{current['margin_hedge']}变为{holiday['margin_hedge']}"

                changes.append({
                    'date': effective_date,
                    'event': f"{title.split('关于')[1].split('的')[0] if '关于' in title else title}长假期间",
                    'source': '表格数据',
                    'params': before_params
                })

                # 假期后变化
                if 'post_holiday_standard' in item:
                    post = item['post_holiday_standard']
                    after_params = f"恢复至节前标准（涨跌停板{post['limit']}，投机交易保证金{post['margin_spec']}，套期保值交易保证金{post['margin_hedge']}）"

                    # 🎯 从公告内容中提取明确的恢复日期
                    recovery_date = self._extract_recovery_date(content, effective_date)

                    changes.append({
                        'date': recovery_date,
                        'event': f"{title.split('关于')[1].split('的')[0] if '关于' in title else title}长假后",
                        'source': '表格数据',
                        'params': after_params
                    })

        return changes

    def extract_announcement_params_for_contract(self, product_name: str, contract: str) -> List[Dict]:
        """🎯 从公告内容中精确提取合约参数变化"""
        changes = []

        # 从所有公告内容中提取参数
        all_announcements = self.json_data + self.txt_data

        for announcement in all_announcements:
            content = announcement.get('content', '')
            title = announcement.get('title', announcement.get('title', ''))

            # 检查是否与该产品相关
            if product_name not in content:
                continue

            # 提取生效日期
            pattern = r'自(\d{4})年(\d{1,2})月(\d{1,2})日[^\n]+?结算时起'
            matches = re.findall(pattern, content)
            if not matches:
                continue

            effective_date = f"{matches[0][0]}-{matches[0][1].zfill(2)}-{matches[0][2].zfill(2)}"

            # 检查是否对合约有效
            contract_expiry = self.parse_contract_expiry(contract)
            if contract_expiry and not self.is_change_valid_for_contract(effective_date, contract_expiry):
                continue

            # 精确提取产品参数
            params = self.extract_params_from_content(content, product_name)
            if params:
                changes.append({
                    'date': effective_date,
                    'event': title,
                    'source': '交易所公告',
                    'params': params['description']
                })

        return changes

    def extract_params_changes_for_contract(self, product_name: str, contract: str) -> List[Dict]:
        """🎯 提取指定合约的所有参数变化（精确版本）"""
        # 从表格数据中提取
        table_changes = self.extract_table_params_for_contract(product_name, contract)

        # 从公告内容中提取
        announcement_changes = self.extract_announcement_params_for_contract(product_name, contract)

        # 合并并按日期排序
        all_changes = table_changes + announcement_changes
        all_changes.sort(key=lambda x: x['date'])

        return all_changes

    def generate_contract_file(self, product_name: str, contract: str) -> str:
        """生成合约参数变化文件"""
        changes = self.extract_params_changes_for_contract(product_name, contract)

        content = f"# {product_name} {contract} - 完整参数变化记录\n\n"

        if not changes:
            content += "暂无参数变化记录\n"
        else:
            content += f"共找到 {len(changes)} 条参数变化记录：\n\n"

            for i, change in enumerate(changes, 1):
                content += f"【变化 {i}】\n"
                content += f"【生效时间】{change['date']}\n"
                content += f"【事件】{change['event']}\n"
                content += f"【参数变化】{change['params']}\n"
                content += f"【来源】{change['source']}\n"
                content += "\n"

        return content

    def integrate_all_data(self):
        """整合所有数据"""
        print("🚀 开始整合数据...")

        # 确保输出目录存在
        self.output_dir.mkdir(exist_ok=True)

        # 提取所有产品
        products = self.extract_products_from_data()
        print(f"📦 发现产品: {', '.join(products)}")

        total_contracts = 0

        # 为每个产品生成合约数据
        for product_name in products:
            print(f"\n📝 处理产品: {product_name}")

            # 生成合约列表
            contracts = self.generate_contracts_for_product(product_name)
            print(f"  合约范围: {', '.join(contracts[:5])}{'...' if len(contracts) > 5 else ''}")

            # 创建产品目录
            product_dir = self.output_dir / product_name
            product_dir.mkdir(exist_ok=True)

            # 为每个合约生成参数变化文件
            for contract in contracts:
                contract_dir = product_dir / contract
                contract_dir.mkdir(exist_ok=True)

                # 生成参数变化文件
                content = self.generate_contract_file(product_name, contract)

                # 写入文件
                params_file = contract_dir / "完整参数.txt"
                with open(params_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                total_contracts += 1

        print(f"\n✅ 数据整合完成！")
        print(f"📊 共处理 {len(products)} 个产品")
        print(f"📄 共生成 {total_contracts} 个合约文件")
        print(f"📁 输出目录: {self.output_dir}")


def main():
    """主函数"""
    # 检测操作系统
    system = platform.system()

    if system == "Darwin":  # macOS
        data_dir = "/Users/tony/Desktop/公告爬虫分析/最终爬取结果_输出数据"
        script_dir = Path(__file__).parent
        output_dir = script_dir / "智能版解析结果_输出_v3"
    else:  # Linux
        data_dir = "/home/liyuexuan/下载/最终爬取结果_输出数据"
        output_dir = Path("/home/liyuexuan/智能版解析结果_输出_v3")

    print("=" * 80)
    print("🔧 智能版万能表格解析整合器 v3.0 启动")
    print("=" * 80)
    print(f"📁 数据目录: {data_dir}")
    print(f"📁 输出目录: {output_dir}")
    print("🆕 完全基于爬取结果数据，精确提取个体参数")
    print("=" * 80)

    # 创建整合器
    integrator = SmartTableIntegrator(data_dir, output_dir)

    # 加载数据
    print("\n📖 加载数据文件...")
    integrator.load_json_data()
    integrator.load_txt_data()

    # 分析数据时间范围
    print("\n🔍 分析数据时间范围...")
    integrator.analyze_data_time_range()

    # 整合数据
    print("\n" + "=" * 80)
    integrator.integrate_all_data()

    print("\n" + "=" * 80)
    print("🎉 智能版万能表格解析整合完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
