#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝价格监控主控程序 - 使用 agent-browser
"""
import os
import sys
import json
import argparse
import csv
from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict

# 添加脚本目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 关闭 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

from database import Database, extract_item_id, format_price_change
from crawler_agent_browser import TaobaoAgentBrowserCrawler
from notifier import FeishuNotifier


class PriceMonitor:
    """价格监控主控"""
    
    def __init__(self):
        self.db = Database()
        self.notifier = FeishuNotifier()
        self.crawler = TaobaoAgentBrowserCrawler()
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
                # 兼容webhook方式
                elif config.get('feishu_webhook'):
                    self.notifier.set_webhook(config['feishu_webhook'])
    
    def import_from_csv(self, csv_file: str) -> Dict:
        """从 CSV 文件导入监控商品"""
        imported = 0
        updated = 0
        errors = []
        
        try:
            with open(csv_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        url = row.get('商品链接', '').strip()
                        if not url:
                            continue
                        
                        title = row.get('商品名称', '').strip()
                        shop = row.get('店铺名称', '').strip()
                        note = row.get('备注', '').strip()
                        
                        # 组合备注信息
                        full_note = f"{shop}"
                        if note:
                            full_note += f" | {note}"
                        
                        # 解析价格
                        target_price = None
                        try:
                            target = row.get('目标价格', '').strip()
                            if target:
                                target_price = float(target)
                        except:
                            pass
                        
                        result = self.add_product(url, target_price, full_note, title)
                        if result['action'] == 'added':
                            imported += 1
                        else:
                            updated += 1
                            
                    except Exception as e:
                        errors.append(f"行导入失败: {e}")
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}
        
        return {
            'success': True,
            'imported': imported,
            'updated': updated,
            'errors': errors
        }
    
    def add_product(self, url: str, target_price: float = None, note: str = '', title: str = None) -> Dict:
        """添加监控商品"""
        item_id = extract_item_id(url)
        if not item_id:
            return {'success': False, 'error': '无法从链接中提取商品ID'}
        
        # 检查是否已存在
        existing = self.db.get_product_by_item_id(item_id)
        if existing:
            # 更新现有记录
            product_id = self.db.add_product(url, item_id, title, target_price, note)
            return {
                'success': True,
                'action': 'updated',
                'product_id': product_id,
                'item_id': item_id,
                'message': f'商品已存在，已更新配置 (ID: {product_id})'
            }
        else:
            # 添加新记录
            product_id = self.db.add_product(url, item_id, title, target_price, note)
            return {
                'success': True,
                'action': 'added',
                'product_id': product_id,
                'item_id': item_id,
                'message': f'添加成功 (ID: {product_id})'
            }
    
    def list_products(self, status: str = 'active') -> List[Dict]:
        """列出监控商品"""
        products = self.db.get_products(status)
        return [
            {
                'id': p.id,
                'item_id': p.item_id,
                'title': p.title or '(未抓取)',
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
    
    def check_all(self, notify: bool = True) -> List[Dict]:
        """检查所有商品价格"""
        products = self.db.get_products('active')
        if not products:
            print("没有监控中的商品")
            return []
        
        results = []
        
        for product in products:
            print(f"\n检查: {product.url}")
            result = self._check_product(product)
            results.append(result)
            
            # 实时通知价格变动
            if notify and result.get('price_changed') and result.get('success'):
                self.notifier.send_price_alert(
                    product_name=result.get('title', '未知商品'),
                    old_price=result['old_price'],
                    new_price=result['new_price'],
                    url=product.url,
                    target_price=product.target_price
                )
        
        # 发送汇总报告
        if notify and results:
            self.notifier.send_daily_report(results)
        
        return results
    
    def check_single(self, product_id: int) -> Dict:
        """检查单个商品价格"""
        products = self.db.get_products('active')
        product = next((p for p in products if p.id == product_id), None)
        
        if not product:
            return {'success': False, 'error': '商品不存在'}
        
        return self._check_product(product)
    
    def _check_product(self, product) -> Dict:
        """检查单个商品并记录"""
        result = {
            'product_id': product.id,
            'item_id': product.item_id,
            'url': product.url,
            'success': False,
            'price_changed': False,
            'target_hit': False,
        }
        
        # 抓取价格
        crawl_result = self.crawler.fetch_price(product.url)
        
        if crawl_result.get('error') or not crawl_result.get('price'):
            result['error'] = crawl_result.get('error', '无法获取价格')
            return result
        
        # 更新商品信息
        new_price = crawl_result['price']
        old_price = product.last_price
        title = crawl_result.get('title') or product.title or '未知商品'
        
        result.update({
            'success': True,
            'title': title,
            'new_price': new_price,
            'old_price': old_price,
            'available': crawl_result.get('available', True),
        })
        
        # 检查价格变动
        if old_price and new_price != old_price:
            result['price_changed'] = True
        
        # 检查是否达到目标价
        if product.target_price and new_price <= product.target_price:
            result['target_hit'] = True
        
        # 保存到数据库
        self.db.add_price_record(product.id, new_price, crawl_result.get('original_price'), 
                                  crawl_result.get('available', True))
        self.db.update_product_price(product.id, new_price)
        
        # 打印结果
        status = "✅" if result['success'] else "❌"
        change_info = ""
        if result['price_changed']:
            change_info = f" ({format_price_change(old_price, new_price)})"
        print(f"{status} {title[:30]}: ¥{new_price}{change_info}")
        
        return result


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
        current = f"¥{p['last_price']:.0f}" if p['last_price'] else '未抓取'
        title = p['title'][:28] + '..' if len(p['title']) > 30 else p['title']
        print(f"{p['id']:<6} {p['item_id']:<12} {title:<30} {target:<10} {current:<10} {p['note']}")
    
    print("="*100)


def main():
    parser = argparse.ArgumentParser(description='淘宝价格监控')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 添加商品
    add_parser = subparsers.add_parser('add', help='添加监控商品')
    add_parser.add_argument('url', help='商品链接')
    add_parser.add_argument('--target', '-t', type=float, help='目标价格')
    add_parser.add_argument('--title', '-T', help='商品名称')
    add_parser.add_argument('--note', '-n', default='', help='备注')
    
    # 从 CSV 导入
    import_parser = subparsers.add_parser('import', help='从 CSV 导入商品')
    import_parser.add_argument('file', help='CSV 文件路径')
    
    # 列出商品
    subparsers.add_parser('list', help='列出监控商品')
    
    # 删除商品
    remove_parser = subparsers.add_parser('remove', help='删除监控商品')
    remove_parser.add_argument('id', type=int, help='商品ID')
    
    # 检查价格
    check_parser = subparsers.add_parser('check', help='检查价格')
    check_parser.add_argument('--id', type=int, help='只检查指定商品')
    check_parser.add_argument('--no-notify', action='store_true', help='不发送通知')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    monitor = PriceMonitor()
    
    if args.command == 'add':
        result = monitor.add_product(args.url, args.target, args.note, args.title)
        print(result['message'])
        
    elif args.command == 'import':
        result = monitor.import_from_csv(args.file)
        if result['success']:
            print(f"导入完成: 新增 {result['imported']} 个, 更新 {result['updated']} 个")
            if result['errors']:
                print(f"错误: {len(result['errors'])} 个")
                for e in result['errors'][:5]:
                    print(f"  - {e}")
        else:
            print(f"导入失败: {result['error']}")
        
    elif args.command == 'list':
        products = monitor.list_products()
        print_products_table(products)
        
    elif args.command == 'remove':
        result = monitor.remove_product(args.id)
        print(result['message'])
        
    elif args.command == 'check':
        if args.id:
            result = monitor.check_single(args.id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            results = monitor.check_all(notify=not args.no_notify)
            print(f"\n检查完成: {len(results)} 个商品")


if __name__ == '__main__':
    main()
