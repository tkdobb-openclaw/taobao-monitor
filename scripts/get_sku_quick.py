#!/usr/bin/env python3
"""
快速点击 SKU 获取价格
"""
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

async def get_sku_prices():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        # 只取前 4 个 SKU（主要款式）
        all_items = await page.query_selector_all('[class*="valueItem--"]')
        sku_items = all_items[:4]
        
        prices = []
        for i, item in enumerate(sku_items):
            text = await item.text_content()
            if not text or any(x in text for x in ['表带', '套装']):
                continue
                
            print(f"SKU: {text.strip()[:20]}")
            
            try:
                await item.click()
                await asyncio.sleep(1)
                
                # 获取价格
                price_text = await page.evaluate('''() => {
                    const el = document.querySelector('[class*="priceText--"]') || 
                               document.querySelector('.tb-rmb-num');
                    return el ? el.innerText : null;
                }''')
                
                if price_text:
                    match = re.search(r'([\d,]+\.?\d*)', price_text)
                    if match:
                        price = float(match.group(1).replace(',', ''))
                        prices.append(price)
                        print(f"  → ¥{price}")
            except:
                pass
        
        if prices:
            print(f"\n价格范围: ¥{min(prices):.0f} - ¥{max(prices):.0f}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(get_sku_prices())
