#!/bin/bash
# 淘宝价格监控 - 20商品完整版
# 使用agent-browser直接执行

cd ~/.openclaw/workspace/skills/taobao-monitor

LOG="logs/full_$(date +%Y%m%d_%H%M).log"

echo "==========================================" | tee -a "$LOG"
echo "淘宝价格监控 - $(date +%H:%M)" | tee -a "$LOG"
echo "==========================================" | tee -a "$LOG"

# 加载登录态
echo "加载登录态..." | tee -a "$LOG"
npx agent-browser state load data/taobao_auth.json 2>/dev/null

# 价格获取函数
get_price() {
    npx agent-browser eval "document.querySelector('[class*=\"Price--\"]')?.innerText" 2>/dev/null | grep -o '[¥￥][0-9,]\+\.\?[0-9]*' | head -1 | tr -d '¥￥,'
}

# 商品1: 塞班户外 Peregrine
echo -e "\n【塞班户外 - Peregrine】" | tee -a "$LOG"
npx agent-browser open "https://item.taobao.com/item.htm?id=624281587175" 2>/dev/null
sleep 3

echo "  灰色 DARK:" | tee -a "$LOG"
npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[1].click()" 2>/dev/null
sleep 6
PRICE=$(get_price)
echo "    ¥$PRICE" | tee -a "$LOG"

echo "  黑色经典版:" | tee -a "$LOG"
npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[2].click()" 2>/dev/null
sleep 6
PRICE=$(get_price)
echo "    ¥$PRICE" | tee -a "$LOG"

echo "  黑色 TX 版:" | tee -a "$LOG"
npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[3].click()" 2>/dev/null
sleep 6
PRICE=$(get_price)
echo "    ¥$PRICE" | tee -a "$LOG"

# 商品2: 大洋潜水 Perdix
echo -e "\n【大洋潜水 - Perdix】" | tee -a "$LOG"
npx agent-browser open "https://item.taobao.com/item.htm?id=676780234187" 2>/dev/null
sleep 3

# 先获取SKU列表，找到目标索引
SKUS=$(npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\"valueItem--\"]')).map((el,i) => i+':'+el.innerText?.trim()).join('|')" 2>/dev/null)
echo "  SKU列表: $SKUS" | tee -a "$LOG"

# 点击第一个SKU（perdix2 ti 银色）
echo "  perdix2 ti 银色:" | tee -a "$LOG"
npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[0].click()" 2>/dev/null
sleep 6
PRICE=$(get_price)
echo "    ¥$PRICE" | tee -a "$LOG"

echo -e "\n==========================================" | tee -a "$LOG"
echo "完成: $(date +%H:%M)" | tee -a "$LOG"
echo "日志: $LOG" | tee -a "$LOG"
