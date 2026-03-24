#!/usr/bin/env python3
"""
淘宝价格监控 - SKU点击版（获取真实价格）
- 单浏览器连续检查所有商品
- 前台展示便于调试
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
        self.manual_review = []
        self.browser = None
        self.context = None
        self.page = None
    
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
    
    async def init_browser(self):
        """初始化浏览器（前台展示）"""
        auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
        
        print("🌐 启动浏览器...")
        p = await async_playwright().start()
        self.playwright = p
        
        # 前台展示模式
        self.browser = await p.chromium.launch(
            headless=False,  # 前台展示
            args=['--window-size=1400,900']
        )
        
        self.context = await self.browser.new_context(
            storage_state=auth_file,
            viewport={'width': 1400, 'height': 900}
        )
        
        self.page = await self.context.new_page()
        print("✅ 浏览器已启动\n")
    
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("\n🌐 浏览器已关闭")
    
    async def check_product(self, item_id: str, rule: dict) -> dict:
        """检查单个商品（使用同一浏览器会话）"""
        url = f"https://item.taobao.com/item.htm?id={item_id}"
        shop = rule.get('shop', 'Unknown')
        model = rule.get('model', 'Unknown')
        target_skus = rule.get('target_skus', [])
        
        print(f"\n🔍 检查: {shop} - {model}")
        print(f"   URL: {url}")
        
        result = {
            'item_id': item_id,
            'shop': shop,
            'model': model,
            'title': '',
            'sku_prices': [],
            'error': None
        }
        
        try:
            # 访问页面
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # 检查登录状态
            if 'login' in self.page.url:
                result['error'] = '需要登录'
                self.manual_review.append({'shop': shop, 'model': model, 'error': '需要登录'})
                print(f"   ❌ 需要登录")
                return result
            
            result['title'] = await self.page.title()
            
            # 移除遮罩层
            await self.page.evaluate('''() => {
                document.querySelectorAll('.J_MIDDLEWARE_FRAME_WIDGET, [class*="overlay"]').forEach(el => el.remove());
            }''')
            
            # 获取所有SKU
            sku_info = await self.page.evaluate('''() => {
                const items = document.querySelectorAll('[class*="valueItem--"]');
                return Array.from(items).map((el, i) => ({
                    index: i,
                    text: el.innerText?.trim() || '',
                    disabled: el.classList.contains('isDisabled--')
                })).filter(item => item.text);
            }''')
            
            if not sku_info:
                result['error'] = '未找到SKU元素'
                print(f"   ❌ 未找到SKU元素")
                return result
            
            print(f"   找到 {len(sku_info)} 个SKU")
            found_skus = set()
            
            for sku in sku_info:
                if sku['disabled']:
                    continue
                
                text = sku['text']
                
                # 匹配目标SKU
                matched = None
                for target in target_skus:
                    target_clean = target.lower().replace(' ', '')
                    text_clean = text.lower().replace(' ', '')
                    if target_clean in text_clean:
                        matched = target
                        break
                
                if not matched or matched in found_skus:
                    continue
                
                found_skus.add(matched)
                print(f"   ✅ 匹配: {matched[:20]}")
                
                # 点击SKU
                await self.page.evaluate(
                    f'(idx) => document.querySelectorAll(\'[class*="valueItem--"]\')[idx]?.click()', 
                    sku['index']
                )
                await asyncio.sleep(4)  # 等待价格更新
                
                # 获取价格
                price_text = await self.page.evaluate('''() => {
                    const selectors = [
                        '[class*="highlightPrice--"]',
                        '[class*="priceWrap--"]',
                        '.tb-rmb-num'
                    ];
                    for (let sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.innerText && (el.innerText.includes('¥') || el.innerText.includes('￥'))) {
                            return el.innerText;
                        }
                    }
                    return null;
                }''')
                
                if price_text:
                    match = re.search(r'([\d,]+\.?\d*)', price_text.replace(',', ''))
                    if match:
                        price = float(match.group(1))
                        result['sku_prices'].append({'sku': text, 'price': price, 'target': matched})
                        print(f"      💰 ¥{price:.0f}")
            
            if not result['sku_prices']:
                result['error'] = '未找到匹配的SKU'
                self.manual_review.append({'shop': shop, 'model': model, 'error': '未找到匹配的SKU'})
                print(f"   ❌ 未找到匹配的SKU")
            
        except Exception as e:
            result['error'] = str(e)
            self.manual_review.append({'shop': shop, 'model': model, 'error': str(e)})
            print(f"   ❌ 错误: {e}")
        
        return result
    
    async def run(self):
        """执行监控（单浏览器连续检查）"""
        sku_rules = self.config.get('sku_rules', {})
        
        print("="*60)
        print(f"🚀 淘宝价格监控")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"📦 监控商品: {len(sku_rules)} 个")
        print("="*60)
        
        # 启动浏览器
        await self.init_browser()
        
        try:
            # 连续检查所有商品
            for item_id, rule in sku_rules.items():
                result = await self.check_product(item_id, rule)
                self.results.append(result)
                
                # 每个商品间隔避免请求过快
                await asyncio.sleep(2)
        finally:
            # 确保关闭浏览器
            await self.close_browser()
        
        # 保存结果
        self.save_results()
        
        # 发送报告
        self.send_report()
        
        # 打印汇总
        success_count = len([r for r in self.results if r['sku_prices']])
        print("\n" + "="*60)
        print(f"✅ 成功: {success_count}/{len(self.results)}")
        if self.manual_review:
            print(f"⚠️  需复核: {len(self.manual_review)} 个")
        print("="*60)
    
    def save_results(self):
        """保存结果到数据库"""
        for r in self.results:
            if r['sku_prices']:
                self.db.add_price(r['item_id'], r['sku_prices'][0]['price'], available=True)
    
    def send_report(self):
        """发送飞书报告"""
        lines = [
            "📊 淘宝价格监控报告",
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ""
        ]
        
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
                        lines.append(f"  {item['shop']:8s} ¥{sp['price']:>6.0f}")
                elif item['error']:
                    lines.append(f"  {item['shop']:8s} ❌ {item['error']}")
        
        # 需人工复核
        if self.manual_review:
            lines.append("\n" + "="*40)
            lines.append("⚠️ 需人工复核:")
            for item in self.manual_review[:5]:
                lines.append(f"  - {item['shop']} {item['model']}: {item['error']}")
        
        message = "\n".join(lines)
        self.notifier.send_text(message)
        print("\n📤 报告已发送")


if __name__ == '__main__':
    monitor = SkuPriceMonitor()
    asyncio.run(monitor.run())
