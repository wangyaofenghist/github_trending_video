#!/bin/bash
# GitHub Trending 视频生成系统 - 启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "====================================="
echo "  GitHub Trending 视频生成系统"
echo "====================================="
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}虚拟环境不存在，正在创建...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}虚拟环境创建完成${NC}"
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖是否已安装
if ! python -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}正在安装依赖...${NC}"
    pip install -r requirements.txt > /dev/null 2>&1
    echo -e "${GREEN}依赖安装完成${NC}"
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}.env 文件不存在，从 .env.example 复制...${NC}"
    cp .env.example .env
    echo -e "${RED}请编辑 .env 文件填入 ANTHROPIC_API_KEY${NC}"
fi

# 检查数据库
if [ ! -f "instance/github_trending.db" ]; then
    echo -e "${YELLOW}数据库不存在，正在初始化...${NC}"
    python -c "from run import app, db; app.app_context().push(); db.create_all(); print('数据库初始化完成')"
fi

# 查找可用端口
find_available_port() {
    local port=$1
    while lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; do
        port=$((port + 1))
    done
    echo $port
}

START_PORT=${PORT:-5000}
AVAILABLE_PORT=$(find_available_port $START_PORT)

if [ "$AVAILABLE_PORT" != "$START_PORT" ]; then
    echo -e "${YELLOW}端口 $START_PORT 被占用，使用端口 $AVAILABLE_PORT${NC}"
    # 更新 run.py 中的端口
    sed -i.bak "s/app.run(host='0.0.0.0', port=[0-9]*,/app.run(host='0.0.0.0', port=$AVAILABLE_PORT,/" run.py
    rm -f run.py.bak
fi

echo ""
echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}  启动成功！${NC}"
echo -e "${GREEN}  访问地址：http://localhost:$AVAILABLE_PORT${NC}"
echo -e "${GREEN}=====================================${NC}"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动应用
python run.py
