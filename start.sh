#!/bin/bash
# 启动淘宝价格监控（手动模式）

cd ~/.openclaw/workspace/skills/taobao-monitor

echo "======================================"
echo "淘宝价格监控系统"
echo "======================================"
echo ""
echo "1. 确保 Chrome 扩展已开启（显示 ON）"
echo "2. 确保当前标签页是淘宝页面"
echo "3. 按回车开始抓取"
echo ""
read -p "准备好了吗？按回车开始..."

echo ""
echo "开始抓取..."
python3 scripts/monitor_daily.py

echo ""
echo "完成！"
read -p "按回车退出..."
