#!/usr/bin/env python3
"""
调试价格提取 - 等待 JS 加载
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

async def debug():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    url = "https://item.taobao.com/item.htm?id=624281587175"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(storage_state=auth_file)
        page = await context.new_page()
        
        # 拦截网络请求，查看 API 响应
        prices_from_api = []
        
        async def handle_route(route, request):
            if 'detail' in request.url or 'price' in request.url:
                try:
                    response = await route.fetch()
                    text = await response.text()
                    if 'price' in text.lower():
                        prices_from_api.append({
                            'url': request.url[:80],
                            'has_price': True
                        })
                except:
                    pass
            await route.continue_()
        
        await page.route("**/*", handle_route)
        
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await asyncio.sleep(5)  # 等待 JS 执行
        
        print(f"当前 URL: {page.url}")
        print(f"标题: {await page.title()}")
        
        # 截图看看
        await page.screenshot(path='debug2.png', full_page=True)
        print("已保存截图: debug2.png")
        
        # 尝试用 JS 获取价格
        price = await page.evaluate('''() => {
            // 淘宝价格通常在 g_config 或 TB 对象中
            if (window.g_config && window.g_config.sku) {
                return window.g_config.sku.val;
            }
            if (window.Hub && window.Hub.config) {
                return window.Hub.config.sku;
            }
            // 查找 visible 的价格元素
            const els = document.querySelectorAll('span, div');
            for (let el of els) {
                const text = el.textContent;
                if (text && text.match(/¥\s*\d{3,}/) && el.offsetHeight > 0) {
                    return text.trim();
                }
            }
            return null;
        }''')
        
        print(f"\nJS 获取的价格: {price}")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug())
