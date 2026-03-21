#!/bin/bash
# 淘宝价格监控系统安装脚本

set -e

echo "🚀 安装淘宝价格监控系统..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 需要安装 Python3"
    exit 1
fi

echo "✓ Python3 已安装"

# 安装依赖
echo "📦 安装 Python 依赖..."
pip3 install playwright requests -q

# 安装 Playwright 浏览器
echo "🌐 安装 Playwright 浏览器..."
playwright install chromium

# 创建目录
mkdir -p data logs

# 设置权限
chmod +x scripts/cron.sh
chmod +x scripts/monitor.py

echo ""
echo "✅ 安装完成!"
echo ""
echo "📋 使用说明:"
echo "  1. 配置飞书Webhook: 编辑 config.json 文件"
echo "  2. 添加监控商品: python3 scripts/monitor.py add <url> --target 199"
echo "  3. 查看监控列表: python3 scripts/monitor.py list"
echo "  4. 手动检查价格: python3 scripts/monitor.py check"
echo ""
echo "⏰ 设置定时任务 (每天两次):"
echo "  crontab -e"
echo "  0 9,21 * * * $SCRIPT_DIR/cron.sh"
echo ""
