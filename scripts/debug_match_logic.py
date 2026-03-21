#!/usr/bin/env python3
"""
调试 - 完整模拟匹配逻辑
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

# 配置的目标SKU（从config.json）
TARGET_SKUS = ["perdix2 ti 银色"]

async def debug_match():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=676780234187"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)
        
        # 获取SKU（模拟代码中的逻辑）
        sku_info = await page.evaluate('''() => {
            const items = document.querySelectorAll('[class*="valueItem--"]');
            return Array.from(items).map((el, i) => ({
                index: i,
                text: el.innerText?.trim() || '',
                disabled: el.classList.contains('isDisabled--')
            })).filter(item => item.text);
        }''')
        
        print(f"找到 {len(sku_info)} 个SKU\n")
        
        # 模拟匹配逻辑
        found_skus = set()
        
        for sku in sku_info:
            if sku['disabled']:
                print(f"[{sku['index']}] {sku['text']} - 已禁用")
                continue
            
            text = sku['text']
            print(f"[{sku['index']}] 检查: '{text}'")
            
            matched = None
            for target in TARGET_SKUS:
                target_clean = target.lower().replace(' ', '')
                text_clean = text.lower().replace(' ', '')
                
                print(f"    比较: '{target_clean}' in '{text_clean}' = {target_clean in text_clean}")
                
                if target_clean in text_clean:
                    matched = target
                    break
            
            if matched:
                if matched in found_skus:
                    print(f"    已找到过，跳过")
                else:
                    found_skus.add(matched)
                    print(f"    ✓ 匹配成功: {matched}")
            else:
                print(f"    ✗ 未匹配")
        
        print(f"\n最终找到: {len(found_skus)} 个")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug_match())
