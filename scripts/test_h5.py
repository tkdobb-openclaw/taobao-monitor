#!/usr/bin/env python3
"""
测试手机淘宝 H5 商品页
"""
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

async def test_h5():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    
    # 商品链接转 H5
    item_id = "624281587175"  # 塞班户外 Peregrine
    h5_url = f"https://detail.m.tmall.com/item.htm?id={item_id}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            storage_state=auth_file,
            viewport={'width': 375, 'height': 812},
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15'
        )
        page = await context.new_page()
        
        print(f"访问 H5 商品页: {h5_url}")
        await page.goto(h5_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)
        
        print(f"当前 URL: {page.url}")
        print(f"标题: {await page.title()}")
        
        # 获取价格
        price = await page.evaluate('''() => {
            // H5 页面价格选择器
            const selectors = [
                '.price .num',
                '[class*="price"]',
                '.tb-price',
            ];
            for (let sel of selectors) {
                const el = document.querySelector(sel);
                if (el) return el.innerText;
            }
            return null;
        }''')
        
        print(f"价格: {price}")
        
        # 检查 SKU 选择器
        sku_btn = await page.query_selector('[class*="sku"], [class*="spec"], button')
        if sku_btn:
            text = await sku_btn.text_content()
            print(f"找到 SKU 按钮: {text[:30] if text else 'N/A'}")
        
        # 截图
        await page.screenshot(path='h5_item.png')
        print("已截图: h5_item.png")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_h5())
