#!/usr/bin/env python3
"""
调试 - 查看实际 SKU 文本
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def debug():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=676780234187"  # 大洋潜水 Perdix
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        print(f"访问: {url}")
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)  # 多等一会儿
        
        print(f"标题: {await page.title()}")
        print(f"URL: {page.url}")
        
        # 获取所有 SKU 文本
        sku_texts = await page.evaluate('''() => {
            const items = document.querySelectorAll('[class*="valueItem--"]');
            return Array.from(items).map(el => ({
                text: el.innerText?.trim() || '',
                className: el.className
            }));
        }''')
        
        print(f"\n找到 {len(sku_texts)} 个 SKU 元素:")
        for i, s in enumerate(sku_texts):
            print(f"  [{i}] {s['text']}")
            print(f"      class: {s['className'][:60]}...")
        
        # 检查配置的关键词是否匹配
        target = "perdix2 ti 银色"
        print(f"\n配置关键词: '{target}'")
        for s in sku_texts:
            text = s['text'].lower().replace(' ', '')
            target_clean = target.lower().replace(' ', '')
            if target_clean in text:
                print(f"  ✓ 匹配: {s['text']}")
            else:
                print(f"  ✗ 不匹配: {s['text']}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug())
