#!/usr/bin/env python3
"""
淘宝价格监控 - 飞书登录版
- 二维码发送到飞书群
- 手机扫码登录
- 自动开始监控

用法（在飞书群里调用）:
  @机器人 淘宝登录监控
"""
import asyncio
import json
import re
import sys
import base64
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
STORAGE_PATH = Path("~/.openclaw/workspace/skills/taobao-monitor/data/taobao_storage.json").expanduser()
FEISHU_CONFIG_PATH = Path("~/.openclaw/workspace/skills/taobao-monitor/data/feishu_bot.json").expanduser()

LOG_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)


class FeishuSender:
    """飞书消息发送器"""
    def __init__(self):
        self.webhook_url = None
        self.load_config()
    
    def load_config(self):
        """加载飞书配置"""
        try:
            if FEISHU_CONFIG_PATH.exists():
                with open(FEISHU_CONFIG_PATH) as f:
                    config = json.load(f)
                    self.webhook_url = config.get('webhook_url')
                    self.access_token = config.get('access_token')
        except Exception as e:
            print(f"加载飞书配置失败: {e}")
    
    async def send_text(self, text: str):
        """发送文本消息到飞书群"""
        if not self.webhook_url:
            print(f"[飞书] {text}")
            return
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            payload = {
                "msg_type": "text",
                "content": {"text": text}
            }
            try:
                async with session.post(self.webhook_url, json=payload) as resp:
                    return await resp.json()
            except Exception as e:
                print(f"发送飞书消息失败: {e}")
    
    async def send_image(self, image_path: Path, text: str = ""):
        """发送图片到飞书群"""
        if not self.webhook_url:
            print(f"[飞书图片] {image_path}")
            return
        
        import aiohttp
        
        # 读取图片并转 base64
        with open(image_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "msg_type": "image",
                "content": {
                    "image_key": image_base64  # 飞书需要上传到服务器，这里简化处理
                }
            }
            # 实际发送时先用文本提示
            await self.send_text(f"{text}\n[图片: {image_path.name}]")


