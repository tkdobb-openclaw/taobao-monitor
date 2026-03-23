#!/usr/bin/env python3
"""
淘宝价格抓取 - 使用 stealth
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from playwright_stealth.stealth import Stealth

async def fetch_with_stealth():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        # 应用 stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        print(f"URL: {page.url}")
        print(f"Title: {await page.title()}")
        
        # 检查是否有验证码
        content = await page.content()
        if 'unusual traffic' in content or 'verify' in content:
            print("❌ 被检测到，有验证码")
        else:
            print("✅ 没有验证码")
            # 尝试获取价格
            price = await page.evaluate('''() => {
                const el = document.querySelector('.tb-rmb-num, [class*="priceText--"]');
                return el ? el.innerText : null;
            }''')
            print(f"Price: {price}")
        
        await page.screenshot(path='stealth_test.png')
        print("Screenshot: stealth_test.png")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(fetch_with_stealth())
