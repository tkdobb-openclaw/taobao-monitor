#!/usr/bin/env python3
"""
淘宝价格抓取 - Playwright 常驻版（使用新登录态）
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def test_fetch():
    auth_file = Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 加载登录态
        context = await browser.new_context(storage_state=str(auth_file))
        page = await context.new_page()
        
        # 测试商品
        url = "https://item.taobao.com/item.htm?id=624281587175"
        print(f"访问: {url}")
        
        # 访问页面，不等待 networkidle
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)  # 简单等待
        
        print(f"当前 URL: {page.url}")
        print(f"标题: {await page.title()}")
        
        # 检查是否登录成功
        if 'login' not in page.url:
            print("✅ 登录有效！")
            
            # 提取价格
            price_selectors = [
                '[class*="priceText--"]',
                '.tb-rmb-num',
                '[class*="price"]',
            ]
            
            for selector in price_selectors:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        text = await el.text_content()
                        print(f"价格元素 ({selector}): {text}")
                except:
                    pass
            
            # 保存截图
            await page.screenshot(path='test_result.png')
            print("已保存截图: test_result.png")
        else:
            print("❌ 还是被跳登录页")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_fetch())
