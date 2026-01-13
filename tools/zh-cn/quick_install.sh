#!/bin/bash

# 华为云API文档抓取工具部署脚本
# 通过 git clone 下载最新代码并部署到本地

set -e  # 遇到错误就退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
REPO_URL="https://github.com/Lance52259/huaweicloud-service-xmind-translate.git"
INSTALL_BASE_DIR="$HOME/.local"
INSTALL_DIR="$INSTALL_BASE_DIR/bin"
TOOL_DIR="$INSTALL_BASE_DIR/share/xmind-translate"
SCRIPT_NAME="xmind-translate"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  华为云API文档抓取工具${NC}"
echo -e "${BLUE}  本地部署工具${NC}"
echo -e "${BLUE}========================================${NC}"

# 检查必要的工具
echo -e "${YELLOW}检查系统环境...${NC}"

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 python3${NC}"
    echo "请先安装 Python 3.6 或更高版本"
    exit 1
fi
echo -e "${GREEN}✓ Python3: $(python3 --version)${NC}"

# 检查 Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 git${NC}"
    echo "请先安装 Git"
    exit 1
fi
echo -e "${GREEN}✓ Git: $(git --version)${NC}"

# 检查 pip3
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠ 警告: 未找到 pip3，尝试使用 python3 -m pip${NC}"
    if ! python3 -m pip --version &> /dev/null; then
        echo -e "${RED}❌ 错误: 未找到 pip${NC}"
        echo "请先安装 pip"
        exit 1
    fi
    PIP_CMD="python3 -m pip"
else
    PIP_CMD="pip3"
fi
echo -e "${GREEN}✓ pip: $($PIP_CMD --version)${NC}"

# 创建必要目录
echo -e "${YELLOW}创建目录结构...${NC}"
mkdir -p "$INSTALL_DIR"
mkdir -p "$(dirname "$TOOL_DIR")"

# 删除旧版本（如果存在）
if [ -d "$TOOL_DIR" ]; then
    echo -e "${YELLOW}发现现有安装，正在更新...${NC}"
    rm -rf "$TOOL_DIR"
fi

# 克隆代码仓库
echo -e "${YELLOW}克隆最新代码...${NC}"
echo "仓库地址: $REPO_URL"
echo "安装位置: $TOOL_DIR"

if git clone "$REPO_URL" "$TOOL_DIR"; then
    echo -e "${GREEN}✓ 代码下载成功${NC}"
else
    echo -e "${RED}❌ 代码下载失败${NC}"
    exit 1
fi

# 验证 Python 脚本
echo -e "${YELLOW}验证工具...${NC}"
PYTHON_SCRIPT="$TOOL_DIR/src/cli.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}❌ 未找到 Python 脚本: $PYTHON_SCRIPT${NC}"
    exit 1
fi

# 安装 Python 依赖
echo -e "${YELLOW}安装 Python 依赖...${NC}"
REQUIREMENTS_FILE="$TOOL_DIR/requirements.txt"

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo -e "${RED}❌ 未找到依赖文件: $REQUIREMENTS_FILE${NC}"
    exit 1
fi

if $PIP_CMD install -r "$REQUIREMENTS_FILE" --quiet --user; then
    echo -e "${GREEN}✓ 依赖安装成功${NC}"
else
    echo -e "${YELLOW}⚠ 警告: 依赖安装可能有问题，但继续执行${NC}"
fi

# 测试脚本是否可执行
if python3 "$PYTHON_SCRIPT" --help > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 工具验证成功${NC}"
else
    echo -e "${YELLOW}⚠ 警告: 工具验证返回非零退出码（这可能是正常的）${NC}"
fi

# 创建可执行的包装脚本
echo -e "${YELLOW}创建可执行命令...${NC}"
WRAPPER_SCRIPT="$INSTALL_DIR/$SCRIPT_NAME"

cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash

# 华为云API文档抓取工具包装脚本
# 自动生成 - $(date)

TOOL_SCRIPT="$TOOL_DIR/src/cli.py"

# 检查脚本是否存在
if [ ! -f "\$TOOL_SCRIPT" ]; then
    echo "错误: 华为云API文档抓取工具脚本未找到"
    echo "脚本路径: \$TOOL_SCRIPT"
    echo "请重新运行部署脚本"
    exit 1
fi

# 切换到工具目录以确保相对导入正常工作
cd "\$TOOL_DIR"

# 执行工具，传递所有参数
exec python3 "\$TOOL_SCRIPT" "\$@"
EOF

# 设置执行权限
chmod +x "$WRAPPER_SCRIPT"
echo -e "${GREEN}✓ 可执行命令已创建: $WRAPPER_SCRIPT${NC}"

# 检查并配置 PATH
echo -e "${YELLOW}配置环境变量...${NC}"
PATH_ALREADY_SET=false

# 检查当前 PATH 是否包含 install directory
if [[ ":$PATH:" == *":$INSTALL_DIR:"* ]]; then
    PATH_ALREADY_SET=true
    echo -e "${GREEN}✓ PATH 已包含 $INSTALL_DIR${NC}"
fi

