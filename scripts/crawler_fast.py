#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝价格抓取 - 快速版（使用登录态 cookies）
"""
import requests
import re
import json
import time
from pathlib import Path
from typing import Optional, Dict, List

class TaobaoFastCrawler:
    """使用登录态 cookies 快速抓取淘宝价格"""
    
    def __init__(self, auth_file: str = None):
        self.auth_file = auth_file or "~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json"
        self.session = requests.Session()
        self._load_cookies()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.taobao.com/',
        })
    
    def _load_cookies(self):
        """从登录态文件加载 cookies"""
        try:
            with open(Path(self.auth_file).expanduser(), 'r') as f:
                data = json.load(f)
                cookies = data.get('cookies', [])
                for cookie in cookies:
                    self.session.cookies.set(
                        cookie['name'],
                        cookie['value'],
                        domain=cookie.get('domain', '.taobao.com'),
                        path=cookie.get('path', '/')
                    )
        except Exception as e:
            print(f"加载 cookies 失败: {e}")
    
    def extract_item_id(self, url: str) -> Optional[str]:
        """从 URL 提取商品 ID"""
        match = re.search(r'id=(\d+)', url)
        if match:
            return match.group(1)
        return None
    
    def fetch_price(self, url: str) -> Dict:
        """
        抓取商品价格
        """
        result = {
            'title': None,
            'price': None,
            'original_price': None,
            'available': True,
            'platform': 'taobao',
            'url': url,
            'error': None
        }
        
        item_id = self.extract_item_id(url)
        if not item_id:
            result['error'] = '无法提取商品ID'
            return result
        
        try:
            # 请求商品详情页
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            html = resp.text
            
            # 检查是否被拦截
            if 'login.taobao.com' in resp.url or 'login.m.taobao.com' in resp.url:
                result['error'] = '需要重新登录'
                result['available'] = False
                return result
            
            # 检查是否下架
            if '此宝贝已下架' in html or '商品已下架' in html:
                result['available'] = False
                return result
            
            # 提取标题
            title_match = re.search(r'<title>(.+?)</title>', html, re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()
                title = title.replace('-淘宝网', '').replace('-淘宝', '').strip()
                result['title'] = title
            
            # 提取价格 - 淘宝价格通常在 g_config 或页面脚本中
            # 方法1: g_config
            config_match = re.search(r'g_config\s*=\s*({.+?});', html, re.DOTALL)
            if config_match:
                try:
                    config = json.loads(config_match.group(1))
                    if 'sku' in config and 'val' in config['sku']:
                        price = config['sku']['val'].get('price')
                        if price:
                            result['price'] = float(price)
                except:
                    pass
            
            # 方法2: 查找 Hub.data
            if not result['price']:
                hub_match = re.search(r'Hub\.data\s*=\s*({.+?});', html, re.DOTALL)
                if hub_match:
                    try:
                        hub = json.loads(hub_match.group(1))
                        # Hub.data 结构复杂，尝试多种路径
                        if 'config' in hub and 'sku' in hub['config']:
                            sku = hub['config']['sku']
                            if 'price' in sku:
                                result['price'] = float(sku['price'])
                    except:
                        pass
            
            # 方法3: 页面中直接搜索价格
            if not result['price']:
                # 淘宝价格通常在特定的 script 标签中
                scripts = re.findall(r'<script[^>]*>(.+?)</script>', html, re.DOTALL)
                for script in scripts:
                    # 查找 defaultItemPrice 或类似字段
                    price_match = re.search(r'"defaultItemPrice":"([\d.]+)"', script)
                    if price_match:
                        result['price'] = float(price_match.group(1))
                        break
                    # 查找 price 字段
                    price_match = re.search(r'"price":"([\d.]+)"', script)
                    if price_match and float(price_match.group(1)) > 100:
                        result['price'] = float(price_match.group(1))
                        break
            
            # 方法4: 直接搜索 ¥ 价格
            if not result['price']:
                prices = re.findall(r'[¥￥](\d{3,5})', html)
                if prices:
                    # 取众数或中间值
                    price_list = [int(p) for p in prices]
                    result['price'] = sorted(price_list)[len(price_list)//2]
        
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def fetch_batch(self, urls: List[str], delay: float = 0.5) -> List[Dict]:
        """
        批量抓取价格
        
        Args:
            urls: 商品 URL 列表
            delay: 请求间隔（秒）
        
        Returns:
            结果列表
        """
        results = []
        for i, url in enumerate(urls):
            result = self.fetch_price(url)
            results.append(result)
            if i < len(urls) - 1:
                time.sleep(delay)
        return results


def test_crawler():
    """测试爬虫"""
    crawler = TaobaoFastCrawler()
    
    test_urls = [
        "https://item.taobao.com/item.htm?id=624281587175",  # Peregrine
        "https://item.taobao.com/item.htm?id=676780234187",  # Perdix
        "https://item.taobao.com/item.htm?id=584863170468",  # Teric
    ]
    
    print("开始测试快速爬虫...")
    start = time.time()
    results = crawler.fetch_batch(test_urls, delay=1)
    elapsed = time.time() - start
    
    print(f"\n总耗时: {elapsed:.2f}s (平均 {elapsed/len(test_urls):.2f}s/商品)")
    print("\n结果:")
    for i, result in enumerate(results):
        print(f"\n[{i+1}] {result['url']}")
        print(f"    标题: {result['title'][:30] if result['title'] else 'N/A'}...")
        print(f"    价格: ¥{result['price']}")
        if result['error']:
            print(f"    错误: {result['error']}")


if __name__ == '__main__':
    test_crawler()
