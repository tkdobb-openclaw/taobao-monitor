#!/usr/bin/env python3
"""
手动模式价格抓取
用户在前台操作浏览器，AI在后台记录价格
"""

import subprocess
import re
import sqlite3
import sys
from pathlib import Path

TARGET_ID = "E30C9A453542B8CAFF51022789B4948C"

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def get_current_page_info():
    """获取当前页面信息"""
    # 获取标题
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => document.title" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    title = stdout.strip().strip('"')
    
    # 获取URL
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => window.location.href" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    url = stdout.strip().strip('"')
    
    return title, url

def get_price():
    """从当前页面获取价格"""
    # 获取页面文本
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => document.body.innerText" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    text = stdout.strip()
    
    # 提取价格 - Shearwater 潜水表通常在 2000-6000 区间
    prices = re.findall(r'[¥￥](\d{3,5})', text)
    if prices:
        valid_prices = [int(p) for p in prices if 1500 <= int(p) <= 10000]
        if valid_prices:
            return min(valid_prices)
    return None

def save_price(note, url, price):
    """保存价格到数据库"""
    db_path = Path(__file__).parent.parent / "data" / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 根据URL找到对应商品ID
    cursor.execute("SELECT id FROM products WHERE url = ?", (url,))
    result = cursor.fetchone()
    
    if result:
        product_id = result[0]
        cursor.execute("""
            UPDATE products SET last_price = ?, last_check = datetime('now') WHERE id = ?
        """, (price, product_id))
        cursor.execute("""
            INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, datetime('now'))
        """, (product_id, price))
        conn.commit()
        conn.close()
        return True
    else:
        conn.close()
        return False

def main():
    if len(sys.argv) < 2:
        print("用法: python3 manual_crawler.py <商品备注>")
        print("示例: python3 manual_crawler.py '大洋潜水 - Peregrine'")
        return
    
    note = sys.argv[1]
    
    print(f"\n正在抓取: {note}")
    print("-" * 50)
    
    # 获取页面信息
    title, url = get_current_page_info()
    print(f"页面标题: {title}")
    print(f"页面URL: {url[:60]}...")
    
    if 'item.taobao.com' not in url and 'detail.tmall.com' not in url:
        print("❌ 当前不是商品详情页，请确认已打开正确的商品页面")
        return
    
    # 获取价格
    price = get_price()
    
    if price:
        print(f"✅ 抓取到价格: ¥{price}")
        if save_price(note, url, price):
            print(f"✅ 已保存到数据库")
        else:
            print(f"⚠️ 未找到对应商品记录，URL: {url}")
    else:
        print(f"❌ 未获取到有效价格")
    
    print("-" * 50)

if __name__ == '__main__':
    main()
