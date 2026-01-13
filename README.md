# 华为云服务API文档抓取工具

本项目用于抓取华为云各云产品的API文档，并汇总成Markdown格式文件。

## 功能

1. ✅ **第一步**：从 https://www.huaweicloud.com/product/ 和 https://support.huaweicloud.com 获取华为云的全部产品列表
2. ✅ **第二步**：根据每个产品的文档链接，找到其API文档的分类（只保留"API参考" -> "API" -> 子分类的结构）
3. ✅ **第三步**：将API文档分类下的各API按照指定格式输出成Markdown文件

## 项目结构

```
.
├── src/
│   ├── cli.py                      # 统一命令行入口（推荐使用）
│   ├── main.py                     # 第一步入口（已废弃）
│   ├── step2_main.py               # 第二步入口（已废弃）
│   ├── scraper/
│   │   ├── product_fetcher.py      # 产品列表抓取模块
│   │   └── api_category_fetcher.py # API分类抓取模块
│   └── __init__.py
├── tools/                          # 快速安装脚本
│   ├── zh-cn/                      # 中文版安装脚本
│   │   └── quick_install.sh
│   └── en-us/                      # 英文版安装脚本
│       └── quick_install.sh
├── requirements.txt                # Python依赖
├── build.spec                      # PyInstaller打包配置
├── build.sh                        # 打包脚本
├── products.json                   # 抓取的产品列表（运行后生成）
├── api_categories.json             # API分类数据（运行后生成）
└── README.md                       # 项目说明

```

## 快速安装

推荐使用快速安装脚本，一键安装并配置环境：

### 中文版安装脚本

```bash
# 下载并执行安装脚本
curl -fsSL https://raw.githubusercontent.com/Lance52259/huaweicloud-service-xmind-translate/master/tools/zh-cn/quick_install.sh | bash

# 或者先下载再执行
wget https://raw.githubusercontent.com/Lance52259/huaweicloud-service-xmind-translate/master/tools/zh-cn/quick_install.sh
chmod +x quick_install.sh
./quick_install.sh
```

### 英文版安装脚本

```bash
# 下载并执行安装脚本
curl -fsSL https://raw.githubusercontent.com/Lance52259/huaweicloud-service-xmind-translate/master/tools/en-us/quick_install.sh | bash

# 或者先下载再执行
wget https://raw.githubusercontent.com/Lance52259/huaweicloud-service-xmind-translate/master/tools/en-us/quick_install.sh
chmod +x quick_install.sh
./quick_install.sh
```

安装完成后，工具将安装到 `~/.local/share/xmind-translate`，可执行命令 `xmind-translate` 将添加到 `~/.local/bin`。

**注意：** 安装完成后，请运行 `source ~/.bashrc`（或 `source ~/.zshrc`）来刷新环境变量，或者重新打开终端。

## 手动安装

### 安装依赖

```bash
pip install -r requirements.txt
```

### 克隆仓库

```bash
git clone https://github.com/Lance52259/huaweicloud-service-xmind-translate.git
cd huaweicloud-service-xmind-translate
```

## 使用方法

### 使用快速安装后的命令

如果使用快速安装脚本安装，可以直接使用 `xmind-translate` 命令：

```bash
# 扫描所有服务（执行所有步骤）
xmind-translate

# 只扫描指定的服务
xmind-translate --category ecs,obs,rds

# 扫描所有服务，但跳过某些服务
xmind-translate --skip ecs,obs

# 只执行第一步（获取产品列表）
xmind-translate --step 1

# 只执行第二步（获取API分类）
xmind-translate --step 2

# 只执行第三步（生成Markdown）
xmind-translate --step 3

# 搜索产品（当不确定产品代码时）
xmind-translate --search CodeArts_Check
```

### 使用源代码运行

如果手动安装或从源代码运行，使用统一的命令行工具 `src/cli.py`：

```bash
# 扫描所有服务（执行所有步骤）
python3.10 src/cli.py

# 只扫描指定的服务
python3.10 src/cli.py --category ecs,obs,rds

# 扫描所有服务，但跳过某些服务
python3.10 src/cli.py --skip ecs,obs

# 组合使用：扫描ECS和OBS，但跳过某些子服务
python3.10 src/cli.py --category ecs,obs --skip ecs

# 只执行第一步（获取产品列表）
python3.10 src/cli.py --step 1

# 只执行第二步（获取API分类）
python3.10 src/cli.py --step 2

# 只执行第三步（生成Markdown）
python3.10 src/cli.py --step 3

# 指定输出目录（用于products.json和api_categories.json）
python3.10 src/cli.py --output-dir ./output

# 指定Markdown文件输出目录
python3.10 src/cli.py --category ecs --step 3 -o ./markdown_output
python3.10 src/cli.py --category ecs --step 3 --output ./markdown_output

# 搜索产品（当不确定产品代码时）
python3.10 src/cli.py --search CodeArts_Check
python3.10 src/cli.py -S check
python3.10 src/cli.py --search 数据库
```

### 产品搜索功能

当您不确定产品的代码时，可以使用 `--search` 或 `-S` 参数进行模糊搜索：

```bash
# 搜索 CodeArts Check
python3.10 src/cli.py --search CodeArts_Check

# 搜索包含 "check" 的产品（使用简写）
python3.10 src/cli.py -S check

# 搜索中文关键词
python3.10 src/cli.py --search 数据库
```

