#!/bin/bash
# 部署价格监控看板到 GitHub Pages

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 部署价格监控看板..."

# 1. 生成 HTML 看板
echo "📊 生成 HTML 看板..."
python3 scripts/generate_dashboard.py

# 2. 检查是否有 docs 目录变更
if [ -z "$(git status --porcelain docs/ 2>/dev/null)" ]; then
    echo "✅ 看板无变更，无需部署"
    exit 0
fi

# 3. 提交并推送
echo "📤 推送到 GitHub..."
git add docs/
git commit -m "📊 更新价格监控看板 $(date '+%Y-%m-%d %H:%M')" || true
git push origin master

echo "✅ 部署完成！"
echo "🌐 访问地址: https://tkdobb-openclaw.github.io/taobao-monitor/"
