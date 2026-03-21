#!/bin/bash
# 淘宝价格监控 - 完整版（20商品）
# 输出JSON格式，方便后续处理

cd ~/.openclaw/workspace/skills/taobao-monitor

LOG_FILE="logs/full_monitor_$(date +%Y%m%d_%H%M).log"
JSON_FILE="logs/prices_$(date +%Y%m%d_%H%M).json"

exec > "$LOG_FILE" 2>&1

echo "{"
echo '  "time": "'$(date +%Y-%m-%d\ %H:%M)'",'
echo '  "results": ['

npx agent-browser state load data/taobao_auth.json 2>/dev/null

# 商品配置
# 格式: 商品ID|店铺|型号|SKU索引,SKU名称|SKU索引,SKU名称...
declare -a ITEMS
declare -a ITEMS=(
    "624281587175|塞班户外|Peregrine|1,灰色 DARK|2,黑色经典版|3,黑色 TX 版"
    "623907417709|大洋潜水|Peregrine|0,Peregrine 灰色|1,Peregrine TX 需预定"
    "676780234187|大洋潜水|Perdix|0,perdix2 ti 银色"
)

FIRST_ITEM=true

for item in "${ITEMS[@]}"; do
    IFS='|' read -r ID SHOP MODEL SKUS_STR <<< "$item"
    
    [ "$FIRST_ITEM" = true ] || echo ","
    FIRST_ITEM=false
    
    echo "    {"
    echo '      "shop": "'$SHOP'",'
    echo '      "model": "'$MODEL'",'
    echo '      "item_id": "'$ID'",'
    echo '      "skus": ['
    
    URL="https://item.taobao.com/item.htm?id=$ID"
    npx agent-browser open "$URL" 2>/dev/null
    sleep 3
    
    # 解析SKU
    IFS='|' read -ra SKU_LIST <<< "$SKUS_STR"
    FIRST_SKU=true
    
    for sku_pair in "${SKU_LIST[@]}"; do
        IFS=',' read -r IDX NAME <<< "$sku_pair"
        
        [ "$FIRST_SKU" = true ] || echo ","
        FIRST_SKU=false
        
        # 点击SKU
        npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[$IDX].click()" 2>/dev/null
        sleep 6
        
        # 获取价格
        PRICE=$(npx agent-browser eval "document.querySelector('[class*=\"Price--\"]')?.innerText" 2>/dev/null | grep -o '[¥￥][0-9,]\+\.\?[0-9]*' | head -1 | tr -d '¥￥,')
        
        echo "        {"
        echo '          "name": "'$NAME'",'
        echo '          "price": "'${PRICE:-N/A}'"'
        echo -n "        }"
    done
    
    echo ""
    echo -n "      ]"
    echo ""
    echo -n "    }"
done

echo ""
echo "  ]"
echo "}"

echo -e "\n=========================================="
echo "完成: $(date +%H:%M)"
echo "日志: $LOG_FILE"
