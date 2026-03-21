#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书通知模块 - 支持自建应用API
"""
import json
import time
import requests
from typing import List, Dict
from datetime import datetime


class FeishuNotifier:
    """飞书自建应用消息通知"""
    
    def __init__(self, app_id: str = None, app_secret: str = None, chat_id: str = None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.chat_id = chat_id
        self._access_token = None
        self._token_expire = 0
        self.webhook_url = None
    
    def set_webhook(self, url: str):
        """设置Webhook地址（备用）"""
        self.webhook_url = url
    
    def set_credentials(self, app_id: str, app_secret: str, chat_id: str):
        """设置自建应用凭证"""
        self.app_id = app_id
        self.app_secret = app_secret
        self.chat_id = chat_id
    
    def _get_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self._access_token and time.time() < self._token_expire:
            return self._access_token
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=30)
            data = resp.json()
            if data.get("code") == 0:
                self._access_token = data["tenant_access_token"]
                # token有效期2小时，提前5分钟刷新
                self._token_expire = time.time() + data["expire"] - 300
                return self._access_token
            else:
                print(f"获取token失败: {data}")
                return None
        except Exception as e:
            print(f"获取token出错: {e}")
            return None
    
    def _send_api(self, content: dict) -> bool:
        """通过API发送消息"""
        if not self.chat_id:
            print("未设置chat_id")
            return False
        
        token = self._get_access_token()
        if not token:
            return False
        
        url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "receive_id": self.chat_id,
            "msg_type": content.get("msg_type", "text"),
            "content": json.dumps(content.get("content", {}))
        }
        
        # 如果包含card，需要特殊处理
        if "card" in content:
            payload["msg_type"] = "interactive"
            payload["content"] = json.dumps({"card": content["card"]})
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            result = resp.json()
            if result.get("code") == 0:
                return True
            else:
                print(f"发送消息失败: {result}")
                return False
        except Exception as e:
            print(f"发送请求出错: {e}")
            return False
    
    def send_text(self, text: str) -> bool:
        """发送纯文本消息"""
        content = {
            "msg_type": "text",
            "content": {"text": text}
        }
        return self._send_api(content)
    
    def send_markdown(self, title: str, content_md: str) -> bool:
        """发送Markdown消息"""
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": content_md}
                }
            ]
        }
        return self._send_api({"card": card})
    
    def send_price_alert(self, product_name: str, old_price: float, 
                         new_price: float, url: str, target_price: float = None):
        """发送价格变动告警"""
        diff = new_price - old_price
        percent = (diff / old_price * 100) if old_price else 0
        
        if diff < 0:
            template = "green"  # 降价
            emoji = "📉"
            trend = "下跌"
        elif diff > 0:
            template = "red"  # 涨价
            emoji = "📈"
            trend = "上涨"
        else:
            template = "grey"
            emoji = "➡️"
            trend = "持平"
        
        # 检查是否达到目标价
        target_hit = target_price and new_price <= target_price
        target_text = f"\n🎯 **目标价**: ¥{target_price:.2f} {'✅ 已达到!' if target_hit else ''}" if target_price else ""
        
        content_md = f"""**{product_name}**

{emoji} **价格{trend}**: ¥{old_price:.2f} → ¥{new_price:.2f}
💰 **变动**: ¥{abs(diff):.2f} ({percent:+.1f}%){target_text}

[查看商品]({url})
"""
        
        card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"价格监控告警 - {product_name[:20]}"},
                "template": template
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": content_md}
                }
            ]
        }
        return self._send_api({"card": card})
    
    def send_daily_report(self, results: List[Dict]):
        """发送每日价格监控报告 - 表格版"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 按商品名称分组
        from collections import defaultdict
        products = defaultdict(list)
        for r in results:
            if r.get('success'):
                title = r.get('title', '未知商品')
                product_name = title[:20].split('-')[0].strip()
                products[product_name].append(r)
        
        lines = [f"📊 **价格监控日报** - {now}\n"]
        
        # 统计摘要
        total_products = len(products)
        total_shops = len([r for r in results if r.get('success')])
        changed_count = sum(1 for r in results if r.get('price_changed'))
        
        lines.append(f"📈 概况：{total_products} 款商品 · {total_shops} 家店铺")
        if changed_count > 0:
            lines.append(f"⚠️ 今日 {changed_count} 家价格变动\n")
        else:
            lines.append("✅ 今日价格无变动\n")
        
        # 显示价格变动的店铺（简洁版）
        if changed_count > 0:
            lines.append("**💰 今日变动**")
            for r in results:
                if r.get('price_changed'):
                    shop = r.get('note', '未知')[:8]
                    old = int(r.get('old_price', 0))
                    new = int(r.get('new_price', 0))
                    diff = new - old
                    emoji = "📉" if diff < 0 else "📈"
                    lines.append(f"{emoji} **{shop}** ¥{old} → ¥{new}")
            lines.append("")
        
        # 按商品显示表格
        for product_name, shops in sorted(products.items()):
            lines.append(f"**🔍 {product_name}**")
            
            # 表头
            lines.append("| 店铺 | 现价 | 变动 |")
            lines.append("|------|------|------|")
            
            # 按价格排序
            shops_sorted = sorted(shops, key=lambda x: x.get('new_price', float('inf')))
            
            for i, shop in enumerate(shops_sorted):
                price = int(shop.get('new_price', 0))
                shop_name = shop.get('note', '未知')[:8]
                
                # 最低价标识
                price_display = f"**¥{price}** 🔥" if i == 0 else f"¥{price}"
                
                # 变动标识
                if shop.get('price_changed'):
                    old = int(shop.get('old_price', 0))
                    diff = price - old
                    change_display = f"{diff:+,d} 📊" if diff != 0 else "-"
                else:
                    change_display = "-"
                
                lines.append(f"| {shop_name} | {price_display} | {change_display} |")
            
            lines.append("")
        
        content = "\n".join(lines)
        return self.send_text(content)


if __name__ == '__main__':
    print("飞书通知模块")
    # 测试代码
    # notifier = FeishuNotifier("your-webhook-url")
    # notifier.send_text("测试消息")
