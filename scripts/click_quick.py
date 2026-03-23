#!/usr/bin/env python3
"""
快速测试 SKU 点击 - 只测前 4 个
"""
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

async def quick_test():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        print(f"访问商品页...")
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        # 获取所有 SKU
        all_items = await page.query_selector_all('[class*="valueItem--"]')
        items = [item for item in all_items if await item.text_content()][0:4]  # 只取4个
        
        print(f"测试前 {len(items)} 个 SKU:\n")
        
        for i, item in enumerate(items):
            text = (await item.text_content()).strip()
            print(f"[{i+1}] {text}")
            
            try:
                await item.click()
                await asyncio.sleep(1)
                
                # 获取价格
                price_text = await page.evaluate('''() => {
                    const el = document.querySelector('[class*="priceText--"]');
                    return el ? el.innerText : 'N/A';
                }''')
                
                match = re.search(r'([\d.]+)', price_text)
                price = f"¥{match.group(1)}" if match else price_text
                print(f"    价格: {price}\n")
            except Exception as e:
                print(f"    失败: {e}\n")
        
        await browser.close()
        print("测试完成")

if __name__ == '__main__':
    asyncio.run(quick_test())
