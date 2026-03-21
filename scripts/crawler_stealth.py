#!/usr/bin/env python3
"""
淘宝价格抓取 - 反检测版
"""
import asyncio
import json
import random
from pathlib import Path
from playwright.async_api import async_playwright

async def fetch_price(url: str, auth_file: str) -> dict:
    """抓取单个商品价格"""
    result = {
        'title': None,
        'price': None,
        'available': True,
        'error': None
    }
    
    async with async_playwright() as p:
        # 启动参数，隐藏自动化特征
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ]
        )
        
        # 加载登录态
        context = await browser.new_context(
            storage_state=auth_file,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        
        # 注入脚本隐藏 webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
        """)
        
        page = await context.new_page()
        
        try:
            # 随机延迟，模拟人类
            await asyncio.sleep(random.uniform(1, 3))
            
            # 访问页面
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # 检查是否被拦截
            if 'login' in page.url or 'verify' in page.url:
                result['error'] = '需要验证'
                result['available'] = False
                return result
            
            # 获取标题
            result['title'] = await page.title()
            
            # 滚动页面模拟浏览
            await page.evaluate('window.scrollTo(0, 300)')
            await asyncio.sleep(0.5)
            
            # 提取价格 - 多种选择器
            price_js = await page.evaluate('''() => {
                // 尝试找到价格元素
                const selectors = [
                    '.tb-rmb-num',
                    '[class*="priceText--"]',
                    '[class*="Price--"]',
                    'span[data-spm="price"]',
                ];
                for (let sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.includes('¥')) {
                        return el.innerText.trim();
                    }
                }
                // 备选：搜索包含价格的文本
                const allSpans = document.querySelectorAll('span');
                for (let span of allSpans) {
                    const text = span.innerText;
                    if (text.match(/¥[\d,]+/) && text.length < 20) {
                        return text;
                    }
                }
                return null;
            }''')
            
            if price_js:
                result['price'] = price_js
            
        except Exception as e:
            result['error'] = str(e)
        
        await browser.close()
        return result


async def test():
    auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
    
    test_urls = [
        "https://item.taobao.com/item.htm?id=624281587175",
        "https://item.taobao.com/item.htm?id=676780234187",
    ]
    
    print("开始测试反检测抓取...\n")
    
    for i, url in enumerate(test_urls):
        print(f"[{i+1}/{len(test_urls)}] {url}")
        result = await fetch_price(url, auth_file)
        print(f"    标题: {result.get('title', 'N/A')[:40] if result.get('title') else 'N/A'}...")
        print(f"    价格: {result.get('price', 'N/A')}")
        if result.get('error'):
            print(f"    错误: {result['error']}")
        print()
        
        # 间隔防止触发风控
        if i < len(test_urls) - 1:
            await asyncio.sleep(random.uniform(3, 5))


if __name__ == '__main__':
    asyncio.run(test())
