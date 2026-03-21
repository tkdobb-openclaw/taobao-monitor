#!/usr/bin/env python3
"""
淘宝价格监控 - SKU点击版（获取真实价格）
- 直接点击配置的SKU获取价格
- 失败时标记为需人工复核
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

class SkuPriceMonitor:
    def __init__(self):
        self.db = Database()
        self.notifier = FeishuNotifier()
        self.config = self._load_config()
        self._load_notifier_config()
        self.results = []
        self.manual_review = []  # 需要人工复核的
    
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
    
    async def fetch_sku_prices(self, page, url: str, target_skus: list) -> list:
        """点击SKU获取价格，失败返回空列表"""
        results = []
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(5)  # 等待JS渲染
            
            # 检查是否需要登录
            if 'login' in page.url:
                return [{'error': '需要登录', 'need_login': True}]
            
            # 移除遮罩层
            await page.evaluate('''() => {
                document.querySelectorAll('.J_MIDDLEWARE_FRAME_WIDGET, [class*="overlay"]').forEach(el => el.remove());
            }''')
            
            # 获取所有SKU
            sku_info = await page.evaluate('''() => {
                const items = document.querySelectorAll('[class*="valueItem--"]');
                return Array.from(items).map((el, i) => ({
                    index: i,
                    text: el.innerText?.trim() || '',
                    disabled: el.classList.contains('isDisabled--')
                })).filter(item => item.text);
            }''')
            
            if not sku_info:
                return [{'error': '未找到SKU元素', 'debug': 'sku_info empty'}]
            
            print(f"  找到 {len(sku_info)} 个SKU元素")
            for s in sku_info[:3]:
                print(f"    - {s['text']}")
            
            found_skus = set()
            
            for sku in sku_info:
                if sku['disabled']:
                    continue
                
                text = sku['text']
                
                # 匹配目标SKU
                matched = None
                for target in target_skus:
                    if target.lower().replace(' ', '') in text.lower().replace(' ', ''):
                        matched = target
                        break
                
                if not matched or matched in found_skus:
                    continue
                
                found_skus.add(matched)
                
                # JS点击
                await page.evaluate(f'(idx) => document.querySelectorAll(\'[class*="valueItem--"]\')[idx]?.click()', sku['index'])
                await asyncio.sleep(5)  # 等待价格更新
                
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
            
            return results
            
        except Exception as e:
            return [{'error': str(e)}]
    
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
            
            sku_prices = await self.fetch_sku_prices(page, url, target_skus)
            title = await page.title()
            
            await browser.close()
            
            result = {
                'item_id': item_id,
                'shop': shop,
                'model': model,
                'title': title,
                'sku_prices': [],
                'error': None
            }
            
            # 检查结果
            if sku_prices and 'error' in sku_prices[0]:
                result['error'] = sku_prices[0]['error']
                self.manual_review.append({'shop': shop, 'model': model, 'error': sku_prices[0]['error']})
                print(f"  ❌ 失败: {sku_prices[0]['error']}")
            elif not sku_prices:
                result['error'] = '未找到匹配的SKU'
                self.manual_review.append({'shop': shop, 'model': model, 'error': '未找到匹配的SKU'})
                print(f"  ❌ 失败: 未找到匹配的SKU")
            else:
                result['sku_prices'] = sku_prices
                for sp in sku_prices:
                    print(f"  ✅ {sp['sku'][:20]}... ¥{sp['price']:.0f}")
            
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
        print(f"监控完成! 成功: {len([r for r in self.results if r['sku_prices']])}/{len(self.results)}")
        if self.manual_review:
            print(f"需人工复核: {len(self.manual_review)} 个")
    
    def save_results(self):
        """保存结果到数据库"""
        for r in self.results:
            if r['sku_prices']:
                # 取第一个SKU价格保存
                self.db.add_price(r['item_id'], r['sku_prices'][0]['price'], available=True)
    
    def send_report(self):
        """发送飞书报告"""
        lines = ["📊 淘宝价格监控报告", f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        
        # 按型号分组
        from collections import defaultdict
        by_model = defaultdict(list)
        for r in self.results:
            by_model[r['model']].append(r)
        
        # 成功获取的价格
        lines.append("✅ 成功获取:")
        for model, items in by_model.items():
            lines.append(f"\n【{model}】")
            for item in items:
                if item['sku_prices']:
                    for sp in item['sku_prices']:
                        lines.append(f"  {item['shop']:8s} ¥{sp['price']:>6.0f} ({sp['sku'][:15]}...)")
                elif not item['error']:
                    lines.append(f"  {item['shop']:8s} 无数据")
        
        # 需人工复核
        if self.manual_review:
            lines.append("\n" + "="*40)
            lines.append("⚠️ 需人工复核:")
            for item in self.manual_review:
                lines.append(f"  - {item['shop']} {item['model']}: {item['error']}")
        
        message = "\n".join(lines)
        self.notifier.send_text(message)
        print("\n报告已发送")

if __name__ == '__main__':
    monitor = SkuPriceMonitor()
    asyncio.run(monitor.run())
