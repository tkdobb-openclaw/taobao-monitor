#!/bin/bash
# 淘宝价格监控脚本
# 用法: ./taobao-monitor.sh [--headed]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 检查参数
HEADLESS="true"
if [ "$1" == "--headed" ]; then
    HEADLESS="false"
    echo "🖥️  可视化模式（前台显示浏览器）"
else
    echo "🤖 后台模式（无浏览器窗口）"
fi

# 运行监控
echo "================================"
echo "📊 淘宝价格监控 - $(date '+%Y-%m-%d %H:%M')"
echo "================================"

if [ "$HEADLESS" == "false" ]; then
    # 可视化模式 - 先关闭现有浏览器，再以可视化模式启动
    npx agent-browser close 2>/dev/null
    sleep 2
    # 启动可视化浏览器实例（后台运行）
    npx agent-browser --headed open "about:blank" &
    BROWSER_PID=$!
    sleep 3
    echo "🖥️  可视化浏览器已启动"
    # 运行Python脚本
    python3 monitor_20_full.py 2>&1 | tee "logs/monitor_$(date +%Y%m%d_%H%M).log"
    # 清理
    kill $BROWSER_PID 2>/dev/null
else
    # 纯后台模式
    python3 monitor_20_full.py 2>&1 | tee "logs/monitor_$(date +%Y%m%d_%H%M).log"
fi

echo ""
echo "✅ 监控完成！"
echo "📁 日志保存到: logs/monitor_$(date +%Y%m%d_%H%M).log"
