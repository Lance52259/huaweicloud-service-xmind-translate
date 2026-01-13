#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为云API文档抓取工具命令行接口
"""

import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scraper.product_fetcher import ProductFetcher
from src.scraper.api_category_fetcher import APICategoryFetcher
from src.markdown_generator import MarkdownGenerator


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='华为云API文档抓取工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描所有服务
  python src/cli.py

  # 只扫描ECS和OBS服务
  python src/cli.py --category ecs,obs

  # 扫描所有服务，但跳过ECS和OBS
  python src/cli.py --skip ecs,obs

  # 组合使用：扫描ECS和OBS，但跳过某些子服务
  python src/cli.py --category ecs,obs --skip ecs

  # 搜索产品（模糊匹配）
  python src/cli.py --search CodeArts_Check
  python src/cli.py -S check
  python src/cli.py --search 数据库
        """
    )
    
    parser.add_argument(
        '--category', '-c',
        type=str,
        default=None,
        help='指定要扫描的服务（产品代码），多个用逗号分隔，如: ecs,obs,rds'
    )
    
    parser.add_argument(
        '--skip', '-s',
        type=str,
        default=None,
        help='指定要跳过的服务（产品代码），多个用逗号分隔，如: ecs,obs'
    )
    
    parser.add_argument(
        '--search', '-S',
        type=str,
        default=None,
        help='模糊搜索产品，输出匹配的产品名称和描述，如: --search CodeArts_Check'
    )
    
    parser.add_argument(
        '--step',
        type=int,
        choices=[1, 2, 3],
        default=None,
        help='指定执行的步骤：1=获取产品列表，2=获取API分类，3=生成Markdown（默认执行所有步骤）'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='输出目录（默认：当前目录），用于products.json和api_categories.json'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Markdown文件输出目录（默认：当前执行命令的目录）'
    )
    
    parser.add_argument(
        '--products-file',
        type=str,
        default='products.json',
        help='产品列表文件路径（默认：products.json）'
    )
    
    parser.add_argument(
        '--categories-file',
        type=str,
        default='api_categories.json',
        help='API分类文件路径（默认：api_categories.json）'
    )
    
    return parser.parse_args()


def filter_products(products, category_filter=None, skip_filter=None):
    """
    过滤产品列表
    
    Args:
        products: 产品列表
        category_filter: 要包含的产品代码列表（None表示全部）
        skip_filter: 要跳过的产品代码列表（None表示不跳过）
        
    Returns:
        过滤后的产品列表
    """
    filtered = []
    
    # 解析过滤器
    category_codes = None
    if category_filter:
        category_codes = [c.strip().lower() for c in category_filter.split(',') if c.strip()]
    
    skip_codes = None
    if skip_filter:
        skip_codes = [c.strip().lower() for c in skip_filter.split(',') if c.strip()]
    
    for product in products:
        product_code = product.get('product_code', '').lower()
        
        # 如果指定了category，只包含指定的产品
        if category_codes and product_code not in category_codes:
            continue
        
        # 如果指定了skip，跳过这些产品
        if skip_codes and product_code in skip_codes:
            continue
        
        filtered.append(product)
    
    return filtered


def search_products(search_term, products_data):
    """
    模糊搜索产品
    
    Args:
        search_term: 搜索关键词
        products_data: 产品列表
        
    Returns:
        list: 匹配的产品列表，按匹配度排序
    """
    import re
    
    search_term_lower = search_term.lower()
    search_words = search_term_lower.replace('_', ' ').replace('-', ' ').split()
    
    scored_products = []
    
    for product in products_data:
        product_name = product.get('name', '')
        product_code = product.get('product_code', '')
        
        name_lower = product_name.lower()
        code_lower = product_code.lower()
        
        score = 0
        
        # 完全匹配产品代码（最高优先级）
        if search_term_lower == code_lower:
            score += 1000
        elif code_lower.startswith(search_term_lower):
            score += 500
        elif search_term_lower in code_lower:
            score += 200
        
        # 完全匹配产品名称
        if search_term_lower == name_lower:
            score += 800
        elif name_lower.startswith(search_term_lower):
            score += 400
        elif search_term_lower in name_lower:
            score += 100
        
        # 单词匹配
        for word in search_words:
            if word in code_lower:
                score += 50
            if word in name_lower:
                score += 30
        
        # 如果匹配到，添加到结果列表
        if score > 0:
            scored_products.append({
                'product': product,
                'score': score
            })
    
    # 按分数排序
    scored_products.sort(key=lambda x: x['score'], reverse=True)
    
    return [item['product'] for item in scored_products]


