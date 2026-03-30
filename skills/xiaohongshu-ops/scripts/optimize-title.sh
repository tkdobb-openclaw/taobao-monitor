#!/bin/bash
# 标题优化器 - 基于小红书爆款标题公式

TITLE="${1:-}"

if [ -z "$TITLE" ]; then
    echo "用法: ./optimize-title.sh '原标题'"
    exit 1
fi

echo "🎯 标题优化建议"
echo "================"
echo "原标题: $TITLE"
echo ""

echo "【优化方向】"
echo ""

# 数字法
if [[ ! "$TITLE" =~ [0-9] ]]; then
    echo "1️⃣ 数字法 - 增加具体数字"
    echo "   原: $TITLE"
    echo "   改: 3个技巧｜$TITLE"
    echo "   改: 5年经验总结：$TITLE"
    echo ""
fi

# 身份标签法
echo "2️⃣ 身份法 - 增加目标人群"
echo "   改: 新手必看！$TITLE"
echo "   改: 打工人专属｜$TITLE"
echo "   改: 宝妈收藏✨ $TITLE"
echo ""

# emoji法
echo "3️⃣ emoji法 - 增加视觉符号"
echo "   改: 🚨$TITLE"
echo "   改: 💡$TITLE"
echo "   改: ✨$TITLE｜亲测有效"
echo ""

# 悬念法
echo "4️⃣ 悬念法 - 制造好奇心"
echo "   改: 后悔没早知道！$TITLE"
echo "   改: 终于懂了：$TITLE"
echo "   改: 99%的人都不知道的$TITLE"
echo ""

# 对比法
echo "5️⃣ 对比法 - 制造反差"
echo "   改: 花X万买来的教训：$TITLE"
echo "   改: 别再做XX了！$TITLE"
echo ""

echo "【组合示例】"
echo "   🚨3个潜水考证避坑技巧｜新手必看"
echo "   💡5年潜导经验：OW考证千万别这样"
echo "   ✨后悔没早知道！涛岛考证真实体验"
