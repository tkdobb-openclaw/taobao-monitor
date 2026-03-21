#!/usr/bin/env python3
"""
淘宝价格抓取 - 调试版
"""
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

async def debug_price():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        # 点击一个 SKU
        await page.evaluate('''() => {
            const items = document.querySelectorAll('[class*="valueItem--"]');
            for (let item of items) {
                if (item.innerText.includes('黑色经典版')) {
                    item.click();
                    return 'clicked';
                }
            }
            return 'not found';
        }''')
        
        await asyncio.sleep(2)
        
        # 尝试多种方式获取价格
        prices = await page.evaluate('''() => {
            const results = [];
            
            // 方式1: 常见价格选择器
            const selectors = [
                '[class*="priceText--"]',
                '[class*="Price--"]',
                '.tb-rmb-num',
                '.price',
                '[data-spm*="price"]',
                'span[class*="price"]'
            ];
            
            for (let sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText) {
                    results.push({method: sel, text: el.innerText.substring(0, 50)});
                }
            }
            
            // 方式2: 搜索所有包含 ¥ 的文本
            const allElements = document.querySelectorAll('*');
            for (let el of allElements) {
                if (el.children.length === 0 && el.innerText) {
                    const text = el.innerText.trim();
                    if (text.startsWith('¥') && text.length < 20) {
                        results.push({method: 'text-search', text: text});
                        if (results.length > 10) break;
                    }
                }
            }
            
            return results;
        }''')
        
        print(f"找到 {len(prices)} 个价格元素:")
        for p in prices:
            print(f"  [{p['method']}] {p['text']}")
        
        # 截图
        await page.screenshot(path='price_debug.png')
        print("\n截图: price_debug.png")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug_price())
