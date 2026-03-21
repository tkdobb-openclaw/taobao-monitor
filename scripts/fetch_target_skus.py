#!/usr/bin/env python3
"""
淘宝价格抓取 - 指定 SKU 版本
针对塞班户外 Peregrine，抓取：
- 灰色 DARK New
- 黑色经典版  
- 黑色 TX 版【可接传感器】
"""
import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

# 目标 SKU 关键词（优先级排序）
TARGET_SKUS = [
    "黑色 TX 版",
    "黑色经典版", 
    "灰色 DARK"
]

async def fetch_target_skus():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    print(f"🎯 目标 SKU: {', '.join(TARGET_SKUS)}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        print(f"访问: {url}")
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)
        
        print(f"页面标题: {await page.title()}\n")
        
        # 获取所有 SKU 选项
        sku_items = await page.query_selector_all('[class*="valueItem--"]')
        print(f"找到 {len(sku_items)} 个 SKU 选项\n")
        
        results = []
        found_skus = set()
        
        for item in sku_items:
            text = await item.text_content()
            if not text:
                continue
            
            text = text.strip()
            
            # 检查是否匹配目标 SKU
            matched_sku = None
            for target in TARGET_SKUS:
                # 模糊匹配（关键词包含关系）
                if target.replace(" ", "").lower() in text.replace(" ", "").lower():
                    matched_sku = target
                    break
            
            if not matched_sku:
                continue
            
            # 跳过已找到的（防止重复）
            if matched_sku in found_skus:
                continue
            found_skus.add(matched_sku)
            
            print(f"点击: {text}")
            
            try:
                # 滚动到可见
                await item.scroll_into_view_if_needed()
                await item.click()
                await asyncio.sleep(1.5)  # 等待价格更新
                
                # 获取价格
                price_text = await page.evaluate('''() => {
                    const selectors = [
                        '[class*="priceText--"]',
                        '.tb-rmb-num',
                        '[class*="Price--"]'
                    ];
                    for (let sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText.includes('¥')) {
                            return el.innerText.trim();
                        }
                    }
                    return null;
                }''')
                
                # 提取数字价格
                if price_text:
                    match = re.search(r'¥?\s*([\d,]+(?:\.\d{2})?)', price_text.replace(',', ''))
                    if match:
                        price = float(match.group(1))
                        results.append({
                            'sku': text,
                            'price': price,
                            'matched': matched_sku
                        })
                        print(f"  ✅ 价格: ¥{price:.0f}\n")
                    else:
                        print(f"  ⚠️  无法解析: {price_text}\n")
                else:
                    print(f"  ❌ 未找到价格元素\n")
                    
            except Exception as e:
                print(f"  ❌ 点击失败: {e}\n")
        
        print("="*60)
        print(f"\n📊 抓取结果 ({len(results)}/{len(TARGET_SKUS)}):")
        
        for r in sorted(results, key=lambda x: x['price']):
            print(f"  ¥{r['price']:>6.0f} - {r['sku']}")
        
        # 检查缺失的 SKU
        missing = set(TARGET_SKUS) - {r['matched'] for r in results}
        if missing:
            print(f"\n⚠️ 未找到的 SKU:")
            for m in missing:
                print(f"  - {m}")
        
        # 截图
        await page.screenshot(path='target_skus.png')
        print(f"\n📸 截图已保存: target_skus.png")
        
        await browser.close()
        return results

if __name__ == '__main__':
    results = asyncio.run(fetch_target_skus())
    
    print("\n" + "="*60)
    print("返回数据:")
    for r in results:
        print(f"  {r}")
