#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026年第一季度大商所公告参数变化监控 - 修复版
修复参数解析和品种匹配问题
"""

import json
from datetime import datetime
from typing import Dict, List
import re

class Q12026AnnouncementMonitor:
    """2026年第一季度公告监控 - 修复版"""

    def __init__(self):
        # 2026年第一季度模拟公告数据
        self.q1_announcements = [
            # 春节期间调整公告
            {
                "id": "20260115_001",
                "title": "关于2026年春节期间调整涨跌停板幅度和交易保证金的通知",
                "date": "2026-01-15",
                "effective_date": "2026-01-24",
                "content": """
                2026年春节临近，为做好节假日风险工作，经研究决定，自2026年1月24日（星期日）结算时起：

                豆粕期货M2603合约涨跌停板幅度调整为8%，交易保证金调整为10%；
                豆油期货Y2603合约涨跌停板幅度调整为8%，交易保证金调整为10%；
                棕榈油期货P2603合约涨跌停板幅度调整为9%，交易保证金调整为11%；
                铁矿石期货I2603合约涨跌停板幅度调整为11%，交易保证金调整为13%；
                焦炭期货J2603合约涨跌停板幅度调整为10%，交易保证金调整为12%。

                2026年2月4日（星期三）恢复交易后，自各品种持仓量最大的合约未出现涨跌停板单边无连续报价的第一个交易日结算时起，
                豆粕、豆油期货合约涨跌停板幅度恢复至4%，交易保证金恢复至5%；
                棕榈油期货合约涨跌停板幅度恢复至7%，交易保证金恢复至8%；
                铁矿石期货合约涨跌停板幅度恢复至8%，交易保证金恢复至9%；
                焦炭期货合约涨跌停板幅度恢复至8%，交易保证金恢复至10%。
                """,
                "type": "holiday_adjustment",
                "importance": "high"
            },
            # 新合约上市公告
            {
                "id": "20260210_002",
                "title": "关于发布大豆原木等期货合约及业务细则的通知",
                "date": "2026-02-10",
                "effective_date": "2026-03-01",
                "content": """
                经研究决定，自2026年3月1日起上市大豆原木期货合约，合约参数如下：

                大豆原木期货合约：
                交易单位：10吨/手
                报价单位：元（人民币）/吨
                最小变动价位：2元/吨
                涨跌停板幅度：不超过上一交易日结算价±4%
                最低交易保证金：合约价值的5%
                合约月份：1、3、5、7、9、11月
                交易手续费：4元/手

                现已挂牌大豆原木期货2610、2611合约。
                """,
                "type": "new_contract",
                "importance": "medium"
            },
            # 手续费调整公告
            {
                "id": "20260218_003",
                "title": "关于调整部分品种交易手续费收取标准的通知",
                "date": "2026-02-18",
                "effective_date": "2026-02-25",
                "content": """
                为促进市场健康发展，经研究决定，自2026年2月25日起：

                1. 聚乙烯期货L2605、L2607、L2609合约交易手续费调整为成交金额的万分之一；
                2. 聚丙烯期货PP2605、PP2607、PP2609合约交易手续费调整为成交金额的万分之一点二；
                3. 聚氯乙烯期货V2605、V2607、V2609合约交易手续费调整为成交金额的万分之一；
                4. 玉米期货C2605、C2607、C2609合约日内交易手续费减半收取。

                现行手续费标准高于上述标准的，仍按现行规定执行。
                """,
                "type": "fee_adjustment",
                "importance": "medium"
            },
            # 保证金调整公告
            {
                "id": "20260305_004",
                "title": "关于调整铁矿石期货合约交易保证金的通知",
                "date": "2026-03-05",
                "effective_date": "2026-03-12",
                "content": """
                近期铁矿石市场波动加大，为防范市场风险，经研究决定：

                自2026年3月12日（星期五）结算时起：
                铁矿石期货I2606、I2609合约交易保证金调整为12%，涨跌停板幅度调整为10%。

                如遇上述交易保证金比例、涨跌停板幅度与执行的交易保证金比例、涨跌停板幅度不同时，
                则按两者中比例高、幅度大的执行。
                """,
                "type": "risk_management",
                "importance": "high"
            },
            # 品种细则修订
            {
                "id": "20260320_005",
                "title": "关于修订豆粕期货合约及相关规则的通知",
                "date": "2026-03-20",
                "effective_date": "2026-04-01",
                "content": """
                为优化合约结构，经研究决定，对豆粕期货合约进行如下修订：

                自豆粕M2609合约起：
                最小变动价位由2元/吨调整为1元/吨；
                交易单位保持30吨/手不变；
                涨跌停板幅度保持4%不变；
                最低交易保证金保持5%不变；
                交易手续费保持4元/手不变。

                该修订将自2026年4月1日起实施。
                """,
                "type": "contract_revision",
                "importance": "medium"
            },
            # 临时风控措施
            {
                "id": "20260325_006",
                "title": "关于对部分品种实施交易限额的通知",
                "date": "2026-03-25",
                "effective_date": "2026-03-27",
                "content": """
                近期部分品种交易过度活跃，为维护市场稳定，经研究决定：

                自2026年3月27日起：
                对鸡蛋期货JD2605、JD2606合约实施交易限额：
                非期货公司会员和客户在鸡蛋期货JD2605、JD2606合约上
                每日开仓交易不得超过500手。

                套期保值交易和做市商交易不适用本通知限制。
                """,
                "type": "position_limit",
                "importance": "high"
            }
        ]

        # 当前合约基础参数（2026年初）
        self.base_params = {
            'M': {'name': '豆粕', 'limit': '4%', 'margin': '5%', 'fee': '4元/手', 'tick': '2元/吨'},
            'Y': {'name': '豆油', 'limit': '4%', 'margin': '5%', 'fee': '4元/手', 'tick': '2元/吨'},
            'P': {'name': '棕榈油', 'limit': '7%', 'margin': '8%', 'fee': '4元/手', 'tick': '2元/吨'},
            'I': {'name': '铁矿石', 'limit': '8%', 'margin': '9%', 'fee': '成交额的万分之一', 'tick': '0.5元/吨'},
            'J': {'name': '焦炭', 'limit': '8%', 'margin': '10%', 'fee': '成交额的万分之一点五', 'tick': '0.5元/吨'},
            'L': {'name': '聚乙烯', 'limit': '4%', 'margin': '5%', 'fee': '6元/手', 'tick': '5元/吨'},
            'PP': {'name': '聚丙烯', 'limit': '4%', 'margin': '5%', 'fee': '6元/手', 'tick': '1元/吨'},
            'V': {'name': '聚氯乙烯', 'limit': '4%', 'margin': '5%', 'fee': '4元/手', 'tick': '2元/吨'},
            'C': {'name': '玉米', 'limit': '4%', 'margin': '5%', 'fee': '3元/手', 'tick': '1元/吨'},
            'JD': {'name': '鸡蛋', 'limit': '4%', 'margin': '6%', 'fee': '6元/手', 'tick': '1元/吨'},
            'WW': {'name': '大豆原木', 'limit': '4%', 'margin': '5%', 'fee': '4元/手', 'tick': '2元/吨', 'status': 'new'}
        }

        # 品种名称到代码的映射
        self.variety_map = {
            '豆粕': 'M', '豆油': 'Y', '棕榈油': 'P', '铁矿石': 'I',
            '焦炭': 'J', '聚乙烯': 'L', '聚丙烯': 'PP', '聚氯乙烯': 'V',
            '玉米': 'C', '鸡蛋': 'JD', '大豆原木': 'WW'
        }

    def parse_single_rule(self, rule_text: str) -> Dict:
        """解析单条规则，提取品种和参数变化"""
        result = {
            'variety': None,
            'contracts': [],
            'changes': {}
        }

        # 提取品种名称
        for variety_name in self.variety_map.keys():
            if variety_name in rule_text:
                result['variety'] = self.variety_map[variety_name]
                break

        if not result['variety']:
            return None

        # 提取合约代码
        contract_pattern = r'([A-Za-z]+\d{4})'
        contracts = re.findall(contract_pattern, rule_text)
        result['contracts'] = contracts

        # 提取涨跌停板
        limit_match = re.search(r'涨跌停板[^。]*?调整为(\d+)%', rule_text)
        if limit_match:
            result['changes']['limit'] = f"{limit_match.group(1)}%"

        # 恢复条款中的涨跌停板
        restore_limit_match = re.search(r'涨跌停板[^。]*?恢复至(\d+)%', rule_text)
        if restore_limit_match:
            result['changes']['limit_restore'] = f"{restore_limit_match.group(1)}%"

        # 提取保证金
        margin_match = re.search(r'交易保证金[^。]*?调整为(\d+)%', rule_text)
        if margin_match:
            result['changes']['margin'] = f"{margin_match.group(1)}%"

        # 恢复条款中的保证金
        restore_margin_match = re.search(r'交易保证金[^。]*?恢复至(\d+)%', rule_text)
        if restore_margin_match:
            result['changes']['margin_restore'] = f"{restore_margin_match.group(1)}%"

        # 提取手续费
        fee_match = re.search(r'交易手续费[^。]*?调整为([^。;]+)[。;]?', rule_text)
        if fee_match:
            result['changes']['fee'] = fee_match.group(1).strip()

        # 提取最小变动价位
        tick_match = re.search(r'最小变动价位[^。]*?调整为([^。]+)', rule_text)
        if tick_match:
            result['changes']['tick'] = tick_match.group(1).strip()

        return result if result['changes'] else None

    def parse_announcement(self, announcement: Dict) -> Dict:
        """解析单个公告，提取参数变化"""
        parsed = {
            'id': announcement['id'],
            'title': announcement['title'],
            'date': announcement['date'],
            'effective_date': announcement.get('effective_date', announcement['date']),
            'type': announcement['type'],
            'importance': announcement['importance'],
            'contract_changes': []
        }

        content = announcement['content']
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue

            # 跳过非规则行
            if any(keyword in line for keyword in ['经研究决定', '自2026年', '合约如下：', '现已挂牌', '为促进市场', '近期', '套期保值']):
                continue

            # 尝试解析为规则
            rule = self.parse_single_rule(line)
            if rule:
                parsed['contract_changes'].append({
                    'contract': rule['variety'],
                    'contracts_detail': rule['contracts'],
                    'param_type': list(rule['changes'].keys())[0] if rule['changes'] else None,
                    'new_value': list(rule['changes'].values())[0] if rule['changes'] else None,
                    'change_context': line,
                    'all_changes': rule['changes']
                })

        return parsed

    def analyze_changes(self) -> Dict:
        """分析所有公告的变化"""
        analysis = {
            'period': '2026年第一季度',
            'total_announcements': len(self.q1_announcements),
            'high_importance_count': 0,
            'affected_varieties': set(),
            'change_summary': {
                'holiday_adjustments': [],
                'fee_changes': [],
                'risk_measures': [],
                'contract_revisions': [],
                'new_contracts': []
            },
            'detailed_changes': []
        }

        for announcement in self.q1_announcements:
            parsed = self.parse_announcement(announcement)

            if parsed['importance'] == 'high':
                analysis['high_importance_count'] += 1

            # 按类型分类
            category_map = {
                'holiday_adjustment': 'holiday_adjustments',
                'fee_adjustment': 'fee_changes',
                'risk_management': 'risk_measures',
                'contract_revision': 'contract_revisions',
                'new_contract': 'new_contracts'
            }

            category_key = category_map.get(parsed['type'])
            if category_key:
                analysis['change_summary'][category_key].append(parsed)

            # 收集涉及的品种
            for change in parsed['contract_changes']:
                if change['contract']:
                    analysis['affected_varieties'].add(change['contract'])

            analysis['detailed_changes'].append(parsed)

        analysis['affected_varieties'] = sorted(list(analysis['affected_varieties']))

        return analysis

    def generate_comparison_table(self) -> Dict:
        """生成参数比对表"""
        comparison = {
            'period': '2026年第一季度',
            'contracts': {}
        }

        for announcement in self.q1_announcements:
            parsed = self.parse_announcement(announcement)

            for change in parsed['contract_changes']:
                variety_code = change['contract']
                if not variety_code or variety_code not in self.base_params:
                    continue

                # 获取该品种的所有变化
                for param_type, new_value in change['all_changes'].items():
                    # 处理恢复类型的参数
                    if '_restore' in param_type:
                        base_param = param_type.replace('_restore', '')
                        final_value = new_value
                        change_type = f'{base_param}_restore'
                    else:
                        base_param = param_type
                        final_value = new_value
                        change_type = param_type

                    if variety_code not in comparison['contracts']:
                        base = self.base_params[variety_code]
                        comparison['contracts'][variety_code] = {
                            'variety_name': base['name'],
                            'base_params': {
                                'limit': base['limit'],
                                'margin': base['margin'],
                                'fee': base['fee'],
                                'tick': base.get('tick', 'N/A')
                            },
                            'changes': []
                        }

                    comparison['contracts'][variety_code]['changes'].append({
                        'param': change_type,
                        'new_value': final_value,
                        'announcement_title': parsed['title'],
                        'effective_date': parsed['effective_date'],
                        'importance': parsed['importance'],
                        'context': change['change_context']
                    })

        return comparison

    def format_report(self, analysis: Dict, comparison: Dict) -> str:
        """生成格式化报告"""
        lines = []
        lines.append("=" * 80)
        lines.append("📊 2026年第一季度大商所公告参数变化分析报告（修复版）")
        lines.append("=" * 80)
        lines.append(f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"分析期间：2026-01-01 至 2026-03-31")
        lines.append("")

        # 总体概况
        lines.append("📋 总体概况")
        lines.append("-" * 80)
        lines.append(f"• 公告总数：{analysis['total_announcements']} 条")
        lines.append(f"• 高重要性公告：{analysis['high_importance_count']} 条")
        lines.append(f"• 涉及品种数：{len(analysis['affected_varieties'])} 个")
        lines.append(f"• 涉及品种：{', '.join([self.base_params.get(v, {}).get('name', v) for v in analysis['affected_varieties']])}")
        lines.append("")

        # 参数比对表
        lines.append("📊 详细参数比对表")
        lines.append("-" * 80)

        # 表头
        lines.append("┌" + "─" * 78 + "┐")
        lines.append("│ {:12s} │ {:10s} │ {:10s} │ {:10s} │ {:12s} │ {:12s} │".format(
            "品种", "原涨跌停", "新涨跌停", "原保证金", "新保证金", "生效日期", "变化类型"
        ))
        lines.append("├" + "─" * 78 + "┤")

        for variety_code in sorted(comparison['contracts'].keys()):
            data = comparison['contracts'][variety_code]
            base = data['base_params']

            # 按生效日期分组变化
            changes_by_date = {}
            for change in data['changes']:
                date_key = change['effective_date']
                if date_key not in changes_by_date:
                    changes_by_date[date_key] = {}
                changes_by_date[date_key][change['param']] = change['new_value']

            for date in sorted(changes_by_date.keys()):
                changes = changes_by_date[date]
                new_limit = changes.get('limit', changes.get('limit_restore', '-'))
                new_margin = changes.get('margin', changes.get('margin_restore', '-'))

                # 确定变化类型
                change_types = []
                if 'limit' in changes or 'limit_restore' in changes:
                    change_types.append('涨跌停板')
                if 'margin' in changes or 'margin_restore' in changes:
                    change_types.append('保证金')
                if 'fee' in changes:
                    change_types.append('手续费')
                if 'tick' in changes:
                    change_types.append('最小价位')

                change_type_str = '+'.join(change_types) if change_types else '-'

                lines.append("│ {:12s} │ {:10s} │ {:10s} │ {:10s} │ {:12s} │ {:12s} │".format(
                    data['variety_name'],
                    base['limit'],
                    new_limit,
                    base['margin'],
                    new_margin,
                    date,
                    change_type_str
                ))

        lines.append("└" + "─" * 78 + "┘")

        # 重要变化详细说明
        lines.append("\n🚨 重要变化详细说明")
        lines.append("-" * 80)

        # 春节调整详情
        if analysis['change_summary']['holiday_adjustments']:
            item = analysis['change_summary']['holiday_adjustments'][0]
            lines.append("\n【春节假期风控调整】")
            lines.append(f"生效日期：{item['effective_date']}")

            # 按品种整理
            variety_changes = {}
            for change in item['contract_changes']:
                variety = change['contract']
                if variety not in variety_changes:
                    variety_changes[variety] = {'name': self.base_params.get(variety, {}).get('name', variety), 'changes': {}}

                for param, value in change['all_changes'].items():
                    if '_restore' not in param:  # 只显示调整，不显示恢复
                        variety_changes[variety]['changes'][param] = value

            for variety, data in sorted(variety_changes.items(), key=lambda x: x[1]['name']):
                lines.append(f"\n{data['name']}（{variety}）:")
                for param, value in sorted(data['changes'].items()):
                    param_name = {'limit': '涨跌停板', 'margin': '保证金', 'fee': '手续费', 'tick': '最小价位'}.get(param, param)
                    lines.append(f"  • {param_name}：{self.base_params[variety][param.replace('limit', 'limit').replace('margin', 'margin').replace('fee', 'fee').replace('tick', 'tick')]} → {value}")

        # 铁矿石风控
        if analysis['change_summary']['risk_measures']:
            item = analysis['change_summary']['risk_measures'][0]
            lines.append(f"\n【铁矿石风险控制】")
            lines.append(f"生效日期：{item['effective_date']}")

            for change in item['contract_changes']:
                if change['contract'] == 'I':
                    lines.append(f"铁矿石（{change['contract']}）:")
                    for param, value in change['all_changes'].items():
                        param_name = {'limit': '涨跌停板', 'margin': '保证金'}.get(param, param)
                        lines.append(f"  • {param_name}：{self.base_params['I'][param]} → {value}")

        # 手续费调整
        if analysis['change_summary']['fee_changes']:
            item = analysis['change_summary']['fee_changes'][0]
            lines.append(f"\n【手续费调整】")
            lines.append(f"生效日期：{item['effective_date']}")

            variety_fees = {}
            for change in item['contract_changes']:
                variety = change['contract']
                if variety and 'fee' in change['all_changes']:
                    variety_fees[variety] = change['all_changes']['fee']

            for variety, fee in sorted(variety_fees.items()):
                name = self.base_params.get(variety, {}).get('name', variety)
                old_fee = self.base_params.get(variety, {}).get('fee', 'N/A')
                lines.append(f"  • {name}（{variety}）：{old_fee} → {fee}")

        # 新合约
        if analysis['change_summary']['new_contracts']:
            item = analysis['change_summary']['new_contracts'][0]
            lines.append(f"\n【新品种上市】")
            lines.append(f"上市日期：{item['effective_date']}")
            lines.append(f"新品种：大豆原木（WW）")
            lines.append(f"  • 涨跌停板：±4%")
            lines.append(f"  • 保证金：5%")
            lines.append(f"  • 手续费：4元/手")
            lines.append(f"  • 最小变动价位：2元/吨")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    def save_results(self, analysis: Dict, comparison: Dict):
        """保存结果文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_path = f"/Users/tony/Desktop/工作文件"

        # 保存详细JSON
        detailed_file = f"{base_path}/Q1_2026_detailed_analysis_FIXED_{timestamp}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump({
                'analysis': analysis,
                'comparison': comparison
            }, f, ensure_ascii=False, indent=2)

        # 保存简化版
        simplified_file = f"{base_path}/Q1_2026_simplified_rules_FIXED_{timestamp}.json"
        simplified_data = {
            'period': '2026年第一季度',
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_announcements': analysis['total_announcements'],
                'high_importance_count': analysis['high_importance_count'],
                'affected_varieties': [self.base_params.get(v, {}).get('name', v) for v in analysis['affected_varieties']]
            },
            'contract_rules': {}
        }

        for contract, data in comparison['contracts'].items():
            simplified_data['contract_rules'][contract] = {
                'variety': data['variety_name'],
                'base_params': data['base_params'],
                'changes': []
            }

            # 按生效日期分组
            changes_by_date = {}
            for change in data['changes']:
                date_key = change['effective_date']
                if date_key not in changes_by_date:
                    changes_by_date[date_key] = {}
                changes_by_date[date_key][change['param']] = change['new_value']

            for date in sorted(changes_by_date.keys()):
                simplified_data['contract_rules'][contract]['changes'].append({
                    'effective_date': date,
                    'changes': changes_by_date[date]
                })

        with open(simplified_file, 'w', encoding='utf-8') as f:
            json.dump(simplified_data, f, ensure_ascii=False, indent=2)

        print(f"💾 详细分析已保存：{detailed_file}")
        print(f"💾 简化规则已保存：{simplified_file}")

        return detailed_file, simplified_file


def main():
    """主函数"""
    monitor = Q12026AnnouncementMonitor()

    print("🔍 正在分析2026年第一季度大商所公告参数变化（修复版）...")
    print("=" * 60)

    # 分析变化
    analysis = monitor.analyze_changes()

    # 生成比对表
    comparison = monitor.generate_comparison_table()

    # 生成报告
    report = monitor.format_report(analysis, comparison)
    print("\n" + report)

    # 保存结果
    monitor.save_results(analysis, comparison)

    print("\n✅ 2026年第一季度公告分析完成（参数匹配已修复）！")


if __name__ == "__main__":
    main()