def main():
    """主函数"""
    args = parse_args()
    
    # 如果指定了 --search，执行搜索并退出
    if args.search:
        print("=" * 80)
        print("产品搜索")
        print("=" * 80)
        print(f"\n搜索关键词: {args.search}\n")
        
        # 自动执行第一步获取产品列表（不保存文件）
        print("正在获取产品列表（全局扫描）...")
        print("-" * 80)
        
        fetcher = ProductFetcher()
        products = fetcher.fetch_all_products()
        
        if not products:
            print("错误: 未能获取到产品列表")
            return 1
        
        print(f"成功获取 {len(products)} 个产品\n")
        
        # 搜索匹配的产品
        matched_products = search_products(args.search, products)
        
        if not matched_products:
            print(f"未找到匹配 '{args.search}' 的产品")
            print("\n提示：")
            print("  - 可以尝试使用部分关键词，如 'CodeArts' 或 'Check'")
            print("  - 产品代码不区分大小写")
            print("  - 支持使用下划线或连字符，如 'CodeArts_Check' 或 'CodeArts-Check'")
            return 1
        
        print(f"找到 {len(matched_products)} 个匹配的产品：\n")
        print("-" * 80)
        
        for i, product in enumerate(matched_products[:20], 1):  # 最多显示20个
            product_code = product.get('product_code', 'N/A')
            product_name = product.get('name', 'N/A')
            doc_url = product.get('doc_url', 'N/A')
            
            print(f"{i:2d}. 产品代码: {product_code}")
            print(f"    产品名称: {product_name}")
            if doc_url != 'N/A':
                print(f"    文档URL: {doc_url}")
            print()
        
        if len(matched_products) > 20:
            print(f"... 还有 {len(matched_products) - 20} 个匹配结果\n")
        
        print("-" * 80)
        print("\n使用方法：")
        print(f"  使用产品代码 '{matched_products[0].get('product_code', 'N/A')}' 来指定该服务：")
        print(f"  python3.10 src/cli.py --category {matched_products[0].get('product_code', 'N/A')}")
        print()
        
        return 0
    
    print("=" * 80)
    print("华为云API文档抓取工具")
    print("=" * 80)
    print()
    
    # 步骤1：获取产品列表
    if args.step is None or args.step == 1:
        print("步骤1: 获取产品列表")
        print("-" * 80)
        
        fetcher = ProductFetcher()
        products = fetcher.fetch_all_products()
        
        if not products:
            print("错误: 未能获取到产品列表")
            return 1
        
        print(f"\n成功获取 {len(products)} 个产品")
        
        # 应用过滤器
        filtered_products = filter_products(products, args.category, args.skip)
        
        if args.category:
            print(f"指定扫描服务: {args.category}")
        if args.skip:
            print(f"跳过服务: {args.skip}")
        
        print(f"过滤后剩余 {len(filtered_products)} 个产品")
        
        # 保存产品列表
        products_file = os.path.join(args.output_dir, args.products_file)
        import json
        with open(products_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_products, f, ensure_ascii=False, indent=2)
        
        print(f"产品列表已保存到: {products_file}\n")
        
        # 如果只执行步骤1，退出
        if args.step == 1:
            return 0
    
    # 步骤2：获取API分类
    if args.step is None or args.step == 2:
        print("步骤2: 获取API文档分类")
        print("-" * 80)
        
        # 读取产品列表
        products_file = os.path.join(args.output_dir, args.products_file)
        if not os.path.exists(products_file):
            print(f"错误: 找不到产品列表文件 {products_file}")
            print("请先运行步骤1获取产品列表")
            return 1
        
        import json
        with open(products_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        # 应用过滤器（如果指定了）
        filtered_products = filter_products(products, args.category, args.skip)
        
        if args.category:
            print(f"指定扫描服务: {args.category}")
        if args.skip:
            print(f"跳过服务: {args.skip}")
        
        print(f"共 {len(filtered_products)} 个产品需要处理\n")
        
        # 创建API分类抓取器
        fetcher = APICategoryFetcher()
        
        # 存储结果
        results = []
        
        for i, product in enumerate(filtered_products, 1):
            product_code = product.get('product_code')
            product_name = product.get('name', 'N/A')
            doc_url = product.get('doc_url')
            
            if not product_code or not doc_url:
                print(f"{i:3d}. 跳过 {product_name[:50]} (缺少产品代码或文档URL)")
                continue
            
            print(f"{i:3d}. 处理 {product_name[:50]}")
            print(f"     产品代码: {product_code}")
            
            try:
                result = fetcher.fetch_api_categories(product_code, doc_url)
                
                if result and result.get('categories'):
                    num_categories = len(result['categories'])
                    total_apis = sum(len(cat.get('apis', [])) for cat in result['categories'])
                    print(f"     ✓ 找到 {num_categories} 个分类，共 {total_apis} 个API")
                    
                    results.append({
                        'product_code': product_code,
                        'product_name': product_name,
                        **result
                    })
                else:
                    print(f"     ✗ 未找到API分类")
                    results.append({
                        'product_code': product_code,
                        'product_name': product_name,
                        'api_doc_url': None,
                        'categories': []
                    })
            except Exception as e:
                print(f"     ✗ 错误: {e}")
                results.append({
                    'product_code': product_code,
                    'product_name': product_name,
                    'error': str(e)
                })
        
        # 保存结果
        categories_file = os.path.join(args.output_dir, args.categories_file)
        with open(categories_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到: {categories_file}")
        
        # 统计信息
        success_count = sum(1 for r in results if r.get('categories'))
        print(f"\n统计信息:")
        print(f"  - 成功获取分类: {success_count} 个产品")
        print(f"  - 失败: {len(results) - success_count} 个产品")
    
    # 步骤3：生成Markdown文件
    if args.step is None or args.step == 3:
        print("\n步骤3: 生成Markdown文件")
        print("-" * 80)
        
        # 读取API分类数据
        categories_file = os.path.join(args.output_dir, args.categories_file)
        if not os.path.exists(categories_file):
            print(f"错误: 找不到API分类文件 {categories_file}")
            print("请先运行步骤2获取API分类")
            return 1
        
        import json
        with open(categories_file, 'r', encoding='utf-8') as f:
            api_categories = json.load(f)
        
        # 应用过滤器
        filtered_categories = filter_products(api_categories, args.category, args.skip)
        
        if args.category:
            print(f"指定生成服务: {args.category}")
        if args.skip:
            print(f"跳过服务: {args.skip}")
        
        print(f"共 {len(filtered_categories)} 个产品需要生成Markdown\n")
        
        # 读取产品数据（可选）
        products_data = None
        products_file = os.path.join(args.output_dir, args.products_file)
        if os.path.exists(products_file):
            with open(products_file, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        
        # 创建Markdown生成器
        generator = MarkdownGenerator()
        
        # 生成Markdown文件
        markdown_files = generator.generate_markdown(filtered_categories, products_data)
        
        # 确定Markdown文件输出目录
        # 如果指定了--output，使用指定目录；否则使用当前执行命令的目录
        if args.output:
            markdown_output_dir = args.output
        else:
            # 获取当前执行命令的目录（工作目录）
            markdown_output_dir = os.getcwd()
        
        # 确保输出目录存在
        os.makedirs(markdown_output_dir, exist_ok=True)
        
        # 保存Markdown文件
        saved_count = 0
        for product_code, file_info in markdown_files.items():
            filename = file_info['filename']
            content = file_info['content']
            
            filepath = os.path.join(markdown_output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            saved_count += 1
            print(f"✓ 已保存: {filepath} ({len(content)} 字符)")
        
        print(f"\n统计信息:")
        print(f"  - 成功生成: {saved_count} 个Markdown文件")
    
    print("\n" + "=" * 80)
    print("完成!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
