#!/usr/bin/env python3
"""
单个商品详细调试
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def debug_single():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=676780234187"
    target_skus = ["perdix2 ti 银色"]
    
    print(f"目标SKU: {target_skus}")
    print(f"URL: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        print("\n访问页面...")
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            print(f"页面加载完成: {page.url}")
        except Exception as e:
            print(f"页面加载失败: {e}")
            await browser.close()
            return
        
        await asyncio.sleep(5)
        
        print(f"标题: {await page.title()}")
        
        # 检查是否需要登录
        if 'login' in page.url:
            print("❌ 需要登录")
            await browser.close()
            return
        
        # 移除遮罩
        await page.evaluate('''() => {
            document.querySelectorAll('.J_MIDDLEWARE_FRAME_WIDGET, [class*="overlay"]').forEach(el => el.remove());
        }''')
        
        # 获取SKU
        print("\n获取SKU元素...")
        sku_info = await page.evaluate('''() => {
            const items = document.querySelectorAll('[class*="valueItem--"]');
            return Array.from(items).map((el, i) => ({
                index: i,
                text: el.innerText?.trim() || '',
                disabled: el.classList.contains('isDisabled--')
            })).filter(item => item.text);
        }''')
        
        print(f"找到 {len(sku_info)} 个SKU:")
        for s in sku_info:
            print(f"  [{s['index']}] {s['text']} (disabled: {s['disabled']})")
        
        if not sku_info:
            print("❌ 未找到SKU元素")
            await browser.close()
            return
        
        # 匹配SKU
        print("\n开始匹配...")
        found_skus = set()
        
        for sku in sku_info:
            if sku['disabled']:
                print(f"  跳过禁用SKU: {sku['text']}")
                continue
            
            text = sku['text']
            print(f"  检查: '{text}'")
            
            matched = None
            for target in target_skus:
                target_clean = target.lower().replace(' ', '')
                text_clean = text.lower().replace(' ', '')
                
                is_match = target_clean in text_clean
                print(f"    匹配 '{target}' -> {is_match}")
                
                if is_match:
                    matched = target
                    break
            
            if matched:
                if matched in found_skus:
                    print(f"    已存在，跳过")
                else:
                    found_skus.add(matched)
                    print(f"    ✓ 匹配成功: {matched}")
                    
                    # 点击
                    print(f"    点击 index {sku['index']}...")
                    await page.evaluate(f'(idx) => document.querySelectorAll(\'[class*="valueItem--"]\')[idx]?.click()', sku['index'])
                    await asyncio.sleep(5)
                    
                    # 获取价格
                    price_text = await page.evaluate('''() => {
                        const el = document.querySelector('[class*="priceText--"]');
                        return el ? el.innerText : null;
                    }''')
                    print(f"    价格: {price_text}")
        
        await browser.close()
        print("\n完成")

if __name__ == '__main__':
    asyncio.run(debug_single())
