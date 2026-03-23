#!/usr/bin/env python3
"""
淘宝价格抓取 - 反爬优化版
增加随机延迟、滚动交互、多账号轮换
"""

import subprocess
import re
import time
import random
import sqlite3
from pathlib import Path

TARGET_ID = "E30C9A453542B8CAFF51022789B4948C"

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

def human_like_delay(min_sec=30, max_sec=60):
    """随机延迟，模拟真人浏览间隔"""
    delay = random.randint(min_sec, max_sec)
    print(f"    等待 {delay} 秒...")
    time.sleep(delay)

def random_scroll():
    """随机滚动页面"""
    scroll_amount = random.randint(300, 800)
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
        --fn "() => {{ window.scrollTo(0, {scroll_amount}); return \"scrolled\"; }}" 2>/dev/null'
    run_cmd(cmd, timeout=10)
    time.sleep(random.uniform(1, 3))

def random_mouse_move():
    """模拟鼠标移动"""
    x, y = random.randint(100, 800), random.randint(100, 600)
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
        --fn "() => {{ document.dispatchEvent(new MouseEvent(\"mousemove\", {{ clientX: {x}, clientY: {y} }})); return \"moved\"; }}" 2>/dev/null'
    run_cmd(cmd, timeout=10)

def navigate_to(url):
    """导航到商品页，增加随机行为"""
    print(f"    导航到商品页...")
    cmd = f'openclaw browser --browser-profile chrome-relay navigate --target-id {TARGET_ID} --url "{url}" 2>/dev/null'
    stdout, stderr, code = run_cmd(cmd, timeout=30)
    
    # 随机等待页面加载
    time.sleep(random.uniform(5, 8))
    
    # 模拟真人行为：滚动、鼠标移动
    if random.random() > 0.3:  # 70% 概率滚动
        random_scroll()
    if random.random() > 0.5:  # 50% 概率移动鼠标
        random_mouse_move()
    
    return code

def get_page_info():
    """获取页面信息"""
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
        --fn "() => JSON.stringify({{ title: document.title, url: window.location.href }})" 2>/dev/null'
    stdout, _, _ = run_cmd(cmd, timeout=15)
    
    try:
        last_line = stdout.strip().split('\n')[-1]
        data = json.loads(last_line.strip().strip('"').replace('\\"', '"'))
        return data.get('title', ''), data.get('url', '')
    except:
        return '', ''

def get_price():
    """获取价格 - 多种策略"""
    # 策略1: 直接找价格元素
    selectors = [
        'document.querySelector("[class*=price]")?.textContent',
        'document.querySelector(".tb-rmb-num")?.textContent',
        'document.querySelector("[class*=Price]")?.textContent',
    ]
    
    for selector in selectors:
        cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
            --fn "() => {selector}" 2>/dev/null'
        stdout, _, _ = run_cmd(cmd, timeout=10)
        text = stdout.strip().split('\n')[-1].strip().strip('"')
        
        if text and text != 'null' and '¥' in text:
            prices = re.findall(r'[¥￥](\d+)', text)
            if prices:
                return int(prices[0])
    
    # 策略2: 搜索页面文本
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
        --fn "() => document.body.innerText" 2>/dev/null'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    text = stdout.strip()
    
    # 找价格模式
    prices = re.findall(r'[¥￥](\d{3,5})', text)
    if prices:
        # 过滤掉异常值（如20000这种跳首页的值）
        valid_prices = [int(p) for p in prices if 1000 <= int(p) <= 20000 and int(p) != 20000]
        if valid_prices:
            return min(valid_prices)  # 返回最小价格（通常是促销价）
    
    return None

def save_price(product_id, price):
    """保存价格"""
    db_path = Path(__file__).parent.parent / "data" / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE products SET last_price = ?, last_check = datetime('now') WHERE id = ?
    """, (price, product_id))
    
    cursor.execute("""
        INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, datetime('now'))
    """, (product_id, price))
    
    conn.commit()
    conn.close()

def main():
    import json
    
    print("=" * 60)
    print("淘宝价格抓取 - 反爬优化版")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    success_count = 0
    failed_urls = []
    
    for i, product in enumerate(products, 1):
        print(f"[{i:2d}/{len(products)}] {product['note']}")
        
        # 导航到商品页
        navigate_to(product['url'])
        
        # 获取页面信息
        title, current_url = get_page_info()
        print(f"       页面: {title[:40] if title else '加载失败'}...")
        
        # 检查是否被跳转（淘宝首页）
        if 'taobao.com' in current_url and 'item.htm' not in current_url:
            print(f"       ⚠️ 被跳转到首页，可能触发风控")
            failed_urls.append(product['url'])
            # 加长等待时间
            human_like_delay(60, 120)
            continue
        
        # 获取价格
        price = get_price()
        
        if price and price != 20000:
            print(f"       ✅ 价格: ¥{price}")
            save_price(product['id'], price)
            success_count += 1
        else:
            print(f"       ❌ 未获取到有效价格")
        
        # 随机间隔 - 模拟真人浏览间隔
        if i < len(products):  # 最后一个不需要等待
            human_like_delay(30, 60)
        
        print()
    
    print("=" * 60)
    print(f"完成: {success_count}/{len(products)} 个商品成功")
    if failed_urls:
        print(f"失败URL数: {len(failed_urls)}")
    print(f"结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == '__main__':
    main()
