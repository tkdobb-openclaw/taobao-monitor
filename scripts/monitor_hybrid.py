#!/usr/bin/env python3
"""
淘宝价格监控 - 混合模式
1. 快速获取默认价格
2. 价格异常时，点击指定 SKU 核实
3. 降速防验证码
"""
import asyncio
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from database import Database
from notifier import FeishuNotifier

class HybridPriceMonitor:
    def __init__(self):
        self.db = Database()
        self.notifier = FeishuNotifier()
        self.config = self._load_config()
        self._load_notifier_config()
        self.results = []
    
    def _load_config(self):
        config_path = Path(__file__).parent.parent / "config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_notifier_config(self):
        if self.config.get('app_id') and self.config.get('app_secret') and self.config.get('chat_id'):
            self.notifier.set_credentials(
                self.config['app_id'],
                self.config['app_secret'],
                self.config['chat_id']
            )
    
    def is_price_anomaly(self, price: float) -> bool:
        """判断价格是否异常"""
        return price < 1000 or price > 8000
    
    async def fetch_default_price(self, page, url: str) -> dict:
        """获取默认价格（不点击 SKU）"""
        result = {'price': None, 'title': None}
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)
            
            result['title'] = await page.title()
            
            # 获取默认价格
            price_text = await page.evaluate('''() => {
                const el = document.querySelector('[class*="priceText--"]') || 
                           document.querySelector('.tb-rmb-num');
                return el ? el.innerText : null;
            }''')
            
            if price_text:
                match = re.search(r'([\d.]+)', price_text.replace(',', ''))
                if match:
                    result['price'] = float(match.group(1))
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def fetch_sku_price(self, page, target_skus: list) -> list:
        """点击指定 SKU 获取价格（降速版）"""
        results = []
        
        try:
            # 移除遮罩
            await page.evaluate('''() => {
                document.querySelectorAll('.J_MIDDLEWARE_FRAME_WIDGET, [class*="overlay"]').forEach(el => el.remove());
            }''')
            
            # 获取所有 SKU
            sku_info = await page.evaluate('''() => {
                const items = document.querySelectorAll('[class*="valueItem--"]');
                return Array.from(items).map((el, i) => ({
                    index: i,
                    text: el.innerText?.trim() || '',
                    disabled: el.classList.contains('isDisabled--')
                })).filter(item => item.text);
            }''')
            
            found_skus = set()
            
            for sku in sku_info:
                if sku['disabled']:
                    continue
                
                text = sku['text']
                
                # 匹配目标 SKU
                matched = None
                for target in target_skus:
                    if target.lower().replace(' ', '') in text.lower().replace(' ', ''):
                        matched = target
                        break
                
                if not matched or matched in found_skus:
                    continue
                
                found_skus.add(matched)
                
                # JS 点击
                await page.evaluate(f'(idx) => document.querySelectorAll(\'[class*="valueItem--"]\')[idx]?.click()', sku['index'])
                await asyncio.sleep(8)  # 降速：等待 8 秒
                
                # 获取价格
                price_text = await page.evaluate('''() => {
                    const el = document.querySelector('[class*="priceText--"]');
                    return el ? el.innerText : null;
                }''')
                
                if price_text:
                    match = re.search(r'([\d.]+)', price_text.replace(',', ''))
                    if match:
                        price = float(match.group(1))
                        results.append({'sku': text, 'price': price, 'target': matched})
        except Exception as e:
            print(f"SKU 点击错误: {e}")
        
        return results
    
    async def check_product(self, item_id: str, rule: dict) -> dict:
        """检查单个商品"""
        url = f"https://item.taobao.com/item.htm?id={item_id}"
        shop = rule.get('shop', 'Unknown')
        model = rule.get('model', 'Unknown')
        target_skus = rule.get('target_skus', [])
        
        print(f"\n检查: {shop} - {model}")
        
        auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=auth_file)
            page = await context.new_page()
            
            # 第一步：获取默认价格
            default = await self.fetch_default_price(page, url)
            
            result = {
                'item_id': item_id,
                'shop': shop,
                'model': model,
                'title': default.get('title', ''),
                'default_price': default.get('price'),
                'sku_prices': [],
                'used_sku': False
            }
            
            # 第二步：判断是否需要点击 SKU
            if default.get('price') and self.is_price_anomaly(default['price']) and target_skus:
                print(f"  默认价格异常: ¥{default['price']:.0f}，开始点击 SKU...")
                result['sku_prices'] = await self.fetch_sku_price(page, target_skus)
                result['used_sku'] = True
                print(f"  获取到 {len(result['sku_prices'])} 个 SKU 价格")
            else:
                print(f"  默认价格: ¥{default['price']:.0f if default.get('price') else 'N/A'}")
            
            await browser.close()
            return result
    
    async def run(self):
        """执行监控"""
        sku_rules = self.config.get('sku_rules', {})
        print(f"开始监控: {len(sku_rules)} 个商品")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)
        
        for item_id, rule in sku_rules.items():
            result = await self.check_product(item_id, rule)
            self.results.append(result)
        
        # 保存结果
        self.save_results()
        
        # 发送报告
        self.send_report()
        
        print("\n" + "="*60)
        print("监控完成!")
    
    def save_results(self):
        """保存结果到数据库"""
        for r in self.results:
            price = None
            if r['sku_prices']:
                price = r['sku_prices'][0]['price']
            elif r['default_price']:
                price = r['default_price']
            
            if price:
                self.db.add_price(r['item_id'], price, available=True)
    
    def send_report(self):
        """发送飞书报告"""
        lines = ["📊 淘宝价格监控报告", f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        
        # 按型号分组
        from collections import defaultdict
        by_model = defaultdict(list)
        for r in self.results:
            by_model[r['model']].append(r)
        
        for model, items in by_model.items():
            lines.append(f"【{model}】")
            for item in items:
                if item['sku_prices']:
                    for sp in item['sku_prices']:
                        lines.append(f"  {item['shop']:8s} ¥{sp['price']:>6.0f} ({sp['sku'][:15]}...)")
                elif item['default_price']:
                    lines.append(f"  {item['shop']:8s} ¥{item['default_price']:>6.0f}")
                else:
                    lines.append(f"  {item['shop']:8s} 获取失败")
            lines.append("")
        
        message = "\n".join(lines)
        self.notifier.send_text(message)
        print("\n报告已发送")

if __name__ == '__main__':
    monitor = HybridPriceMonitor()
    asyncio.run(monitor.run())
