#!/bin/bash
# 打包脚本

set -e

echo "开始打包华为云API文档抓取工具..."

# 检查是否安装了PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: 未找到PyInstaller，请先安装:"
    echo "  pip install pyinstaller"
    exit 1
fi

# 创建构建目录
BUILD_DIR="build"
DIST_DIR="dist"

# 清理旧的构建文件
if [ -d "$BUILD_DIR" ]; then
    echo "清理旧的构建文件..."
    rm -rf "$BUILD_DIR"
fi

if [ -d "$DIST_DIR" ]; then
    echo "清理旧的发布文件..."
    rm -rf "$DIST_DIR"
fi

# 执行打包
echo "开始打包..."
pyinstaller --clean build.spec

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================================================="
    echo "打包成功!"
    echo "=================================================================================="
    echo ""
    echo "可执行文件位置: $DIST_DIR/huaweicloud-api-scraper"
    echo ""
    echo "使用方法:"
    echo "  ./dist/huaweicloud-api-scraper --help"
    echo "  ./dist/huaweicloud-api-scraper --category ecs,obs"
    echo "  ./dist/huaweicloud-api-scraper --skip ecs,obs"
else
    echo "打包失败!"
    exit 1
fi
