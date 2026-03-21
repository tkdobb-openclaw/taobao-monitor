#!/usr/bin/env python3
"""
淘宝价格抓取 - 全部20个商品
可视化模式，慢速抓取
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

def run_cmd(cmd, timeout=20):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def navigate_and_wait(url):
    """导航到页面并等待加载"""
    cmd = f'openclaw browser --browser-profile chrome-relay navigate --target-id {TARGET_ID} --url "{url}" 2>/dev/null'
    run_cmd(cmd, timeout=25)
    
    wait_time = random.randint(5, 8)
    time.sleep(wait_time)
    
    # 滚动页面
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => {{ window.scrollTo(0, 300); return \"done\"; }}" 2>/dev/null'
    run_cmd(cmd, timeout=10)
    time.sleep(2)
    
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => {{ window.scrollTo(0, 600); return \"done\"; }}" 2>/dev/null'
    run_cmd(cmd, timeout=10)
    time.sleep(2)

def get_page_title():
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => document.title" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    return stdout.strip().strip('"')

def get_price():
    # 尝试直接获取价格元素
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => {{ const el = document.querySelector(\".tb-rmb-num\"); return el ? el.textContent : null; }}" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    text = stdout.strip().strip('"')
    
    if text and text != 'null':
        prices = re.findall(r'(\d+)', text)
        if prices:
            price = int(prices[0])
            if 1000 <= price <= 10000:
                return price
    
    # 备用：搜索页面文本
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => document.body.innerText" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    text = stdout.strip()
    
    prices = re.findall(r'[¥￥](\d{3,5})', text)
    valid = [int(p) for p in prices if 2000 <= int(p) <= 8000 and int(p) != 20000]
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
    print("淘宝价格抓取 - 全部20个商品")
    print(f"开始时间: {time.strftime('%H:%M:%S')}")
    print("=" * 60)
    print()
    
    success = 0
    for i, product in enumerate(products, 1):
        print(f"[{i:2d}/20] {product['note']}")
        
        navigate_and_wait(product['url'])
        
        title = get_page_title()
        print(f"       页面: {title[:40] if title else '加载失败'}...")
        
        price = get_price()
        
        if price:
            print(f"       ✅ 价格: ¥{price}")
            save_price(product['id'], price)
            success += 1
        else:
            print(f"       ❌ 未获取到价格")
        
        if i < len(products):
            interval = random.randint(10, 15)
            print(f"       等待 {interval} 秒...")
            time.sleep(interval)
        print()
    
    print("=" * 60)
    print(f"完成: {success}/20 成功")
    print(f"结束时间: {time.strftime('%H:%M:%S')}")
    print("=" * 60)

if __name__ == '__main__':
    main()
