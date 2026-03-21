#!/bin/bash
# 淘宝价格监控 - 20商品完整测试（带计时）

cd ~/.openclaw/workspace/skills/taobao-monitor

START_TIME=$(date +%s)
LOG="logs/full_test_$(date +%Y%m%d_%H%M).log"

echo "==========================================" | tee -a "$LOG"
echo "淘宝价格监控 - 20商品完整测试" | tee -a "$LOG"
echo "开始时间: $(date +%H:%M:%S)" | tee -a "$LOG"
echo "==========================================" | tee -a "$LOG"

npx agent-browser state load data/taobao_auth.json 2>/dev/null

# 获取价格函数
get_price() {
    npx agent-browser eval "document.querySelector('[class*=\"Price--\"]')?.innerText" 2>/dev/null | grep -o '[¥￥][0-9,]\+\.\?[0-9]*' | head -1 | tr -d '¥￥,'
}

# 点击SKU并获取价格
click_and_price() {
    local idx=$1
    local name=$2
    
    npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[$idx].click()" 2>/dev/null
    sleep 6
    
    PRICE=$(get_price)
    if [ -n "$PRICE" ]; then
        echo "      ¥$PRICE - $name" | tee -a "$LOG"
    else
        echo "      获取失败 - $name" | tee -a "$LOG"
    fi
}

# ===== 商品列表 =====

# Peregrine - 塞班户外 (3 SKUs)
echo -e "\n【1/20】塞班户外 - Peregrine" | tee -a "$LOG"
npx agent-browser open "https://item.taobao.com/item.htm?id=624281587175" 2>/dev/null
sleep 3
click_and_price 1 "灰色 DARK"
click_and_price 2 "黑色经典版"
click_and_price 3 "黑色 TX 版"

# Perdix - 大洋潜水 (1 SKU)
echo -e "\n【2/20】大洋潜水 - Perdix" | tee -a "$LOG"
npx agent-browser open "https://item.taobao.com/item.htm?id=676780234187" 2>/dev/null
sleep 3
click_and_price 0 "perdix2 ti 银色"

# Peregrine - 大洋潜水 (2 SKUs)
echo -e "\n【3/20】大洋潜水 - Peregrine" | tee -a "$LOG"
npx agent-browser open "https://item.taobao.com/item.htm?id=623907417709" 2>/dev/null
sleep 3
# 先列出SKU找到正确索引
SKUS=$(npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\"valueItem--\"]')).map((el,i) => i+':'+el.innerText?.substring(0,15)).join(', ')" 2>/dev/null)
echo "    SKU列表: $SKUS" | tee -a "$LOG"
click_and_price 0 "Peregrine 灰色"
click_and_price 1 "Peregrine TX 需预定"

# 继续其他商品...（先测试前3个）

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo -e "\n==========================================" | tee -a "$LOG"
echo "完成时间: $(date +%H:%M:%S)" | tee -a "$LOG"
echo "总耗时: ${MINUTES}分${SECONDS}秒" | tee -a "$LOG"
echo "日志: $LOG" | tee -a "$LOG"
echo "==========================================" | tee -a "$LOG"
