#!/bin/bash
# 大商所持仓爬虫 - 一键运行脚本

echo "=================================="
echo "大商所持仓数据爬虫"
echo "=================================="
echo ""

cd "/home/liyuexuan/下载"

echo "正在启动爬虫..."
echo ""

python3 大商所持仓爬虫.py

echo ""
echo "按任意键退出..."
read -n 1
