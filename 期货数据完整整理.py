#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货合约参数变化数据整理程序（完整版）
功能：从JSON文件精确解析期货公告文本，按照产品-合约结构整理参数变化信息
特点：
1. 按品种名精确解析参数变化
2. 区分投机保证金和套期保值保证金
3. 智能判断"其他合约"具体代码
4. 使用生效时间（而非发布时间）排序
5. 显示完整信息：涉及合约、参数变化、公告标题、公告链接
"""

import os
import re
import json
from pathlib import Path


class FuturesDataOrganizer:
    """期货数据整理器"""

    def __init__(self, input_file, output_dir="期货数据整理结果"):
        """初始化"""
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.announcements = []

        # 产品代码映射
        self.product_codes = {
            '纯苯': 'BZ',
            '焦炭': 'J',
            '焦煤': 'JM',
            '铁矿石': 'I',
            '黄大豆1号': 'A',
            '黄大豆2号': 'B',
            '豆粕': 'M',
            '豆油': 'Y',
            '棕榈油': 'P',
            '玉米': 'C',
            '玉米淀粉': 'CS',
            '粳米': 'RR',
            '鸡蛋': 'JD',
            '生猪': 'LH',
            '线型低密度聚乙烯': 'L',
            '聚丙烯': 'PP',
            '聚氯乙烯': 'V',
            '乙二醇': 'EG',
            '苯乙烯': 'EB',
            '液化石油气': 'PG',
            '原木': 'LG',
            '纤维板': 'FB',
            '胶合板': 'BB'
        }

    def load_data(self):
        """加载JSON数据"""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            self.announcements = json.load(f)
        print(f"从JSON加载了 {len(self.announcements)} 条公告")

    def extract_effective_dates(self, content):
        """提取所有生效日期及其位置"""
        # 模式1：自X年X月X日结算时起
        date_pattern = r'自(\d{4})年(\d{1,2})月(\d{1,2})日[^\n]+?结算时起'
        dates = []

        for match in re.finditer(date_pattern, content):
            year = match.group(1)
            month = match.group(2).zfill(2)
            day = match.group(3).zfill(2)
            date_str = f"{year}-{month}-{day}"
            dates.append((date_str, match.start(), match.end()))

        # 模式2：X年X月X日恢复交易后（用于恢复至节前标准的情况）
        recovery_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日[^\n]*?恢复交易后'
        for match in re.finditer(recovery_pattern, content):
            year = match.group(1)
            month = match.group(2).zfill(2)
            day = match.group(3).zfill(2)
            date_str = f"{year}-{month}-{day}"
            dates.append((date_str, match.start(), match.end()))

        # 按位置排序
        dates.sort(key=lambda x: x[1])

        return dates

    def extract_params_from_text(self, text, is_holiday_context=False):
        """从文本中提取参数变化

        Args:
            text: 参数文本
            is_holiday_context: 是否在休市前后的上下文中（用于判断"恢复"是否为恢复至节前标准）
        """
        params = {
            'limit': None,
            'margin_spec': None,
            'margin_hedge': None,
            'margin_general': None,  # 通用的交易保证金（不区分投机/套保）
            'special_notes': [],  # 特殊说明（如"恢复"、"维持不变"等）
            'has_changes': False
        }

        # 0. 提取特殊说明（优先处理）
        special_patterns = []

        # 只有在休市前后上下文中，才将"恢复"识别为恢复至节前标准
        if is_holiday_context:
            special_patterns.append(r'恢复')
        else:
            # 非休市上下文，只识别明确的"恢复至节前标准"等表述
            special_patterns.append(r'恢复[^。]*?(?:节前标准|原标准|原水平)')

        special_patterns.extend([
            r'维持不变',
            r'保持[^。]*?一致',
        ])

        for pattern in special_patterns:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                if match:
                    note = match.group(0)
                    # 如果匹配到的是"恢复"且在休市上下文中，统一显示为"恢复至节前标准"
                    if note == '恢复' and is_holiday_context:
                        note = '恢复至节前标准'
                    params['special_notes'].append(note)
                    params['has_changes'] = True

        # 0.5. 提取"仍为"的情况（分别处理涨跌停板和保证金）
        # 格式：涨跌停板幅度仍为X%，交易保证金水平仍为Y%
        still_limit_pattern = r'涨跌停板[^。]*?仍为[^。]*?(\d+)'

        # 投机和套期保证的"仍为"模式
        still_spec_margin_pattern = r'投机[^和]*?交易保证金[^。]*?仍为[^。]*?(\d+)'
        still_hedge_margin_pattern = r'套期保值[^和]*?交易保证金[^。]*?仍为[^。]*?(\d+)'
        # 通用的"交易保证金...仍为"模式
        still_margin_pattern = r'交易保证金[^。]*?仍为[^。]*?(\d+)'

        limit_match = re.search(still_limit_pattern, text)
        spec_margin_match = re.search(still_spec_margin_pattern, text)
        hedge_margin_match = re.search(still_hedge_margin_pattern, text)
        general_margin_match = re.search(still_margin_pattern, text)

        if limit_match:
            params['limit'] = ('仍为', limit_match.group(1) + '%')
            params['has_changes'] = True

        # 优先检查投机和套期保证的"仍为"
        if spec_margin_match:
            params['margin_spec'] = ('仍为', spec_margin_match.group(1) + '%')
            params['has_changes'] = True
        elif hedge_margin_match:
            params['margin_hedge'] = ('仍为', hedge_margin_match.group(1) + '%')
            params['has_changes'] = True
        # 然后检查通用的"交易保证金...仍为"
        elif general_margin_match:
            params['margin_general'] = ('仍为', general_margin_match.group(1) + '%')
            params['has_changes'] = True

        # 1. 优先处理"分别"模式（投机和套期保值一起）
        both_patterns = [
            r'投机和套期保值[^。]*?分别由[^。]*?(\d+%)[^。]*?和[^。]*?(\d+%)[^。]*?调整为[^。]*?(\d+%)',
            r'投机和套期保值[^。]*?分别由[^。]*?(\d+%)[^。]*?和[^。]*?(\d+%)[^。]*?调整为[^。]*?(\d+%)[^。]*?和[^。]*?(\d+%)',
        ]

        for i, pattern in enumerate(both_patterns):
            match = re.search(pattern, text)
            if match:
                if i == 0:  # 调整为同一个值
                    params['margin_spec'] = (match.group(1), match.group(3))
                    params['margin_hedge'] = (match.group(2), match.group(3))
                else:  # 分别调整为不同值
                    params['margin_spec'] = (match.group(1), match.group(3))
                    params['margin_hedge'] = (match.group(2), match.group(4))
                params['has_changes'] = True
                break

        # 2. 提取涨跌停板变化
        if not params['margin_spec'] and not params['margin_hedge']:
            limit_patterns = [
                r'涨跌停板[^。]*?由[^。]*?(\d+%)[^。]*?调整为[^。]*?(\d+%)',
                r'涨跌停板[^。]*?调整为[^。]*?(\d+%)',
            ]

            for pattern in limit_patterns:
                match = re.search(pattern, text)
                if match:
                    if '由' in pattern:
                        params['limit'] = (match.group(1), match.group(2))
                    else:
                        params['limit'] = ('未明确', match.group(1))
                    params['has_changes'] = True
                    break

        # 3. 提取单独的保证金模式
        if not params['margin_spec'] and not params['margin_hedge'] and not params['margin_general']:
            # 优先检查投机和套期保值
            margin_patterns = [
                # 投机交易保证金
                r'投机[^和]*?交易保证金[^。]*?由[^。]*?(\d+%)[^。]*?调整为[^。]*?(\d+%)',
                r'投机[^和]*?交易保证金[^。]*?调整为[^。]*?(\d+%)',
                # 套期保值交易保证金
                r'套期保值[^和]*?交易保证金[^。]*?由[^。]*?(\d+%)[^。]*?调整为[^。]*?(\d+%)',
                r'套期保值[^和]*?交易保证金[^。]*?调整为[^。]*?(\d+%)',
                # 通用的交易保证金（不区分投机/套保）
                r'交易保证金[^。]*?由[^。]*?(\d+%)[^。]*?调整为[^。]*?(\d+%)',
                r'交易保证金[^。]*?调整为[^。]*?(\d+%)',
            ]

            for pattern in margin_patterns:
                match = re.search(pattern, text)
                if match:
                    if '投机' in pattern:
                        params['margin_spec'] = (match.group(1), match.group(2)) if len(match.groups()) >= 2 else ('未明确', match.group(1))
                    elif '套期保值' in pattern:
                        params['margin_hedge'] = (match.group(1), match.group(2)) if len(match.groups()) >= 2 else ('未明确', match.group(1))
                    elif '由' in pattern:
                        # 通用的交易保证金，有"由X%调整为Y%"格式
                        params['margin_general'] = (match.group(1), match.group(2))
                    else:
                        # 通用的交易保证金，只有"调整为X%"格式
                        params['margin_general'] = ('未明确', match.group(1))
                    params['has_changes'] = True
                    break

        return params

    def is_contract_expired(self, contract_code, effective_date_str):
        """
        判断合约在生效日期时是否已过期
        contract_code: 如 'J2601' 或 'EG2607'
        effective_date_str: 如 '2026-03-10'
        返回: True表示已过期，False表示仍有效
        """
        # 解析合约代码（至少需要5位：产品代码(1-2位) + 年月(4位)）
        if len(contract_code) < 5:
            return False  # 无法解析，假设有效

        year_suffix = contract_code[-4:-2]
        month = int(contract_code[-2:])

        # 解析生效日期
        try:
            eff_year = int(effective_date_str[:4])
            eff_month = int(effective_date_str[5:7])
        except:
            return False  # 解析失败，假设有效

        # 合约年份（20XX）
        contract_year = 2000 + int(year_suffix)

        # 判断逻辑：
        # 1. 如果生效年份 > 合约年份，合约已过期
        # 2. 如果年份相同且生效月份 >= 合约月份，合约已过期（已进入或超过交割月）
        if eff_year > contract_year:
            return True
        elif eff_year == contract_year and eff_month >= month:
            return True
        else:
            return False

    def get_active_contracts(self, product_code, effective_date_str):
        """
        获取在指定生效日期时仍有效的合约列表
        """
        active_contracts = []
        for year in ['26', '27']:
            for month in range(1, 13):
                if year == '27' and month > 3:
                    continue
                month_str = str(month).zfill(2)
                contract = f'{product_code}{year}{month_str}'
                if not self.is_contract_expired(contract, effective_date_str):
                    active_contracts.append(contract)
        return sorted(active_contracts)

    def calculate_other_contracts(self, listed_contracts, product_code, effective_date_str):
        """
        计算其他合约（排除已过期的合约）
        """
        # 获取在该生效日期时所有有效的合约
        all_active = set(self.get_active_contracts(product_code, effective_date_str))

        # 排除已列出的合约
        exclude = set(listed_contracts)
        exclude.discard('全部合约')

        other = sorted(all_active - exclude)
        return other

    def parse_product_changes_by_name(self, segment, product_name, product_code, effective_date, is_holiday_context=False):
        """按品种名精确解析参数变化，避免重复

        Args:
            segment: 文本段落
            product_name: 产品名称
            product_code: 产品代码
            effective_date: 生效日期
            is_holiday_context: 是否在休市前后的上下文中
        """
        changes = []
        processed_ranges = []  # 存储已处理的文本范围 (start, end)

        def is_processed(pos):
            """检查某个位置是否已被处理"""
            for start, end in processed_ranges:
                if start <= pos < end:
                    return True
            return False

        def mark_processed(start, end):
            """标记一个范围为已处理"""
            processed_ranges.append((start, end))

        # 模式1：产品名 + 期货 + 具体合约代码 + 参数（优先处理）
        # 改进：确保不匹配到"其他合约"部分，在"，其他"或"；"或"。 "处停止
        specific_pattern = f'{product_name}期货([A-Z0-9,、]+合约[^。]*?)(?:，其他|；|。)'
        specific_matches = list(re.finditer(specific_pattern, segment))

        # 模式1.5：处理多个产品名称组合的情况（如"棕榈油、乙二醇、苯乙烯和液化石油气品种期货合约"）
        # 改进：支持产品在组合中的任意位置（开头、中间、结尾），支持任意数量的产品
        # 格式：(产品1、)(产品2、)...产品N-1和产品N品种期货合约参数...；
        # 重要：使用([^；]+)；只匹配到"；"之前的内容，确保不匹配到"；"之后
        multi_product_patterns = [
            # 产品在开头：产品A、产品B、...、产品N-1和产品N品种期货合约...
            # 匹配产品名开头，后跟任意数量的"产品、"或"产品和"，最后以"品种期货合约"结束
            f'{product_name}(?:、[^、，]+)*(?:和[^、，]+)?品种期货合约([^；]+)；',
            # 产品在中间：...、产品X、目标产品、...、产品N品种期货合约...
            # 匹配前面有产品列表，后面还有产品的情况
            f'(?:[^、]+、){1,3}{product_name}(?:、[^、，]+)*(?:和[^、，]+)?品种期货合约([^；]+)；',
            # 产品在结尾（用"和"连接）：产品A、产品B、...和目标产品品种期货合约...
            f'(?:[^、]+、){1,4}和{product_name}品种期货合约([^；]+)；',
        ]
        multi_matches = []
        for pattern in multi_product_patterns:
            matches = list(re.finditer(pattern, segment))
            # 过滤掉包含"其他品种"的匹配
            filtered_matches = [m for m in matches if '其他品种' not in m.group(0)]
            multi_matches.extend(filtered_matches)

        for match in specific_matches:
            pos = match.start()
            if is_processed(pos):
                continue
            # 只标记到"，其他"之前的位置
            end_pos = match.end()
            if '，其他' in match.group(0):
                # 找到"，其他"的位置
                comma_pos = match.group(0).find('，其他')
                end_pos = match.start() + comma_pos
            mark_processed(match.start(), end_pos)

            contracts_text = match.group(1)
            contracts = re.findall(f'{product_code}\\d{{4}}', contracts_text)
            if contracts:
                # 过滤已过期的合约
                active_contracts = [c for c in contracts if not self.is_contract_expired(c, effective_date)]
                if active_contracts:
                    params = self.extract_params_from_text(contracts_text, is_holiday_context)
                    if params and params['has_changes']:
                        changes.append({
                            'contracts': sorted(list(set(active_contracts))),
                            'contract_type': '具体合约',
                            'params': params,
                            'source_text': match.group(0)
                        })

        # 模式1.5：处理多产品组合的情况（如"棕榈油、乙二醇、苯乙烯和液化石油气品种期货合约"）
        for match in multi_matches:
            pos = match.start()
            if is_processed(pos):
                continue
            mark_processed(match.start(), match.end())

            # 新的正则中参数在group(1)（如果只有一个分组）
            # 需要检查实际的分组数量
            params_text = match.group(1) if len(match.groups()) >= 1 else match.group(0)
            # 从参数文本中提取真正的参数部分
            # 格式通常是：品种期货合约涨跌停板幅度调整为X%，交易保证金水平调整为Y%
            # 或者：恢复至节前标准
            params_match = re.search(r'涨跌停板[^。]*?(?:调整为|仍为)[^。]*?[%\d]+[^。]*?(?:；|。|$)', params_text)
            if params_match:
                params_text = params_match.group(0)
            else:
                # 尝试保证金部分
                margin_match = re.search(r'交易保证金[^。]*?(?:调整为|仍为)[^。]*?[%\d]+[^。]*?(?:；|。|$)', params_text)
                if margin_match:
                    params_text = margin_match.group(0)
                else:
                    # 尝试特殊说明（如"恢复至节前标准"）
                    recovery_match = re.search(r'恢复[^。]*?(?:节前标准|原标准|原水平)[^。]*?(?:；|。|$)', params_text)
                    if recovery_match:
                        params_text = recovery_match.group(0)
                    else:
                        # 尝试"维持不变"
                        unchanged_match = re.search(r'维持不变[^。]*?(?:；|。|$)', params_text)
                        if unchanged_match:
                            params_text = unchanged_match.group(0)

            params = self.extract_params_from_text(params_text, is_holiday_context)
            if params and params['has_changes']:
                # 生成该产品的所有有效合约
                all_contracts = self.generate_all_contracts(product_code, effective_date)
                changes.append({
                    'contracts': all_contracts,
                    'contract_type': '全部合约（多产品组合）',
                    'params': params,
                    'source_text': match.group(0)
                })

        # 模式2：产品名 + 期货合约/品种期货合约 + 参数（没有具体合约代码，默认所有合约）
        # 使用([^；]+)[；。]匹配到"；"/"。"之前的内容
        all_contract_patterns = [
            f'{product_name}品种期货合约([^；]+)[；。]',
            f'{product_name}期货合约([^；]+)[；。]',
        ]

        for pattern in all_contract_patterns:
            all_matches = list(re.finditer(pattern, segment))
            for match in all_matches:
                pos = match.start()
                if is_processed(pos):
                    continue
                mark_processed(match.start(), match.end())

                params_text = match.group(1)
                params = self.extract_params_from_text(params_text, is_holiday_context)
                if params and params['has_changes']:
                    # 生成该产品的所有有效合约（排除已过期的）
                    all_contracts = self.generate_all_contracts(product_code, effective_date)
                    changes.append({
                        'contracts': all_contracts,
                        'contract_type': '全部合约',
                        'params': params,
                        'source_text': match.group(0)
                    })

        # 模式3：处理"其他合约"（需要捕获完整的参数描述）
        # 改进：直接匹配"，其他合约"开头，避免与具体合约匹配冲突
        # 匹配格式：，其他合约参数...（；|。|$）
        other_pattern = f'，其他合约([^。]*?)(?:；|。|$)'
        other_matches = list(re.finditer(other_pattern, segment))

        for match in other_matches:
            pos = match.start()
            if is_processed(pos):
                continue
            mark_processed(match.start(), match.end())

            # 检查这个"其他合约"是否属于该产品
            # 向前查找产品名
            before_text = segment[max(0, pos-100):pos]
            if product_name in before_text or product_code in before_text:
                other_text = match.group(1)  # "其他合约"后面的参数描述

                # 计算其他合约
                all_listed = []
                for change in changes:
                    all_listed.extend(change['contracts'])

                other_contracts = self.calculate_other_contracts(all_listed, product_code, effective_date)
                if other_contracts:
                    params = self.extract_params_from_text(other_text)
                    if params and params['has_changes']:
                        changes.append({
                            'contracts': other_contracts,
                            'contract_type': '其他合约',
                            'params': params,
                            'source_text': match.group(0)
                        })

        return changes

    def generate_all_contracts(self, product_code, effective_date_str):
        """生成该产品在指定生效日期时所有有效的合约"""
        return self.get_active_contracts(product_code, effective_date_str)

    def parse_parameter_changes(self, announcement):
        """解析单个公告的参数变化信息"""
        content = announcement.get('content', '')
        link = announcement.get('link', '')
        title = announcement.get('title', '')

        changes = []
        effective_dates = self.extract_effective_dates(content)

        if not effective_dates:
            return changes

        # 检查是否为休市前后公告（包含"休市"、"长假"、"春节"、"国庆"等关键词）
        is_holiday_announcement = any(keyword in content or keyword in title
                                     for keyword in ['休市', '长假', '春节', '国庆', '劳动节', '端午节', '中秋节'])

        # 处理每个生效日期段
        for i, (date, start_pos, end_pos) in enumerate(effective_dates):
            if i + 1 < len(effective_dates):
                next_start = effective_dates[i + 1][1]
                segment = content[start_pos:next_start]
            else:
                segment = content[start_pos:]

            # 解析该段落中的产品变化
            mentioned_products = set()
            for product_name, product_code in self.product_codes.items():
                if product_name in segment or product_code in segment:
                    product_changes = self.parse_product_changes_by_name(segment, product_name, product_code, date, is_holiday_announcement)
                    for change in product_changes:
                        changes.append({
                            'date': date,
                            'product': product_name,
                            'link': link,
                            'title': title,
                            **change
                        })
                    mentioned_products.add(product_name)

            # 检查是否有"其他品种"的描述
            other_variety_pattern = r'其他品种期货合约[^。]*?维持不变'
            other_match = re.search(other_variety_pattern, segment)
            if other_match:
                # 找出未提及的产品
                for product_name, product_code in self.product_codes.items():
                    if product_name not in mentioned_products:
                        # 为未提及的产品添加"维持不变"记录
                        all_contracts = self.generate_all_contracts(product_code, date)
                        if all_contracts:
                            changes.append({
                                'date': date,
                                'product': product_name,
                                'contracts': all_contracts,
                                'contract_type': '全部合约（其他品种）',
                                'params': {
                                    'limit': None,
                                    'margin_general': None,
                                    'special_notes': ['维持不变'],
                                    'has_changes': True
                                },
                                'link': link,
                                'title': title,
                                'source_text': other_match.group(0)
                            })

        return changes

    def format_parameter_description(self, params):
        """格式化参数变化描述"""
        descriptions = []

        # 优先显示特殊说明
        if params.get('special_notes'):
            for note in params['special_notes']:
                descriptions.append(f"特殊说明：{note}")

        if params['limit']:
            old_val, new_val = params['limit']
            if old_val == '未明确':
                descriptions.append(f"涨跌停板幅度调整为{new_val}")
            elif old_val == '仍为':
                descriptions.append(f"涨跌停板幅度仍为{new_val}")
            else:
                descriptions.append(f"涨跌停板幅度：{old_val} → {new_val}")

        # 优先显示通用的交易保证金（不区分投机/套保）
        if params.get('margin_general'):
            old_val, new_val = params['margin_general']
            if old_val == '未明确':
                descriptions.append(f"交易保证金调整为{new_val}")
            elif old_val == '仍为':
                descriptions.append(f"交易保证金仍为{new_val}")
            else:
                descriptions.append(f"交易保证金：{old_val} → {new_val}")
        # 然后显示投机交易保证金
        elif params.get('margin_spec'):
            old_val, new_val = params['margin_spec']
            if old_val == '未明确':
                descriptions.append(f"投机交易保证金调整为{new_val}")
            elif old_val == '仍为':
                descriptions.append(f"投机交易保证金仍为{new_val}")
            else:
                descriptions.append(f"投机交易保证金：{old_val} → {new_val}")

        # 最后显示套期保值交易保证金
        if params.get('margin_hedge'):
            old_val, new_val = params['margin_hedge']
            if old_val == '仍为':
                descriptions.append(f"套期保值交易保证金仍为{new_val}")
            elif old_val != new_val or params.get('margin_spec') != params['margin_hedge']:
                descriptions.append(f"套期保值交易保证金：{old_val} → {new_val}")

        return '; '.join(descriptions)

    def organize_data(self):
        """整理数据并按结构输出"""
        all_changes = []

        # 解析所有公告
        for ann in self.announcements:
            changes = self.parse_parameter_changes(ann)
            all_changes.extend(changes)

        # 按生效日期排序
        all_changes.sort(key=lambda x: x['date'])

        # 组织数据结构
        organized = {}
        for change in all_changes:
            product = change['product']
            contracts = change['contracts']

            if product not in organized:
                organized[product] = {}

            for contract in contracts:
                if contract not in organized[product]:
                    organized[product][contract] = []

                organized[product][contract].append({
                    'date': change['date'],
                    'all_contracts': contracts,
                    'contract_type': change['contract_type'],
                    'params': change['params'],
                    'link': change['link'],
                    'title': change['title'],
                    'source_text': change.get('source_text', '')
                })

        # 创建输出目录结构
        self.output_dir.mkdir(exist_ok=True)

        # 为每个产品-合约创建文件夹和文件
        for product in sorted(organized.keys()):
            product_dir = self.output_dir / product
            product_dir.mkdir(exist_ok=True)

            for contract in sorted(organized[product].keys()):
                contract_dir = product_dir / contract
                contract_dir.mkdir(exist_ok=True)

                # 写入参数变化文件
                changes_file = contract_dir / "合约参数变化.txt"
                with open(changes_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {product} - {contract} 合约参数变化记录\n\n")
                    f.write(f"共 {len(organized[product][contract])} 次调整\n\n")
                    f.write("=" * 80 + "\n\n")

                    for change_info in organized[product][contract]:
                        # 基本信息
                        f.write(f"【生效时间】{change_info['date']}\n")

                        # 涉及的合约列表
                        all_contracts = change_info['all_contracts']
                        contract_type = change_info['contract_type']

                        if len(all_contracts) > 1:
                            f.write(f"【涉及合约】{contract} 等 {len(all_contracts)} 个合约: {', '.join(all_contracts)}\n")
                        elif all_contracts[0] == '全部合约':
                            f.write(f"【涉及范围】{product}全部合约\n")
                        elif contract_type == '其他合约':
                            f.write(f"【涉及合约】{product}其他合约: {', '.join(all_contracts)}\n")
                        else:
                            f.write(f"【涉及合约】{all_contracts[0]}\n")

                        # 参数变化
                        param_desc = self.format_parameter_description(change_info['params'])
                        f.write(f"【参数变化】{param_desc}\n")

                        # 公告信息
                        f.write(f"【公告标题】{change_info['title']}\n")
                        f.write(f"【公告链接】{change_info['link']}\n")

                        f.write("\n" + "-" * 80 + "\n\n")

                print(f"已创建: {changes_file}")

        print(f"\n数据整理完成！输出目录: {self.output_dir}")
        print(f"共处理 {len(organized)} 个产品，{sum(len(v) for v in organized.values())} 个合约文件")


def main():
    """主函数"""
    input_file = "/home/liyuexuan/下载/最终爬取结果_输出数据/zhetin_optimized.json"
    output_dir = "/home/liyuexuan/期货数据完整结果"

    organizer = FuturesDataOrganizer(input_file, output_dir)
    organizer.load_data()
    organizer.organize_data()


if __name__ == "__main__":
    main()
