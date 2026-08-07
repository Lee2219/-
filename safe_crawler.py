#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大商所豆粕数据爬虫 - 跨平台安全版
推荐使用Firefox（绕过反爬保护）
"""

from selenium import webdriver
import time
import json
import sys

class SafeCrawler:
    """安全爬虫类 - 优先使用Firefox"""

    def __init__(self, prefer_firefox=True):
        """
        初始化爬虫

        Args:
            prefer_firefox: 是否优先使用Firefox（推荐绕过反爬）
        """
        self.prefer_firefox = prefer_firefox
        self.driver = None
        self.browser_used = None

    def start(self):
        """智能启动浏览器"""
        if self.prefer_firefox:
            try:
                self._start_firefox()
                self.browser_used = 'firefox'
                print("✅ Firefox 启动成功（推荐用于大商所）")
                return
            except Exception as e:
                print(f"⚠️ Firefox启动失败: {e}")
                print("🔄 尝试使用Chrome...")

        # Firefox失败时尝试Chrome
        try:
            self._start_chrome()
            self.browser_used = 'chrome'
            print("✅ Chrome 启动成功")
            print("⚠️ 注意：Chrome可能被大商所拦截")
        except Exception as e:
            print(f"❌ Chrome也启动失败: {e}")
            raise Exception("所有浏览器都启动失败")

    def _start_firefox(self):
        """启动Firefox（推荐用于大商所）"""
        from selenium.webdriver.firefox.service import Service
        from selenium.webdriver.firefox.options import Options
        from webdriver_manager.firefox import GeckoDriverManager

        options = Options()
        options.add_argument('--headless')

        self.driver = webdriver.Firefox(
            service=Service(GeckoDriverManager().install()),
            options=options
        )

    def _start_chrome(self):
        """启动Chrome（可能被拦截）"""
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        # 添加反检测特征
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

    def test_dce_access(self):
        """测试大商所访问是否成功"""
        print("\n=== 测试大商所访问 ===")

        self.driver.get('http://www.dce.com.cn')
        time.sleep(5)

        page_title = self.driver.title
        page_length = len(self.driver.page_source)

        print(f"浏览器: {self.browser_used}")
        print(f"页面标题: {page_title}")
        print(f"页面长度: {page_length}")

        # 检查是否被拦截
        if '大连商品交易所' in self.driver.page_source and page_length > 10000:
            print("✅ 成功访问大商所")
            return True
        else:
            print("❌ 被大商所拦截或页面异常")
            return False

    def crawl_data(self):
        """爬取数据"""
        # 测试访问
        if not self.test_dce_access():
            print("⚠️ 当前浏览器被拦截，建议切换到Firefox")

        # 实际爬取逻辑...
        return {"test": "data"}

    def stop(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()


def main():
    """主函数"""
    import platform

    print(f"系统: {platform.system()}")

    # 创建爬虫（优先Firefox）
    crawler = SafeCrawler(prefer_firefox=True)

    try:
        crawler.start()
        data = crawler.crawl_data()
    finally:
        crawler.stop()


if __name__ == "__main__":
    main()
