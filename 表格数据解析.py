#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货表格数据解析程序
功能：从JSON文件精确解析期货公告表格数据，提取各品种的基准参数
特点：
1. 解析公告中的表格数据
2. 提取各品种的现行标准参数
3. 按品种-合约结构整理基准参数信息
4. 显示完整信息：涨跌停板、投机保证金、保值保证金
"""

import os
import re
import json
from pathlib import Path


class FuturesTableParser:
    """期货表格数据解析器"""

    def __init__(self, input_file, output_dir="期货表格数据结果"):
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

        # 基准参数数据（从表格中提取）
        self.base_parameters = {}

    def load_data(self):
        """加载JSON数据"""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            self.announcements = json.load(f)
        print(f"从JSON加载了 {len(self.announcements)} 条公告")

    def load_table_files(self, spring_festival_file, labor_day_file):
        """加载单独的表格文件"""
        self.spring_festival_table = spring_festival_file
        self.labor_day_table = labor_day_file
        print(f"加载表格文件:")
        print(f"  春节表格: {spring_festival_file}")
        print(f"  劳动节表格: {labor_day_file}")

    def parse_table_file(self, file_path):
        """解析单个表格文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            result = self.parse_table_data(content)
            print(f"  调试: 从 {file_path.split('/')[-1]} 解析得到 {len(result)} 个数据")
            specific_count = sum(1 for v in result.values() if v.get('contracts'))
            all_count = sum(1 for v in result.values() if not v.get('contracts'))
            print(f"  调试: 其中 {specific_count} 个分合约数据, {all_count} 个全部合约数据")
            return result
        except Exception as e:
            print(f"解析表格文件 {file_path} 时出错: {e}")
            return {}

    def parse_table_data(self, content):
        """解析表格数据，提取各品种的基准参数"""
        table_data = {}

        # 检查是否包含表格
        if '+-' not in content:
            return table_data

        lines = content.split('\n')
        in_table = False
        table_lines = []

        # 提取表格部分
        for line in lines:
            if '+-' in line:
                in_table = True
            if in_table:
                table_lines.append(line)

        print(f"  调试表格提取: 总行数={len(lines)}, 表格行数={len(table_lines)}")

        # 显示包含焦煤的表格行
        if table_lines:
            print(f"  调试: 查找焦煤相关行")
            for i, line in enumerate(table_lines):
                if '焦煤' in line:
                    print(f"    找到焦煤行{i}: {line[:70]}...")
                    break

        # 解析表格数据，先处理分合约的，再处理全部合约的
        specific_contracts_data = {}  # 分合约数据
        all_contracts_data = {}        # 全部合约数据

        for line in table_lines:
            # 检查是否有分合约信息
            contract_match = re.search(r'（([^）]+)）', line)
            contract_info = contract_match.group(1) if contract_match else None

            # 检查是否包含产品名称（使用最长匹配原则）
            matched_product = None
            for known_product in sorted(self.product_codes.keys(), key=len, reverse=True):
                if known_product in line:
                    matched_product = known_product
                    break

            if matched_product:
                # 在同一行中提取数值
                values = re.findall(r'(\d+)%', line)
                if len(values) >= 3:
                    # 生成数据键
                    if contract_info:
                        # 分合约数据
                        data_key = f"{matched_product}（{contract_info}）"
                        specific_contracts_data[data_key] = {
                            'limit': values[0] + '%',
                            'margin_spec': values[1] + '%',
                            'margin_hedge': values[2] + '%',
                            'contracts': contract_info
                        }
                    else:
                        # 全部合约数据（只有在没有分合约版本时才记录）
                        base_key = matched_product
                        if base_key not in specific_contracts_data:
                            all_contracts_data[base_key] = {
                                'limit': values[0] + '%',
                                'margin_spec': values[1] + '%',
                                'margin_hedge': values[2] + '%',
                                'contracts': None
                            }

        print(f"  调试parse_table_data: 表格行数={len(table_lines)}, 分合约数据={len(specific_contracts_data)}, 全部合约数据={len(all_contracts_data)}")

        # 合并数据：分合约数据优先，然后是全部合约数据
        table_data = {}
        table_data.update(specific_contracts_data)
        table_data.update(all_contracts_data)

        return table_data

    def extract_table_parameters(self):
        """从所有公告和表格文件中提取表格参数数据"""
        all_table_data = {}

        # 先处理JSON公告（较简单）
        for announcement in self.announcements:
            content = announcement.get('content', '')
            table_data = self.parse_table_data(content)
            all_table_data.update(table_data)

        # 处理单独的表格文件（包含分合约信息）
        # 劳动节表格优先，先处理劳动节
        if hasattr(self, 'labor_day_table'):
            labor_data = self.parse_table_file(self.labor_day_table)
            # 劳动节数据包含分合约信息，优先添加
            for key, value in labor_data.items():
                all_table_data[key] = value
            print(f"从劳动节表格提取了 {len(labor_data)} 个品种参数")

        if hasattr(self, 'spring_festival_table'):
            spring_data = self.parse_table_file(self.spring_festival_table)
            # 只添加不在all_table_data中的品种（劳动节数据优先）
            for key, value in spring_data.items():
                if key not in all_table_data:
                    all_table_data[key] = value
            print(f"从春节表格提取了 {len(spring_data)} 个品种参数")

        self.base_parameters = all_table_data
        print(f"总共提取了 {len(all_table_data)} 个品种参数（包含分合约）")

        # 分别统计全部合约和分合约
        all_contracts_count = sum(1 for v in all_table_data.values() if not v.get('contracts'))
        specific_count = sum(1 for v in all_table_data.values() if v.get('contracts'))
        print(f"  其中: {all_contracts_count} 个全部合约品种, {specific_count} 个分合约参数")

        # 显示分合约参数
        print("\n分合约参数明细:")
        for product, params in sorted(all_table_data.items()):
            if params.get('contracts'):
                contract_info = params.get('contracts')
                print(f"  {product}: 涨跌停板={params['limit']}, 投机={params['margin_spec']}, 保值={params['margin_hedge']}, 合约={contract_info}")

        return all_table_data

    def generate_all_contracts(self, product_code):
        """生成该产品的所有合约（用于表格数据，不需要考虑过期）"""
        all_contracts = []
        for year in ['26', '27']:
            for month in range(1, 13):
                if year == '27' and month > 3:
                    continue
                month_str = str(month).zfill(2)
                contract = f'{product_code}{year}{month_str}'
                all_contracts.append(contract)
        return sorted(all_contracts)

    def organize_table_data(self):
        """整理表格数据并按结构输出"""
        if not self.base_parameters:
            print("没有基准参数数据，请先运行 extract_table_parameters()")
            return

        print(f"  调试organize_table_data: 开始处理 {len(self.base_parameters)} 个数据键")

        # 创建输出目录结构
        self.output_dir.mkdir(exist_ok=True)

        # 为每个产品-合约创建文件夹和文件
        for data_key, params in self.base_parameters.items():
            # 解析产品名称和合约信息
            product_name = data_key
            specific_contracts = None
            is_other_contracts = False

            # 检查是否有分合约信息
            if '（' in data_key and '）' in data_key:
                product_name = data_key.split('（')[0]
                contract_str = params.get('contracts', '')
                if contract_str:
                    # 检查是否是"其他合约"
                    if '其他' in contract_str:
                        is_other_contracts = True
                        # 对于"其他合约"，需要找出已明确指定的合约
                        existing_contracts = []
                        for other_key in self.base_parameters.keys():
                            if other_key.startswith(product_name) and '（' in other_key and '）' in other_key:
                                other_params = self.base_parameters[other_key]
                                other_contracts_str = other_params.get('contracts', '')
                                if other_contracts_str and '其他' not in other_contracts_str:
                                    existing_contracts.extend(re.findall(r'(\d{4})', other_contracts_str))

                        # 生成所有合约并排除已指定的
                        all_contracts = self.generate_all_contracts(self.product_codes.get(product_name, ''))
                        # 排除已指定的合约
                        specific_contracts = []
                        for contract in all_contracts:
                            year_month = contract[-4:]
                            if year_month not in existing_contracts:
                                specific_contracts.append(year_month)
                    else:
                        # 解析合约列表，如 "2605、2606、2607、2608、2609合约"
                        specific_contracts = re.findall(r'(\d{4})', contract_str)
                        print(f"  处理分合约数据: {product_name} -> {specific_contracts}")

            product_code = self.product_codes.get(product_name)
            if not product_code:
                continue

            product_dir = self.output_dir / product_name
            product_dir.mkdir(exist_ok=True)

            # 确定要处理的合约列表
            if specific_contracts:
                # 有特定合约列表
                contracts_to_process = []
                for year_month in specific_contracts:
                    year = year_month[:2]
                    month = year_month[2:]
                    contract = f'{product_code}{year}{month}'
                    contracts_to_process.append(contract)

                if is_other_contracts:
                    print(f"    处理其他合约: {contracts_to_process}")
                else:
                    print(f"    将处理合约: {contracts_to_process} 参数: {params['limit']}/{params['margin_spec']}/{params['margin_hedge']}")
            else:
                # 全部合约
                contracts_to_process = self.generate_all_contracts(product_code)

            for contract in contracts_to_process:
                contract_dir = product_dir / contract

                # 如果目录不存在，创建它
                if not contract_dir.exists():
                    contract_dir.mkdir(exist_ok=True)

                # 写入基准参数文件（添加到现有目录）
                params_file = contract_dir / "基准参数.txt"
                with open(params_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {product_name} - {contract} 基准参数\n\n")
                    f.write(f"【产品名称】{product_name}\n")
                    f.write(f"【合约代码】{contract}\n")
                    f.write(f"【涨跌停板幅度】{params['limit']}\n")
                    f.write(f"【投机交易保证金】{params['margin_spec']}\n")
                    f.write(f"【套期保值交易保证金】{params['margin_hedge']}\n")

                    if specific_contracts:
                        f.write(f"\n说明：此为该品种特定合约的基准参数，来源于交易所公告表格数据。\n")
                        f.write(f"适用合约: {', '.join([f'{product_code}{c}' for c in specific_contracts])}\n")
                    elif is_other_contracts:
                        f.write(f"\n说明：此为该品种其他合约的基准参数，来源于交易所公告表格数据。\n")
                    else:
                        f.write(f"\n说明：此为该品种的标准基准参数，来源于交易所公告表格数据。\n")

                print(f"已添加: {params_file}")

        print(f"\n表格数据整理完成！")
        print(f"输出目录: {self.output_dir}")


def main():
    """主函数"""
    input_file = "/home/liyuexuan/下载/最终爬取结果_输出数据/zhetin_optimized.json"
    output_dir = "/home/liyuexuan/期货数据完整结果"  # 修改为输出到现有目录
    spring_festival_table = "/home/liyuexuan/下载/测试结果_1222.txt"
    labor_day_table = "/home/liyuexuan/下载/关于2026年劳动节假期调整相关品种期货合约涨跌停板幅度和交_1222.txt"

    parser = FuturesTableParser(input_file, output_dir)
    parser.load_data()
    parser.load_table_files(spring_festival_table, labor_day_table)
    parser.extract_table_parameters()
    parser.organize_table_data()


if __name__ == "__main__":
    main()