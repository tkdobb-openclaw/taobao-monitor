#!/bin/bash
# 淘宝价格监控 - 20商品完整测试（带计时）

cd ~/.openclaw/workspace/skills/taobao-monitor

START_TIME=$(date +%s)
LOG="logs/final_test_$(date +%Y%m%d_%H%M).log"

echo "==========================================" | tee -a "$LOG"
echo "淘宝价格监控 - 20商品完整测试" | tee -a "$LOG"
echo "开始时间: $(date +%H:%M:%S)" | tee -a "$LOG"
echo "==========================================" | tee -a "$LOG"

npx agent-browser state load data/taobao_auth.json 2>/dev/null

get_price() {
    npx agent-browser eval "document.querySelector('[class*=\"Price--\"]')?.innerText" 2>/dev/null | grep -o '[¥￥][0-9,]\+\.\?[0-9]*' | head -1 | tr -d '¥￥,'
}

click_and_price() {
    local idx=$1
    local name=$2
    
    npx agent-browser eval "document.querySelectorAll('[class*=\"valueItem--\"]')[$idx].click()" 2>/dev/null
    sleep 6
    
    PRICE=$(get_price)
    if [ -n "$PRICE" ]; then
        echo "      ¥$PRICE - $name" | tee -a "$LOG"
    else
        echo "      失败 - $name" | tee -a "$LOG"
    fi
}

# 20个商品配置
# 格式: 序号|商品ID|店铺|型号|SKU索引,名称|SKU索引,名称...
ITEMS=(
    "1|624281587175|塞班户外|Peregrine|1,灰色DARK|2,黑色经典版|3,黑色TX版"
    "2|676780234187|大洋潜水|Perdix|0,perdix2 ti银色"
    "3|676463247224|塞班户外|Perdix|0,PERDIX2 Ti银色"
    "4|544005716799|白鳍鲨|Perdix|0,PERDIX2 Ti BLACK"
    "5|675444560376|岁老板|Perdix|0,Ti Black钛黑版"
    "6|632230014333|三潜社|Perdix|2,PERDIX2 Ti BLACK"
    "7|623907417709|大洋潜水|Peregrine|0,Peregrine灰色|1,Peregrine TX"
    "8|623777445212|白鳍鲨|Peregrine|0,peregrine黑色|1,peregrine TX黑色"
    "9|626899529012|岁老板|Peregrine|0,普通版黑蓝色|1,TX版黑色"
    "10|988652922548|三潜社|Peregrine|0,peregrine黑色|1,peregrine TX黑色"
    "11|584863170468|大洋潜水|Teric|0,浅灰色"
    "12|575523804132|塞班户外|Teric|0,黑盘黑表带"
    "13|570722701118|白鳍鲨|Teric|0,黑色"
    "14|667904575973|岁老板|Teric|1,黑色"
    "15|629563113404|三潜社|Teric|0,黑色"
    "16|753330765355|大洋潜水|Tern|0,Tern|1,Tern TX"
    "17|756509652959|塞班户外|Tern|0,TERN New|1,TERN TX"
    "18|753672216139|白鳍鲨|Tern|0,TERN|1,TERN TX"
    "19|749763697229|岁老板|Tern|0,TERN银色|1,TERN TX黑色"
    "20|899733746263|三潜社|Tern|0,TERN|1,TERN TX"
)

for item in "${ITEMS[@]}"; do
    IFS='|' read -r NUM ID SHOP MODEL SKUS_STR <<< "$item"
    
    echo -e "\n【$NUM/20】$SHOP - $MODEL" | tee -a "$LOG"
    
    URL="https://item.taobao.com/item.htm?id=$ID"
    npx agent-browser open "$URL" 2>/dev/null
    sleep 3
    
    # 检查是否登录成功
    TITLE=$(npx agent-browser eval "document.title" 2>/dev/null | tr -d '"')
    if echo "$TITLE" | grep -q "登录"; then
        echo "  ❌ 需要登录，跳过" | tee -a "$LOG"
        continue
    fi
    
    # 解析并点击SKU
    IFS='|' read -ra SKU_LIST <<< "$SKUS_STR"
    for sku in "${SKU_LIST[@]}"; do
        IFS=',' read -r IDX NAME <<< "$sku"
        click_and_price "$IDX" "$NAME"
    done
done

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MIN=$((DURATION / 60))
SEC=$((DURATION % 60))

echo -e "\n==========================================" | tee -a "$LOG"
echo "完成时间: $(date +%H:%M:%S)" | tee -a "$LOG"
echo "总耗时: ${MIN}分${SEC}秒" | tee -a "$LOG"
echo "日志: $LOG" | tee -a "$LOG"
echo "==========================================" | tee -a "$LOG"
