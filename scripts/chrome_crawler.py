#!/usr/bin/env python3
"""
使用 Chrome 扩展自动化抓取淘宝价格
直接使用已知的 target_id
"""

import subprocess
import re
import time
import sqlite3
from pathlib import Path

# 淘宝标签页 ID (从之前的 tabs 命令获取)
TARGET_ID = "E30C9A453542B8CAFF51022789B4948C"

# 20个商品链接
products = [
    # Perdix
    {"id": 2, "note": "大洋潜水 - Perdix", "url": "https://item.taobao.com/item.htm?id=676780234187"},
    {"id": 3, "note": "塞班户外 - Perdix", "url": "https://item.taobao.com/item.htm?id=676463247224"},
    {"id": 4, "note": "白鳍鲨 - Perdix", "url": "https://item.taobao.com/item.htm?id=544005716799"},
    {"id": 5, "note": "岁老板 - Perdix", "url": "https://item.taobao.com/item.htm?id=675444560376"},
    {"id": 6, "note": "三潜社 - Perdix", "url": "https://item.taobao.com/item.htm?id=632230014333"},
    # Peregrine
    {"id": 7, "note": "大洋潜水 - Peregrine", "url": "https://item.taobao.com/item.htm?id=623907417709"},
    {"id": 8, "note": "塞班户外 - Peregrine", "url": "https://item.taobao.com/item.htm?id=624281587175"},
    {"id": 9, "note": "白鳍鲨 - Peregrine", "url": "https://item.taobao.com/item.htm?id=623777445212"},
    {"id": 10, "note": "岁老板 - Peregrine", "url": "https://item.taobao.com/item.htm?id=626899529012"},
    {"id": 11, "note": "三潜社 - Peregrine", "url": "https://item.taobao.com/item.htm?id=988652922548"},
    # Teric
    {"id": 12, "note": "大洋潜水 - Teric", "url": "https://item.taobao.com/item.htm?id=584863170468"},
    {"id": 13, "note": "塞班户外 - Teric", "url": "https://item.taobao.com/item.htm?id=575523804132"},
    {"id": 14, "note": "白鳍鲨 - Teric", "url": "https://item.taobao.com/item.htm?id=570722701118"},
    {"id": 15, "note": "岁老板 - Teric", "url": "https://item.taobao.com/item.htm?id=667904575973"},
    {"id": 16, "note": "三潜社 - Teric", "url": "https://item.taobao.com/item.htm?id=629563113404"},
    # Tern
    {"id": 17, "note": "大洋潜水 - Tern", "url": "https://item.taobao.com/item.htm?id=753330765355"},
    {"id": 18, "note": "塞班户外 - Tern", "url": "https://item.taobao.com/item.htm?id=756509652959"},
    {"id": 19, "note": "白鳍鲨 - Tern", "url": "https://item.taobao.com/item.htm?id=753672216139"},
    {"id": 20, "note": "岁老板 - Tern", "url": "https://item.taobao.com/item.htm?id=749763697229"},
    {"id": 21, "note": "三潜社 - Tern", "url": "https://item.taobao.com/item.htm?id=899733746263"},
]

def run_cmd(cmd, timeout=30):
    """运行命令"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def navigate_to(url):
    """导航到指定URL"""
    cmd = f'openclaw browser --browser-profile chrome-relay navigate --target-id {TARGET_ID} --url "{url}" 2>/dev/null'
    stdout, stderr, code = run_cmd(cmd, timeout=25)
    print(f"    导航结果: {code}")
    time.sleep(4)  # 等待页面加载

def get_page_info():
    """获取页面标题和URL"""
    # 获取标题
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => document.title" 2>/dev/null'
    stdout, _, _ = run_cmd(cmd, timeout=15)
    title = stdout.strip().split('\n')[-1].strip().strip('"')
    
    # 获取URL
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => window.location.href" 2>/dev/null'
    stdout, _, _ = run_cmd(cmd, timeout=15)
    url = stdout.strip().split('\n')[-1].strip().strip('"')
    
    return title, url

def get_price():
    """从页面获取价格"""
    # 先尝试获取页面源码找价格
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} --fn "() => document.body.innerText" 2>/dev/null'
    stdout, _, _ = run_cmd(cmd, timeout=15)
    text = stdout.strip()
    
    # 提取价格
    prices = re.findall(r'[¥￥](\d+)', text)
    if prices:
        # 返回第一个找到的价格
        return int(prices[0])
    
    return None

def save_price(product_id, price):
    """保存价格到数据库"""
    db_path = Path(__file__).parent.parent / "data" / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 更新最后价格
    cursor.execute("""
        UPDATE products 
        SET last_price = ?, last_check = datetime('now')
        WHERE id = ?
    """, (price, product_id))
    
    # 记录历史
    cursor.execute("""
        INSERT INTO price_history (product_id, price, timestamp)
        VALUES (?, ?, datetime('now'))
    """, (product_id, price))
    
    conn.commit()
    conn.close()

def main():
    print("=" * 60)
    print("淘宝价格自动化抓取 (Chrome扩展模式)")
    print("=" * 60)
    print()
    
    success_count = 0
    for i, product in enumerate(products, 1):
        print(f"[{i:2d}/{len(products)}] {product['note']}")
        
        # 导航到商品页
        navigate_to(product['url'])
        
        # 获取页面信息
        title, current_url = get_page_info()
        print(f"       标题: {title[:40]}...")
        print(f"       URL: {current_url[:50]}...")
        
        # 获取价格
        price = get_price()
        
        if price:
            print(f"       ✅ 价格: ¥{price}")
            save_price(product['id'], price)
            success_count += 1
        else:
            print(f"       ❌ 未获取到价格")
        
        print()
        time.sleep(1)
    
    print("=" * 60)
    print(f"完成: {success_count}/{len(products)} 个商品成功")
    print("=" * 60)

if __name__ == '__main__':
    main()
