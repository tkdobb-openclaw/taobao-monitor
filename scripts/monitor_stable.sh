#!/bin/bash
# 淘宝价格监控 - 稳定版（等待6秒）

cd ~/.openclaw/workspace/skills/taobao-monitor

echo "=========================================="
echo "淘宝价格监控 - $(date +%H:%M)"
echo "=========================================="

npx agent-browser state load data/taobao_auth.json 2>/dev/null

URL="https://item.taobao.com/item.htm?id=624281587175"
echo -e "\n【塞班户外 - Peregrine】"
npx agent-browser open "$URL" 2>/dev/null
sleep 2

# 获取价格函数
get_price() {
    npx agent-browser eval "document.querySelector('[class*=\"Price--\"]')?.innerText" 2>/dev/null | grep -o '[¥￥][0-9,]\+\.\?[0-9]*' | head -1 | tr -d '¥￥,'
}

# 点击并获取价格
click_sku() {
    local idx=$1
    local name=$2
    
    echo -e "\n点击 [$idx]: $name"
    npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[$idx].click()" 2>/dev/null
    sleep 6
    
    price=$(get_price)
    if [ -n "$price" ]; then
        echo "  价格: ¥$price"
    else
        echo "  价格: 获取失败"
    fi
}

echo "默认价格: ¥$(get_price)"

click_sku 1 "灰色 DARK"
click_sku 2 "黑色经典版"  
click_sku 3 "黑色 TX 版"

echo -e "\n=========================================="
echo "完成: $(date +%H:%M)"