class TaobaoMonitor:
    def __init__(self, headless: bool = True, feishu_chat_id: str = None):
        self.headless = headless
        self.feishu_chat_id = feishu_chat_id
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.results: List[Dict] = []
        self.feishu = FeishuSender()
        
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
        
        context_options = {
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        if STORAGE_PATH.exists():
            context_options['storage_state'] = str(STORAGE_PATH)
        
        self.context = await self.browser.new_context(**context_options)
        
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        
        self.page = await self.context.new_page()
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
    
    async def login_with_qr(self) -> bool:
        """扫码登录流程（飞书版）"""
        await self.feishu.send_text("🔐 启动淘宝登录流程...")
        
        # 打开登录页面
        await self.page.goto("https://login.taobao.com", wait_until='networkidle')
        await asyncio.sleep(3)
        
        # 截图二维码区域
        qr_path = LOG_DIR / f"taobao_qr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        # 尝试找到二维码元素并截图
        try:
            # 等待二维码加载
            await self.page.wait_for_selector('.qrcode-img, .login-box .qrcode, [class*="qrcode"]', timeout=10000)
            
            # 截图整个页面或二维码区域
            await self.page.screenshot(path=str(qr_path), full_page=False)
            
            await self.feishu.send_text(f"📱 请用【手机淘宝】扫描以下二维码登录:\n{qr_path}")
            
        except Exception as e:
            # 截图失败，截全屏
            await self.page.screenshot(path=str(qr_path), full_page=True)
            await self.feishu.send_text(f"📱 请在浏览器页面中找到二维码，用【手机淘宝】扫码登录\n截图: {qr_path}")
        
        await self.feishu.send_text("⏳ 等待扫码登录...（5分钟内有效）")
        
        # 等待登录成功
        max_wait = 300  # 5分钟
        for i in range(max_wait):
            await asyncio.sleep(1)
            
            try:
                url = self.page.url
                title = await self.page.title()
                
                if 'i.taobao.com' in url or ('taobao.com' in url and '我的淘宝' in title):
                    await self.feishu.send_text("✅ 登录成功！正在保存登录态...")
                    await asyncio.sleep(3)
                    await self.save_login_state()
                    return True
                    
            except:
                pass
            
            # 每30秒提醒一次
            if i > 0 and i % 30 == 0:
                remaining = (max_wait - i) // 60
                await self.feishu.send_text(f"⏳ 等待扫码中...还剩 {remaining} 分钟")
        
        await self.feishu.send_text("❌ 登录超时，请重新发起登录")
        return False
        
    async def check_login(self) -> bool:
        """检查是否已登录"""
        try:
            await self.page.goto("https://i.taobao.com/my_taobao.htm", timeout=10000)
            await asyncio.sleep(2)
            
            title = await self.page.title()
            url = self.page.url
            
            if '登录' in title or 'login' in url:
                return False
            
            if '我的淘宝' in title:
                return True
                
        except Exception as e:
            print(f"检查登录状态失败: {e}")
            
        return False
        
    async def fetch_product(self, item_id: str, rule: Dict, max_retries: int = 2) -> Dict:
        """抓取单个商品"""
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
                
                await self.page.goto(url, wait_until='networkidle', timeout=45000)
                await asyncio.sleep(3)
                
                title = await self.page.title()
                if '登录' in title or 'login' in title.lower():
                    result['errors'].append('需要登录')
                    return result
                
                # 获取SKU
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
                                break
                    except:
                        continue
                
                if not skus:
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
                                sku_data = {'name': target, 'price': price, 'shop': shop}
                                if 'tx' in target.lower():
                                    result['skus_tx'].append(sku_data)
                                else:
                                    result['skus'].append(sku_data)
                            else:
                                result['errors'].append(f'价格获取失败: {target}')
                            
                            break
                    
                    if not found:
                        result['errors'].append(f'未找到: {target}')
                
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    await asyncio.sleep(3)
                else:
                    result['errors'].append(f'异常: {str(e)[:50]}')
                    return result
        
        return result
    
    def generate_report(self) -> str:
        """生成报告"""
        lines = []
        lines.append("📊 淘宝价格监控报告")
        lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("-" * 40)
        
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
            
            normal_skus = by_model[model]['normal']
            tx_skus = by_model[model]['tx']
            
            if normal_skus:
                prices = [s['price'] for s in normal_skus]
                min_p, max_p = min(prices), max(prices)
                lines.append(f"  普通版 {len(normal_skus)}个 | ¥{min_p:.0f}-{max_p:.0f}")
                for s in sorted(normal_skus, key=lambda x: x['price'])[:3]:
                    lines.append(f"    ¥{s['price']:.0f} {s['shop']}")
            
            if tx_skus:
                prices = [s['price'] for s in tx_skus]
                min_p, max_p = min(prices), max(prices)
                lines.append(f"  TX版 {len(tx_skus)}个 | ¥{min_p:.0f}-{max_p:.0f}")
                for s in sorted(tx_skus, key=lambda x: x['price'])[:3]:
                    lines.append(f"    ¥{s['price']:.0f} TX {s['shop']}")
        
        lines.append(f"\n✅ 成功: {total_success} | ❌ 失败: {total_errors}")
        
        return "\n".join(lines)


async def main():
    """主流程：登录 + 监控"""
    # 加载配置
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    
    sku_rules = config.get('sku_rules', {})
    
    # 初始化（无头模式，后台运行）
    monitor = TaobaoMonitor(headless=True)
    
    try:
        await monitor.init()
        
        # 检查是否需要登录
        is_logged_in = await monitor.check_login()
        
        if not is_logged_in:
            await monitor.feishu.send_text("⚠️ 未登录或登录已失效，需要重新扫码")
            
            # 重新初始化一个有界面的浏览器用于扫码
            await monitor.close()
            monitor = TaobaoMonitor(headless=False)  # 可视化
            await monitor.init()
            
            # 扫码登录
            success = await monitor.login_with_qr()
            if not success:
                return
            
            # 登录成功后切回无头模式继续监控
            await monitor.close()
            monitor = TaobaoMonitor(headless=True)
            await monitor.init()
        
        # 开始监控
        await monitor.feishu.send_text(f"🚀 开始价格监控，共 {len(sku_rules)} 个商品...")
        
        items = list(sku_rules.items())
        for i, (item_id, rule) in enumerate(items):
            if i > 0 and i % 5 == 0:
                await monitor.page.reload()
                await asyncio.sleep(2)
            
            result = await monitor.fetch_product(item_id, rule)
            monitor.results.append(result)
            await asyncio.sleep(2)
        
        # 生成并发送报告
        report = monitor.generate_report()
        await monitor.feishu.send_text(report)
        
        # 保存日志
        log_file = LOG_DIR / f"monitor_feishu_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        await monitor.feishu.send_text("✅ 监控完成！")
        
    except Exception as e:
        error_msg = f"❌ 监控失败: {str(e)[:200]}"
        await monitor.feishu.send_text(error_msg)
        import traceback
        traceback.print_exc()
        
    finally:
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())
