#!/usr/bin/env python3
"""
调试价格提取
"""
import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright

async def debug():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        # 获取页面文本内容
        content = await page.content()
        
        # 查找价格相关的文本
        import re
        prices = re.findall(r'¥([\d,]+(?:\.\d{2})?)', content)
        print(f"找到 {len(prices)} 个价格:")
        for p in prices[:10]:
            print(f"  - ¥{p}")
        
        # 查找特定的价格元素
        price_info = await page.evaluate('''() => {
            const result = [];
            // 查找所有包含 ¥ 的元素
            document.querySelectorAll('*').forEach(el => {
                if (el.children.length === 0 && el.textContent.includes('¥')) {
                    result.push({
                        tag: el.tagName,
                        text: el.textContent.trim(),
                        class: el.className
                    });
                }
            });
            return result.slice(0, 10);
        }''')
        
        print("\n包含 ¥ 的元素:")
        for info in price_info:
            print(f"  [{info['tag']}] class={info['class'][:30] if info['class'] else 'N/A'}...: {info['text']}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug())
