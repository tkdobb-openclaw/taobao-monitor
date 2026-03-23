---
name: taobao-monitor
description: 淘宝/天猫价格监控系统，使用 agent-browser 自动抓取价格，支持定时监控、价格变动通知、目标价提醒
---

# 淘宝价格监控

自动监控淘宝、天猫商品价格变动，每天两次检查，价格变动或达到目标价时自动发送飞书通知。

## 工作原理

使用 `agent-browser` + 淘宝登录态，绕过反爬机制自动抓取价格。

**首次使用需要：**
1. 用 agent-browser 登录淘宝（一次即可）
2. 保存登录态
3. 之后全自动抓取

## 首次配置（必须）

### 1. 登录淘宝并保存登录态

```bash
# 打开可视化浏览器登录淘宝
cd ~/.openclaw/workspace/skills/taobao-monitor
npx agent-browser --headed open "https://login.taobao.com"

# 扫码/密码登录成功后，保存登录态
npx agent-browser state save data/taobao_auth.json
```

### 2. 配置飞书通知（可选）

编辑 `config.json`：

```json
{
  "app_id": "cli_a933ae5b17b9dcd4",
  "app_secret": "pRrUlxBcvBNC4woA2abEHd3fVOyObxaT",
  "chat_id": "oc_04717cb2f786e5e9a2869f84840924d8"
}
```

## 使用方法

### 添加监控商品

```bash
python3 scripts/monitor.py add "https://item.taobao.com/item.htm?id=624281587175" \
  --target 3000 \
  --note "Shearwater 潜水表"
```

### 手动检查价格

```bash
# 检查所有商品
python3 scripts/monitor.py check

# 只检查指定商品
python3 scripts/monitor.py check --id 1

# 检查但不发送通知（测试用）
python3 scripts/monitor.py check --no-notify
```

### 查看监控列表

```bash
python3 scripts/monitor.py list
```

### 删除监控

```bash
python3 scripts/monitor.py remove 1
```

## 设置定时任务

每天 09:00 和 21:00 自动检查：

```bash
crontab -e

# 添加以下行
0 9,21 * * * cd ~/.openclaw/workspace/skills/taobao-monitor && python3 scripts/monitor.py check >> logs/cron.log 2>&1
```

## 飞书通知示例

**价格变动通知：**
```
📉 价格监控告警 - Shearwater 潜水表

Shearwater Peregrine TX
📉 价格下跌: ¥3360 → ¥2999
💰 变动: ¥-361 (-10.7%)
🎯 目标价: ¥3000 ✅ 已达到!

[查看商品](https://item.taobao.com/item.htm?id=624281587175)
```

**每日汇总报告：**
```
📊 价格监控日报 - 2024-03-17 21:00

📊 统计摘要
• 监控商品: 5 个
• 成功抓取: 5 个
• 价格变动: 1 个
• 达到目标价: 1 个

💰 价格变动明细
• Shearwater潜水表: ¥3360 → ¥2999 📉

🎯 目标价提醒
• ✅ Shearwater潜水表: 当前¥2999 ≤ 目标¥3000
```

## 登录态失效处理

如果提示需要重新登录：

```bash
# 重新登录
npx agent-browser --headed open "https://login.taobao.com"
# 登录成功后
npx agent-browser state save data/taobao_auth.json
```

建议每月重新登录一次，避免登录态过期。

## 故障排查

**问题1: 无法抓取价格**
- 检查登录态是否有效：`npx agent-browser state load data/taobao_auth.json`
- 重新登录淘宝并保存状态

**问题2: 飞书通知未收到**
- 检查 config.json 中的 app_id/app_secret/chat_id
- 确认机器人已添加到群聊并有发送消息权限

**问题3: 价格显示不正确**
- 淘宝页面结构变化，可能需要更新选择器
- 在 scripts/crawler_agent_browser.py 中修改 price_selectors

## 支持的链接格式

- 淘宝: `https://item.taobao.com/item.htm?id=xxxx`
- 天猫: `https://detail.tmall.com/item.htm?id=xxxx`

## 数据存储

- 数据库: `data/monitor.db` (SQLite)
- 登录态: `data/taobao_auth.json`
- 日志: `logs/cron.log`

## 技术架构

```
定时任务 (cron)
    ↓
monitor.py
    ↓
crawler_agent_browser.py (使用 agent-browser)
    ↓
加载 taobao_auth.json → 访问商品页 → 提取价格
    ↓
notifier.py → 飞书群通知
```

## 更新日志

- **2026-03-17** - 使用 agent-browser 重写，解决淘宝反爬问题
- **2026-03-17** - 支持手动录入模式（备用）
- **2026-03-17** - 初始版本，使用 Playwright（被淘宝拦截）
