#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合表格数据和JSON公告数据，正确处理分合约的劳动节表格
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime

class DataIntegrator:
    """数据整合器"""

    def __init__(self):
        self.base_dir = Path("/home/liyuexuan/期货数据完整结果")
        self.table_files = {
            'spring': "/home/liyuexuan/下载/测试结果_1222.txt",
            'labor_day': "/home/liyuexuan/下载/关于2026年劳动节假期调整相关品种期货合约涨跌停板幅度和交_1222.txt"
        }

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

    def parse_simple_table_line(self, line):
        """解析简单表格单行数据（春节格式）"""
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
        """解析分合约表格单行数据（劳动节格式）
        格式：| 产品（合约信息） | 限幅1% | 投机1% | 保值1% | 限幅2% | 投机2% | 保值2% | 限幅3% | 投机3% | 保值3% |
        """
        # 匹配带合约信息的格式：| 棕榈油（2605、2606合约） |  10%   |  12%   |  12%   |  10%   |  12%   |  12%   |  10%   |  12%   |  12%   |
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

    def parse_table_file(self, file_path, is_labor_day=False):
        """解析表格文件，提取所有产品的数据"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

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

    def contract_matches_table_info(self, contract, contract_info, product_code):
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

    def get_table_changes(self, product_name, contract):
        """从表格中获取该合约的变化数据"""
        changes = []

        # 解析春节表格
        spring_data = self.parse_table_file(self.table_files['spring'], is_labor_day=False)
        labor_data = self.parse_table_file(self.table_files['labor_day'], is_labor_day=True)

        # 春节变化
        if product_name in spring_data:
            data = spring_data[product_name][0]  # 春节数据格式简单，直接取第一个

            # 春节前变化
            changes.append({
                'date': '2026-02-12',
                'event': '春节长假期间',
                'source': '表格数据',
                'params': f"涨跌停板幅度从{data['current_standard']['limit']}变为{data['holiday_standard']['limit']}，投机交易保证金从{data['current_standard']['margin_spec']}变为{data['holiday_standard']['margin_spec']}"
            })

            # 春节后变化
            changes.append({
                'date': '2026-02-24',
                'event': '春节长假后',
                'source': '表格数据',
                'params': f"恢复至节前标准（涨跌停板{data['post_holiday_standard']['limit']}，投机保证金{data['post_holiday_standard']['margin_spec']}，保值保证金{data['post_holiday_standard']['margin_hedge']}）"
            })

        # 劳动节变化
        if product_name in labor_data:
            product_code = self.product_codes.get(product_name, '')

            # 劳动节数据可能有多条（分合约）
            matched_data = None
            for data_item in labor_data[product_name]:
                if 'contract_info' in data_item:
                    # 检查合约是否匹配
                    if self.contract_matches_table_info(contract, data_item['contract_info'], product_code):
                        matched_data = data_item
                        break
                else:
                    # 没有合约信息，说明是全部合约
                    matched_data = data_item
                    break

            if matched_data:
                # 劳动节前变化
                changes.append({
                    'date': '2026-04-29',
                    'event': '劳动节长假期间',
                    'source': '表格数据',
                    'params': f"涨跌停板幅度从{matched_data['current_standard']['limit']}变为{matched_data['holiday_standard']['limit']}，投机交易保证金从{matched_data['current_standard']['margin_spec']}变为{matched_data['holiday_standard']['margin_spec']}"
                })

                # 劳动节后变化
                changes.append({
                    'date': '2026-05-06',
                    'event': '劳动节长假后',
                    'source': '表格数据',
                    'params': f"恢复至节前标准（涨跌停板{matched_data['post_holiday_standard']['limit']}，投机保证金{matched_data['post_holiday_standard']['margin_spec']}，保值保证金{matched_data['post_holiday_standard']['margin_hedge']}）"
                })

        return changes

    def get_json_changes_for_contract(self, product_name, contract):
        """获取某个合约的JSON公告变化数据"""
        changes_file = self.base_dir / product_name / contract / "合约参数变化.txt"
        if not changes_file.exists():
            return []

        changes = []
        with open(changes_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析每个变化记录
        lines = content.split('\n')
        current_change = {}

        for line in lines:
            if line.startswith('【生效时间】'):
                if current_change:  # 保存前一个变化
                    changes.append(current_change)
                date_match = re.search(r'【生效时间】(\d{4}-\d{2}-\d{2})', line)
                current_change = {
                    'date': date_match.group(1) if date_match else 'N/A',
                    'source': '交易所公告'
                }
            elif '【涉及合约】' in line and current_change:
                current_change['contracts'] = line.split('【涉及合约】')[1].strip()
            elif '【参数变化】' in line and current_change:
                current_change['params'] = line.split('【参数变化】')[1].strip()
            elif '【公告标题】' in line and current_change:
                current_change['title'] = line.split('【公告标题】')[1].strip()
            elif '【公告链接】' in line and current_change:
                current_change['link'] = line.split('【公告链接】')[1].strip()

        if current_change:
            changes.append(current_change)

        return changes

    def get_base_params(self, product_name, contract):
        """获取基准参数"""
        base_params_file = self.base_dir / product_name / contract / "基准参数.txt"
        if not base_params_file.exists():
            return None

        with open(base_params_file, 'r', encoding='utf-8') as f:
            content = f.read()

        params = {}
        for line in content.split('\n'):
            if '【涨跌停板幅度】' in line:
                params['limit'] = line.split('【涨跌停板幅度】')[1].strip()
            elif '【投机交易保证金】' in line:
                params['margin_spec'] = line.split('【投机交易保证金】')[1].strip()
            elif '【套期保值交易保证金】' in line:
                params['margin_hedge'] = line.split('【套期保值交易保证金】')[1].strip()

        return params

    def create_full_timeline(self, product_name, contract):
        """创建完整的时间线"""
        timeline = []

        # 添加表格变化
        table_changes = self.get_table_changes(product_name, contract)
        for change in table_changes:
            timeline.append(change)

        # 添加JSON公告变化
        json_changes = self.get_json_changes_for_contract(product_name, contract)
        for change in json_changes:
            timeline.append(change)

        # 按日期排序
        timeline.sort(key=lambda x: x['date'])

        return timeline

    def generate_integrated_file(self, product_name, contract):
        """生成整合后的完整参数文件"""
        timeline = self.create_full_timeline(product_name, contract)
        base_params = self.get_base_params(product_name, contract)

        # 生成文件内容
        content = f"# {product_name} - {contract} 完整参数记录\n\n"

        # 添加基准参数
        if base_params:
            content += "=" * 80 + "\n"
            content += "【当前基准参数】\n"
            content += "=" * 80 + "\n"
            content += f"涨跌停板幅度：{base_params['limit']}\n"
            content += f"投机交易保证金：{base_params['margin_spec']}\n"
            content += f"套期保值交易保证金：{base_params['margin_hedge']}\n\n"

        content += "=" * 80 + "\n"
        content += "【参数变化时间线】（包含表格数据和交易所公告，按时间顺序排列）\n"
        content += "=" * 80 + "\n\n"

        for item in timeline:
            content += f"【生效时间】{item['date']}\n"

            if item.get('event'):
                content += f"【事件】{item['event']}\n"

            if item.get('contracts'):
                content += f"【涉及合约】{item['contracts']}\n"

            content += f"【参数变化】{item['params']}\n"
            content += f"【来源】{item['source']}\n"

            if item.get('title'):
                content += f"【公告标题】{item['title']}\n"

            if item.get('link'):
                content += f"【公告链接】{item['link']}\n"

            content += "\n" + "-" * 80 + "\n\n"

        return content

    def integrate_all_data(self):
        """整合所有数据"""
        integrated_count = 0

        # 遍历所有产品和合约
        for product_dir in sorted(self.base_dir.iterdir()):
            if not product_dir.is_dir():
                continue

            product_name = product_dir.name

            for contract_dir in sorted(product_dir.iterdir()):
                if not contract_dir.is_dir():
                    continue

                contract = contract_dir.name

                # 生成整合后的文件
                content = self.generate_integrated_file(product_name, contract)

                # 写入完整参数.txt文件
                full_params_file = contract_dir / "完整参数.txt"
                with open(full_params_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                integrated_count += 1

        print(f"数据整合完成！共整合了 {integrated_count} 个合约的完整参数文件")
        print(f"表格数据的变化（春节+劳动节）已加入参数变化时间线")
        print(f"输出目录: {self.base_dir}")

def main():
    integrator = DataIntegrator()
    integrator.integrate_all_data()

if __name__ == "__main__":
    main()
