#!/bin/bash
# 淘宝价格监控 - 使用 agent-browser

LOG_FILE="$HOME/.openclaw/workspace/skills/taobao-monitor/logs/agent_monitor_$(date +%H%M).log"
exec > "$LOG_FILE" 2>&1

echo "=========================================="
echo "淘宝价格监控 - $(date)"
echo "=========================================="

cd "$HOME/.openclaw/workspace/skills/taobao-monitor"

# 测试一个商品 - 塞班户外 Peregrine
echo -e "\n测试: 塞班户外 - Peregrine"
echo "URL: https://item.taobao.com/item.htm?id=624281587175"

# 加载登录态并访问
npx agent-browser state load data/taobao_auth.json 2>/dev/null

# 打开页面
npx agent-browser open "https://item.taobao.com/item.htm?id=624281587175" 2>/dev/null
sleep 3

# 获取标题
echo "页面标题:"
npx agent-browser eval 'document.title' 2>/dev/null

# 获取所有 SKU 文本
echo -e "\nSKU 列表:"
npx agent-browser eval '
const items = document.querySelectorAll("[class*=\\'valueItem--\\']");
Array.from(items).map((el, i) => `[${i}] ${el.innerText?.trim() || ""}`).join("\\n")
' 2>/dev/null

echo -e "\n=========================================="
echo "测试完成"
