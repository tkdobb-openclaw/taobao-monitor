#!/usr/bin/env python3
"""
淘宝价格抓取 - 使用 JS 点击绕过遮罩层
"""
import asyncio
import json
import re
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from notifier import FeishuNotifier

class SkuCrawlerJS:
    def __init__(self):
        self.config = self._load_config()
        self.notifier = FeishuNotifier()
        self._load_notifier_config()
    
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
    
    async def fetch_sku_prices(self, url: str, target_skus: list) -> list:
        """使用 JS 点击抓取价格"""
        results = []
        auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=auth_file)
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(3)  # 等待页面完全加载
                
                title = await page.title()
                
                # 关闭可能的弹窗/遮罩
                await page.evaluate('''() => {
                    // 关闭常见弹窗
                    const closeBtns = document.querySelectorAll('.close, .J_Close, [class*="close"]');
                    closeBtns.forEach(btn => btn.click());
                    // 移除遮罩层
                    const overlays = document.querySelectorAll('.J_MIDDLEWARE_FRAME_WIDGET, [class*="overlay"], [class*="modal"]');
                    overlays.forEach(el => el.remove());
                }''')
                
                # 获取所有 SKU 文本和索引
                sku_info = await page.evaluate('''() => {
                    const items = document.querySelectorAll('[class*="valueItem--"]');
                    return Array.from(items).map((el, i) => ({
                        index: i,
                        text: el.innerText?.trim() || '',
                        disabled: el.classList.contains('isDisabled--') || el.disabled
                    })).filter(item => item.text);
                }''')
                
                print(f"找到 {len(sku_info)} 个 SKU")
                
                found_skus = set()
                
                for sku in sku_info:
                    text = sku['text']
                    
                    # 匹配目标 SKU
                    matched = None
                    for target in target_skus:
                        if target.replace(" ", "").lower() in text.replace(" ", "").lower():
                            matched = target
                            break
                    
                    if not matched or matched in found_skus or sku['disabled']:
                        continue
                    
                    found_skus.add(matched)
                    
                    print(f"点击 SKU: {text}")
                    
                    # 使用 JS 点击（绕过遮罩）
                    await page.evaluate(f'''(index) => {{
                        const items = document.querySelectorAll('[class*="valueItem--"]');
                        if (items[index]) {{
                            items[index].click();
                            items[index].dispatchEvent(new Event('click', {{ bubbles: true }}));
                        }}
                    }}''', sku['index'])
                    
                    await asyncio.sleep(2)  # 等待价格更新
                    
                    # 获取价格
                    price_text = await page.evaluate('''() => {
                        const el = document.querySelector('[class*="priceText--"]') || 
                                   document.querySelector('.tb-rmb-num');
                        return el ? el.innerText : null;
                    }''')
                    
                    if price_text:
                        match = re.search(r'([\d.]+)', price_text.replace(',', ''))
                        if match:
                            price = float(match.group(1))
                            results.append({'sku': text, 'price': price, 'target': matched})
                            print(f"  价格: ¥{price}")
                
                await browser.close()
                return {'title': title, 'results': results}
                
            except Exception as e:
                await browser.close()
                return {'title': 'Error', 'results': [], 'error': str(e)}
    
    async def run(self):
        sku_rules = self.config.get('sku_rules', {})
        all_results = []
        
        for item_id, rule in sku_rules.items():
            url = f"https://item.taobao.com/item.htm?id={item_id}"
            target_skus = rule.get('target_skus', [])
            
            print(f"\n检查: {rule.get('shop', 'Unknown')} - {rule.get('model', 'Unknown')}")
            result = await self.fetch_sku_prices(url, target_skus)
            all_results.append({
                'item_id': item_id,
                'shop': rule.get('shop', 'Unknown'),
                'model': rule.get('model', 'Unknown'),
                **result
            })
        
        # 打印结果
        print("\n" + "="*60)
        for r in all_results:
            print(f"\n{r['shop']} - {r['model']}:")
            if r.get('error'):
                print(f"  错误: {r['error']}")
            else:
                for item in r.get('results', []):
                    print(f"  ¥{item['price']:.0f} - {item['sku']}")
        
        return all_results

if __name__ == '__main__':
    crawler = SkuCrawlerJS()
    results = asyncio.run(crawler.run())
