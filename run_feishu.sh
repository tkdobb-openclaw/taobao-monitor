#!/bin/bash
# 淘宝监控 - 飞书登录版
# 用法: ./run_feishu.sh

cd ~/.openclaw/workspace/skills/taobao-monitor

# 检查 Playwright 是否安装
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "首次运行，安装 Playwright..."
    pip3 install playwright aiohttp
    python3 -m playwright install chromium
fi

# 运行飞书登录版监控
python3 monitor_feishu_login.py 2>&1 | tee logs/feishu_run_$(date +%Y%m%d_%H%M).log