搜索功能会：
1. **自动执行全局扫描**：自动执行第一步获取最新的产品列表（不保存文件，仅用于搜索）
2. 在产品代码和产品名称中搜索匹配项
3. 按匹配度排序显示结果（完全匹配 > 前缀匹配 > 包含匹配）
4. 显示产品代码、产品名称和文档URL
5. 提供使用产品代码的示例命令

**注意：** 搜索功能不需要预先运行步骤1，会自动获取最新的产品列表进行搜索。

**示例输出：**
```
搜索关键词: CodeArts_Check

找到 13 个匹配的产品：

 1. 产品代码: codecheck
    产品名称: 代码检查 CodeArts Check基于云端实现代码质量管理的服务
    文档URL: https://support.huaweicloud.com/codecheck/index.html

使用方法：
  使用产品代码 'codecheck' 来指定该服务：
  python3.10 src/cli.py --category codecheck
```

**注意：** 
- `-S` 是 `--search` 的简写，用于搜索产品
- `-s` 是 `--skip` 的简写，用于跳过某些服务

### 命令行参数

- `--category, -c`: 指定要扫描的服务（产品代码），多个用逗号分隔
- `--skip, -s`: 指定要跳过的服务（产品代码），多个用逗号分隔
- `--search, -S`: 模糊搜索产品，输出匹配的产品名称和描述（用于查找产品代码）
- `--step`: 指定执行的步骤（1=获取产品列表，2=获取API分类，3=生成Markdown）
- `--output-dir`: 输出目录（默认：当前目录），用于products.json和api_categories.json
- `--output, -o`: Markdown文件输出目录（默认：当前执行命令的目录）
- `--products-file`: 产品列表文件路径（默认：products.json）
- `--categories-file`: API分类文件路径（默认：api_categories.json）

### 输出示例

**步骤1输出：**
```
步骤1: 获取产品列表
成功获取 220 个产品
指定扫描服务: ecs,obs
过滤后剩余 2 个产品
产品列表已保存到: products.json
```

**步骤2输出：**
```
步骤2: 获取API文档分类
共 2 个产品需要处理

  1. 处理 弹性云服务器 ECS
     产品代码: ecs
     ✓ 找到 19 个分类
```

**步骤3输出：**
```
步骤3: 生成Markdown文件
共 1 个产品需要生成Markdown

✓ 已保存: ecs.md (9731 字符)
```

### 旧版入口（已废弃）

- `src/main.py` - 第一步入口（已废弃，请使用 `src/cli.py`）
- `src/step2_main.py` - 第二步入口（已废弃，请使用 `src/cli.py`）

## 数据格式

`products.json` 文件包含产品列表，每个产品包含以下字段：

```json
{
  "name": "弹性云服务器 ECS可随时自动获取、弹性伸缩的云服务器",
  "url": "https://www.huaweicloud.com/product/ecs.html",
  "doc_url": "https://support.huaweicloud.com/ecs/index.html",
  "product_code": "ecs",
  "source": "product_page"
}
```

## 打包为可执行文件

### 使用PyInstaller打包

```bash
# 安装PyInstaller（如果未安装）
pip install pyinstaller

# 使用打包脚本
./build.sh

# 或手动打包
pyinstaller --clean build.spec
```

打包完成后，可执行文件位于 `dist/huaweicloud-api-scraper`

### 使用打包后的可执行文件

```bash
# 查看帮助
./dist/huaweicloud-api-scraper --help

# 扫描所有服务
./dist/huaweicloud-api-scraper

# 只扫描指定服务
./dist/huaweicloud-api-scraper --category ecs,obs

# 跳过某些服务
./dist/huaweicloud-api-scraper --skip ecs,obs
```

## 开发进度

- [x] 第一步：获取华为云产品列表
- [x] 第二步：获取每个产品的API文档分类（只保留"API参考" -> "API" -> 子分类）
- [x] 第三步：生成Markdown格式的API文档汇总
- [x] 命令行参数支持（--category, --skip）
- [x] 打包支持（PyInstaller）

## 数据格式

### products.json
包含产品列表，每个产品包含：
- `name`: 产品名称
- `url`: 产品页面URL
- `doc_url`: 产品文档URL
- `product_code`: 产品代码
- `source`: 数据来源

### api_categories.json
包含各产品的API分类结构，每个产品包含：
- `product_code`: 产品代码
- `api_doc_url`: API文档URL
- `categories`: 分类列表（只包含"API参考" -> "API" -> 子分类），每个分类包含：
  - `name`: 分类名称
  - `url`: 分类URL
  - `category_id`: 分类ID
  - `subcategories`: 子分类列表
  - `apis`: API列表

### 生成的Markdown文件
每个产品生成一个Markdown文件（`{product_code}.md`），格式为：
- 一级标题：产品简称（如 `# ECS`）
- 二级标题：API分类（如 `## 生命周期管理`）
- 三级标题：子分类（如果有，如 `### BCS管理`）
- API列表：格式为 `- [API名称 URI](API链接地址)`

**示例：**
```markdown
# ECS

## 生命周期管理

- [创建云服务器 POST /v1.1/{project_id}/cloudservers](https://support.huaweicloud.com/api-ecs/ecs_02_0101.html)

- [删除云服务器 POST /v1/{project_id}/cloudservers/delete](https://support.huaweicloud.com/api-ecs/ecs_02_0103.html)
```
