#!/bin/bash
# 小红书标签生成器

KEYWORDS="${1:-}"

if [ -z "$KEYWORDS" ]; then
    echo "用法: ./generate-tags.sh '关键词1 关键词2 关键词3'"
    echo "示例: ./generate-tags.sh '潜水 OW 考证 泰国'"
    exit 1
fi

echo "🏷️ 小红书标签生成"
echo "=================="
echo "关键词: $KEYWORDS"
echo ""

# 基础标签库
DIVE_TAGS="#潜水 #OW考证 #AOW #潜水证 #潜水考证 #潜水入门 #潜水新手 #潜水攻略"
TRAVEL_TAGS="#泰国潜水 #涛岛 #仙本那 #马尔代夫 #潜水旅行 #海岛游 #出境游"
EQUIP_TAGS="#潜水装备 #面镜 #湿衣 #BCD #调节器 #潜水电脑表 #装备推荐"
LIFE_TAGS="#潜水生活 #水下世界 #海洋动物 #蓝色鸦片 #潜水员 #极限运动"

# 根据关键词匹配标签
echo "【推荐标签组合】"
echo ""
echo "🔥 精准标签（必加）:"
echo "   $DIVE_TAGS" | fold -s -w 50 | head -3

echo ""
echo "🌊 场景标签:"
echo "   $TRAVEL_TAGS" | fold -s -w 50 | head -2

echo ""
echo "💡 热门标签:"
echo "   #旅行攻略 #避坑指南 #干货分享 #真实体验"

echo ""
echo "✨ 品牌/个人标签（建议固定）:"
echo "   #大洋潜水 #潜水日记 #[你的名字]"

echo ""
echo "【完整标签示例】"
echo "   #潜水 #OW考证 #涛岛潜水 #潜水攻略 #避坑指南 #旅行攻略 #干货分享 #真实体验 #大洋潜水"
echo ""
echo "💡 标签规则:"
echo "   • 总共9个标签（小红书上限）"
echo "   • 2-3个精准标签 + 2-3个热门标签 + 2-3个长尾标签 + 1个个人标签"
