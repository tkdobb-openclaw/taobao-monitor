#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝价格抓取 - 使用 agent-browser
"""
import subprocess
import json
import re
from typing import Optional, Dict

class TaobaoAgentBrowserCrawler:
    """使用 agent-browser 抓取淘宝价格"""
    
    def __init__(self, auth_file: str = None):
        self.auth_file = auth_file or "~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json"
    
    def _run_cmd(self, cmd: str, timeout: int = 60) -> tuple:
        """运行 agent-browser 命令"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Timeout", 1
        except Exception as e:
            return "", str(e), 1
    
    def fetch_price(self, url: str) -> Dict:
        """
        抓取商品价格
        
        Returns:
            {
                'title': str,
                'price': float,
                'original_price': float or None,
                'available': bool,
                'platform': str,
                'url': str
            }
        """
        result = {
            'title': None,
            'price': None,
            'original_price': None,
            'available': True,
            'platform': 'taobao',
            'url': url
        }
        
        # 1. 加载登录态并访问商品页
        load_cmd = f'npx agent-browser state load {self.auth_file} 2>/dev/null || true'
        open_cmd = f'npx agent-browser open "{url}"'
        wait_cmd = 'npx agent-browser wait 5000'
        
        # 执行加载和访问
        self._run_cmd(f'{load_cmd} && {open_cmd} && {wait_cmd}', timeout=45)
        
        # 2. 获取标题
        title_cmd = "npx agent-browser eval 'document.title'"
        stdout, _, _ = self._run_cmd(title_cmd, timeout=15)
        try:
            title = stdout.strip().strip('"')
            if title and title != 'null':
                result['title'] = title
        except:
            pass
        
        # 3. 获取价格 - 尝试多种选择器
        price_selectors = [
            'document.querySelector("[class*=price], .tb-rmb-num, .notranslate")?.innerText',
            'document.querySelector(".tb-rmb-num")?.innerText',
            'document.querySelector("[class*=Price]")?.innerText',
            'Array.from(document.querySelectorAll("span")).find(el => el.innerText.includes("¥"))?.innerText',
        ]
        
        for selector in price_selectors:
            price_cmd = f"npx agent-browser eval '{selector}'"
            stdout, _, _ = self._run_cmd(price_cmd, timeout=15)
            
            if stdout and 'null' not in stdout and 'undefined' not in stdout:
                price_text = stdout.strip().strip('"')
                price, original_price = self._parse_price_text(price_text)
                
                if price:
                    result['price'] = price
                    if original_price:
                        result['original_price'] = original_price
                    break
        
        # 4. 检查是否下架
        check_cmd = "npx agent-browser eval 'document.body.innerText.includes(\"下架\") || document.body.innerText.includes(\"售罄\")'"
        stdout, _, _ = self._run_cmd(check_cmd, timeout=15)
        if 'true' in stdout:
            result['available'] = False
        
        return result
    
    def _parse_price_text(self, text: str) -> tuple:
        """
        解析价格文本
        返回: (当前价格, 原价)
        
        示例:
        - "券后￥3360起卖家优惠￥4200起" -> (3360, 4200)
        - "¥4280" -> (4280, None)
        """
        if not text:
            return None, None
        
        # 查找所有价格数字
        prices = re.findall(r'[￥¥](\d+)', text)
        
        if len(prices) >= 2:
            # 有券后价和原价
            return float(prices[0]), float(prices[1])
        elif len(prices) == 1:
            # 只有当前价
            return float(prices[0]), None
        
        return None, None


if __name__ == '__main__':
    # 测试
    crawler = TaobaoAgentBrowserCrawler()
    url = "https://item.taobao.com/item.htm?id=624281587175"
    result = crawler.fetch_price(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
