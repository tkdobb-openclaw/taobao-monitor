#!/usr/bin/env python3
"""
深入分析淘宝 SKU 价格结构
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def analyze_sku_prices():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"  # 塞班户外 Peregrine
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        # 获取完整的 g_config
        g_config = await page.evaluate('''() => {
            return window.g_config || null;
        }''')
        
        if g_config:
            print("g_config 结构:")
            print(json.dumps(list(g_config.keys()), indent=2))
            
            if 'sku' in g_config:
                sku = g_config['sku']
                print("\nsku 数据:")
                print(json.dumps(sku, ensure_ascii=False, indent=2)[:2000])
        
        # 尝试找到所有价格
        prices = await page.evaluate('''() => {
            // 查找页面上所有包含 ¥ 的元素
            const results = [];
            const elements = document.querySelectorAll('*');
            for (let el of elements) {
                const text = el.innerText;
                if (text && text.match(/¥\s*[\d,]+/) && el.children.length === 0) {
                    results.push({
                        text: text.trim(),
                        parent: el.parentElement?.className?.substring(0, 50)
                    });
                }
            }
            return results.slice(0, 20);
        }''')
        
        print("\n页面上找到的价格元素:")
        for p in prices:
            print(f"  {p['text']} (parent: {p['parent']})")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(analyze_sku_prices())
