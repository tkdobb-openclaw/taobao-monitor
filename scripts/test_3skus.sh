#!/bin/bash
# 淘宝价格监控 - 完整测试（3个SKU）

cd ~/.openclaw/workspace/skills/taobao-monitor

echo "=========================================="
echo "淘宝价格监控 - $(date +%H:%M)"
echo "=========================================="

# 加载登录态
npx agent-browser state load data/taobao_auth.json 2>/dev/null

# 商品信息
URL="https://item.taobao.com/item.htm?id=624281587175"
echo -e "\n【塞班户外 - Peregrine】"

# 访问页面
npx agent-browser open "$URL" 2>/dev/null
sleep 3

# 获取默认价格
echo "默认价格:"
npx agent-browser eval "document.querySelector('[class*=\"Price--\"]')?.innerText" 2>/dev/null

# 点击 SKU 获取价格
click_and_get_price() {
    local idx=$1
    local name=$2
    
    echo -e "\n点击 [$idx]: $name"
    npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[$idx].click()" 2>/dev/null
    sleep 4
    
    price=$(npx agent-browser eval "const t = document.querySelector('[class*=\"Price--\"]')?.innerText; const m = t?.match(/[¥￥]\s*([\d,]+\.?\d*)/); m ? m[1] : 'N/A'" 2>/dev/null)
    echo "  价格: ¥$price"
}

# 点击三个目标 SKU
click_and_get_price 1 "灰色 DARK"
click_and_get_price 2 "黑色经典版"  
click_and_get_price 3 "黑色 TX 版"

echo -e "\n=========================================="
echo "完成"
