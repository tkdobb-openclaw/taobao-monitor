#!/usr/bin/env python3
"""
点击 SKU 获取真实价格
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def click_sku_test():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        # 先获取默认价格
        default_price = await page.evaluate('''() => {
            const el = document.querySelector('.tb-rmb-num') || 
                       document.querySelector('[class*="price"]');
            return el ? el.innerText : null;
        }''')
        print(f"默认显示价格: {default_price}")
        
        # 查找所有可点击的 SKU
        sku_buttons = await page.query_selector_all('a[class*="sku"], button[class*="sku"], [data-spm*="sku"]')
        print(f"\n找到 {len(sku_buttons)} 个 SKU 按钮")
        
        for i, btn in enumerate(sku_buttons[:5]):
            text = await btn.text_content()
            print(f"\nSKU {i+1}: {text[:30] if text else 'N/A'}")
            
            # 点击
            try:
                await btn.click()
                await asyncio.sleep(1.5)
                
                # 获取点击后的价格
                new_price = await page.evaluate('''() => {
                    const el = document.querySelector('.tb-rmb-num') || 
                               document.querySelector('[class*="price--"]');
                    return el ? el.innerText : null;
                }''')
                print(f"  点击后价格: {new_price}")
            except Exception as e:
                print(f"  点击失败: {e}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(click_sku_test())
