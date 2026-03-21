#!/bin/bash
# 淘宝监控 - Playwright 版本启动脚本

cd ~/.openclaw/workspace/skills/taobao-monitor

# 检查参数
if [ "$1" == "--login" ]; then
    echo "🔐 启动登录模式..."
    python3 monitor_playwright.py --login
elif [ "$1" == "--check" ]; then
    echo "🔍 检查登录状态..."
    python3 monitor_playwright.py --check
else
    echo "📊 启动价格监控..."
    python3 monitor_playwright.py 2>&1 | tee logs/monitor_pw_$(date +%Y%m%d_%H%M).log
fi
