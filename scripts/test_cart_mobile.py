#!/usr/bin/env python3
"""
测试手机淘宝购物车页面
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def test_cart():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=auth_file,
            viewport={'width': 375, 'height': 812},  # 手机尺寸
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
        )
        page = await context.new_page()
        
        # 尝试访问购物车
        print("访问手机淘宝购物车...")
        await page.goto("https://cart.m.taobao.com/cart.htm", timeout=30000)
        await asyncio.sleep(3)
        
        print(f"当前 URL: {page.url}")
        print(f"标题: {await page.title()}")
        
        # 检查是否需要登录
        content = await page.content()
        if 'login' in page.url or '登录' in content:
            print("❌ 需要登录")
        else:
            print("✅ 已登录")
            # 查找购物车商品
            items = await page.evaluate('''() => {
                const items = document.querySelectorAll('[class*="item"], [class*="cart"]');
                return Array.from(items).map(el => el.innerText?.substring(0, 50));
            }''')
            print(f"找到 {len(items)} 个商品元素")
            for item in items[:5]:
                print(f"  - {item}")
        
        # 截图
        await page.screenshot(path='cart_mobile.png')
        print("已截图: cart_mobile.png")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_cart())
