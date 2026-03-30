#!/bin/bash
# 生成小红书笔记内容

TOPIC="${1:-}"
TYPE="${2:-攻略}"

if [ -z "$TOPIC" ]; then
    echo "用法: ./generate-note.sh '话题' [类型]"
    echo "类型: 攻略|种草|故事|对比"
    exit 1
fi

echo "📝 生成小红书笔记"
echo "=================="
echo "话题: $TOPIC"
echo "类型: $TYPE"
echo ""

# 输出模板结构
case $TYPE in
    "攻略")
        echo "【结构模板 - 攻略类】"
        echo ""
        echo "1️⃣ 痛点引入（1-2句）"
        echo "   示例: 刚学潜水的姐妹注意！OW考证这些坑千万别踩..."
        echo ""
        echo "2️⃣ 个人经历（3-5句）"
        echo "   示例: 我是去年在涛岛考的OW，当时没做功课吃了不少亏..."
        echo ""
        echo "3️⃣ 干货内容（分点）"
        echo "   • 避坑点1: xxx"
        echo "   • 避坑点2: xxx"
        echo "   • 避坑点3: xxx"
        echo ""
        echo "4️⃣ 总结提醒"
        echo "   示例: 记住这几点，考证顺顺利利！"
        echo ""
        echo "5️⃣ CTA引导"
        echo "   示例: 有问题评论区问我～"
        ;;
    "种草")
        echo "【结构模板 - 种草类】"
        echo ""
        echo "1️⃣ 场景化开头"
        echo "2️⃣ 产品亮点（3-5个）"
        echo "3️⃣ 真实体验"
        echo "4️⃣ 购买信息"
        echo "5️⃣ 推荐理由"
        ;;
    "故事")
        echo "【结构模板 - 故事类】"
        echo ""
        echo "1️⃣ 悬念开头"
        echo "2️⃣ 故事发展"
        echo "3️⃣ 转折/冲突"
        echo "4️⃣ 结局/收获"
        echo "5️⃣ 感悟升华"
        ;;
    *)
        echo "【通用结构】"
        echo "开头 → 正文 → 结尾 → CTA"
        ;;
esac

echo ""
echo "💡 提示: 使用 ./optimize-title.sh 来优化标题"
echo "💡 提示: 使用 ./generate-tags.sh 来生成标签"
