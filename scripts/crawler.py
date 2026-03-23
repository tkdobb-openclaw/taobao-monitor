#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝价格抓取模块 - 增强反检测版
"""
import asyncio
import re
import json
import random
from typing import Optional, Dict
from playwright.async_api import async_playwright, Page


class TaobaoCrawler:
    """淘宝/天猫价格爬虫 - 增强反爬"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.playwright = None
    
    async def __aenter__(self):
        """异步上下文管理器"""
        self.playwright = await async_playwright().start()
        
        # 随机UA
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        ]
        
        # 启动浏览器 - 使用 stealth 配置
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1440,900',
            ]
        )
        
        # 创建上下文 - 模拟真实浏览器
        self.context = await self.browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={'width': 1440, 'height': 900},
            locale='zh-CN',
            timezone_id='Asia/Shanghai',
            device_scale_factor=2,
            is_mobile=False,
            has_touch=False,
            color_scheme='light',
            reduced_motion='no-preference',
        )
        
        # 设置 cookies 和 localStorage
        await self.context.add_init_script("""
            // 隐藏 webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 伪造 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: "Chrome PDF Plugin", filename: "internal-pdf-viewer", description: "Portable Document Format"},
                    {name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", description: ""},
                    {name: "Native Client", filename: "internal-nacl-plugin", description: ""},
                ]
            });
            
            // 伪造 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en']
            });
            
            // 伪造 chrome
            window.chrome = {
                runtime: {},
                app: {},
                csi: function() {},
                loadTimes: function() {}
            };
            
            // 覆盖 permission 查询
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 清理自动化痕迹
            delete navigator.__proto__.webdriver;
        """)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def fetch_price(self, url: str, timeout: int = 45) -> Optional[Dict]:
        """
        抓取商品价格信息
        
        Returns:
            {
                'title': str,
                'price': float,
                'original_price': float or None,
                'available': bool,
                'platform': 'taobao' | 'tmall' | 'jd' | 'unknown'
            }
        """
        page = await self.context.new_page()
        try:
            # 随机延迟，模拟真人
            await asyncio.sleep(random.uniform(1, 3))
            
            # 设置超时
            page.set_default_timeout(timeout * 1000)
            
            # 如果是淘宝，先访问首页建立 cookies
            if 'taobao.com' in url:
                await self._warmup_taobao(page)
            
            # 访问商品页面
            try:
                response = await page.goto(url, wait_until='commit', timeout=timeout*1000)
                await asyncio.sleep(random.uniform(3, 5))
            except Exception as e:
                print(f"页面加载部分失败，继续尝试: {e}")
            
            # 模拟滚动
            await self._simulate_scroll(page)
            
            # 判断平台
            current_url = page.url
            if 'tmall.com' in current_url:
                platform = 'tmall'
            elif 'taobao.com' in current_url:
                platform = 'taobao'
            elif 'jd.com' in current_url:
                platform = 'jd'
            else:
                platform = 'unknown'
            
            result = await self._extract_price_info(page, platform)
            result['platform'] = platform
            result['url'] = current_url
            
            return result
            
        except Exception as e:
            print(f"抓取失败: {e}")
            return {
                'title': None,
                'price': None,
                'original_price': None,
                'available': False,
                'platform': 'unknown',
                'url': url,
                'error': str(e)
            }
        finally:
            await page.close()
    
    async def _warmup_taobao(self, page: Page):
        """预热淘宝 - 先访问首页建立 cookies"""
        try:
            await page.goto('https://www.taobao.com', wait_until='commit', timeout=10000)
            await asyncio.sleep(random.uniform(1, 2))
        except:
            pass
    
    async def _simulate_scroll(self, page: Page):
        """模拟滚动行为"""
        try:
            for _ in range(random.randint(2, 4)):
                await page.mouse.wheel(0, random.randint(200, 500))
                await asyncio.sleep(random.uniform(0.5, 1.5))
        except:
            pass
    
    async def _extract_price_info(self, page: Page, platform: str) -> Dict:
        """提取价格信息"""
        result = {
            'title': None,
            'price': None,
            'original_price': None,
            'available': True,
        }
        
        try:
            # 提取标题
            title_selectors = [
                'h1[data-spm="1000983"]',
                'h1[data-spm="1007227"]',
                '.tb-detail-hd h1',
                '[class*="ItemTitle"]',
                '[class*="title"]',
                'h1',
            ]
            for selector in title_selectors:
                try:
                    title_elem = await page.query_selector(selector)
                    if title_elem:
                        title = await title_elem.text_content()
                        if title and len(title.strip()) > 5:
                            result['title'] = title.strip()
                            break
                except:
                    continue
            
            # 提取价格 - 淘宝/天猫
            if platform in ('taobao', 'tmall'):
                price_selectors = [
                    '.tb-rmb-num',
                    '.notranslate',
                    '[class*="price"]',
                    '[class*="Price"]',
                    '[class*="priceInt"]',
                    '.tm-price',
                    '[class*="itemPrice"]',
                ]
                
                for selector in price_selectors:
                    try:
                        price_elem = await page.query_selector(selector)
                        if price_elem:
                            price_text = await price_elem.text_content()
                            price = self._parse_price(price_text)
                            if price and price > 0:
                                result['price'] = price
                                break
                    except:
                        continue
                
                # 如果从页面元素找不到，从源码中找
                if not result['price']:
                    content = await page.content()
                    
            # 京东价格提取
            elif platform == 'jd':
                price_selectors = [
                    '.price .p-price .price',
                    '.p-price .price',
                    '[class*="price"]',
                ]
                for selector in price_selectors:
                    try:
                        price_elem = await page.query_selector(selector)
                        if price_elem:
                            price_text = await price_elem.text_content()
                            price = self._parse_price(price_text)
                            if price:
                                result['price'] = price
                                break
                    except:
                        continue
            
            # 检查商品是否下架
            unavailable_keywords = ['下架', '售完', '缺货', 'sold out', 'off-sale']
            content = await page.content()
            for kw in unavailable_keywords:
                if kw in content:
                    result['available'] = False
                    break
            
        except Exception as e:
            print(f"提取价格信息出错: {e}")
        
        return result
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """解析价格文本"""
        if not price_text:
            return None
        # 提取数字
        match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if match:
            try:
                return float(match.group())
            except:
                return None
        return None


async def test_crawler():
    """测试爬虫"""
    test_urls = [
        # 这里放测试链接
    ]
    
    async with TaobaoCrawler() as crawler:
        for url in test_urls:
            print(f"\n测试: {url}")
            result = await crawler.fetch_price(url)
            print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == '__main__':
    print("淘宝价格爬虫模块 - 增强版")
    # asyncio.run(test_crawler())
