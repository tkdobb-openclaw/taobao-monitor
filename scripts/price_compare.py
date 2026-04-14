#!/usr/bin/env python3
"""
价格对比分析工具
读取 data/price_data.json 生成价格对比报表
"""
import json
from pathlib import Path
from datetime import datetime

def load_price_data():
    """加载价格数据"""
    data_file = Path(__file__).parent.parent / "data" / "price_data.json"
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_lowest_price(prices):
    """获取最低价"""
    valid_prices = [p for p in prices if p['price'] is not None]
    if not valid_prices:
        return None
    return min(valid_prices, key=lambda x: x['price'])

def get_price_range(prices):
    """获取价格区间"""
    valid_prices = [p['price'] for p in prices if p['price'] is not None]
    if not valid_prices:
        return None, None
    return min(valid_prices), max(valid_prices)

def generate_text_report():
    """生成文本报表"""
    data = load_price_data()
    
    lines = []
    lines.append("=" * 60)
    lines.append("📊 潜水装备价格对比报表")
    lines.append(f"🕐 更新时间: {data['update_time']}")
    lines.append("=" * 60)
    
    for category in data['categories']:
        lines.append(f"\n{'='*60}")
        lines.append(f"🤿 {category['name']}")
        lines.append("=" * 60)
        
        for product in category['products']:
            model = product['model']
            prices = product['prices']
            
            # 获取最低价
            lowest = get_lowest_price(prices)
            min_price, max_price = get_price_range(prices)
            
            lines.append(f"\n📌 {model}")
            
            if lowest:
                lines.append(f"   💰 最低价: ¥{lowest['price']:,} ({lowest['shop']})")
                if max_price and max_price > min_price:
                    save_amount = max_price - min_price
                    lines.append(f"   📉 最高价差: ¥{save_amount:,}")
            else:
                lines.append("   ❌ 暂无价格数据")
            
            # 显示各店铺价格
            for p in prices:
                shop = p['shop']
                price = p['price']
                discount = p['discount']
                verified = "✅" if p['verified'] else "⏳"
                
                if price:
                    price_str = f"¥{price:,}"
                    if p == lowest:
                        price_str += " 🔥最低"
                    if discount:
                        price_str += f" ({discount})"
                else:
                    price_str = "暂无数据"
                
                lines.append(f"   {verified} {shop}: {price_str}")
    
    # 店铺总结
    lines.append(f"\n{'='*60}")
    lines.append("🏪 店铺价格优势分析")
    lines.append("=" * 60)
    
    shop_lowest_count = {}
    total_products = 0
    
    for category in data['categories']:
        for product in category['products']:
            total_products += 1
            lowest = get_lowest_price(product['prices'])
            if lowest:
                shop = lowest['shop']
                shop_lowest_count[shop] = shop_lowest_count.get(shop, 0) + 1
    
    for shop, count in sorted(shop_lowest_count.items(), key=lambda x: -x[1]):
        percentage = (count / total_products) * 100
        lines.append(f"   🏆 {shop}: {count}/{total_products} 款最低价 ({percentage:.1f}%)")
    
    lines.append(f"\n💡 提示: ✅=已验证价格 ⏳=待补充数据")
    lines.append("=" * 60)
    
    return "\n".join(lines)

