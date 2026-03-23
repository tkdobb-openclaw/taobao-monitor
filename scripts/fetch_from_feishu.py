#!/usr/bin/env python3
"""
淘宝价格抓取 - 从飞书表格实时读取
"""

import subprocess
import re
import time
import random
import sqlite3
import json
from pathlib import Path

TARGET_ID = "9F774C740CC4F9178A9B0A4F84DCE2AC"
APP_ID = "cli_a933ae5b17b9dcd4"
APP_SECRET = "pRrUlxBcvBNC4woA2abEHd3fVOyObxaT"
BASE_ID = "HTs1bGCYaaIo2WsXAvbcHni4nSd"
TABLE_ID = "tbl3KGI2KEADYH8B"

def get_feishu_token():
    """获取飞书token"""
    cmd = f'''curl -s "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
        -H "Content-Type: application/json" \
        -d '{{"app_id":"{APP_ID}","app_secret":"{APP_SECRET}"}}' | jq -r '.tenant_access_token' '''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def fetch_products_from_feishu():
    """从飞书表格读取商品列表"""
    token = get_feishu_token()
    cmd = f'''curl -s "https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{TABLE_ID}/records?page_size=100" \
        -H "Authorization: Bearer {token}" '''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    try:
        data = json.loads(result.stdout)
        products = []
        
        for item in data.get('data', {}).get('items', []):
            fields = item.get('fields', {})
            store = fields.get('列1', '')
            
            if not store or store == 'null':
                continue
            
            # 每个产品有4个型号
            product_types = [
                ('perdix', 'Shearwater Perdix'),
                ('peregrine', 'Shearwater Peregrine'),
                ('teric', 'Shearwater Teric'),
                ('tern', 'Shearwater Tern')
            ]
            
            for type_key, type_name in product_types:
                url_field = fields.get(type_key, {})
                if isinstance(url_field, dict):
                    url = url_field.get('text', '')
                    if url and 'item.taobao.com' in url:
                        products.append({
                            'store': store,
                            'type': type_name,
                            'url': url,
                            'note': f"{store} - {type_name}"
                        })
        
        return products
    except Exception as e:
        print(f"读取飞书表格失败: {e}")
        return []

def run_cmd(cmd, timeout=30):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def navigate_and_wait(url):
    """导航并等待"""
    print(f"  打开: {url[:50]}...")
    cmd = f'openclaw browser --browser-profile chrome-relay navigate --target-id {TARGET_ID} --url "{url}" 2>/dev/null'
    run_cmd(cmd, timeout=30)
    
    wait_time = random.randint(8, 12)
    print(f"  等待 {wait_time} 秒...")
    time.sleep(wait_time)
    
    # 滚动
    for pos in [300, 500]:
        cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => {{ window.scrollTo(0, {pos}); }}" 2>/dev/null'
        run_cmd(cmd, timeout=10)
        time.sleep(2)

def get_price():
    """获取价格"""
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => document.body.innerText" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=15)
    text = stdout.strip()
    
    prices = re.findall(r'[¥￥](\d{3,5})', text)
    valid = [int(p) for p in prices if 2000 <= int(p) <= 8000 
             and int(p) not in [20000, 3561, 2760, 2407]]
    if valid:
        return min(valid)
    return None

def save_price(url, price):
    """保存价格"""
    db_path = Path(__file__).parent.parent / "data" / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM products WHERE url = ?", (url,))
    result = cursor.fetchone()
    
    if result:
        product_id = result[0]
        cursor.execute("UPDATE products SET last_price = ?, last_check = datetime('now') WHERE id = ?", (price, product_id))
        cursor.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, datetime('now'))", (product_id, price))
        conn.commit()
    
    conn.close()

def main():
    print("=" * 60)
    print("淘宝价格抓取 - 从飞书表格读取")
    print("=" * 60)
    
    # 从飞书读取商品
    print("\n正在读取飞书表格...")
    products = fetch_products_from_feishu()
    print(f"读取到 {len(products)} 个商品\n")
    
    if not products:
        print("没有读取到商品，请检查表格")
        return
    
    success = 0
    for i, product in enumerate(products, 1):
        print(f"[{i:2d}/{len(products)}] {product['note']}")
        
        navigate_and_wait(product['url'])
        
        price = get_price()
        
        if price:
            print(f"       ✅ 价格: ¥{price}")
            save_price(product['url'], price)
            success += 1
        else:
            print(f"       ❌ 未获取到价格")
        
        if i < len(products):
            time.sleep(random.randint(5, 10))
        print()
    
    print("=" * 60)
    print(f"完成: {success}/{len(products)} 成功")
    print("=" * 60)

if __name__ == '__main__':
    main()
