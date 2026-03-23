#!/usr/bin/env python3
"""
淘宝价格监控 - Playwright 稳定版
- 一次启动浏览器，连续操作
- 智能等待 + 重试机制
- 可视化登录模式

用法:
  python3 monitor_playwright.py --login    # 首次登录/重新登录
  python3 monitor_playwright.py            # 日常监控
"""
import asyncio
import json
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
except ImportError:
    print("正在安装 Playwright...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# 配置
CONFIG_PATH = Path("~/.openclaw/workspace/skills/taobao-monitor/config.json").expanduser()
LOG_DIR = Path("~/.openclaw/workspace/skills/taobao-monitor/logs").expanduser()
COOKIES_PATH = Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_cookies.json").expanduser()
STORAGE_PATH = Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_storage.json").expanduser()

LOG_DIR.mkdir(parents=True, exist_ok=True)
COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)


class TaobaoMonitor:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.results: List[Dict] = []
        
    async def init(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # 创建上下文
        context_options = {
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # 如果有保存的 storage state，加载它
        if STORAGE_PATH.exists():
            print(f"📂 加载已保存的登录态: {STORAGE_PATH}")
            context_options['storage_state'] = str(STORAGE_PATH)
        
        self.context = await self.browser.new_context(**context_options)
        
        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        
        self.page = await self.context.new_page()
        
        # 设置超时
        self.page.set_default_timeout(30000)
        self.page.set_default_navigation_timeout(45000)
        
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()
        
    async def save_login_state(self):
        """保存登录状态"""
        if self.context:
            await self.context.storage_state(path=str(STORAGE_PATH))
            print(f"💾 登录态已保存: {STORAGE_PATH}")
    
    async def login(self):
        """可视化登录流程"""
        print("=" * 60)
        print("🔐 淘宝登录模式")
        print("=" * 60)
        print("\n1. 浏览器窗口即将打开")
        print("2. 请手动扫码或密码登录淘宝")
        print("3. 登录成功后，按回车键保存登录态\n")
        
        # 打开登录页面
        await self.page.goto("https://login.taobao.com", wait_until='networkidle')
        
        print("⏳ 等待登录...（浏览器窗口中操作）")
        print("提示: 如果看到滑块验证，请手动完成")
        
        # 等待用户登录成功（检测是否跳转到我的淘宝或首页）
        max_wait = 300  # 最多等5分钟
        for i in range(max_wait):
            await asyncio.sleep(1)
            
            try:
                url = self.page.url
                title = await self.page.title()
                
                # 检测登录成功标志
                if 'i.taobao.com' in url or 'taobao.com' in url:
                    if '我的淘宝' in title or '淘宝网' in title:
                        print(f"\n✅ 检测到登录成功!")
                        print(f"   当前页面: {title}")
                        print(f"   URL: {url}")
                        break
            except:
                pass
            
            # 每30秒提醒一次
            if i > 0 and i % 30 == 0:
                print(f"   ...已等待 {i} 秒，请完成登录")
        else:
            print("\n⚠️ 等待超时，请检查浏览器窗口")
            return False
        
        # 再等等让 cookies 稳定
        print("\n⏳ 保存登录态中...")
        await asyncio.sleep(3)
        
        # 保存状态
        await self.save_login_state()
        
        print("\n✅ 登录完成！下次运行无需重复登录")
        return True
        
    async def check_login(self) -> bool:
        """检查是否已登录"""
        try:
            await self.page.goto("https://i.taobao.com/my_taobao.htm", timeout=10000)
            await asyncio.sleep(2)
            
            title = await self.page.title()
            url = self.page.url
            
            if '登录' in title or 'login' in url:
                print("⚠️ 登录态已失效，需要重新登录")
                return False
            
            if '我的淘宝' in title:
                print("✅ 登录态有效")
                return True
                
        except Exception as e:
            print(f"⚠️ 检查登录状态失败: {e}")
            
        return False
        
    async def fetch_product(self, item_id: str, rule: Dict, max_retries: int = 2) -> Dict:
        """抓取单个商品，带重试"""
        shop = rule['shop']
        model = rule['model']
        target_skus = rule['target_skus']
        url = f"https://item.taobao.com/item.htm?id={item_id}"
        
        result = {
            'shop': shop,
            'model': model,
            'skus': [],
            'skus_tx': [],
            'errors': []
        }
        
        for attempt in range(max_retries + 1):
            try:
                print(f"\n【{shop} - {model}】{' (重试)' if attempt > 0 else ''}")
                
                # 访问页面 - 使用 domcontentloaded 而不是 networkidle（更快）
                await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(5)  # 等待页面完全渲染
                
                # 检查登录状态
                title = await self.page.title()
                if '登录' in title or 'login' in title.lower():
                    print(f"  ⚠️ 需要登录！")
                    result['errors'].append('需要登录')
                    return result
                
                # 等待SKU加载 - 多种选择器
                sku_selectors = [
                    '[class*="valueItem"]',
                    '.tb-sku .tb-prop .tb-selected',
                    '[data-spm="sku"] .sku-item',
                    '.sku-wrapper .sku-item',
                    '[class*="sku"] [class*="item"]',
                ]
                
                skus = []
                for selector in sku_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if elements:
                            for el in elements:
                                text = await el.inner_text()
                                if text:
                                    skus.append(text.strip())
                            if skus:
                                print(f"  找到 {len(skus)} 个SKU")
                                break
                    except:
                        continue
                
                if not skus:
                    print(f"  ❌ 未找到SKU元素")
                    if attempt < max_retries:
                        await asyncio.sleep(3)
                        continue
                    result['errors'].append('未找到SKU')
                    return result
                
                # 抓取每个目标SKU
                for target in target_skus:
                    found = False
                    for i, sku_text in enumerate(skus):
                        if target.lower().replace(' ', '') in sku_text.lower().replace(' ', ''):
                            print(f"  点击 [{i}]: {target}")
                            
                            # 点击SKU
                            for selector in sku_selectors:
                                try:
                                    elements = await self.page.query_selector_all(selector)
                                    if i < len(elements):
                                        await elements[i].click()
                                        await asyncio.sleep(4)
                                        found = True
                                        break
                                except:
                                    continue
                            
                            if not found:
                                continue
                            
                            # 获取价格
                            price_selectors = [
                                '[class*="Price"]',
                                '.tb-rmb-num',
                                '.notranslate',
                                '[class*="price"]',
                                '.tm-price',
                                '.tb-price',
                            ]
                            
                            price = None
                            for price_selector in price_selectors:
                                try:
                                    price_el = await self.page.query_selector(price_selector)
                                    if price_el:
                                        price_text = await price_el.inner_text()
                                        match = re.search(r'[¥￥]?\s*([\d,]+\.?\d*)', price_text)
                                        if match:
                                            price = float(match.group(1).replace(',', ''))
                                            break
                                except:
                                    continue
                            
                            if price:
                                print(f"    ✅ ¥{price:.0f}")
                                sku_data = {'name': target, 'price': price, 'shop': shop}
                                
                                if 'tx' in target.lower():
                                    result['skus_tx'].append(sku_data)
                                else:
                                    result['skus'].append(sku_data)
                            else:
                                print(f"    ❌ 价格获取失败")
                                result['errors'].append(f'价格获取失败: {target}')
                            
                            break
                    
                    if not found:
                        print(f"  ❌ 未找到SKU: '{target}'")
                        result['errors'].append(f'未找到: {target}')
                
                return result
                
            except Exception as e:
                print(f"  ⚠️ 错误: {str(e)[:50]}")
                if attempt < max_retries:
                    print(f"  🔄 等待3秒后重试...")
                    await asyncio.sleep(3)
                else:
                    result['errors'].append(f'异常: {str(e)[:50]}')
                    return result
        
        return result
    
    def generate_report(self) -> str:
        """生成报告"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"📊 淘宝价格监控 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 60)
        
        from collections import defaultdict
        by_model = defaultdict(lambda: {'normal': [], 'tx': []})
        
        total_success = 0
        total_errors = 0
        
        for r in self.results:
            model = r['model']
            by_model[model]['normal'].extend(r.get('skus', []))
            by_model[model]['tx'].extend(r.get('skus_tx', []))
            total_success += len(r.get('skus', [])) + len(r.get('skus_tx', []))
            total_errors += len(r.get('errors', []))
        
        for model in ['Perdix', 'Peregrine', 'Teric', 'Tern']:
            if model not in by_model:
                continue
            
            lines.append(f"\n🏷️ {model}")
            lines.append("-" * 40)
            
            normal_skus = by_model[model]['normal']
            tx_skus = by_model[model]['tx']
            
            if normal_skus:
                prices = [s['price'] for s in normal_skus]
                min_p, max_p = min(prices), max(prices)
                lines.append(f"  普通版: {len(normal_skus)}个 | 最低¥{min_p:.0f} 最高¥{max_p:.0f}")
                for s in sorted(normal_skus, key=lambda x: x['price']):
                    marker = "🔥" if s['price'] == min_p else ""
                    lines.append(f"    {marker} ¥{s['price']:.0f} | {s['shop']}")
            
            if tx_skus:
                prices = [s['price'] for s in tx_skus]
                min_p, max_p = min(prices), max(prices)
                lines.append(f"  TX版: {len(tx_skus)}个 | 最低¥{min_p:.0f} 最高¥{max_p:.0f}")
                for s in sorted(tx_skus, key=lambda x: x['price']):
                    marker = "🔥" if s['price'] == min_p else ""
                    lines.append(f"    {marker} ¥{s['price']:.0f} | TX | {s['shop']}")
        
        lines.append("\n" + "=" * 60)
        lines.append(f"✅ 成功: {total_success} | ❌ 失败: {total_errors}")
        lines.append("=" * 60)
        
        return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description='淘宝价格监控')
    parser.add_argument('--login', action='store_true', help='登录模式（可视化）')
    parser.add_argument('--check', action='store_true', help='检查登录状态')
    args = parser.parse_args()
    
    # 登录模式
    if args.login:
        monitor = TaobaoMonitor(headless=False)  # 可视化
        try:
            await monitor.init()
            success = await monitor.login()
            if success:
                print("\n🎉 登录成功！可以运行监控任务了")
            else:
                print("\n❌ 登录失败")
        finally:
            await monitor.close()
        return
    
    # 检查登录状态
    if args.check:
        monitor = TaobaoMonitor(headless=True)
        try:
            await monitor.init()
            is_logged_in = await monitor.check_login()
            sys.exit(0 if is_logged_in else 1)
        finally:
            await monitor.close()
        return
    
    # 正常监控模式
    # 加载配置
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    
    sku_rules = config.get('sku_rules', {})
    
    print("=" * 60)
    print(f"📊 淘宝价格监控 - Playwright稳定版")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"商品数: {len(sku_rules)}")
    print("=" * 60)
    
    # 检查是否有登录态
    if not STORAGE_PATH.exists():
        print("\n⚠️ 未找到登录态，请先运行: python3 monitor_playwright.py --login")
        return
    
    monitor = TaobaoMonitor(headless=True)
    
    try:
        await monitor.init()
        
        # 先检查登录状态
        if not await monitor.check_login():
            print("\n⚠️ 登录已失效，请重新运行: python3 monitor_playwright.py --login")
            return
        
        items = list(sku_rules.items())
        for i, (item_id, rule) in enumerate(items):
            # 每5个商品刷新
            if i > 0 and i % 5 == 0:
                print(f"\n🔄 已处理5个商品，刷新页面...")
                await monitor.page.reload()
                await asyncio.sleep(2)
            
            result = await monitor.fetch_product(item_id, rule)
            monitor.results.append(result)
            
            await asyncio.sleep(2)
        
        # 生成报告
        report = monitor.generate_report()
        print("\n" + report)
        
        # 保存日志
        log_file = LOG_DIR / f"monitor_pw_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n💾 报告已保存: {log_file}")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())
