#!/bin/bash
# 淘宝价格监控 - 带重试

cd ~/.openclaw/workspace/skills/taobao-monitor

echo "=========================================="
echo "淘宝价格监控 - $(date +%H:%M)"
echo "=========================================="

npx agent-browser state load data/taobao_auth.json 2>/dev/null

URL="https://item.taobao.com/item.htm?id=624281587175"
echo -e "\n【塞班户外 - Peregrine】"

npx agent-browser open "$URL" 2>/dev/null
sleep 3

# 获取价格函数（带重试）
get_price() {
    for i in 1 2 3; do
        price=$(npx agent-browser eval "const t = document.querySelector('[class*=\"Price--\"]')?.innerText; const m = t?.match(/[¥￥]\s*([\d,]+\.?\d*)/); m ? m[1] : ''" 2>/dev/null | tr -d '"')
        if [ -n "$price" ] && [ "$price" != "null" ]; then
            echo "$price"
            return 0
        fi
        sleep 2
    done
    echo "N/A"
    return 1
}

# 点击并获取价格
click_sku() {
    local idx=$1
    local name=$2
    
    echo -e "\n点击 [$idx]: $name"
    npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[$idx].click()" 2>/dev/null
    sleep 5
    
    price=$(get_price)
    echo "  价格: ¥$price"
}

echo "默认价格:"
get_price

click_sku 1 "灰色 DARK"
click_sku 2 "黑色经典版"  
click_sku 3 "黑色 TX 版"

echo -e "\n=========================================="
