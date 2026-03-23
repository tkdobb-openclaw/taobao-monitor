#!/usr/bin/env python3
"""
探索淘宝 SKU 价格加载机制
"""
import asyncio
import json
import re
from pathlib import Path
from playwright.async_api import async_playwright

async def explore_sku():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    
    # 测试两个不同店铺
    urls = [
        ("塞班户外", "https://item.taobao.com/item.htm?id=624281587175"),  # Peregrine
        ("大洋潜水", "https://item.taobao.com/item.htm?id=623907417709"),  # Peregrine
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        for shop_name, url in urls:
            print(f"\n{'='*60}")
            print(f"店铺: {shop_name}")
            print(f"URL: {url}")
            print('='*60)
            
            # 拦截所有网络请求
            api_responses = []
            
            async def handle_route(route, request):
                # 关注包含 price/detail 的 API
                if any(x in request.url for x in ['detail', 'price', 'sku', 'item']):
                    try:
                        response = await route.fetch()
                        text = await response.text()
                        if len(text) < 50000:  # 只记录小响应
                            api_responses.append({
                                'url': request.url[:100],
                                'size': len(text),
                                'preview': text[:500] if 'price' in text.lower() else None
                            })
                    except:
                        pass
                await route.continue_()
            
            await page.route("**/*", handle_route)
            
            # 访问页面
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            # 获取页面中的 SKU 数据
            sku_data = await page.evaluate('''() => {
                // 淘宝通常在 Hub.config 或 g_config 中有 SKU 数据
                const data = {
                    hub: window.Hub?.config || null,
                    g_config: window.g_config || null,
                    skuMap: window.skuMap || null,
                    _DATA: window._DATA || null
                };
                return data;
            }''')
            
            print("\n页面 JS 数据:")
            if sku_data.get('hub'):
                print("  ✅ 找到 Hub.config")
                # 尝试提取价格信息
                hub = sku_data['hub']
                if 'sku' in hub:
                    print(f"  SKU 数据: {json.dumps(hub['sku'], ensure_ascii=False)[:300]}...")
            
            if sku_data.get('g_config'):
                print("  ✅ 找到 g_config")
                if 'sku' in sku_data['g_config']:
                    sku = sku_data['g_config']['sku']
                    print(f"  SKU: {json.dumps(sku, ensure_ascii=False)[:300]}...")
            
            # 查找 SKU 列表
            sku_list = await page.evaluate('''() => {
                // 查找 SKU 选择器
                const skuEls = document.querySelectorAll('[data-spm*="sku"], .tb-sku, .tm-sku, [class*="sku"]');
                return Array.from(skuEls).map(el => ({
                    text: el.innerText?.trim(),
                    className: el.className,
                    clickable: el.onclick !== null || el.tagName === 'A' || el.tagName === 'BUTTON'
                })).slice(0, 5);
            }''')
            
            print(f"\n找到 {len(sku_list)} 个 SKU 元素:")
            for sku in sku_list[:5]:
                print(f"  - {sku['text'][:30] if sku['text'] else 'N/A'}... (clickable: {sku['clickable']})")
            
            # 打印 API 响应
            print(f"\nAPI 请求 ({len(api_responses)} 个):")
            for api in api_responses[:5]:
                print(f"  - {api['url'][:60]}... (size: {api['size']})")
                if api['preview']:
                    print(f"    Preview: {api['preview'][:200]}...")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(explore_sku())
