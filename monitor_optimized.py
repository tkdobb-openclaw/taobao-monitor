#!/usr/bin/env python3
"""
淘宝价格监控 - 优化版
- 定期保存中间结果
- 支持断点续传
- 分批处理
- 更好的错误处理
"""
import subprocess
import re
import time
import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# 配置
CONFIG_PATH = Path(__file__).parent / "config.json"
CHECKPOINT_FILE = Path(__file__).parent / "data" / "checkpoint.json"
RESULTS_FILE = Path(__file__).parent / "data" / "latest_results.json"
LOGS_DIR = Path(__file__).parent / "logs"

def log(msg):
    """打印带时间戳的日志"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def run(cmd, timeout=45):
    """运行命令，带错误处理"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0 and result.stderr:
            log(f"⚠️ 命令警告: {result.stderr[:100]}")
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        log(f"⚠️ 超时: {cmd[:50]}")
        return ""
    except Exception as e:
        log(f"❌ 错误: {e}")
        return ""

def bring_to_front():
    """将 Chrome 窗口带到前台"""
    script = '''
    tell application "Google Chrome"
        activate
    end tell
    '''
    try:
        subprocess.run(['osascript', '-e', script], timeout=5, capture_output=True)
    except:
        pass

def get_skus():
    """获取SKU列表"""
    output = run("""npx agent-browser eval "Array.from(document.querySelectorAll('[class*=\\'valueItem--\\']')).map(el => el.innerText?.trim()).join('|||')" 2>/dev/null""", timeout=15)
    return [s.strip().strip('"') for s in output.split("|||") if s.strip()]

def click_sku(index):
    """点击SKU"""
    run(f"""npx agent-browser eval "document.querySelectorAll('[class*=\\'valueItem--\\']')[{index}].click()" 2>/dev/null""", timeout=10)

def get_price():
    """获取价格"""
    output = run("""npx agent-browser eval "document.querySelector('[class*=\\'Price--\\']')?.innerText || ''" 2>/dev/null""", timeout=10)
    match = re.search(r'[¥￥]\s*([\d,]+\.?\d*)', output)
    return float(match.group(1).replace(',', '')) if match else None

def find_sku_index(skus, target):
    """查找SKU索引"""
    target_clean = target.lower().replace(' ', '').replace('\n', '')
    for i, text in enumerate(skus):
        text_clean = text.lower().replace(' ', '').replace('\n', '')
        if target_clean in text_clean:
            return i
    return -1

def is_tx_version(sku_name):
    """判断是否为TX版本"""
    return 'tx' in sku_name.lower()

def fetch_product(url, target_skus, shop, model, max_retries=2):
    """抓取单个商品，带重试"""
    log(f"【{shop} - {model}】")
    
    for attempt in range(max_retries):
        if attempt > 0:
            log(f"  重试第{attempt}次...")
            time.sleep(3)
        
        # 打开页面
        result = run(f'npx agent-browser open "{url}" 2>/dev/null', timeout=30)
        if not result or 'error' in result.lower():
            log(f"  ⚠️ 页面打开失败")
            continue
            
        time.sleep(3)
        bring_to_front()
        time.sleep(2)
        
        # 检查是否登录页
        title = run("npx agent-browser eval 'document.title' 2>/dev/null", timeout=10)
        if title and '登录' in title:
            log(f"  ❌ 需要登录！")
            return None
        
        # 获取SKU列表
        skus = get_skus()
        log(f"  找到 {len(skus)} 个SKU")
        
        if not skus:
            log(f"  ⚠️ 未找到SKU，可能页面未加载完成")
            continue
        
        # 成功获取SKU，开始抓取
        item_result = {'shop': shop, 'model': model, 'skus': [], 'skus_tx': []}
        
        for target in target_skus:
            idx = find_sku_index(skus, target)
            if idx < 0:
                log(f"  ❌ 未找到: {target}")
                continue
            
            log(f"  点击 [{idx}]: {target}")
            click_sku(idx)
            bring_to_front()
            time.sleep(4)  # 稍微减少等待时间
            
            price = get_price()
            if price:
                log(f"    ✅ ¥{price:.0f}")
                sku_data = {'name': target, 'price': price, 'shop': shop}
                if is_tx_version(target):
                    item_result['skus_tx'].append(sku_data)
                else:
                    item_result['skus'].append(sku_data)
            else:
                log(f"    ❌ 获取失败")
        
        return item_result
    
    log(f"  ❌ 达到最大重试次数，放弃")
    return None

def load_checkpoint():
    """加载检查点"""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE) as f:
                return json.load(f)
        except:
            pass
    return {'completed': [], 'results': []}

