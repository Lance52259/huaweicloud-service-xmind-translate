#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为云API文档抓取工具主程序
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scraper.product_fetcher import ProductFetcher


def main():
    """主函数"""
    print("=" * 80)
    print("华为云产品列表抓取工具 - 第一步")
    print("=" * 80)
    print("\n开始抓取华为云产品列表...\n")
    
    fetcher = ProductFetcher()
    products = fetcher.fetch_all_products()
    
    if products:
        print(f"\n{'='*80}")
        print(f"成功获取 {len(products)} 个产品")
        print(f"{'='*80}\n")
        
        # 按来源分类统计
        from_product_page = [p for p in products if p.get('source') == 'product_page']
        from_support_page = [p for p in products if p.get('source') != 'product_page']
        
        print(f"统计信息:")
        print(f"  - 从产品页面获取: {len(from_product_page)} 个")
        print(f"  - 从支持页面获取: {len(from_support_page)} 个")
        print(f"\n前10个产品示例:")
        print("-" * 80)
        
        for i, product in enumerate(products[:10], 1):
            name = product.get('name', 'N/A')
            product_code = product.get('product_code', 'N/A')
            doc_url = product.get('doc_url', 'N/A')
            print(f"{i:2d}. {name[:50]}")
            print(f"     产品代码: {product_code}")
            print(f"     文档URL: {doc_url}")
            print()
        
        if len(products) > 10:
            print(f"... 还有 {len(products) - 10} 个产品\n")
        
        # 保存到文件
        import json
        output_file = "products.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"{'='*80}")
        print(f"产品列表已保存到: {output_file}")
        print(f"{'='*80}\n")
    else:
        print("未能获取到产品列表")


if __name__ == "__main__":
    main()
