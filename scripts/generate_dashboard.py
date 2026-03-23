#!/usr/bin/env python3
"""
可视化价格监控看板生成器 - 带价格变化趋势
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

def load_all_price_history(logs_dir):
    """加载所有历史价格数据"""
    history = defaultdict(lambda: defaultdict(list))  # model -> shop -> [(date, price)]
    
    for log_file in sorted(logs_dir.glob("prices_*.json")):
        try:
            with open(log_file, 'r') as f:
                data = json.load(f)
            
            timestamp = data.get('time', '')
            if not timestamp:
                continue
            
            date_str = timestamp[:10] if isinstance(timestamp, str) else timestamp.strftime('%Y-%m-%d')
            
            for item in data.get('results', []):
                shop = item.get('shop', '')
                model = item.get('model', '')
                
                # 普通版价格（取平均）
                skus = item.get('skus', [])
                if skus:
                    avg_price = sum(s['price'] for s in skus) / len(skus)
                    history[model][shop].append({
                        'date': date_str,
                        'price': avg_price,
                        'type': '普通版'
                    })
                
                # TX版价格
                skus_tx = item.get('skus_tx', [])
                if skus_tx:
                    avg_price_tx = sum(s['price'] for s in skus_tx) / len(skus_tx)
                    history[f"{model} TX"][shop].append({
                        'date': date_str,
                        'price': avg_price_tx,
                        'type': 'TX版'
                    })
        except Exception as e:
            continue
    
    return history

def get_price_change(current, previous):
    """计算价格变化"""
    if not current or not previous:
        return None, None
    change = current - previous
    percent = (change / previous) * 100 if previous else 0
    return change, percent

def generate_dashboard():
    """生成HTML看板"""
    
    db_path = Path(__file__).parent.parent / "data" / "monitor.db"
    logs_dir = Path(__file__).parent.parent / "logs"
    
    # 加载历史数据
    price_history = load_all_price_history(logs_dir)
    
    # 获取最新数据
    latest_file = max(logs_dir.glob("prices_*.json"), key=lambda x: x.stat().st_mtime)
    with open(latest_file, 'r') as f:
        latest_data = json.load(f)
    
    latest_time = latest_data.get('time', '')
    if isinstance(latest_time, str):
        latest_time = latest_time[:16].replace('T', ' ')
    
    # 获取昨日数据（如果有）
    yesterday_file = None
    today = datetime.now().date()
    for log_file in sorted(logs_dir.glob("prices_*.json"), reverse=True):
        file_date = datetime.fromtimestamp(log_file.stat().st_mtime).date()
        if file_date < today:
            yesterday_file = log_file
            break
    
    yesterday_data = {}
    if yesterday_file:
        with open(yesterday_file, 'r') as f:
            yd = json.load(f)
            for item in yd.get('results', []):
                key = f"{item['shop']}_{item['model']}"
                skus = item.get('skus', [])
                if skus:
                    yesterday_data[key] = sum(s['price'] for s in skus) / len(skus)
    
    # 整理今日数据
    today_data = {}
    model_shops = defaultdict(dict)
    
    for item in latest_data.get('results', []):
        shop = item.get('shop', '')
        model = item.get('model', '')
        key = f"{shop}_{model}"
        
        skus = item.get('skus', [])
        if skus:
            today_price = sum(s['price'] for s in skus) / len(skus)
            today_data[key] = today_price
            model_shops[model][shop] = {
                'today': today_price,
                'yesterday': yesterday_data.get(key, None),
                'skus': skus
            }
        
        # TX版
        skus_tx = item.get('skus_tx', [])
        if skus_tx:
            today_price_tx = sum(s['price'] for s in skus_tx) / len(skus_tx)
            model_shops[f"{model} TX"][shop] = {
                'today': today_price_tx,
                'yesterday': None,
                'skus': skus_tx
            }
    
    # 生成HTML
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤿 潜水装备价格监控看板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ text-align: center; color: white; margin-bottom: 30px; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .header .subtitle {{ opacity: 0.9; font-size: 1.1em; }}
        
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
        }}
        .stat-card .number {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .stat-card .label {{ color: #666; margin-top: 5px; }}
        
        .change-summary {{
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .change-summary h2 {{ margin-bottom: 15px; color: #333; }}
        .change-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }}
        .change-item {{
            padding: 15px;
            border-radius: 10px;
            background: #f8f9fa;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .change-up {{ background: #ffebee; color: #c62828; }}
        .change-down {{ background: #e8f5e9; color: #2e7d32; }}
        .change-flat {{ background: #f5f5f5; color: #616161; }}
        .change-arrow {{ font-size: 1.5em; font-weight: bold; }}
        .change-amount {{ font-size: 1.1em; font-weight: bold; }}
        
        .model-section {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .model-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .model-title {{ font-size: 1.5em; color: #333; display: flex; align-items: center; gap: 10px; }}
        .price-range {{ color: #666; font-size: 0.9em; }}
        
        .price-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        .price-table th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #555;
            border-bottom: 2px solid #e9ecef;
        }}
        .price-table td {{
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
        }}
        .price-table tr:hover {{ background: #f8f9fa; }}
        
        .price {{ font-weight: bold; font-size: 1.1em; }}
        .price-low {{ color: #28a745; }}
        .price-high {{ color: #dc3545; }}
        
        .trend {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .trend-up {{ background: #ffebee; color: #c62828; }}
        .trend-down {{ background: #e8f5e9; color: #2e7d32; }}
        .trend-flat {{ background: #e3f2fd; color: #1565c0; }}
        
        .trend-icon {{ font-size: 1.2em; }}
        
        .chart-container {{ height: 300px; margin-top: 20px; }}
        .update-time {{
            text-align: center;
            color: white;
            opacity: 0.8;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤿 Shearwater 潜水表价格监控</h1>
            <div class="subtitle">实时监控淘宝/天猫价格变动 · 自动发现最低价</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="number">20</div>
                <div class="label">监控商品</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(model_shops)}</div>
                <div class="label">型号类别</div>
            </div>
            <div class="stat-card">
                <div class="number">{len([m for m in model_shops.values() for s in m.values() if s.get('yesterday')])}</div>
                <div class="label">有昨日对比</div>
            </div>
            <div class="stat-card">
                <div class="number">{latest_time}</div>
                <div class="label">最后更新</div>
            </div>
        </div>
'''
    
    # 价格变化汇总
    changes = []
    for model, shops in model_shops.items():
        for shop, data in shops.items():
            if data.get('yesterday'):
                change, percent = get_price_change(data['today'], data['yesterday'])
                if change:
                    changes.append({
                        'model': model,
                        'shop': shop,
                        'change': change,
                        'percent': percent,
                        'today': data['today'],
                        'yesterday': data['yesterday']
                    })
    
    if changes:
        html += '''
        <div class="change-summary">
            <h2>📈 今日价格变化</h2>
            <div class="change-grid">
'''
        for c in sorted(changes, key=lambda x: abs(x['change']), reverse=True)[:8]:
            change_class = 'change-up' if c['change'] > 0 else 'change-down' if c['change'] < 0 else 'change-flat'
            arrow = '↑' if c['change'] > 0 else '↓' if c['change'] < 0 else '→'
            html += f'''
                <div class="change-item {change_class}">
                    <div>
                        <strong>{c['model']}</strong> - {c['shop']}<br>
                        <small>¥{c['yesterday']:,.0f} → ¥{c['today']:,.0f}</small>
                    </div>
                    <div class="change-amount">
                        <span class="change-arrow">{arrow}</span>
                        ¥{abs(c['change']):,.0f} ({c['percent']:+.1f}%)
                    </div>
                </div>
'''
        html += '''
            </div>
        </div>
'''
    
    # 为每个型号生成表格
    colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
    
    for idx, (model, shops) in enumerate(sorted(model_shops.items())):
        color = colors[idx % len(colors)]
        
        # 计算价格范围
        prices = [s['today'] for s in shops.values()]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        
        html += f'''
        <div class="model-section">
            <div class="model-header">
                <div class="model-title">
                    <span>⌚</span>
                    <span>Shearwater {model}</span>
                </div>
                <div class="price-range">
                    价格区间: ¥{min_price:,.0f} - ¥{max_price:,.0f} (价差 ¥{max_price-min_price:,.0f})
                </div>
            </div>
            <table class="price-table">
                <thead>
                    <tr>
                        <th>店铺</th>
                        <th>当前价格</th>
                        <th>较昨日</th>
                        <th>历史趋势</th>
                    </tr>
                </thead>
                <tbody>
'''
        
        chart_data = []
        for shop_name in sorted(shops.keys(), key=lambda x: shops[x]['today']):
            shop_data = shops[shop_name]
            today_price = shop_data['today']
            yesterday_price = shop_data.get('yesterday')
            
            # 价格样式
            is_lowest = (today_price == min_price)
            price_class = 'price-low' if is_lowest else 'price-high' if today_price == max_price else ''
            price_display = f'¥{today_price:,.0f} {"⭐" if is_lowest else ""}'
            
            # 涨跌显示
            if yesterday_price:
                change, percent = get_price_change(today_price, yesterday_price)
                if change > 0:
                    trend = f'<span class="trend trend-up"><span class="trend-icon">📈</span> +¥{change:,.0f} (+{percent:.1f}%)</span>'
                elif change < 0:
                    trend = f'<span class="trend trend-down"><span class="trend-icon">📉</span> -¥{abs(change):,.0f} ({percent:.1f}%)</span>'
                else:
                    trend = '<span class="trend trend-flat"><span class="trend-icon">➡️</span> 持平</span>'
            else:
                trend = '<span class="trend trend-flat">无数据</span>'
            
            # 历史趋势
            history_key = model.replace(' TX', '')
            if history_key in price_history and shop_name in price_history[history_key]:
                hist = price_history[history_key][shop_name]
                if len(hist) >= 2:
                    trend_text = f"近{len(hist)}天记录"
                else:
                    trend_text = "数据不足"
                chart_data.append({
                    'label': shop_name,
                    'data': hist,
                    'color': color
                })
            else:
                trend_text = "-"
            
            html += f'''
                    <tr>
                        <td><strong>{shop_name}</strong></td>
                        <td class="price {price_class}">{price_display}</td>
                        <td>{trend}</td>
                        <td>{trend_text}</td>
                    </tr>
'''
        
        html += '''
                </tbody>
            </table>
'''
        
        # 添加趋势图
        if chart_data:
            chart_id = f"chart_{model.replace(' ', '_').replace('/', '_')}"
            # 获取所有日期
            all_dates = sorted(set(
                d['date'] for cd in chart_data for d in cd['data']
            ))[-10:]  # 最近10天
            
            html += f'''
            <div class="chart-container">
                <canvas id="{chart_id}"></canvas>
            </div>
            <script>
                (function() {{
                    const ctx = document.getElementById('{chart_id}').getContext('2d');
                    new Chart(ctx, {{
                        type: 'line',
                        data: {{
                            labels: {all_dates},
                            datasets: [
'''
            for i, cd in enumerate(chart_data[:5]):
                # 按日期整理数据
                price_by_date = {d['date']: d['price'] for d in cd['data']}
                prices = [price_by_date.get(d, None) for d in all_dates]
                
                html += f'''                                {{
                                    label: '{cd['label']}',
                                    data: {prices},
                                    borderColor: '{colors[i % len(colors)]}',
                                    backgroundColor: '{colors[i % len(colors)]}20',
                                    tension: 0.4,
                                    fill: false,
                                    spanGaps: true
                                }}{',' if i < len(chart_data[:5])-1 else ''}
'''
            
            html += f'''                            ]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                title: {{
                                    display: true,
                                    text: '{model} 价格趋势 (最近10天)'
                                }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: false,
                                    ticks: {{
                                        callback: function(value) {{
                                            return '¥' + value.toLocaleString();
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }})();
            </script>
'''
        
        html += '''        </div>
'''
    
    html += f'''
        <div class="update-time">
            最后更新: {latest_time} | 数据自动同步中
        </div>
    </div>
</body>
</html>
'''
    
    # 保存HTML文件
    output_path = Path(__file__).parent.parent / "dashboard.html"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ 看板已生成: {output_path}")
    print(f"   - 包含价格变化趋势")
    print(f"   - 显示涨跌对比 (📈📉)")
    print(f"   - 历史价格图表")
    return output_path

if __name__ == '__main__':
    generate_dashboard()