# 确定需要配置的shell配置文件列表
SHELL_CONFIGS=()
if [ -n "$BASH_VERSION" ]; then
    # Bash shell - 配置多个文件以确保兼容性
    [ -f "$HOME/.bashrc" ] && SHELL_CONFIGS+=("$HOME/.bashrc")
    [ -f "$HOME/.bash_profile" ] && SHELL_CONFIGS+=("$HOME/.bash_profile")
    # 如果都不存在，创建 .bashrc
    if [ ${#SHELL_CONFIGS[@]} -eq 0 ]; then
        touch "$HOME/.bashrc"
        SHELL_CONFIGS+=("$HOME/.bashrc")
    fi
elif [ -n "$ZSH_VERSION" ]; then
    # Zsh shell
    [ -f "$HOME/.zshrc" ] && SHELL_CONFIGS+=("$HOME/.zshrc")
    if [ ${#SHELL_CONFIGS[@]} -eq 0 ]; then
        touch "$HOME/.zshrc"
        SHELL_CONFIGS+=("$HOME/.zshrc")
    fi
else
    # 其他shell或未知shell
    [ -f "$HOME/.profile" ] && SHELL_CONFIGS+=("$HOME/.profile")
    [ -f "$HOME/.bashrc" ] && SHELL_CONFIGS+=("$HOME/.bashrc")
    if [ ${#SHELL_CONFIGS[@]} -eq 0 ]; then
        touch "$HOME/.profile"
        SHELL_CONFIGS+=("$HOME/.profile")
    fi
fi

# 为每个配置文件添加PATH（如果需要）
PATH_ADDED=false
for SHELL_CONFIG in "${SHELL_CONFIGS[@]}"; do
    # 检查配置文件中是否已有 PATH 设置
    CONFIG_HAS_PATH=false
    if [ -f "$SHELL_CONFIG" ] && grep -q "$INSTALL_DIR" "$SHELL_CONFIG" 2>/dev/null; then
        CONFIG_HAS_PATH=true
    fi
    
    # 添加 PATH 到配置文件（如果需要）
    if [ "$CONFIG_HAS_PATH" = false ]; then
        echo -e "${YELLOW}添加 PATH 到 $SHELL_CONFIG${NC}"
        {
            echo ""
            echo "# 华为云API文档抓取工具 - $(date)"
            echo "export PATH=\"$INSTALL_DIR:\$PATH\""
        } >> "$SHELL_CONFIG"
        echo -e "${GREEN}✓ PATH 已添加到 $SHELL_CONFIG${NC}"
        PATH_ADDED=true
    else
        echo -e "${GREEN}✓ PATH 配置已存在于 $SHELL_CONFIG${NC}"
    fi
done

# 临时设置 PATH（如果有添加配置）
if [ "$PATH_ADDED" = true ]; then
    export PATH="$INSTALL_DIR:$PATH"
fi

# 最终测试
echo -e "${YELLOW}进行最终测试...${NC}"
if "$WRAPPER_SCRIPT" --help > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 部署成功！${NC}"
else
    echo -e "${YELLOW}⚠ 警告: 最终测试返回非零退出码（这可能是正常的）${NC}"
fi

# 显示部署信息
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}安装信息:${NC}"
echo "  工具目录: $TOOL_DIR"
echo "  可执行文件: $WRAPPER_SCRIPT"
echo ""
echo -e "${YELLOW}使用方法:${NC}"
echo "  xmind-translate                    # 扫描所有服务"
echo "  xmind-translate --category ecs,obs # 只扫描指定的服务"
echo "  xmind-translate --skip ecs,obs     # 扫描所有服务，但跳过某些服务"
echo "  xmind-translate --step 1           # 只执行第一步（获取产品列表）"
echo "  xmind-translate --step 2           # 只执行第二步（获取API分类）"
echo "  xmind-translate --step 3           # 只执行第三步（生成Markdown）"
echo "  xmind-translate --search CodeArts  # 搜索产品"
echo ""
echo -e "${YELLOW}示例:${NC}"
echo "  xmind-translate --category ecs"
echo "  xmind-translate --category ecs,obs,rds --step 3"
echo "  xmind-translate --search CodeArts_Check"
echo ""
echo -e "${YELLOW}环境配置:${NC}"
if [ "$PATH_ALREADY_SET" = true ]; then
    echo "  ✓ PATH 已配置，可直接使用命令"
else
    echo "  ⚠️  请运行以下命令激活环境:"
    for SHELL_CONFIG in "${SHELL_CONFIGS[@]}"; do
        echo "     source $SHELL_CONFIG"
    done
    echo "  或者重新打开终端"
    echo ""
    echo "  临时使用: 当前终端已可直接使用 xmind-translate 命令"
fi

echo ""
echo -e "${YELLOW}测试安装:${NC}"
if command -v xmind-translate &> /dev/null; then
    echo "  ✅ xmind-translate 命令可用"
    echo ""
    echo -e "${YELLOW}快速测试:${NC}"
    echo "  运行: xmind-translate --help"
else
    echo "  ⚠️  请运行以下命令刷新环境:"
    for SHELL_CONFIG in "${SHELL_CONFIGS[@]}"; do
        echo "     source $SHELL_CONFIG"
    done
fi

echo ""
echo -e "${GREEN}开始使用华为云API文档抓取工具吧！${NC}"

