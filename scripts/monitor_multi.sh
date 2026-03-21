#!/bin/bash
# 淘宝价格监控 - 多商品完整版

cd ~/.openclaw/workspace/skills/taobao-monitor

echo "=========================================="
echo "淘宝价格监控 - $(date +%H:%M)"
echo "=========================================="

npx agent-browser state load data/taobao_auth.json 2>/dev/null

# 商品列表: ID|店铺|型号|SKU索引1,SKU名称1|SKU索引2,SKU名称2...
ITEMS=(
    "624281587175|塞班户外|Peregrine|1,灰色 DARK|2,黑色经典版|3,黑色 TX 版"
    "676780234187|大洋潜水|Perdix|0,perdix2 ti 银色"
    "623907417709|大洋潜水|Peregrine|0,Peregrine 灰色"
)

get_price() {
    npx agent-browser eval "document.querySelector('[class*=\"Price--\"]')?.innerText" 2>/dev/null | grep -o '[¥￥][0-9,]\+\.\?[0-9]*' | head -1 | tr -d '¥￥,'
}

for item in "${ITEMS[@]}"; do
    IFS='|' read -r ID SHOP MODEL SKUS_STR <<< "$item"
    
    echo -e "\n【$SHOP - $MODEL】"
    
    URL="https://item.taobao.com/item.htm?id=$ID"
    npx agent-browser open "$URL" 2>/dev/null
    sleep 3
    
    # 解析SKU列表
    IFS='|' read -ra SKU_LIST <<< "$SKUS_STR"
    
    for sku_pair in "${SKU_LIST[@]}"; do
        IFS=',' read -r IDX NAME <<< "$sku_pair"
        
        echo "  点击 [$IDX]: $NAME"
        npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[$IDX].click()" 2>/dev/null
        sleep 6
        
        PRICE=$(get_price)
        if [ -n "$PRICE" ]; then
            echo "    价格: ¥$PRICE"
        else
            echo "    价格: 获取失败"
        fi
    done
done

echo -e "\n=========================================="
echo "完成: $(date +%H:%M)"
