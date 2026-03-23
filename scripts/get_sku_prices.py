#!/usr/bin/env python3
"""
点击 SKU 获取真实价格 - 塞班户外
"""
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

async def get_sku_prices():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        # 找到所有 SKU 选项
        sku_items = await page.query_selector_all('[class*="valueItem--"]')
        print(f"找到 {len(sku_items)} 个 SKU 选项\n")
        
        prices = []
        for i, item in enumerate(sku_items):
            text = await item.text_content()
            if not text:
                continue
                
            # 跳过非价格相关的（如表带、套装等）
            if any(x in text for x in ['表带', '套装', '传感器']):
                continue
                
            print(f"SKU {i+1}: {text.strip()}")
            
            # 点击
            try:
                await item.click()
                await asyncio.sleep(1.5)
                
                # 获取价格
                price_text = await page.evaluate('''() => {
                    // 尝试多种价格选择器
                    const selectors = [
                        '.tb-rmb-num',
                        '[class*="priceText--"]',
                        '[class*="Price--"]',
                        'span[class*="price"]'
                    ];
                    for (let sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el) return el.innerText;
                    }
                    return null;
                }''')
                
                # 提取数字价格
                if price_text:
                    match = re.search(r'¥?\s*([\d,]+(?:\.\d{2})?)', price_text)
                    if match:
                        price = float(match.group(1).replace(',', ''))
                        prices.append((text.strip(), price))
                        print(f"  → 价格: ¥{price}")
                    else:
                        print(f"  → 价格文本: {price_text}")
                else:
                    print(f"  → 未找到价格")
                    
            except Exception as e:
                print(f"  → 错误: {e}")
        
        print(f"\n{'='*50}")
        print("价格汇总:")
        for name, price in prices:
            print(f"  {name}: ¥{price}")
        
        if prices:
            main_prices = [p for _, p in prices if p > 1000]  # 过滤配件价
            if main_prices:
                print(f"\n主商品价格范围: ¥{min(main_prices):.0f} - ¥{max(main_prices):.0f}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(get_sku_prices())
