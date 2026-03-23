#!/usr/bin/env python3
"""
点击 SKU 获取真实价格 - 测试版
针对塞班户外 Peregrine (id=624281587175)
"""
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

async def click_all_skus():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        print(f"访问: {url}")
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        print(f"页面标题: {await page.title()}")
        print()
        
        # 获取默认价格
        default_price = await page.evaluate('''() => {
            const el = document.querySelector('[class*="priceText--"]') || 
                       document.querySelector('.tb-rmb-num');
            return el ? el.innerText.trim() : null;
        }''')
        print(f"默认显示价格: {default_price}")
        print()
        
        # 找到所有 SKU 选项（排除 disabled 的）
        sku_items = await page.query_selector_all('[class*="valueItem--"]')
        print(f"找到 {len(sku_items)} 个 SKU 选项\n")
        print("="*60)
        
        sku_prices = []
        
        for i, item in enumerate(sku_items):
            text = await item.text_content()
            if not text:
                continue
            
            text = text.strip()
            
            # 检查是否 disabled
            is_disabled = await item.evaluate('el => el.classList.contains("isDisabled--") || el.disabled')
            if is_disabled:
                print(f"[{i+1}] {text}")
                print(f"     状态: 缺货/不可用\n")
                continue
            
            print(f"[{i+1}] {text}")
            
            # 点击
            try:
                await item.click()
                await asyncio.sleep(1.5)  # 等待价格更新
                
                # 获取更新后的价格
                price_text = await page.evaluate('''() => {
                    const selectors = [
                        '[class*="priceText--"]',
                        '.tb-rmb-num',
                        '[class*="Price--"]',
                        '.price'
                    ];
                    for (let sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText.includes('¥')) {
                            return el.innerText.trim();
                        }
                    }
                    return null;
                }''')
                
                # 提取数字
                if price_text:
                    match = re.search(r'¥?\s*([\d,]+(?:\.\d{2})?)', price_text.replace(',', ''))
                    if match:
                        price = float(match.group(1))
                        sku_prices.append((text, price))
                        print(f"     价格: ¥{price:.0f}")
                    else:
                        print(f"     价格文本: {price_text}")
                else:
                    print(f"     未获取到价格")
                    
            except Exception as e:
                print(f"     点击失败: {e}")
            
            print()
        
        print("="*60)
        print(f"\n抓取完成，共 {len(sku_prices)} 个有效价格:")
        
        # 分类显示
        main_prices = []  # 主商品价格（>1000）
        accessory_prices = []  # 配件价格（<1000）
        
        for name, price in sku_prices:
            if price > 1000:
                main_prices.append((name, price))
            else:
                accessory_prices.append((name, price))
        
        if main_prices:
            print(f"\n【主商品价格】({len(main_prices)}个):")
            for name, price in sorted(main_prices, key=lambda x: x[1]):
                print(f"  ¥{price:>6.0f} - {name}")
        
        if accessory_prices:
            print(f"\n【配件/其他价格】({len(accessory_prices)}个):")
            for name, price in sorted(accessory_prices, key=lambda x: x[1]):
                print(f"  ¥{price:>6.0f} - {name}")
        
        # 截图保存
        await page.screenshot(path='sku_prices.png')
        print(f"\n截图已保存: sku_prices.png")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(click_all_skus())
