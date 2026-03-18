#!/bin/bash
# 安装 cron 定时任务脚本

# 获取脚本所在目录绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Python 路径（可根据实际情况修改）
PYTHON_PATH="/usr/bin/python3"

# 添加到 crontab - 每天早上 9 点执行
CRON_JOB="0 9 * * * cd $PROJECT_DIR && $PYTHON_PATH $SCRIPT_DIR/daily_crawl.py >> $PROJECT_DIR/logs/cron.log 2>&1"

# 检查是否已存在
if crontab -l 2>/dev/null | grep -q "daily_crawl.py"; then
    echo "Cron 任务已存在"
else
    echo "添加 cron 任务..."
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "Cron 任务添加成功！"
    echo "任务内容：每天早上 9 点执行抓取"
fi

# 创建日志目录
mkdir -p "$PROJECT_DIR/logs"

echo ""
echo "手动执行命令：cd $PROJECT_DIR && $PYTHON_PATH $SCRIPT_DIR/daily_crawl.py"
echo "查看 cron 日志：tail -f $PROJECT_DIR/logs/cron.log"
