#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝价格监控核心模块
"""
import re
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "monitor.db"

@dataclass
class Product:
    """商品信息"""
    id: int
    url: str
    item_id: str
    title: str
    target_price: Optional[float]
    note: str
    created_at: str
    last_check: Optional[str]
    last_price: Optional[float]
    status: str  # active, paused, error

@dataclass
class PriceRecord:
    """价格记录"""
    id: int
    product_id: int
    price: float
    original_price: Optional[float]
    timestamp: str
    available: bool

class Database:
    """数据库管理"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    item_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    target_price REAL,
                    note TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_check TIMESTAMP,
                    last_price REAL,
                    status TEXT DEFAULT 'active'
                );
                
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    original_price REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    available BOOLEAN DEFAULT 1,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_product_id ON price_history(product_id);
                CREATE INDEX IF NOT EXISTS idx_timestamp ON price_history(timestamp);
            ''')
    
    def add_product(self, url: str, item_id: str, title: str = None, 
                    target_price: float = None, note: str = '') -> int:
        """添加监控商品"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                '''INSERT INTO products (url, item_id, title, target_price, note)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(item_id) DO UPDATE SET
                   url = excluded.url,
                   target_price = COALESCE(excluded.target_price, target_price),
                   note = COALESCE(NULLIF(excluded.note, ''), note),
                   status = 'active'
                   RETURNING id''',
                (url, item_id, title, target_price, note)
            )
            return cursor.fetchone()[0]
    
    def get_products(self, status: str = 'active') -> List[Product]:
        """获取商品列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                'SELECT * FROM products WHERE status = ? ORDER BY created_at DESC',
                (status,)
            ).fetchall()
            return [Product(**dict(row)) for row in rows]
    
    def get_product_by_item_id(self, item_id: str) -> Optional[Product]:
        """根据商品ID获取商品"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                'SELECT * FROM products WHERE item_id = ?',
                (item_id,)
            ).fetchone()
            return Product(**dict(row)) if row else None
    
    def update_product_price(self, product_id: int, price: float):
        """更新商品最新价格"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''UPDATE products 
                   SET last_price = ?, last_check = CURRENT_TIMESTAMP 
                   WHERE id = ?''',
                (price, product_id)
            )
    
    def add_price_record(self, product_id: int, price: float, 
                         original_price: float = None, available: bool = True):
        """添加价格记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''INSERT INTO price_history (product_id, price, original_price, available)
                   VALUES (?, ?, ?, ?)''',
                (product_id, price, original_price, available)
            )
    
    def get_price_history(self, product_id: int, days: int = 7) -> List[PriceRecord]:
        """获取价格历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            since = datetime.now() - timedelta(days=days)
            rows = conn.execute(
                '''SELECT * FROM price_history 
                   WHERE product_id = ? AND timestamp > ?
                   ORDER BY timestamp DESC''',
                (product_id, since.isoformat())
            ).fetchall()
            return [PriceRecord(**dict(row)) for row in rows]
    
    def delete_product(self, product_id: int):
        """删除商品"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM price_history WHERE product_id = ?', (product_id,))
            conn.execute('DELETE FROM products WHERE id = ?', (product_id,))


def extract_item_id(url: str) -> Optional[str]:
    """从淘宝/天猫链接中提取商品ID"""
    patterns = [
        r'item\.taobao\.com/item\.htm.*[?&]id=(\d+)',
        r'detail\.tmall\.com/item\.htm.*[?&]id=(\d+)',
        r'item\.jd\.com/(\d+)',
        r'[?&]itemId=(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def format_price_change(old_price: float, new_price: float) -> str:
    """格式化价格变动"""
    diff = new_price - old_price
    percent = (diff / old_price) * 100 if old_price else 0
    if diff > 0:
        return f"📈 上涨 ¥{diff:.2f} (+{percent:.1f}%)"
    elif diff < 0:
        return f"📉 下跌 ¥{abs(diff):.2f} (-{abs(percent):.1f}%)"
    else:
        return "➡️ 价格不变"


if __name__ == '__main__':
    # 测试数据库
    db = Database()
    print(f"数据库路径: {DB_PATH}")
    print("数据库初始化完成")
    
    # 测试提取商品ID
    test_urls = [
        "https://item.taobao.com/item.htm?id=123456",
        "https://detail.tmall.com/item.htm?id=789012",
    ]
    for url in test_urls:
        item_id = extract_item_id(url)
        print(f"URL: {url} -> 商品ID: {item_id}")
