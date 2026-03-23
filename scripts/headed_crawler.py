#!/usr/bin/env python3
"""
淘宝价格抓取 - 可视化模式
使用 headed 浏览器，自动导航，慢速抓取
"""

import subprocess
import re
import time
import random
import sqlite3
from pathlib import Path

TARGET_ID = "E30C9A453542B8CAFF51022789B4948C"

products = [
    {"id": 7, "note": "大洋潜水 - Peregrine", "url": "https://item.taobao.com/item.htm?id=623907417709"},
    {"id": 8, "note": "塞班户外 - Peregrine", "url": "https://item.taobao.com/item.htm?id=624281587175"},
]

def run_cmd(cmd, timeout=20):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def navigate_and_wait(url):
    """导航到页面并等待加载"""
    print(f"  正在打开页面...")
    
    # 导航
    cmd = f'openclaw browser --browser-profile chrome-relay navigate --target-id {TARGET_ID} --url "{url}" 2>/dev/null'
    run_cmd(cmd, timeout=25)
    
    # 等待页面加载（模拟真人阅读时间）
    wait_time = random.randint(5, 8)
    print(f"  等待页面加载... {wait_time}秒")
    time.sleep(wait_time)
    
    # 滚动页面（模拟浏览）
    print(f"  滚动页面...")
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => {{ window.scrollTo(0, 300); return \"done\"; }}" 2>/dev/null'
    run_cmd(cmd, timeout=10)
    time.sleep(2)
    
    # 再滚动一点
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => {{ window.scrollTo(0, 600); return \"done\"; }}" 2>/dev/null'
    run_cmd(cmd, timeout=10)
    time.sleep(2)

def get_page_title():
    """获取页面标题"""
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => document.title" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    return stdout.strip().strip('"')

def get_price():
    """获取价格"""
    # 尝试直接获取价格元素
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
        --fn "() => {{ const el = document.querySelector(\".tb-rmb-num\"); return el ? el.textContent : null; }}" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    text = stdout.strip().strip('"')
    
    if text and text != 'null':
        prices = re.findall(r'(\d+)', text)
        if prices:
            price = int(prices[0])
            if 1000 <= price <= 10000:
                return price
    
    # 备用：搜索页面文本
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
        --fn "() => document.body.innerText" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    text = stdout.strip()
    
    # 找价格
    prices = re.findall(r'[¥￥](\d{3,5})', text)
    valid = [int(p) for p in prices if 2000 <= int(p) <= 8000 and int(p) != 20000]
    if valid:
        return min(valid)
    
    return None

def save_price(product_id, price):
    """保存价格"""
    db_path = Path(__file__).parent.parent / "data" / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("UPDATE products SET last_price = ?, last_check = datetime('now') WHERE id = ?", (price, product_id))
    cursor.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, datetime('now'))", (product_id, price))
    
    conn.commit()
    conn.close()

def main():
    print("=" * 50)
    print("淘宝价格抓取 - 可视化模式")
    print("=" * 50)
    print()
    
    success = 0
    for i, product in enumerate(products, 1):
        print(f"[{i}/{len(products)}] {product['note']}")
        print(f"  URL: {product['url']}")
        
        # 导航并等待
        navigate_and_wait(product['url'])
        
        # 获取标题
        title = get_page_title()
        print(f"  页面标题: {title[:50]}...")
        
        # 获取价格
        price = get_price()
        
        if price:
            print(f"  ✅ 价格: ¥{price}")
            save_price(product['id'], price)
            success += 1
        else:
            print(f"  ❌ 未获取到价格")
        
        # 间隔
        if i < len(products):
            interval = random.randint(10, 15)
            print(f"  等待 {interval} 秒后下一个...")
            time.sleep(interval)
        
        print()
    
    print("=" * 50)
    print(f"完成: {success}/{len(products)} 成功")
    print("=" * 50)

if __name__ == '__main__':
    main()
