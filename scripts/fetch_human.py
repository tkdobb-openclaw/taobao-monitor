#!/usr/bin/env python3
"""
淘宝价格抓取 - 深度真人模拟版
20-30秒等待，鼠标移动，随机点击
"""

import subprocess
import re
import time
import random
import sqlite3
from pathlib import Path

TARGET_ID = "9F774C740CC4F9178A9B0A4F84DCE2AC"

products = [
    {"id": 2, "note": "大洋潜水 - Perdix", "url": "https://item.taobao.com/item.htm?id=676780234187"},
    {"id": 3, "note": "塞班户外 - Perdix", "url": "https://item.taobao.com/item.htm?id=676463247224"},
    {"id": 4, "note": "白鳍鲨 - Perdix", "url": "https://item.taobao.com/item.htm?id=544005716799"},
    {"id": 5, "note": "岁老板 - Perdix", "url": "https://item.taobao.com/item.htm?id=675444560376"},
    {"id": 6, "note": "三潜社 - Perdix", "url": "https://item.taobao.com/item.htm?id=632230014333"},
    {"id": 7, "note": "大洋潜水 - Peregrine", "url": "https://item.taobao.com/item.htm?id=623907417709"},
    {"id": 8, "note": "塞班户外 - Peregrine", "url": "https://item.taobao.com/item.htm?id=624281587175"},
    {"id": 9, "note": "白鳍鲨 - Peregrine", "url": "https://item.taobao.com/item.htm?id=623777445212"},
    {"id": 10, "note": "岁老板 - Peregrine", "url": "https://item.taobao.com/item.htm?id=626899529012"},
    {"id": 11, "note": "三潜社 - Peregrine", "url": "https://item.taobao.com/item.htm?id=988652922548"},
    {"id": 12, "note": "大洋潜水 - Teric", "url": "https://item.taobao.com/item.htm?id=584863170468"},
    {"id": 13, "note": "塞班户外 - Teric", "url": "https://item.taobao.com/item.htm?id=575523804132"},
    {"id": 14, "note": "白鳍鲨 - Teric", "url": "https://item.taobao.com/item.htm?id=570722701118"},
    {"id": 15, "note": "岁老板 - Teric", "url": "https://item.taobao.com/item.htm?id=667904575973"},
    {"id": 16, "note": "三潜社 - Teric", "url": "https://item.taobao.com/item.htm?id=629563113404"},
    {"id": 17, "note": "大洋潜水 - Tern", "url": "https://item.taobao.com/item.htm?id=753330765355"},
    {"id": 18, "note": "塞班户外 - Tern", "url": "https://item.taobao.com/item.htm?id=756509652959"},
    {"id": 19, "note": "白鳍鲨 - Tern", "url": "https://item.taobao.com/item.htm?id=753672216139"},
    {"id": 20, "note": "岁老板 - Tern", "url": "https://item.taobao.com/item.htm?id=749763697229"},
    {"id": 21, "note": "三潜社 - Tern", "url": "https://item.taobao.com/item.htm?id=899733746263"},
]

def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def human_behavior():
    """模拟真人行为"""
    # 随机鼠标移动
    for _ in range(random.randint(2, 4)):
        x, y = random.randint(200, 800), random.randint(200, 600)
        cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
            --fn "() => {{ document.dispatchEvent(new MouseEvent(\"mousemove\", {{ clientX: {x}, clientY: {y} }})); }}" 2>/dev/null'
        run_cmd(cmd, timeout=5)
        time.sleep(random.uniform(0.5, 1.5))
    
    # 随机滚动
    scroll_positions = [200, 400, 300, 500]
    for pos in random.sample(scroll_positions, 2):
        cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
            --fn "() => {{ window.scrollTo(0, {pos}); }}" 2>/dev/null'
        run_cmd(cmd, timeout=5)
        time.sleep(random.uniform(2, 4))

def navigate_and_wait(url):
    """导航并深度等待"""
    print(f"  打开页面...")
    cmd = f'openclaw browser --browser-profile chrome-relay navigate --target-id {TARGET_ID} --url "{url}" 2>/dev/null'
    run_cmd(cmd, timeout=30)
    
    # 深度等待 20-30秒
    wait_time = random.randint(20, 30)
    print(f"  等待 {wait_time} 秒让页面加载...")
    
    # 分段等待，期间做真人行为
    for i in range(wait_time // 5):
        time.sleep(5)
        print(f"    已等待 {(i+1)*5} 秒...")
        if i == 1:  # 第10秒做第一次行为
            print("    模拟浏览行为...")
            human_behavior()
    
    # 最后再等几秒
    time.sleep(random.randint(3, 5))

def get_price():
    """获取价格"""
    # 尝试多种选择器
    selectors = [
        'document.querySelector(".tb-rmb-num")?.textContent',
        'document.querySelector("[class*=priceText]")?.textContent',
        'document.querySelector("[class*=Price--priceInt]")?.textContent',
    ]
    
    for selector in selectors:
        cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
            --fn "() => {selector}" 2>/dev/null | tail -1'
        stdout, _, _ = run_cmd(cmd, timeout=15)
        text = stdout.strip().strip('"')
        
        if text and text != 'null' and text != 'undefined':
            prices = re.findall(r'(\d+)', text)
            if prices:
                price = int(prices[0])
                if 1500 <= price <= 10000 and price not in [20000, 3561, 2760]:
                    return price
    
    # 备用：搜索页面文本
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
        --fn "() => document.body.innerText" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=15)
    text = stdout.strip()
    
    prices = re.findall(r'[¥￥](\d{3,5})', text)
    valid = [int(p) for p in prices if 2000 <= int(p) <= 8000 
             and int(p) not in [20000, 3561, 2760]]  # 排除已知的假价格
    if valid:
        return min(valid)
    
    return None

def save_price(product_id, price):
    db_path = Path(__file__).parent.parent / "data" / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET last_price = ?, last_check = datetime('now') WHERE id = ?", (price, product_id))
    cursor.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, datetime('now'))", (product_id, price))
    conn.commit()
    conn.close()

def main():
    print("=" * 60)
    print("淘宝价格抓取 - 深度真人模拟版")
    print(f"开始: {time.strftime('%H:%M:%S')}")
    print("每个商品 25-35 秒（含真人行为）")
    print("=" * 60)
    print()
    
    success = 0
    for i, product in enumerate(products, 1):
        print(f"[{i:2d}/20] {product['note']}")
        
        navigate_and_wait(product['url'])
        
        price = get_price()
        
        if price:
            print(f"       ✅ 价格: ¥{price}")
            save_price(product['id'], price)
            success += 1
        else:
            print(f"       ❌ 未获取到有效价格")
        
        if i < len(products):
            interval = random.randint(15, 25)
            print(f"       间隔 {interval} 秒...\n")
            time.sleep(interval)
    
    print("=" * 60)
    print(f"完成: {success}/20 成功")
    print(f"结束: {time.strftime('%H:%M:%S')}")
    print("=" * 60)

if __name__ == '__main__':
    main()
