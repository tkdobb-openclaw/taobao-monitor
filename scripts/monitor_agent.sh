#!/bin/bash
# 淘宝价格监控 - agent-browser 完整版

cd "$HOME/.openclaw/workspace/skills/taobao-monitor"

LOG_FILE="logs/sku_prices_$(date +%Y%m%d_%H%M).log"

echo "==========================================" | tee -a "$LOG_FILE"
echo "淘宝价格监控 - $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

# 商品列表（只测试前3个）
declare -A ITEMS=(
    ["624281587175"]="塞班户外|Peregrine|黑色 TX 版,黑色经典版,灰色 DARK"
    ["623907417709"]="大洋潜水|Peregrine|Peregrine 灰色,Peregrine TX 需预定"
    ["676780234187"]="大洋潜水|Perdix|perdix2 ti 银色"
)

# 加载登录态
npx agent-browser state load data/taobao_auth.json 2>/dev/null

for ITEM_ID in "${!ITEMS[@]}"; do
    IFS='|' read -r SHOP MODEL SKUS <><< "${ITEMS[$ITEM_ID]}"
    
    echo -e "\n【$SHOP - $MODEL】" | tee -a "$LOG_FILE"
    
    URL="https://item.taobao.com/item.htm?id=$ITEM_ID"
    
    # 访问页面
    npx agent-browser open "$URL" 2>/dev/null
    sleep 3
    
    # 点击每个目标 SKU
    IFS=',' read -ra TARGET_SKUS <><< "$SKUS"
    
    for TARGET in "${TARGET_SKUS[@]}"; do
        # 找到 SKU 索引
        INDEX=$(npx agent-browser eval "
const items = document.querySelectorAll('[class*=\"valueItem--\"]');
for (let i = 0; i < items.length; i++) {
    if (items[i].innerText.toLowerCase().replace(/\s/g, '').includes('$TARGET'.toLowerCase().replace(/\s/g, ''))) {
        return i;
    }
}
return -1;
" 2>/dev/null | tr -d '"')
        
        if [ "$INDEX" != "-1" ] && [ -n "$INDEX" ]; then
            echo "  点击 SKU[$INDEX]: $TARGET" | tee -a "$LOG_FILE"
            
            # 点击
            npx agent-browser eval "
document.querySelectorAll('[class*=\"valueItem--\"]')[$INDEX].click();
" 2>/dev/null
            
            sleep 4
            
            # 获取价格
            PRICE=$(npx agent-browser eval "
const el = document.querySelector('[class*=\"priceText--\"]');
if (el) {
    const match = el.innerText.match(/¥\s*([\d,]+\.?\d*)/);
    return match ? match[1] : el.innerText.substring(0, 30);
}
return 'N/A';
" 2>/dev/null | tr -d '"')
            
            echo "    价格: ¥$PRICE" | tee -a "$LOG_FILE"
        else
            echo "  ✗ 未找到 SKU: $TARGET" | tee -a "$LOG_FILE"
        fi
    done
done

echo -e "\n==========================================" | tee -a "$LOG_FILE"
echo "监控完成: $(date)" | tee -a "$LOG_FILE"
