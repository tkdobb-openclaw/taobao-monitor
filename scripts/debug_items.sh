#!/bin/bash
# 调试特定商品 - 查看所有SKU和价格

cd ~/.openclaw/workspace/skills/taobao-monitor

echo "=========================================="
echo "调试特定商品SKU"
echo "=========================================="

npx agent-browser state load data/taobao_auth.json 2>/dev/null

# 函数：查看商品所有SKU和价格
debug_item() {
    local id=$1
    local shop=$2
    local model=$3
    
    echo -e "\n【$shop - $model】"
    echo "URL: https://item.taobao.com/item.htm?id=$id"
    
    npx agent-browser open "https://item.taobao.com/item.htm?id=$id" 2>/dev/null
    sleep 3
    
    # 获取所有SKU
    echo "  所有SKU:"
    npx agent-browser eval "
Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map((el,i) => {
  el.click();
  return i + ': ' + el.innerText?.trim()?.substring(0,30);
}).join('|||')
" 2>/dev/null | tr '|' '\n' | sed 's/^/    /'
    
    # 逐个点击获取价格
    echo "  各SKU价格:"
    local count=$(npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']').length" 2>/dev/null)
    
    for ((i=0; i<count; i++)); do
        npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[$i].click()" 2>/dev/null
        sleep 5
        
        sku_name=$(npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[$i]?.innerText?.trim()?.substring(0,20)" 2>/dev/null | tr -d '"')
        price=$(npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText" 2>/dev/null | grep -o '[¥￥][0-9,]\+\.\?[0-9]*' | head -1 | tr -d '¥￥,')
        
        echo "    [$i] $sku_name: ¥$price"
    done
}

# 调试问题商品
debug_item "667904575973" "岁老板" "Teric"
debug_item "629563113404" "三潜社" "Teric"
debug_item "632230014333" "三潜社" "Perdix"
debug_item "675444560376" "岁老板" "Perdix"

echo -e "\n=========================================="
