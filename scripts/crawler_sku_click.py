#!/usr/bin/env python3
"""
淘宝价格抓取 - 后台执行版（点击指定 SKU）
执行完成后自动发送飞书通知
"""
import asyncio
import json
import re
import sys
from pathlib import Path
from playwright.async_api import async_playwright

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))
from notifier import FeishuNotifier

class SkuClickCrawler:
    """点击 SKU 抓取价格"""
    
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
        """抓取指定 SKU 的价格"""
        results = []
        auth_file = str(Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_auth.json").expanduser())
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(storage_state=auth_file)
            page = await context.new_page()
            
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                
                # 获取标题
                title = await page.title()
                
                # 找到所有 SKU 选项
                sku_items = await page.query_selector_all('[class*="valueItem--"]')
                found_skus = set()
                
                for item in sku_items:
                    text = await item.text_content()
                    if not text:
                        continue
                    
                    text = text.strip()
                    
                    # 检查是否匹配目标 SKU
                    matched_sku = None
                    for target in target_skus:
                        if target.replace(" ", "").lower() in text.replace(" ", "").lower():
                            matched_sku = target
                            break
                    
                    if not matched_sku or matched_sku in found_skus:
                        continue
                    
                    found_skus.add(matched_sku)
                    
                    try:
                        await item.scroll_into_view_if_needed()
                        await item.click()
                        await asyncio.sleep(1.5)
                        
                        # 获取价格
                        price_text = await page.evaluate('''() => {
                            const selectors = [
                                '[class*="priceText--"]',
                                '.tb-rmb-num',
                                '[class*="Price--"]'
                            ];
                            for (let sel of selectors) {
                                const el = document.querySelector(sel);
                                if (el && el.innerText.includes('¥')) {
                                    return el.innerText.trim();
                                }
                            }
                            return null;
                        }''')
                        
                        if price_text:
                            match = re.search(r'¥?\s*([\d,]+(?:\.\d{2})?)', price_text.replace(',', ''))
                            if match:
                                price = float(match.group(1))
                                results.append({
                                    'sku': text,
                                    'price': price,
                                    'matched': matched_sku
                                })
                    except Exception as e:
                        print(f"点击失败: {e}")
                
                await browser.close()
                return {'title': title, 'results': results}
                
            except Exception as e:
                await browser.close()
                return {'title': 'Error', 'results': [], 'error': str(e)}
    
    async def run_check(self):
        """执行检查"""
        sku_rules = self.config.get('sku_rules', {})
        all_results = []
        
        for item_id, rule in sku_rules.items():
            url = f"https://item.taobao.com/item.htm?id={item_id}"
            target_skus = rule.get('target_skus', [])
            
            print(f"检查: {rule.get('shop', 'Unknown')} - {rule.get('model', 'Unknown')}")
            result = await self.fetch_sku_prices(url, target_skus)
            all_results.append({
                'item_id': item_id,
                'shop': rule.get('shop', 'Unknown'),
                'model': rule.get('model', 'Unknown'),
                **result
            })
        
        # 发送报告
        await self.send_report(all_results)
        return all_results
    
    async def send_report(self, results: list):
        """发送飞书报告"""
        lines = ["📊 SKU 价格抓取报告", ""]
        
        for r in results:
            lines.append(f"【{r['shop']} - {r['model']}】")
            lines.append(f"商品: {r.get('title', 'N/A')[:30]}...")
            
            if r.get('error'):
                lines.append(f"❌ 错误: {r['error']}")
            elif r['results']:
                for item in sorted(r['results'], key=lambda x: x['price']):
                    lines.append(f"  ¥{item['price']:>6.0f} - {item['sku']}")
            else:
                lines.append("  未找到目标 SKU")
            
            lines.append("")
        
        message = "\n".join(lines)
        self.notifier.send_text(message)
        print(f"\n报告已发送")


if __name__ == '__main__':
    crawler = SkuClickCrawler()
    results = asyncio.run(crawler.run_check())
    
    # 打印结果
    print("\n" + "="*60)
    for r in results:
        print(f"\n{r['shop']} - {r['model']}:")
        for item in r.get('results', []):
            print(f"  ¥{item['price']:>6.0f} - {item['sku']}")
