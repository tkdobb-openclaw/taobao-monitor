#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝价格抓取 - Playwright 常驻浏览器版
保持浏览器实例，避免重复启动
"""
import asyncio
import re
import json
from pathlib import Path
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Page, Browser

class TaobaoPlaywrightCrawler:
    """使用常驻浏览器抓取淘宝价格"""
    
    def __init__(self, auth_file: str = None):
        self.auth_file = auth_file or "~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
    
    async def init(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        # 启动浏览器
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 创建页面
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        )
        
        # 加载 cookies
        try:
            with open(Path(self.auth_file).expanduser(), 'r') as f:
                data = json.load(f)
                cookies = data.get('cookies', [])
                if cookies:
                    await context.add_cookies(cookies)
        except Exception as e:
            print(f"加载 cookies 失败: {e}")
        
        self.page = await context.new_page()
        
        # 屏蔽图片和 CSS 加速
        await self.page.route("**/*.{png,jpg,jpeg,gif,css,woff,woff2}", lambda route: route.abort())
    
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def extract_item_id(self, url: str) -> Optional[str]:
        match = re.search(r'id=(\d+)', url)
        if match:
            return match.group(1)
        return None
    
    async def fetch_price(self, url: str) -> Dict:
        """抓取单个商品价格"""
        result = {
            'title': None,
            'price': None,
            'original_price': None,
            'available': True,
            'platform': 'taobao',
            'url': url,
            'error': None
        }
        
        try:
            # 访问页面
            await self.page.goto(url, wait_until='domcontentloaded', timeout=15000)
            
            # 等待页面加载
            await asyncio.sleep(1)
            
            # 检查是否跳转登录
            if 'login' in self.page.url:
                result['error'] = '需要重新登录'
                result['available'] = False
                return result
            
            # 获取标题
            try:
                result['title'] = await self.page.title()
            except:
                pass
            
            # 尝试多种方式获取价格
            price_selectors = [
                '[class*="price"]',
                '.tb-rmb-num',
                '.notranslate',
                '[class*="Price"]',
            ]
            
            for selector in price_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text:
                            price = self._parse_price(text)
                            if price:
                                result['price'] = price
                                break
                except:
                    continue
            
            # 如果还没找到，用 JS 提取
            if not result['price']:
                try:
                    price_text = await self.page.evaluate('''() => {
                        const el = document.querySelector('[class*="price"], .tb-rmb-num');
                        return el ? el.innerText : null;
                    }''')
                    if price_text:
                        result['price'] = self._parse_price(price_text)
                except:
                    pass
            
            # 检查是否下架
            page_text = await self.page.content()
            if '此宝贝已下架' in page_text or '商品已下架' in page_text:
                result['available'] = False
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _parse_price(self, text: str) -> Optional[float]:
        """解析价格文本"""
        if not text:
            return None
        # 查找价格数字
        prices = re.findall(r'[¥￥]?(\d{3,5})', text.replace(',', ''))
        if prices:
            return float(prices[0])
        return None
    
    async def fetch_batch(self, urls: List[str], delay: float = 2) -> List[Dict]:
        """批量抓取"""
        results = []
        for i, url in enumerate(urls):
            result = await self.fetch_price(url)
            results.append(result)
            print(f"[{i+1}/{len(urls)}] {result.get('price') or 'N/A'} - {result.get('title', 'N/A')[:30] if result.get('title') else 'N/A'}...")
            if i < len(urls) - 1:
                await asyncio.sleep(delay)
        return results


async def test():
    """测试"""
    crawler = TaobaoPlaywrightCrawler()
    
    test_urls = [
        "https://item.taobao.com/item.htm?id=624281587175",
        "https://item.taobao.com/item.htm?id=676780234187",
        "https://item.taobao.com/item.htm?id=584863170468",
    ]
    
    print("初始化浏览器...")
    await crawler.init()
    
    print(f"\n开始抓取 {len(test_urls)} 个商品...")
    start = asyncio.get_event_loop().time()
    results = await crawler.fetch_batch(test_urls, delay=1)
    elapsed = asyncio.get_event_loop().time() - start
    
    print(f"\n总耗时: {elapsed:.2f}s (平均 {elapsed/len(test_urls):.2f}s/商品)")
    
    await crawler.close()


if __name__ == '__main__':
    asyncio.run(test())
