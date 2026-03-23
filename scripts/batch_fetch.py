#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量抓取淘宝价格并更新数据库
"""
import sqlite3
import subprocess
import json
import re
from datetime import datetime
from pathlib import Path

DB_PATH = Path("~/.openclaw/workspace/skills/taobao-monitor/data/monitor.db").expanduser()
AUTH_FILE = Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser()

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def get_all_products():
    """获取所有活跃商品"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, url, title, last_price 
        FROM products 
        WHERE status = 'active'
    """)
    products = cursor.fetchall()
    conn.close()
    return products

def run_agent_browser_cmd(cmd, timeout=45):
    """运行agent-browser命令"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "Command timed out", 1
    except Exception as e:
        return "ERROR", str(e), 1

def extract_price_with_agent_browser(url):
    """使用agent-browser提取价格"""
    # 打开页面（agent-browser会自动使用保存的会话）
    open_cmd = f'npx agent-browser open "{url}"'
    stdout, stderr, code = run_agent_browser_cmd(open_cmd, timeout=30)
    if code != 0:
        return None, f"Open failed: {stderr}"
    
    # 等待页面加载
    run_agent_browser_cmd("npx agent-browser wait 4000", timeout=15)
    
    # 尝试多种方式获取价格
    selectors = [
        'document.querySelector(".tb-rmb-num")?.textContent',
        'document.querySelector(".notranslate")?.textContent',
        'document.querySelector("[class*=\\"price\\"] span")?.textContent',
        'Array.from(document.querySelectorAll("span")).find(el => /\\d+\\.\\d{2}/.test(el.textContent) && el.textContent.includes("¥"))?.textContent',
        'document.querySelector(".tm-price-cur")?.textContent',
        'document.querySelector(".tm-price")?.textContent',
    ]
    
    for selector in selectors:
        eval_cmd = f'npx agent-browser eval \'{selector}\''
        stdout, stderr, code = run_agent_browser_cmd(eval_cmd, timeout=15)
        
        if stdout and stdout != 'null' and stdout != 'undefined':
            # 解析价格
            price_text = stdout.strip().strip('"')
            price = parse_price(price_text)
            if price:
                return price, None
    
    return None, "Could not extract price"

def parse_price(text):
    """从文本中提取价格数字"""
    if not text:
        return None
    # 查找价格格式: ¥1234.56, ￥1234, 1234.56等
    matches = re.findall(r'[￥¥]?\s*(\d+(?:\.\d{1,2})?)', text)
    if matches:
        try:
            return float(matches[0])
        except:
            pass
    return None

def update_price(product_id, new_price, error=None):
    """更新价格到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    if error:
        # 只更新检查时间
        cursor.execute("""
            UPDATE products 
            SET last_check = ?
            WHERE id = ?
        """, (now, product_id))
    else:
        # 更新价格历史和产品表
        cursor.execute("""
            INSERT INTO price_history (product_id, price, timestamp)
            VALUES (?, ?, ?)
        """, (product_id, new_price, now))
        
        cursor.execute("""
            UPDATE products 
            SET last_price = ?, last_check = ?
            WHERE id = ?
        """, (new_price, now, product_id))
    
    conn.commit()
    conn.close()

def main():
    products = get_all_products()
    total = len(products)
    success = 0
    failed = 0
    results = []
    
    print(f"开始抓取 {total} 个商品的价格...")
    print("=" * 60)
    
    for idx, (pid, url, title, last_price) in enumerate(products, 1):
        print(f"\n[{idx}/{total}] 抓取: {title or url}")
        print(f"    URL: {url}")
        print(f"    上次价格: {last_price if last_price else 'N/A'}")
        
        new_price, error = extract_price_with_agent_browser(url)
        
        if error:
            failed += 1
            print(f"    ❌ 失败: {error}")
            update_price(pid, None, error)
            results.append({
                'id': pid,
                'title': title,
                'last_price': last_price,
                'new_price': None,
                'status': 'failed',
                'error': error
            })
        else:
            success += 1
            price_change = ""
            if last_price and new_price:
                diff = new_price - last_price
                if abs(diff) > 0.01:
                    direction = "📉" if diff < 0 else "📈"
                    price_change = f" {direction} {diff:+.2f}"
            
            print(f"    ✅ 成功: ¥{new_price}{price_change}")
            update_price(pid, new_price)
            results.append({
                'id': pid,
                'title': title,
                'last_price': last_price,
                'new_price': new_price,
                'status': 'success',
                'change': (new_price - last_price) if (last_price and new_price) else None
            })
    
    # 生成报告
    print("\n" + "=" * 60)
    print("抓取报告")
    print("=" * 60)
    print(f"总计商品: {total}")
    print(f"成功: {success}")
    print(f"失败: {failed}")
    
    # 价格变动
    price_changes = [r for r in results if r['status'] == 'success' and r['change'] and abs(r['change']) > 0.01]
    if price_changes:
        print(f"\n价格变动 ({len(price_changes)}个):")
        for r in price_changes:
            direction = "📉 下跌" if r['change'] < 0 else "📈 上涨"
            print(f"  • {r['title']}: ¥{r['last_price']} → ¥{r['new_price']} ({direction} {abs(r['change']):.2f})")
    else:
        print("\n无价格变动")
    
    # 失败的商品
    failed_items = [r for r in results if r['status'] == 'failed']
    if failed_items:
        print(f"\n失败的商品 ({len(failed_items)}个):")
        for r in failed_items:
            print(f"  • {r['title'] or r['id']}: {r['error']}")
    
    # 保存报告
    report_file = Path("~/.openclaw/workspace/skills/taobao-monitor/logs/fetch_report.json").expanduser()
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total': total,
            'success': success,
            'failed': failed,
            'results': results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存: {report_file}")

if __name__ == '__main__':
    main()