def generate_html_report():
    """生成HTML报表"""
    data = load_price_data()
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤿 潜水装备价格对比看板</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ text-align: center; color: white; padding: 40px 20px; }}
        header h1 {{ font-size: 2.5rem; margin-bottom: 10px; }}
        .update-time {{ background: rgba(255,255,255,0.2); display: inline-block; padding: 8px 20px; border-radius: 20px; margin-top: 15px; }}
        .card {{ background: white; border-radius: 16px; padding: 25px; margin-bottom: 25px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
        .card-title {{ font-size: 1.4rem; color: #333; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 3px solid #667eea; display: flex; align-items: center; gap: 10px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #f8f9fa; padding: 15px 12px; text-align: left; font-weight: 600; color: #555; border-bottom: 2px solid #e9ecef; }}
        td {{ padding: 12px; border-bottom: 1px solid #e9ecef; }}
        tr:hover {{ background: #f8f9fa; }}
        .price {{ font-weight: 700; color: #e74c3c; font-size: 1.1rem; }}
        .price-lowest {{ background: #d4edda; color: #155724; padding: 4px 10px; border-radius: 12px; font-weight: 600; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 0.75rem; font-weight: 500; }}
        .badge-verified {{ background: #d4edda; color: #155724; }}
        .badge-pending {{ background: #fff3cd; color: #856404; }}
        .shop-tag {{ display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 0.75rem; font-weight: 500; margin-right: 5px; }}
        .shop-sanqian {{ background: #ff7675; color: white; }}
        .shop-dayang {{ background: #74b9ff; color: white; }}
        .shop-suilaoban {{ background: #00b894; color: white; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-item {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; }}
        .stat-value {{ font-size: 2rem; font-weight: 700; }}
        .stat-label {{ font-size: 0.9rem; opacity: 0.9; margin-top: 5px; }}
        footer {{ text-align: center; color: white; padding: 30px; opacity: 0.8; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤿 潜水装备价格对比看板</h1>
            <p>淘宝潜水电脑表 & 自由潜面镜 实时价格监控</p>
            <div class="update-time">📅 更新时间：{data['update_time'][:10]}</div>
        </header>
"""
    
    # 统计信息
    total_products = sum(len(cat['products']) for cat in data['categories'])
    verified_count = sum(
        1 for cat in data['categories'] 
        for prod in cat['products'] 
        for p in prod['prices'] 
        if p['verified'] and p['price']
    )
    
    html += f"""
        <div class="card">
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-value">{total_products}</div>
                    <div class="stat-label">监控产品</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{verified_count}</div>
                    <div class="stat-label">已验证价格</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{len(data['shops'])}</div>
                    <div class="stat-label">监控店铺</div>
                </div>
            </div>
        </div>
"""
    
    # 产品表格
    for category in data['categories']:
        html += f"""
        <div class="card">
            <h2 class="card-title">🤿 {category['name']}</h2>
            <table>
                <thead>
                    <tr>
                        <th>型号</th>
                        <th>三潜社</th>
                        <th>大洋潜水中心</th>
                        <th>岁老闆</th>
                        <th>最低价</th>
                    </tr>
                </thead>
                <tbody>
"""
        for product in category['products']:
            model = product['model']
            prices = product['prices']
            lowest = get_lowest_price(prices)
            
            html += f"<tr><td><strong>{model}</strong></td>"
            
            for shop in ['三潜社', '大洋潜水中心', '岁老闆']:
                shop_price = next((p for p in prices if p['shop'] == shop), None)
                if shop_price and shop_price['price']:
                    is_lowest = lowest and shop_price == lowest
                    badge_class = "badge-verified" if shop_price['verified'] else "badge-pending"
                    badge_text = "✅" if shop_price['verified'] else "⏳"
                    price_class = "price-lowest" if is_lowest else "price"
                    html += f'<td><span class="{badge_class}">{badge_text}</span> <span class="{price_class}">¥{shop_price["price"]:,}</span></td>'
                else:
                    html += '<td>-</td>'
            
            if lowest:
                html += f'<td><span class="price-lowest">¥{lowest["price"]:,}</span> ({lowest["shop"]})</td>'
            else:
                html += '<td>-</td>'
            
            html += '</tr>'
        
        html += """
                </tbody>
            </table>
        </div>
"""
    
    # 店铺统计
    html += """
        <div class="card">
            <h2 class="card-title">🏪 店铺价格优势</h2>
            <table>
                <thead>
                    <tr>
                        <th>店铺</th>
                        <th>最低价数量</th>
                        <th>占比</th>
                        <th>专注领域</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    shop_lowest_count = {}
    for category in data['categories']:
        for product in category['products']:
            lowest = get_lowest_price(product['prices'])
            if lowest:
                shop = lowest['shop']
                shop_lowest_count[shop] = shop_lowest_count.get(shop, 0) + 1
    
    shop_classes = {
        '三潜社': 'shop-sanqian',
        '大洋潜水中心': 'shop-dayang',
        '岁老闆': 'shop-suilaoban'
    }
    
    for shop_info in data['shops']:
        shop_name = shop_info['name']
        count = shop_lowest_count.get(shop_name, 0)
        percentage = (count / total_products) * 100 if total_products > 0 else 0
        shop_class = shop_classes.get(shop_name, '')
        
        html += f"""
                    <tr>
                        <td><span class="shop-tag {shop_class}">{shop_name}</span></td>
                        <td>{count}/{total_products}</td>
                        <td>{percentage:.1f}%</td>
                        <td>{shop_info['focus']}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <footer>
            <p>🤿 淘宝潜水装备价格监控 | 数据仅供参考，购买前请核实</p>
            <p style="margin-top: 10px; font-size: 0.9rem;">✅=已验证 ⏳=待补充数据</p>
        </footer>
    </div>
</body>
</html>
"""
    
    return html

def update_website():
    """更新网站"""
    import subprocess
    
    # 生成HTML
    html = generate_html_report()
    
    # 保存到 index.html
    index_file = Path(__file__).parent.parent / "index.html"
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✅ index.html 已更新")
    
    # 推送到GitHub
    try:
        subprocess.run(['git', 'add', 'index.html', 'data/price_data.json'], 
                      cwd=index_file.parent, check=True)
        subprocess.run(['git', 'commit', '-m', f'更新价格数据 - {datetime.now().strftime("%Y-%m-%d %H:%M")}'], 
                      cwd=index_file.parent, check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], 
                      cwd=index_file.parent, check=True)
        print("✅ 已推送到 GitHub Pages")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git推送失败: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'text':
            print(generate_text_report())
        elif sys.argv[1] == 'html':
            print(generate_html_report())
        elif sys.argv[1] == 'update':
            update_website()
    else:
        print(generate_text_report())
