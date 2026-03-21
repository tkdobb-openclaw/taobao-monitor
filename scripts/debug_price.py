#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试淘宝价格提取
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def debug():
    url = "https://item.taobao.com/item.htm?id=624281587175"
    auth_file = "~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        # 加载 cookies
        try:
            with open(Path(auth_file).expanduser(), 'r') as f:
                data = json.load(f)
                await context.add_cookies(data.get('cookies', []))
        except Exception as e:
            print(f"Cookies error: {e}")
        
        page = await context.new_page()
        
        print(f"访问: {url}")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        
        print(f"当前 URL: {page.url}")
        print(f"标题: {await page.title()}")
        
        # 获取页面文本
        text = await page.content()
        print(f"页面长度: {len(text)}")
        
        # 查找价格相关文本
        if 'price' in text.lower():
            print("页面包含 price 关键词")
        if '¥' in text:
            print("页面包含 ¥ 符号")
        
        # 尝试用 JS 获取价格
        price_js = await page.evaluate('''() => {
            // 尝试多种选择器
            const selectors = [
                '[class*="price"]',
                '.tb-rmb-num', 
                '.notranslate',
                '[class*="Price"]',
                'span[data-spm="price"]'
            ];
            for (let sel of selectors) {
                const el = document.querySelector(sel);
                if (el) return {selector: sel, text: el.innerText, html: el.outerHTML.substring(0, 200)};
            }
            return null;
        }''')
        
        if price_js:
            print(f"\n找到价格元素:")
            print(f"  选择器: {price_js['selector']}")
            print(f"  文本: {price_js['text']}")
            print(f"  HTML: {price_js['html']}")
        else:
            print("\n没找到价格元素，页面可能还没完全加载或需要登录")
            # 保存页面截图
            await page.screenshot(path='debug_screenshot.png')
            print("已保存截图: debug_screenshot.png")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug())
