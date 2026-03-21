#!/usr/bin/env python3
"""
查找 SKU 元素的多种方式
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def find_sku_elements():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        # 截图看看页面结构
        await page.screenshot(path='sku_page.png', full_page=True)
        print("已截图: sku_page.png")
        
        # 多种方式查找 SKU
        selectors = [
            'a', 'button', 'span', 'div',
            '[role="button"]',
            '[data-spm]'
        ]
        
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            for el in elements:
                text = await el.text_content()
                if text and ('灰' in text or '黑' in text or 'LIGHT' in text or 'DARK' in text):
                    class_name = await el.get_attribute('class') or 'N/A'
                    print(f"找到: {text[:30]} | class: {class_name[:50]}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(find_sku_elements())
