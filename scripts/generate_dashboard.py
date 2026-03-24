#!/usr/bin/env python3
"""
生成价格监控看板 HTML
- 保留原有结构
- 只添加颜色：大洋潜水红色、价格绿红黑、最低价标签
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DB_PATH = Path(__file__).parent.parent / "data" / "monitor.db"
DOCS_PATH = Path(__file__).parent.parent / "docs"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"

def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_price_data():
    config = load_config()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    data = {}
    shops_sql = """
        SELECT '676780234187' as item_id, '大洋潜水' as shop, 'Perdix' as model
        UNION SELECT '676463247224', '塞班户外', 'Perdix'
        UNION SELECT '544005716799', '白鳍鲨', 'Perdix'
        UNION SELECT '675444560376', '岁老板', 'Perdix'
        UNION SELECT '632230014333', '三潜社', 'Perdix'
        UNION SELECT '623907417709', '大洋潜水', 'Peregrine'
        UNION SELECT '624281587175', '塞班户外', 'Peregrine'
        UNION SELECT '623777445212', '白鳍鲨', 'Peregrine'
        UNION SELECT '626899529012', '岁老板', 'Peregrine'
        UNION SELECT '988652922548', '三潜社', 'Peregrine'
        UNION SELECT '584863170468', '大洋潜水', 'Teric'
        UNION SELECT '575523804132', '塞班户外', 'Teric'
        UNION SELECT '570722701118', '白鳍鲨', 'Teric'
        UNION SELECT '667904575973', '岁老板', 'Teric'
        UNION SELECT '629563113404', '三潜社', 'Teric'
        UNION SELECT '753330765355', '大洋潜水', 'Tern'
        UNION SELECT '756509652959', '塞班户外', 'Tern'
        UNION SELECT '753672216139', '白鳍鲨', 'Tern'
        UNION SELECT '749763697229', '岁老板', 'Tern'
        UNION SELECT '899733746263', '三潜社', 'Tern'
    """
    
    cursor = conn.execute(f"""
        SELECT p.item_id, h.price, h.timestamp, s.shop, s.model
        FROM price_history h
        JOIN products p ON h.product_id = p.id
        JOIN ({shops_sql}) s ON p.item_id = s.item_id
        WHERE h.timestamp = (
            SELECT MAX(timestamp) FROM price_history WHERE product_id = p.id
        )
    """)
    
    for row in cursor.fetchall():
        data[row['item_id']] = {
            'shop': row['shop'],
            'model': row['model'],
            'price': row['price'],
            'timestamp': row['timestamp']
        }
    
    conn.close()
    return data

def load_latest_results():
    """从 latest_results.json 加载详细SKU数据"""
    results_file = Path(__file__).parent.parent / "data" / "latest_results.json"
    if results_file.exists():
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 按店铺+型号作为key
            results = {}
            for r in data.get('results', []):
                key = f"{r.get('shop', '')}-{r.get('model', '')}"
                results[key] = r
            return results
    return {}

def generate_html(data):
    # 加载详细结果（包含SKU信息）
    latest_results = load_latest_results()
    config = load_config()
    
    # 按型号分组（区分 TX 版本）
    by_model = defaultdict(list)
    for item_id, info in data.items():
        shop = info['shop']
        base_model = info['model']
        
        # 从 latest_results 获取SKU详情
        key = f"{shop}-{base_model}"
        result = latest_results.get(key, {})
        
        # 获取所有SKU（区分 TX 版本）
        def add_sku(sku_name, price, is_tx=False):
            if is_tx or 'TX' in sku_name.upper():
                model_name = f"{base_model} TX"
            else:
                model_name = base_model
            by_model[model_name].append({
                'shop': shop,
                'sku': sku_name,
                'price': price,
                'timestamp': info['timestamp']
            })
        
        # 从 latest_results 获取SKU
        has_skus = False
        for sku in result.get('skus', []):
            sku_name = sku.get('name', '-')
            price = sku.get('price', info['price'])
            add_sku(sku_name, price, is_tx=False)
            has_skus = True
            
        for sku in result.get('skus_tx', []):
            sku_name = sku.get('name', '-')
            price = sku.get('price', info['price'])
            add_sku(sku_name, price, is_tx=True)
            has_skus = True
        
        # 如果没有SKU详情，从配置获取目标SKU
        if not has_skus:
            rule = config.get('sku_rules', {}).get(item_id, {})
            target_skus = rule.get('target_skus', ['-'])
            for sku_name in target_skus:
                add_sku(sku_name, info['price'])
    
    # 生成表格行
    rows = ""
    # 按顺序显示型号
    model_order = ['Perdix', 'Peregrine', 'Peregrine TX', 'Teric', 'Tern', 'Tern TX']
    for model in model_order:
        if model not in by_model:
            continue
        
        items = by_model[model]
        prices = [i['price'] for i in items]
        min_price = min(prices)
        max_price = max(prices)
        
        rows += f"<tr class='model-header'><td colspan='4'>📱 {model}</td></tr>"
        
        for info in sorted(items, key=lambda x: x['price']):
            shop = info['shop']
            sku = info['sku']
            price = info['price']
            
            # 店铺样式：大洋潜水红色
            if shop == '大洋潜水':
                shop_html = f'<span style="color: #dc3545; font-weight: bold;">{shop}</span>'
            else:
                shop_html = shop
            
            # 价格样式：最低绿、最高红、其他黑
            if price == min_price:
                price_html = f'<span style="color: #28a745; font-weight: bold;">¥{price:.0f}</span> <span style="background: #d4edda; color: #155724; padding: 2px 6px; border-radius: 4px; font-size: 11px;">最低价</span>'
            elif price == max_price:
                price_html = f'<span style="color: #dc3545; font-weight: bold;">¥{price:.0f}</span>'
            else:
                price_html = f'<span style="color: #333;">¥{price:.0f}</span>'
            
            rows += f"""
            <tr>
                <td>{shop_html}</td>
                <td style="font-size: 12px; color: #666;">{sku[:25]}{'...' if len(sku) > 25 else ''}</td>
                <td>{price_html}</td>
                <td class='time'>{info['timestamp'][:16]}</td>
            </tr>
            """
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>淘宝价格监控 - Shearwater 潜水表</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .header .update-time {{ opacity: 0.9; font-size: 14px; }}
        .stats {{
            display: flex;
            justify-content: space-around;
            padding: 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            font-size: 12px;
            color: #6c757d;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .model-header {{
            background: #e9ecef;
            font-weight: bold;
            color: #495057;
        }}
        .model-header td {{
            padding: 10px 15px;
            border-bottom: 2px solid #dee2e6;
        }}
        .time {{
            color: #6c757d;
            font-size: 12px;
        }}
        .footer {{
            padding: 20px;
            text-align: center;
            color: #6c757d;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 淘宝价格监控</h1>
            <div class="update-time">更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(data)}</div>
                <div class="stat-label">监控商品</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(by_model)}</div>
                <div class="stat-label">型号类别</div>
            </div>
            <div class="stat">
                <div class="stat-value">{min([i['price'] for i in data.values()]) if data else 0:.0f}</div>
                <div class="stat-label">最低价格</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>店铺</th>
                    <th>SKU</th>
                    <th>价格</th>
                    <th>更新时间</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        
        <div class="footer">
            数据来源: 淘宝价格监控系统 | 自动更新
        </div>
    </div>
</body>
</html>"""
    return html

def main():
    print("📊 生成价格看板...")
    DOCS_PATH.mkdir(exist_ok=True)
    data = get_price_data()
    html = generate_html(data)
    
    with open(DOCS_PATH / "index.html", 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 看板已生成: {DOCS_PATH / 'index.html'}")
    print(f"📈 共 {len(data)} 个商品价格")

if __name__ == '__main__':
    main()
