#!/usr/bin/env python3
"""
大连商品交易所API客户端 v3
按照图片要求：每日15:30收盘后获取持仓CSV并分析次日指令
"""

import os
import csv
import json
import time
import logging
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/liyuexuan/dce-futures-crawler/logs/crawler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DCEAPIClient:
    """大连商品交易所API客户端 - 完整版本"""

    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.base_url = self.config['dce']['base_url']
        self.endpoints = self.config['dce']['endpoints']
        self.token = None
        self.token_expires_at = None

    def _load_config(self, config_path: str) -> Dict:
        config_file = Path(__file__).parent.parent / config_path
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            'Content-Type': 'application/json',
            'apikey': self.config['dce']['api_key']
        }
        if self.token:
            headers['Authorization'] = f"Bearer {self.token}"
        return headers

    def login(self) -> bool:
        """登录获取访问令牌"""
        url = f"{self.base_url}{self.endpoints['login']}"
        headers = {
            'Content-Type': 'application/json',
            'apikey': self.config['dce']['api_key']
        }
        payload = {"secret": self.config['dce']['api_secret']}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.token = data['data']['token']
                    self.token_expires_at = time.time() + data['data']['expiresIn']
                    logger.info(f"✅ 登录成功")
                    return True
            logger.error(f"❌ 登录失败: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"❌ 登录异常: {e}")
            return False

    def get_daily_position_ranking(self, variety_id: str, trade_date: str, contract_id: str) -> Optional[Dict]:
        """获取日成交持仓排名"""
        if not self.token:
            if not self.login():
                return None

        url = f"{self.base_url}{self.endpoints['daily_position']}"
        headers = self._get_headers()

        payload = {
            "varietyId": variety_id,
            "tradeDate": trade_date,
            "contractId": contract_id,
            "tradeType": "1"
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data
            return None
        except Exception as e:
            logger.error(f"请求异常: {e}")
            return None

    def save_to_csv(self, data: Dict, variety_id: str, contract_id: str, trade_date: str) -> bool:
        """保存持仓数据到CSV文件"""
        if not data or not data.get('success'):
            return False

        result = data['data']
        qty_list = result.get('qtyFutureList', [])
        buy_list = result.get('buyFutureList', [])
        sell_list = result.get('sellFutureList', [])

        # 按照图片要求的数据目录结构
        # data/dce/[品种]/[合约代码]/[日期].csv
        variety_dir = Path(f"/home/liyuexuan/dce-futures-crawler/data/dce/{variety_id}/{contract_id}")
        variety_dir.mkdir(parents=True, exist_ok=True)

        csv_file = variety_dir / f"{trade_date}.csv"

        # CSV格式：排名,会员简称,成交量,成交量变化,持买单量,买单变化,持卖单量,卖单变化
        csv_rows = []
        csv_rows.append(['排名', '会员简称', '成交量', '成交量变化', '持买单量', '买单变化', '持卖单量', '卖单变化'])

        max_rank = max(len(qty_list), len(buy_list), len(sell_list))

        for i in range(max_rank):
            qty = qty_list[i] if i < len(qty_list) else {}
            buy = buy_list[i] if i < len(buy_list) else {}
            sell = sell_list[i] if i < len(sell_list) else {}

            row = [
                i + 1,
                qty.get('qtyAbbr', ''),
                qty.get('todayQty', ''),
                qty.get('qtySub', ''),
                buy.get('todayBuyQty', ''),
                buy.get('buySub', ''),
                sell.get('todaySellQty', ''),
                sell.get('sellSub', '')
            ]
            csv_rows.append(row)

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(csv_rows)

        logger.info(f"  ✅ 已保存: {csv_file}")
        return True

    def check_delivery_month_warning(self, contract_id: str, current_date: datetime) -> Dict[str, Any]:
        """
        检查交割月预警
        图片要求：自然人不得持有进入交割月的合约，避免强制平仓
        """
        # 解析合约代码：a2509 -> 品种a, 2025年09月
        variety = contract_id[:2] if contract_id[1].isalpha() else contract_id[0]
        year = int(contract_id[-4:-2])
        month = int(contract_id[-2:])

        contract_date = datetime(year + 2000, month, 1)
        months_diff = (contract_date.year - current_date.year) * 12 + (contract_date.month - current_date.month)

        warning = None
        if months_diff <= 1:
            warning = f"⚠️ 警告：合约{contract_id}进入交割月或临近交割月！自然人不得持有，将面临强制平仓风险！"
        elif months_diff <= 2:
            warning = f"⚠️ 提示：合约{contract_id}临近交割月（{months_diff}个月后），请注意风险"

        return {
            "contract_id": contract_id,
            "delivery_month": f"{year+2000}-{month:02d}",
            "months_to_delivery": months_diff,
            "warning": warning
        }

    def analyze_next_day_instruction(self, data: Dict) -> Dict[str, Any]:
        """
        分析次日指令
        图片要求：每日15:30收盘后获取持仓CSV并分析次日指令
        注意：仅聚焦合规性检查，禁止提供交易策略建议
        """
        if not data or not data.get('success'):
            return {"error": "无有效数据"}

        result = data['data']
        qty_list = result.get('qtyFutureList', [])
        buy_list = result.get('buyFutureList', [])
        sell_list = result.get('sellFutureList', [])

        # 合规性分析：检查持仓集中度
        total_volume = sum(item.get('todayQty', 0) for item in qty_list)
        top3_volume = sum(qty_list[i].get('todayQty', 0) for i in range(min(3, len(qty_list))))

        concentration_ratio = (top3_volume / total_volume * 100) if total_volume > 0 else 0

        analysis = {
            "total_volume": total_volume,
            "top3_concentration": f"{concentration_ratio:.1f}%",
            "ranking_count": len(qty_list),
            "compliance_note": "数据来自大商所官方API，符合合规要求"
        }

        # 添加集中度预警
        if concentration_ratio > 50:
            analysis["concentration_warning"] = f"⚠️ 持仓集中度较高({concentration_ratio:.1f}%)，前3名会员占比超过50%"

        return analysis

    def run_daily_collection(self, trade_date: str = None) -> Dict[str, Any]:
        """
        执行每日数据收集任务
        图片要求的核心功能：每日15:30收盘后获取持仓CSV
        """
        if not trade_date:
            today = datetime.now()
            # 如果是周末，使用上周五
            if today.weekday() >= 5:
                days_back = today.weekday() - 4
                today = today - timedelta(days=days_back)
            trade_date = today.strftime("%Y%m%d")

        logger.info(f"=== 开始执行每日数据收集 ({trade_date}) ===")
        logger.info("时间：模拟每日15:30收盘后执行")

        if not self.login():
            return {"success": False, "error": "登录失败"}

        # 当前主要活跃合约（2025年9月、11月、12月）
        active_contracts = [
            ('i', 'i2509', '铁矿石'),
            ('i', 'i2511', '铁矿石'),
            ('m', 'm2509', '豆粕'),
            ('m', 'm2511', '豆粕'),
            ('y', 'y2509', '豆油'),
            ('y', 'y2511', '豆油'),
            ('p', 'p2509', '棕榈油'),
            ('p', 'p2511', '棕榈油'),
            ('a', 'a2509', '黄大豆1号'),
            ('a', 'a2511', '黄大豆1号'),
            ('c', 'c2509', '玉米'),
            ('c', 'c2511', '玉米'),
            ('jd', 'jd2509', '鸡蛋'),
            ('lh', 'lh2511', '生猪'),
            ('pp', 'pp2509', '聚丙烯'),
            ('l', 'l2509', '聚乙烯'),
            ('v', 'v2509', '聚氯乙烯'),
            ('eg', 'eg2509', '乙二醇'),
            ('pg', 'pg2511', '液化石油气')
        ]

        results = {
            "trade_date": trade_date,
            "collection_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_contracts": len(active_contracts),
            "successful": 0,
            "failed": 0,
            "warnings": [],
            "contracts": []
        }

        current_date = datetime.now()

        for variety_id, contract_id, variety_name in active_contracts:
            logger.info(f"\n获取 {variety_name} {contract_id} 持仓数据...")

            # 检查交割月风险
            delivery_check = self.check_delivery_month_warning(contract_id, current_date)
            if delivery_check["warning"]:
                logger.warning(delivery_check["warning"])
                if delivery_check["warning"] not in results["warnings"]:
                    results["warnings"].append(delivery_check["warning"])

            # 获取持仓数据
            data = self.get_daily_position_ranking(variety_id, trade_date, contract_id)

            contract_result = {
                "variety": variety_name,
                "contract_id": contract_id,
                "success": False
            }

            if data and data.get('success'):
                result = data['data']
                has_data = any([
                    result.get('qtyFutureList'),
                    result.get('buyFutureList'),
                    result.get('sellFutureList')
                ])

                if has_data:
                    # 保存CSV
                    if self.save_to_csv(data, variety_id, contract_id, trade_date):
                        results["successful"] += 1
                        contract_result["success"] = True

                        # 分析次日指令（合规性检查）
                        analysis = self.analyze_next_day_instruction(data)
                        contract_result["analysis"] = analysis

                        logger.info(f"  总成交量: {analysis['total_volume']}, 集中度: {analysis['top3_concentration']}")
                        if "concentration_warning" in analysis:
                            logger.warning(f"  {analysis['concentration_warning']}")
                else:
                    logger.info(f"  ℹ️ 该合约暂无持仓数据")
            else:
                results["failed"] += 1
                logger.error(f"  ❌ 获取失败")

            results["contracts"].append(contract_result)
            time.sleep(0.3)  # 避免触发API限流

        # 生成总结报告
        logger.info(f"\n=== 数据收集完成 ===")
        logger.info(f"总计合约: {results['total_contracts']}")
        logger.info(f"成功获取: {results['successful']}")
        logger.info(f"获取失败: {results['failed']}")

        if results["warnings"]:
            logger.warning(f"\n⚠️ 风险预警 ({len(results['warnings'])}条):")
            for warning in results["warnings"]:
                logger.warning(f"  {warning}")

        # 保存收集报告
        report_file = Path("/home/liyuexuan/dce-futures-crawler/logs/collection_report.json")
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"\n收集报告已保存: {report_file}")

        return results


def main():
    """主函数 - 执行每日数据收集任务"""
    logger.info("╔════════════════════════════════════════╗")
    logger.info("║   大连商品交易所持仓数据收集系统      ║")
    logger.info("║   每日15:30收盘后获取持仓CSV          ║")
    logger.info("╚════════════════════════════════════════╝")

    client = DCEAPIClient()

    # 执行每日数据收集（使用昨天的日期，因为今天的数据可能还没发布）
    yesterday = datetime.now() - timedelta(days=1)
    trade_date = yesterday.strftime("%Y%m%d")

    results = client.run_daily_collection(trade_date)

    logger.info("\n=== 任务执行完毕 ===")


if __name__ == "__main__":
    main()
