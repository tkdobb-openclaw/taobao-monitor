#!/usr/bin/env python3
"""
淘宝价格监控 - agent-browser 版本
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
    }
}

def run_cmd(cmd, timeout=30):
    """运行命令"""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.stdout.strip()

def main():
    print("=" * 50)
    print(f"淘宝价格监控 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    cd_cmd = "cd ~/.openclaw/workspace/skills/taobao-monitor"
    
    for item_id, config in ITEMS.items():
        shop = config["shop"]
        model = config["model"]
        target_skus = config["skus"]
        
        print(f"\n【{shop} - {model}】")
        
        url = f"https://item.taobao.com/item.htm?id={item_id}"
        
        # 访问页面
        print(f"  访问页面...")
        run_cmd(f'{cd_cmd} && npx agent-browser open "{url}" 2>/dev/null')
        time.sleep(3)
        
        # 获取 SKU 列表
        output = run_cmd(f'''{cd_cmd} && npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null''')
        
        print(f"  原始输出: {output[:100]}")
        
        if output:
            sku_list = [s.strip() for s in output.split("|||") if s.strip()]
            print(f"  找到 {len(sku_list)} 个 SKU")
            
            for i, sku in enumerate(sku_list[:5]):
                print(f"    [{i}] {sku[:40]}")
        else:
            print("  未获取到 SKU")
    
    print("\n" + "=" * 50)

if __name__ == '__main__':
    main()
