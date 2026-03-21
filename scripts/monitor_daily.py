#!/usr/bin/env python3
"""
淘宝价格监控系统 - 完整版
定时从飞书读取商品，使用 browser relay 抓取，飞书通知
"""

import subprocess
import re
import time
import random
import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime

# 配置
APP_ID = "cli_a933ae5b17b9dcd4"
APP_SECRET = "pRrUlxBcvBNC4woA2abEHd3fVOyObxaT"
BASE_ID = "HTs1bGCYaaIo2WsXAvbcHni4nSd"
TABLE_ID = "tbl3KGI2KEADYH8B"
CHAT_ID = "oc_04717cb2f786e5e9a2869f84840924d8"

def get_target_id():
    """获取当前附加的标签页ID"""
    cmd = "openclaw browser --browser-profile chrome-relay tabs 2>/dev/null | grep 'id:' | head -1 | awk '{print $2}'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    target_id = result.stdout.strip()
    return target_id if target_id else None

def send_feishu_msg(msg):
    """发送飞书消息"""
    cmd = f'openclaw feishu chat send "{CHAT_ID}" "{msg}" 2>/dev/null'
    subprocess.run(cmd, shell=True)

def get_feishu_token():
    cmd = f'''curl -s "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
        -H "Content-Type: application/json" \
        -d '{{"app_id":"{APP_ID}","app_secret":"{APP_SECRET}"}}' | jq -r '.tenant_access_token' '''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip()

def fetch_products():
    """从飞书读取商品"""
    token = get_feishu_token()
    cmd = f'''curl -s "https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables/{TABLE_ID}/records?page_size=200" \
        -H "Authorization: Bearer {token}" '''
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    
    try:
        data = json.loads(result.stdout)
        products = []
        
        for item in data.get('data', {}).get('items', []):
            fields = item.get('fields', {})
            store = fields.get('列1', '')
            
            if not store or store == 'null':
                continue
            
            for type_key, type_name in [('perdix', 'Perdix'), ('peregrine', 'Peregrine'), 
                                         ('teric', 'Teric'), ('tern', 'Tern')]:
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
        print(f"读取飞书失败: {e}")
        return []

def run_browser_cmd(cmd, timeout=20):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except:
        return "", "timeout", 1

def grab_price(product, target_id):
    """抓取单个商品价格"""
    url = product['url']
    note = product['note']
    
    # 导航 - url是位置参数不是选项
    cmd = f'openclaw browser --browser-profile chrome-relay navigate --target-id {target_id} "{url}" 2>/dev/null'
    run_browser_cmd(cmd, timeout=25)
    time.sleep(random.randint(8, 12))
    
    # 滚动
    for pos in [300, 500]:
        cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {target_id} --fn "() => {{ window.scrollTo(0, {pos}); }}" 2>/dev/null'
        run_browser_cmd(cmd, timeout=10)
        time.sleep(2)
    
    # 获取价格
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {target_id} --fn "() => document.body.innerText" 2>/dev/null | tail -1'
    stdout, _, _ = run_browser_cmd(cmd, timeout=15)
    text = stdout.strip()
    
    prices = re.findall(r'[¥￥](\d{3,5})', text)
    valid = [int(p) for p in prices if 1000 <= int(p) <= 20000]
    
    return min(valid) if valid else None

def get_db_price(url):
    """获取数据库中的历史价格"""
    db_path = Path(__file__).parent.parent / "data" / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT last_price FROM products WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_price(url, price, note):
    """保存价格"""
    db_path = Path(__file__).parent.parent / "data" / "monitor.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM products WHERE url = ?", (url,))
    result = cursor.fetchone()
    
    if result:
        product_id = result[0]
        cursor.execute("UPDATE products SET last_price = ?, last_check = datetime('now') WHERE id = ?", 
                      (price, product_id))
        cursor.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, datetime('now'))", 
                      (product_id, price))
        conn.commit()
    else:
        # 插入新产品
        cursor.execute("INSERT INTO products (url, item_id, title, last_price, note, status) VALUES (?, ?, ?, ?, ?, 'active')",
                      (url, re.search(r'id=(\d+)', url).group(1) if re.search(r'id=(\d+)', url) else '', note, price, note))
        conn.commit()
    
    conn.close()

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始价格监控任务")
    
    # 获取 target_id
    target_id = get_target_id()
    if not target_id:
        print("❌ 未找到附加的浏览器标签页，请确保 Chrome 扩展已开启")
        send_feishu_msg("⚠️ 价格监控：浏览器扩展未连接，请检查")
        sys.exit(1)
    
    print(f"✅ 浏览器已连接: {target_id[:16]}...")
    
    # 读取商品
    print("📖 从飞书表格读取商品...")
    products = fetch_products()
    print(f"📦 共 {len(products)} 个商品")
    
    if not products:
        print("❌ 未读取到商品")
        sys.exit(1)
    
    # 抓取价格
    success = 0
    changed = []
    failed = []
    
    for i, product in enumerate(products, 1):
        print(f"\n[{i}/{len(products)}] {product['note']}")
        
        try:
            price = grab_price(product, target_id)
            
            if price:
                old_price = get_db_price(product['url'])
                save_price(product['url'], price, product['note'])
                success += 1
                
                if old_price and abs(price - old_price) > 1:
                    change_pct = ((price - old_price) / old_price) * 100
                    changed.append({
                        'note': product['note'],
                        'old': old_price,
                        'new': price,
                        'change': change_pct
                    })
                    print(f"   ✅ ¥{price} (变动: {change_pct:+.1f}%)")
                else:
                    print(f"   ✅ ¥{price}")
            else:
                print(f"   ❌ 未获取到价格")
                failed.append(product['note'])
                
        except Exception as e:
            print(f"   ❌ 错误: {e}")
            failed.append(product['note'])
        
        # 间隔
        if i < len(products):
            time.sleep(random.randint(10, 15))
    
    # 发送报告
    report = f"📊 价格监控报告 ({datetime.now().strftime('%m-%d %H:%M')})\n"
    report += f"• 监控商品: {len(products)} 个\n"
    report += f"• 成功抓取: {success} 个\n"
    report += f"• 失败: {len(failed)} 个\n"
    
    if changed:
        report += f"\n💰 价格变动 ({len(changed)} 个):\n"
        for item in changed:
            emoji = "📈" if item['change'] > 0 else "📉"
            report += f"{emoji} {item['note']}: ¥{item['old']} → ¥{item['new']} ({item['change']:+.1f}%)\n"
    
    if failed:
        report += f"\n⚠️ 失败商品: {', '.join(failed[:3])}{'...' if len(failed) > 3 else ''}\n"
    
    print(f"\n{report}")
    send_feishu_msg(report)
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 任务完成")

if __name__ == '__main__':
    main()
