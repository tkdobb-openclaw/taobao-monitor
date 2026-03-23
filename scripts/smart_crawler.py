#!/usr/bin/env python3
"""
淘宝价格抓取 - 智能等待版
等待价格元素出现后再抓取
"""

import subprocess
import re
import time
import sqlite3
from pathlib import Path

TARGET_ID = "E30C9A453542B8CAFF51022789B4948C"

def run_cmd(cmd, timeout=15):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def wait_for_price_element(max_wait=10):
    """等待价格元素出现"""
    for i in range(max_wait):
        # 检查是否有价格相关元素
        cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
            --fn "() => document.querySelector(\"[class*=price], .tb-rmb-num\") !== null" 2>/dev/null | tail -1'
        stdout, _, _ = run_cmd(cmd, timeout=5)
        if 'true' in stdout:
            return True
        time.sleep(1)
    return False

def scroll_to_price():
    """滚动到价格区域"""
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
        --fn "() => {{ window.scrollTo(0, 400); return \"done\"; }}" 2>/dev/null'
    run_cmd(cmd, timeout=5)
    time.sleep(1)

def get_price():
    """获取价格"""
    # 先尝试找特定的价格元素
    selectors = [
        'document.querySelector(".tb-rmb-num")?.textContent',
        'document.querySelector("[class*=priceText]")?.textContent',
        'document.querySelector("[class*=Price]")?.textContent',
    ]
    
    for selector in selectors:
        cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
            --fn "() => {selector}" 2>/dev/null | tail -1'
        stdout, _, _ = run_cmd(cmd, timeout=10)
        text = stdout.strip().strip('"')
        
        if text and text != 'null' and text != 'undefined':
            prices = re.findall(r'[¥￥]?\s*(\d{3,5})', text)
            if prices:
                price = int(prices[0])
                if 1500 <= price <= 10000 and price != 20000:
                    return price
    
    # 备用：从页面文本搜索
    cmd = f'openclaw browser --browser-profile chrome-relay evaluate --target-id {TARGET_ID} \
        --fn "() => document.body.innerText" 2>/dev/null | tail -1'
    stdout, _, _ = run_cmd(cmd, timeout=10)
    text = stdout.strip()
    
    # 找价格模式 - 潜水表常见价格区间
    prices = re.findall(r'[¥￥]\s*(\d{3,5})', text)
    valid = [int(p) for p in prices if 2000 <= int(p) <= 8000]
    if valid:
        return min(valid)
    
    return None

def grab_price(note):
    """抓取当前页面价格"""
    print(f"\n抓取: {note}")
    print("-" * 40)
    
    # 等待价格元素
    print("等待价格元素加载...")
    if wait_for_price_element(15):
        print("✅ 价格元素已出现")
    else:
        print("⚠️ 超时，继续尝试")
    
    # 滚动到价格区域
    scroll_to_price()
    
    # 获取价格
    price = get_price()
    
    if price:
        print(f"✅ 价格: ¥{price}")
        return price
    else:
        print("❌ 未获取到价格")
        return None

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 smart_crawler.py '店铺 - 商品名'")
        sys.exit(1)
    
    note = sys.argv[1]
    price = grab_price(note)
    
    if price:
        # 保存到数据库...
        pass
