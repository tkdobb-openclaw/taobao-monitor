#!/bin/bash
# 淘宝价格监控定时任务脚本
# 每天 09:00 和 21:00 执行

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../logs/monitor-$(date +%Y%m%d).log"

# 创建日志目录
mkdir -p "$SCRIPT_DIR/../logs"

# 记录执行时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始执行价格监控任务" >> "$LOG_FILE"

# 执行监控检查
cd "$SCRIPT_DIR" && python3 monitor.py check >> "$LOG_FILE" 2>&1

# 记录完成
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 任务执行完成" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
