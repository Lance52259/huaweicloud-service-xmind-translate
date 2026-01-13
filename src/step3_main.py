#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为云API文档Markdown生成工具主程序 - 第三步
"""

import sys
import os
import json
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.markdown_generator import MarkdownGenerator


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='华为云API文档Markdown生成工具 - 第三步',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--categories-file',
        type=str,
        default='api_categories.json',
        help='API分类文件路径（默认：api_categories.json）'
    )
    
    parser.add_argument(
        '--products-file',
        type=str,
        default='products.json',
        help='产品列表文件路径（默认：products.json）'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='.',
        help='输出目录（默认：当前目录），用于api_categories.json'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Markdown文件输出目录（默认：当前执行命令的目录）'
    )
    
    parser.add_argument(
        '--category', '-c',
        type=str,
        default=None,
        help='指定要生成的服务（产品代码），多个用逗号分隔'
    )
    
    return parser.parse_args()


def filter_products(api_categories, category_filter=None):
    """
    过滤产品列表
    
    Args:
        api_categories: API分类数据
        category_filter: 要包含的产品代码列表（None表示全部）
        
    Returns:
        过滤后的产品列表
    """
    if not category_filter:
        return api_categories
    
    category_codes = [c.strip().lower() for c in category_filter.split(',') if c.strip()]
    
    filtered = []
    for product in api_categories:
        product_code = product.get('product_code', '').lower()
        if product_code in category_codes:
            filtered.append(product)
    
    return filtered


def main():
    """主函数"""
    args = parse_args()
    
    print("=" * 80)
    print("华为云API文档Markdown生成工具 - 第三步")
    print("=" * 80)
    print()
    
    # 读取API分类数据
    categories_file = args.categories_file
    if not os.path.exists(categories_file):
        print(f"错误: 找不到API分类文件 {categories_file}")
        print("请先运行第二步获取API分类")
        return 1
    
    with open(categories_file, 'r', encoding='utf-8') as f:
        api_categories = json.load(f)
    
    # 读取产品数据（可选）
    products_data = None
    products_file = args.products_file
    if os.path.exists(products_file):
        with open(products_file, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
    
    # 应用过滤器
    if args.category:
        api_categories = filter_products(api_categories, args.category)
        print(f"指定生成服务: {args.category}")
    
    print(f"共 {len(api_categories)} 个产品需要生成Markdown\n")
    
    # 创建Markdown生成器
    generator = MarkdownGenerator()
    
    # 生成Markdown文件
    markdown_files = generator.generate_markdown(api_categories, products_data)
    
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
    
    print(f"\n{'='*80}")
    print(f"成功生成 {saved_count} 个Markdown文件")
    print(f"输出目录: {markdown_output_dir}")
    print(f"{'='*80}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
