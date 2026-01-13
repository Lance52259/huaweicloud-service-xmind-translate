#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为云API文档分类抓取工具主程序 - 第二步
"""

import sys
import os
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scraper.api_category_fetcher import APICategoryFetcher


def main():
    """主函数"""
    print("=" * 80)
    print("华为云API文档分类抓取工具 - 第二步")
    print("=" * 80)
    print("\n开始获取各产品的API文档分类...\n")
    
    # 读取产品列表
    products_file = "products.json"
    if not os.path.exists(products_file):
        print(f"错误: 找不到产品列表文件 {products_file}")
        print("请先运行第一步获取产品列表")
        return
    
    with open(products_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"共找到 {len(products)} 个产品\n")
    
    # 创建API分类抓取器
    fetcher = APICategoryFetcher()
    
    # 存储结果
    results = []
    
    # 测试：只处理前3个产品
    test_products = products[:3]
    
    for i, product in enumerate(test_products, 1):
        product_code = product.get('product_code')
        product_name = product.get('name', 'N/A')
        doc_url = product.get('doc_url')
        
        if not product_code or not doc_url:
            print(f"{i}. 跳过 {product_name} (缺少产品代码或文档URL)")
            continue
        
        print(f"{i}. 处理产品: {product_name[:50]}")
        print(f"   产品代码: {product_code}")
        
        try:
            result = fetcher.fetch_api_categories(product_code, doc_url)
            
            if result and result.get('categories'):
                num_categories = len(result['categories'])
                print(f"   ✓ 找到 {num_categories} 个API分类")
                
                # 显示前几个分类
                for j, cat in enumerate(result['categories'][:3], 1):
                    print(f"      {j}. {cat.get('name', 'N/A')[:40]}")
                    if cat.get('apis'):
                        print(f"         包含 {len(cat['apis'])} 个API")
                
                results.append(result)
            else:
                print(f"   ✗ 未找到API分类")
                results.append({
                    'product_code': product_code,
                    'product_name': product_name,
                    'api_doc_url': None,
                    'categories': []
                })
        except Exception as e:
            print(f"   ✗ 错误: {e}")
            results.append({
                'product_code': product_code,
                'product_name': product_name,
                'error': str(e)
            })
        
        print()
    
    # 保存结果
    output_file = "api_categories.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"{'='*80}")
    print(f"结果已保存到: {output_file}")
    print(f"{'='*80}\n")
    
    # 统计信息
    success_count = sum(1 for r in results if r.get('categories'))
    print(f"统计信息:")
    print(f"  - 成功获取分类: {success_count} 个产品")
    print(f"  - 失败: {len(results) - success_count} 个产品")


if __name__ == "__main__":
    main()
