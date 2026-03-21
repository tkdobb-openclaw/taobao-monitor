#!/usr/bin/env python3
"""
直接读取页面价格数据
"""
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

async def read_prices():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        # 读取所有价格
        prices = await page.evaluate('''() => {
            const result = [];
            const elements = document.querySelectorAll('*');
            for (let el of elements) {
                const text = el.innerText;
                if (text && text.match(/¥\s*[\d,]+/) && el.children.length === 0) {
                    result.push(text.trim());
                }
            }
            return result.slice(0, 20);
        }''')
        
        print("页面上的价格文本:")
        seen = set()
        for p in prices:
            if p not in seen:
                seen.add(p)
                print(f"  {p}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(read_prices())
