#!/usr/bin/env python3
"""
淘宝价格监控 - agent-browser 版本
直接调用 agent-browser 命令行工具
"""
import subprocess
import json
import time
import re
from pathlib import Path
from datetime import datetime

# 商品配置
ITEMS = {
    "624281587175": {
        "shop": "塞班户外",
        "model": "Peregrine", 
        "skus": ["黑色 TX 版", "黑色经典版", "灰色 DARK"]
    },
    "623907417709": {
        "shop": "大洋潜水",
        "model": "Peregrine",
        "skus": ["Peregrine 灰色", "Peregrine TX 需预定"]
    }
}

def run_agent(cmd):
    """运行 agent-browser 命令"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout.strip()

def get_sku_list():
    """获取所有 SKU 文本"""
    output = run_agent('''npx agent-browser eval '
const items = document.querySelectorAll("[class*=\\'valueItem--\\']");
JSON.stringify(Array.from(items).map(el => el.innerText?.trim()))
' 2>/dev/null''')
    try:
        # 去掉引号并解析
        output = output.strip('"').replace('\\n', '\n')
        return json.loads('"' + output + '"')
    except:
        return []

def click_sku(index):
    """点击指定索引的 SKU"""
    run_agent(f'''npx agent-browser eval '
document.querySelectorAll("[class*=\\'valueItem--\\']")[{index}].click()
' 2>/dev/null''')

def get_price():
    """获取当前价格"""
    output = run_agent('''npx agent-browser eval '
const el = document.querySelector("[class*=\\'priceText--\\']");
if (el) {
    const match = el.innerText.match(/¥\\s*([\\d,]+\\.?\\d*)/);
    return match ? match[1] : el.innerText.substring(0, 30);
}
return "N/A";
' 2>/dev/null''')
    return output.strip('"')

def find_sku_index(sku_list, target):
    """查找 SKU 索引"""
    target_clean = target.lower().replace(' ', '')
    for i, text in enumerate(sku_list):
        if target_clean in text.lower().replace(' ', ''):
            return i
    return -1

def main():
    print("=" * 50)
    print(f"淘宝价格监控 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    # 加载登录态
    run_agent("npx agent-browser state load data/taobao_auth.json 2>/dev/null")
    
    for item_id, config in ITEMS.items():
        shop = config["shop"]
        model = config["model"]
        target_skus = config["skus"]
        
        print(f"\n【{shop} - {model}】")
        
        url = f"https://item.taobao.com/item.htm?id={item_id}"
        
        # 访问页面
        run_agent(f'npx agent-browser open "{url}" 2>/dev/null')
        time.sleep(3)
        
        # 获取 SKU 列表
        sku_list = get_sku_list()
        print(f"  找到 {len(sku_list)} 个 SKU")
        
        # 点击每个目标 SKU
        for target in target_skus:
            idx = find_sku_index(sku_list, target)
            if idx >= 0:
                print(f"  点击: {target}")
                click_sku(idx)
                time.sleep(4)
                price = get_price()
                print(f"    价格: ¥{price}")
            else:
                print(f"  ✗ 未找到: {target}")
    
    print("\n" + "=" * 50)
    print(f"完成: {datetime.now().strftime('%H:%M')}")

if __name__ == '__main__':
    main()