def save_checkpoint(completed, results):
    """保存检查点"""
    CHECKPOINT_FILE.parent.mkdir(exist_ok=True)
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump({
            'completed': completed,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)

def save_results(results):
    """保存中间结果"""
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    with open(RESULTS_FILE, 'w') as f:
        json.dump({
            'time': datetime.now().isoformat(),
            'results': results
        }, f, indent=2, ensure_ascii=False)

def print_summary(results):
    """打印汇总表格"""
    by_model = defaultdict(lambda: {'normal': [], 'tx': []})
    
    for r in results:
        model = r['model']
        by_model[model]['normal'].extend(r.get('skus', []))
        by_model[model]['tx'].extend(r.get('skus_tx', []))
    
    print("\n" + "="*70)
    print("📊 价格汇总")
    print("="*70)
    
    for model in ['Perdix', 'Peregrine', 'Teric', 'Tern']:
        if model not in by_model:
            continue
        
        normal_skus = by_model[model]['normal']
        tx_skus = by_model[model]['tx']
        
        if normal_skus:
            print(f"\n【{model} - 普通版】")
            print("-" * 60)
            for sku in sorted(normal_skus, key=lambda x: x['price']):
                print(f"  {sku['shop']:<10} ¥{sku['price']:>8.0f}  {sku['name']}")
        
        if tx_skus:
            print(f"\n【{model} - TX版本】")
            print("-" * 60)
            for sku in sorted(tx_skus, key=lambda x: x['price']):
                print(f"  {sku['shop']:<10} ¥{sku['price']:>8.0f}  {sku['name']}")
    
    print("="*70)

def main():
    # 加载配置
    with open(CONFIG_PATH) as f:
        config = json.load(f)
    
    sku_rules = config.get('sku_rules', {})
    
    # 加载检查点
    checkpoint = load_checkpoint()
    completed_ids = set(checkpoint.get('completed', []))
    results = checkpoint.get('results', [])
    
    log("="*60)
    log(f"📊 淘宝价格监控 - 优化版")
    log(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log(f"商品总数: {len(sku_rules)}")
    log(f"已完成: {len(completed_ids)}")
    log(f"剩余: {len(sku_rules) - len(completed_ids)}")
    log("="*60)
    
    # 检查浏览器
    title = run("npx agent-browser eval 'document.title' 2>/dev/null", timeout=10)
    if not title:
        log("❌ 浏览器未运行！请先运行: npx agent-browser connect http://localhost:9222")
        sys.exit(1)
    
    log(f"✅ 浏览器已连接: {title[:30]}")
    bring_to_front()
    
    # 获取待处理商品
    items = [(item_id, rule) for item_id, rule in sku_rules.items() if item_id not in completed_ids]
    
    if not items:
        log("✅ 所有商品已处理完毕")
        print_summary(results)
        return
    
    log(f"开始处理 {len(items)} 个商品...")
    log("-"*60)
    
    try:
        for i, (item_id, rule) in enumerate(items):
            log(f"进度: {i+1}/{len(items)} (总 {len(completed_ids)+i+1}/{len(sku_rules)})")
            
            shop = rule['shop']
            model = rule['model']
            target_skus = rule['target_skus']
            url = f"https://item.taobao.com/item.htm?id={item_id}"
            
            result = fetch_product(url, target_skus, shop, model)
            
            if result:
                results.append(result)
                completed_ids.add(item_id)
                log(f"✅ 完成: {shop} {model}")
            else:
                log(f"❌ 失败: {shop} {model}")
            
            # 每完成一个商品就保存进度
            save_checkpoint(list(completed_ids), results)
            save_results(results)
            
            # 商品间隔，避免被限流
            if i < len(items) - 1:
                time.sleep(2)
        
    except KeyboardInterrupt:
        log("\n⚠️ 用户中断，已保存进度")
    except Exception as e:
        log(f"\n❌ 发生错误: {e}")
    finally:
        # 最终保存
        save_checkpoint(list(completed_ids), results)
        save_results(results)
        
        # 打印汇总
        print_summary(results)
        
        # 保存到日志目录
        output_file = LOGS_DIR / f"prices_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        LOGS_DIR.mkdir(exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump({
                'time': datetime.now().isoformat(),
                'total': len(sku_rules),
                'success': len(results),
                'results': results
            }, f, indent=2, ensure_ascii=False)
        log(f"💾 结果已保存: {output_file}")
        
        # 清理检查点（如果全部完成）
        if len(completed_ids) >= len(sku_rules):
            if CHECKPOINT_FILE.exists():
                CHECKPOINT_FILE.unlink()
            log("✅ 全部完成，已清理检查点")

if __name__ == '__main__':
    main()
