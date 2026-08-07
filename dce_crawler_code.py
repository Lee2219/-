#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大商所豆粕数据爬虫程序
用途: 爬取大连商品交易所豆粕期货的合约信息、公告通知等数据
"""

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager
import time
import json
import re

class DCECrawler:
    """大商所爬虫类"""

    def __init__(self, headless=True):
        """初始化爬虫"""
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.driver = None

    def start(self):
        """启动浏览器"""
        self.driver = webdriver.Firefox(
            service=Service(GeckoDriverManager().install()),
            options=self.options
        )
        print("✅ 浏览器启动成功")

    def stop(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("✅ 浏览器已关闭")

    def crawl_contract_specs(self):
        """爬取豆粕合约规格"""
        print("\n=== 爬取合约规格 ===")

        # 豆粕合约页面
        url = "http://www.dce.com.cn/dce/content/2023/hyygz000000000000000000000/1391326.html"
        self.driver.get(url)
        time.sleep(5)

        page_source = self.driver.page_source

        # 提取合约参数
        contract_data = {
            "交易单位": self._extract_text(page_source, "交易单位", "10吨/手"),
            "报价单位": self._extract_text(page_source, "报价单位", "元（人民币）/吨"),
            "最小变动价位": self._extract_text(page_source, "最小变动价位", "1元/吨"),
            "涨跌停板幅度": self._extract_text(page_source, "涨跌停板幅度", "上一交易日结算价的4%"),
            "合约月份": self._extract_text(page_source, "合约月份", "1,3,5,7,8,9,11,12月"),
            "交易时间": self._extract_text(page_source, "交易时间", "上午9:00-11:30，下午13:30-15:00"),
            "夜盘交易": "21:00-23:00",
            "交易代码": "M",
            "最低交易保证金": self._extract_text(page_source, "最低交易保证金", "合约价值的5％"),
            "交割方式": "实物交割"
        }

        print(f"  ✅ 获取到 {len(contract_data)} 项合约参数")
        return contract_data

    def crawl_notices(self, limit=5):
        """爬取豆粕相关公告"""
        print("\n=== 爬取豆粕公告 ===")

        # 公告列表页面
        url = "http://www.dce.com.cn/dce/channel/list/239.html"
        self.driver.get(url)
        time.sleep(5)

        # 查找所有链接
        links = self.driver.find_elements(By.TAG_NAME, 'a')
        meal_notices = []

        for link in links:
            text = link.text.strip()
            href = link.get_attribute('href')

            # 筛选豆粕相关的公告链接
            if href and '豆粕' in text and len(text) > 10:
                meal_notices.append({
                    "标题": text,
                    "链接": href
                })

                if len(meal_notices) >= limit:
                    break

        # 提取每条公告的详细内容
        detailed_notices = []
        for notice in meal_notices:
            print(f"  处理: {notice['标题'][:30]}...")

            try:
                self.driver.get(notice['链接'])
                time.sleep(5)

                # 提取公告正文（使用段落标签）
                paragraphs = self.driver.find_elements(By.TAG_NAME, 'p')
                content_paragraphs = []

                for p in paragraphs:
                    text = p.text.strip()
                    # 跳过导航和短文本
                    if len(text) > 20 and not any(skip in text for skip in ['首页', '上市品种', '返回']):
                        content_paragraphs.append(text)

                full_content = '\n'.join(content_paragraphs[:10])

                # 提取日期
                date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', full_content)
                publish_date = date_match.group(1) if date_match else ""

                notice_detail = {
                    "标题": notice['标题'],
                    "链接": notice['链接'],
                    "发布日期": publish_date,
                    "正文内容": full_content[:500] + "..." if len(full_content) > 500 else full_content
                }

                detailed_notices.append(notice_detail)
                print(f"    ✅ 提取成功")

            except Exception as e:
                print(f"    ❌ 提取失败: {e}")

        print(f"  ✅ 共获取 {len(detailed_notices)} 条公告详情")
        return detailed_notices

    def _extract_text(self, html, keyword, default=""):
        """从HTML中提取特定关键词后的文本"""
        lines = html.split('\n')
        for i, line in enumerate(lines):
            if keyword in line:
                # 获取该行和下一行的内容
                context = '\n'.join(lines[i:i+2])
                # 简单的文本提取
                cleaned = re.sub(r'<[^>]+>', ' ', context)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                if cleaned:
                    return cleaned
        return default

    def save_data(self, data, filename):
        """保存数据到JSON文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 数据已保存到 {filename}")


def main():
    """主函数"""
    crawler = DCECrawler(headless=True)

    try:
        # 启动浏览器
        crawler.start()

        # 爬取合约规格
        contract_data = crawler.crawl_contract_specs()

        # 爬取公告
        notices_data = crawler.crawl_notices(limit=2)

        # 整合数据
        complete_data = {
            "元数据": {
                "爬取时间": time.strftime("%Y-%m-%d %H:%M:%S"),
                "数据来源": "大连商品交易所",
                "品种": "豆粕期货",
                "交易代码": "M"
            },
            "合约基本信息": contract_data,
            "最新公告": {
                "公告数量": len(notices_data),
                "公告列表": notices_data
            }
        }

        # 保存数据
        crawler.save_data(complete_data, '/tmp/soybean_meal_data.json')

        # 打印摘要
        print("\n=== 爬取完成 ===")
        print(f"合约参数: {len(contract_data)} 项")
        print(f"公告数量: {len(notices_data)} 条")

    finally:
        # 确保关闭浏览器
        crawler.stop()


if __name__ == "__main__":
    main()
