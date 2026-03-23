#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价格监控系统 - 手动录入版
淘宝反爬太强，改为支持手动录入/更新价格
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from database import Database, extract_item_id
from notifier import FeishuNotifier


class PriceMonitor:
    """价格监控主控 - 手动版"""
    
    def __init__(self):
        self.db = Database()
        self.notifier = FeishuNotifier()
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        config_path = Path(__file__).parent.parent / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 优先使用自建应用凭证
                if config.get('app_id') and config.get('app_secret') and config.get('chat_id'):
                    self.notifier.set_credentials(
                        config['app_id'],
                        config['app_secret'],
                        config['chat_id']
                    )
                elif config.get('feishu_webhook'):
                    self.notifier.set_webhook(config['feishu_webhook'])
    
    def add_product(self, url: str, target_price: float = None, 
                    initial_price: float = None, title: str = None, note: str = '') -> Dict:
        """添加监控商品（支持手动录入初始价格）"""
        item_id = extract_item_id(url)
        if not item_id:
            return {'success': False, 'error': '无法从链接中提取商品ID'}
        
        # 检查是否已存在
        existing = self.db.get_product_by_item_id(item_id)
        
        if existing:
            # 更新现有记录
            product_id = self.db.add_product(url, item_id, title, target_price, note)
            # 如果有初始价格，记录
            if initial_price:
                self.db.add_price_record(product_id, initial_price, None, True)
                self.db.update_product_price(product_id, initial_price)
            return {
                'success': True,
                'action': 'updated',
                'product_id': product_id,
                'item_id': item_id,
                'message': f'商品已更新 (ID: {product_id})'
            }
        else:
            # 添加新记录
            product_id = self.db.add_product(url, item_id, title, target_price, note)
            # 如果有初始价格，记录
            if initial_price:
                self.db.add_price_record(product_id, initial_price, None, True)
                self.db.update_product_price(product_id, initial_price)
            return {
                'success': True,
                'action': 'added',
                'product_id': product_id,
                'item_id': item_id,
                'message': f'添加成功 (ID: {product_id})'
            }
    
    def update_price(self, product_id: int, new_price: float, 
                     notify: bool = True) -> Dict:
        """手动更新商品价格"""
        products = self.db.get_products('active')
        product = next((p for p in products if p.id == product_id), None)
        
        if not product:
            return {'success': False, 'error': '商品不存在'}
        
        old_price = product.last_price
        
        # 记录价格
        self.db.add_price_record(product_id, new_price, None, True)
        self.db.update_product_price(product_id, new_price)
        
        result = {
            'success': True,
            'product_id': product_id,
            'title': product.title or '未知商品',
            'old_price': old_price,
            'new_price': new_price,
            'price_changed': old_price is not None and old_price != new_price,
            'target_hit': product.target_price and new_price <= product.target_price,
        }
        
        # 发送通知
        if notify and result['price_changed']:
            self.notifier.send_price_alert(
                product_name=result['title'],
                old_price=old_price,
                new_price=new_price,
                url=product.url,
                target_price=product.target_price
            )
        
        return result
    
    def list_products(self, status: str = 'active') -> List[Dict]:
        """列出监控商品"""
        products = self.db.get_products(status)
        return [
            {
                'id': p.id,
                'item_id': p.item_id,
                'title': p.title or '(未命名)',
                'target_price': p.target_price,
                'last_price': p.last_price,
                'last_check': p.last_check,
                'note': p.note,
            }
            for p in products
        ]
    
    def remove_product(self, product_id: int) -> Dict:
        """删除监控商品"""
        try:
            self.db.delete_product(product_id)
            return {'success': True, 'message': f'已删除商品 (ID: {product_id})'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_product_detail(self, product_id: int) -> Optional[Dict]:
        """获取商品详情和价格历史"""
        products = self.db.get_products('active')
        product = next((p for p in products if p.id == product_id), None)
        
        if not product:
            return None
        
        history = self.db.get_price_history(product_id, days=30)
        
        return {
            'id': product.id,
            'item_id': product.item_id,
            'url': product.url,
            'title': product.title,
            'target_price': product.target_price,
            'last_price': product.last_price,
            'note': product.note,
            'created_at': product.created_at,
            'price_history': [
                {
                    'price': h.price,
                    'timestamp': h.timestamp
                }
                for h in history
            ]
        }
    
    def send_daily_report(self, results: List[Dict]):
        """发送每日报告"""
        self.notifier.send_daily_report(results)


def print_products_table(products: List[Dict]):
    """打印商品列表"""
    if not products:
        print("暂无监控商品")
        return
    
    print("\n" + "="*100)
    print(f"{'ID':<6} {'商品ID':<12} {'商品名称':<30} {'目标价':<10} {'当前价':<10} {'备注'}")
    print("-"*100)
    
    for p in products:
        target = f"¥{p['target_price']:.0f}" if p['target_price'] else '-'
        current = f"¥{p['last_price']:.0f}" if p['last_price'] else '未录入'
        title = p['title'][:28] + '..' if len(p['title']) > 30 else p['title']
        print(f"{p['id']:<6} {p['item_id']:<12} {title:<30} {target:<10} {current:<10} {p['note']}")
    
    print("="*100)


def main():
    parser = argparse.ArgumentParser(description='淘宝价格监控（手动版）')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 添加商品
    add_parser = subparsers.add_parser('add', help='添加监控商品')
    add_parser.add_argument('url', help='商品链接')
    add_parser.add_argument('--target', '-t', type=float, help='目标价格')
    add_parser.add_argument('--price', '-p', type=float, help='初始价格')
    add_parser.add_argument('--title', '-T', help='商品名称')
    add_parser.add_argument('--note', '-n', default='', help='备注')
    
    # 更新价格
    update_parser = subparsers.add_parser('update', help='更新商品价格')
    update_parser.add_argument('id', type=int, help='商品ID')
    update_parser.add_argument('price', type=float, help='新价格')
    update_parser.add_argument('--no-notify', action='store_true', help='不发送通知')
    
    # 列出商品
    subparsers.add_parser('list', help='列出监控商品')
    
    # 查看详情
    detail_parser = subparsers.add_parser('detail', help='查看商品详情')
    detail_parser.add_argument('id', type=int, help='商品ID')
    
    # 删除商品
    remove_parser = subparsers.add_parser('remove', help='删除监控商品')
    remove_parser.add_argument('id', type=int, help='商品ID')
    
    # 发送报告
    subparsers.add_parser('report', help='发送监控报告')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    monitor = PriceMonitor()
    
    if args.command == 'add':
        result = monitor.add_product(
            args.url, args.target, args.price, args.title, args.note
        )
        print(result['message'])
        
    elif args.command == 'update':
        result = monitor.update_price(args.id, args.price, not args.no_notify)
        if result['success']:
            print(f"价格更新: ¥{result['old_price']:.2f} → ¥{result['new_price']:.2f}")
            if result['price_changed']:
                print("已发送价格变动通知")
            if result['target_hit']:
                print("🎯 已达到目标价！")
        else:
            print(f"更新失败: {result.get('error')}")
        
    elif args.command == 'list':
        products = monitor.list_products()
        print_products_table(products)
        
    elif args.command == 'detail':
        detail = monitor.get_product_detail(args.id)
        if detail:
            print(json.dumps(detail, ensure_ascii=False, indent=2))
        else:
            print("商品不存在")
        
    elif args.command == 'remove':
        result = monitor.remove_product(args.id)
        print(result['message'])
        
    elif args.command == 'report':
        products = monitor.list_products()
        results = [
            {
                'title': p['title'],
                'success': True,
                'new_price': p['last_price'],
                'old_price': p['last_price'],
                'price_changed': False,
                'target_hit': p['target_price'] and p['last_price'] and p['last_price'] <= p['target_price'],
                'target_price': p['target_price']
            }
            for p in products if p['last_price']
        ]
        monitor.send_daily_report(results)
        print("报告已发送")


if __name__ == '__main__':
    main()
