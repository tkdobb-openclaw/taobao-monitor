#!/usr/bin/env python3
"""
生成格式化的价格监控报告
格式: 📊 淘宝潜水电脑表价格监控
"""
import json
import sys
from pathlib import Path
from datetime import datetime

def format_price_report(json_file):
    """生成格式化的价格报告"""
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    time_str = data.get('time', '')
    if time_str:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        time_display = dt.strftime('%Y-%m-%d %H:%M')
    else:
        time_display = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    total = data.get('total', 0)
    success = data.get('success', 0)
    
    # 整理数据
    prices = {
        'Perdix': {},
        'Peregrine': {},
        'Peregrine TX': {},
        'Teric': {},
        'Tern': {},
        'Tern TX': {}
    }
    
    for item in data.get('results', []):
        shop = item.get('shop', '')
        model = item.get('model', '')
        
        # 普通版
        for sku in item.get('skus', []):
            key = model
            if key not in prices:
                key = f"{model} 普通版"
            if key in prices:
                if shop not in prices[key]:
                    prices[key][shop] = []
                prices[key][shop].append(sku['price'])
        
        # TX版
        for sku in item.get('skus_tx', []):
            key = f"{model} TX版"
            if key in prices:
                if shop not in prices[key]:
                    prices[key][shop] = []
                prices[key][shop].append(sku['price'])
    
    # 生成报告
    lines = []
    lines.append(f"📊 淘宝潜水电脑表价格监控")
    lines.append(f"🕐 {time_display} | ✅ {success}/{total} 完成")
    
    # 最低价统计
    lowest_count = {}
    max_diff = 0
    max_diff_model = ""
    
    for model_name, shop_prices in prices.items():
        if not shop_prices:
            continue
        
        # 计算每个店铺的平均价格
        shop_avg = {}
        for shop, price_list in shop_prices.items():
            shop_avg[shop] = sum(price_list) / len(price_list)
        
        # 排序
        sorted_shops = sorted(shop_avg.items(), key=lambda x: x[1])
        
        if not sorted_shops:
            continue
        
        # 记录最低价店铺
        lowest_shop = sorted_shops[0][0]
        lowest_count[lowest_shop] = lowest_count.get(lowest_shop, 0) + 1
        
        # 计算价差
        if len(sorted_shops) > 1:
            diff = sorted_shops[-1][1] - sorted_shops[0][1]
            if diff > max_diff:
                max_diff = diff
                max_diff_model = model_name.replace(' 普通版', '').replace(' TX版', ' TX')
        
        # 生成价格行
        price_parts = []
        for shop, price in sorted_shops:
            price_int = int(price)
            is_lowest = (shop == lowest_shop)
            prefix = "▼ " if is_lowest else "▲ " if len(sorted_shops) > 1 else ""
            price_parts.append(f"{prefix}{shop} ¥{price_int:,}")
        
        lines.append(f"\n【{model_name}】")
        lines.append(" | ".join(price_parts))
    
    # 总结
    if lowest_count:
        best_shop = max(lowest_count.items(), key=lambda x: x[1])
        lines.append(f"\n📈 总结: ▼ {best_shop[0]} {best_shop[1]}/{len(prices)}款最低 | 最大价差 {max_diff_model} (¥{int(max_diff):,})")
    
    lines.append(f"💾 结果已保存: {json_file.name}")
    
    return "\n".join(lines)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        json_file = Path(sys.argv[1])
    else:
        # 找最新的价格文件
        logs_dir = Path(__file__).parent.parent / "logs"
        json_files = sorted(logs_dir.glob("prices_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not json_files:
            print("❌ 未找到价格文件")
            sys.exit(1)
        json_file = json_files[0]
    
    report = format_price_report(json_file)
    print(report)
    
    # 同时保存到文件
    output_file = json_file.parent / f"report_{json_file.stem}.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n📝 报告已保存: {output_file}")
