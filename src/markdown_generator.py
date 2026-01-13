#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown格式API文档生成模块
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarkdownGenerator:
    """Markdown格式API文档生成器"""
    
    BASE_URL = "https://support.huaweicloud.com"
    
    def __init__(self):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls = set()
    
    def generate_markdown(self, api_categories_data, products_data=None):
        """
        生成Markdown格式的API文档
        
        Args:
            api_categories_data: API分类数据（从api_categories.json读取）
            products_data: 产品数据（从products.json读取，用于获取产品名称）
            
        Returns:
            dict: 每个产品的Markdown内容
        """
        markdown_files = {}
        
        # 构建产品代码到产品名称的映射
        product_map = {}
        if products_data:
            for product in products_data:
                product_code = product.get('product_code', '').lower()
                product_name = product.get('name', '')
                product_map[product_code] = product_name
        
        for product_data in api_categories_data:
            product_code = product_data.get('product_code', '').lower()
            product_name = product_data.get('product_name', '') or product_map.get(product_code, product_code.upper())
            
            if not product_code:
                continue
            
            logger.info(f"生成产品 {product_code} 的Markdown文档")
            
            # 获取产品简称（英文）
            product_short_name = self._get_product_short_name(product_code, product_name)
            
            # 生成Markdown内容
            markdown_content = self._generate_product_markdown(
                product_short_name,
                product_data.get('categories', []),
                product_code
            )
            
            markdown_files[product_code] = {
                'filename': f"{product_code}.md",
                'content': markdown_content
            }
        
        return markdown_files
    
    def _get_product_short_name(self, product_code, product_name):
        """
        获取产品简称（英文）
        
        Args:
            product_code: 产品代码
            product_name: 产品名称
            
        Returns:
            str: 产品简称
        """
        # 如果产品代码是英文，直接使用大写
        if product_code and product_code.isalpha():
            return product_code.upper()
        
        # 尝试从产品名称中提取英文简称
        # 例如："弹性云服务器 ECS" -> "ECS"
        match = re.search(r'\b([A-Z]{2,})\b', product_name)
        if match:
            return match.group(1)
        
        # 如果都没有，使用产品代码的大写形式
        return product_code.upper() if product_code else 'UNKNOWN'
    
    def _generate_product_markdown(self, product_short_name, categories, product_code):
        """
        生成单个产品的Markdown内容
        
        Args:
            product_short_name: 产品简称
            categories: 分类列表
            product_code: 产品代码
            
        Returns:
            str: Markdown内容
        """
        lines = []
        
        # 一级标题：产品简称
        lines.append(f"# {product_short_name}")
        lines.append("")
        
        if not categories:
            lines.append("（暂无API文档）")
            lines.append("")
            return "\n".join(lines)
        
        # 处理每个分类
        for category in categories:
            # 递归处理子分类和API
            self._add_category_content(lines, category, product_code, level=2)
        
        return "\n".join(lines)
    
    def _add_category_content(self, lines, category, product_code, level=2):
        """
        递归添加分类内容（支持多级嵌套）
        
        Args:
            lines: 输出行列表
            category: 分类信息
            product_code: 产品代码
            level: 当前标题级别（2=二级，3=三级，以此类推）
        """
        category_name = category.get('name', '')
        category_url = category.get('url', '')
        
        if not category_name:
            return
        
        # 获取该分类下的API列表
        apis = self._fetch_apis_from_category(category_url, product_code, category)
        
        # 获取子分类
        subcategories = category.get('subcategories', [])
        
        # 如果没有API也没有子分类，跳过
        if not apis and not subcategories:
            return
        
        # 添加当前分类的标题
        title_prefix = '#' * level
        lines.append(f"{title_prefix} {category_name}")
        lines.append("")
        
        # 如果有子分类，先处理子分类
        if subcategories:
            # 递归处理每个子分类
            for subcategory in subcategories:
                self._add_category_content(lines, subcategory, product_code, level + 1)
        
        # 添加API列表
        if apis:
            for api in apis:
                api_name = api.get('name', '')
                api_uri = api.get('uri', '')
                api_url = api.get('url', '')
                
                if api_name and api_url:
                    if api_uri:
                        lines.append(f"- [{api_name} {api_uri}]({api_url})")
                    else:
                        lines.append(f"- [{api_name}]({api_url})")
                    lines.append("")
    
    def _fetch_apis_from_category(self, category_url, product_code, category_info):
        """
        从分类页面获取API列表
        
        Args:
            category_url: 分类页面URL
            product_code: 产品代码
            category_info: 分类信息
            
        Returns:
            list: API列表，每个API包含name、uri、url
        """
        apis = []
        
        try:
            if category_url in self.visited_urls:
                return apis
            
            self.visited_urls.add(category_url)
            
            # 添加重试机制
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = self.session.get(category_url, timeout=30, allow_redirects=True)
                    if response.status_code == 200:
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.debug(f"获取分类页面失败，重试 {attempt + 1}/{max_retries}: {e}")
                        import time
                        time.sleep(1)
                    else:
                        logger.warning(f"获取分类页面失败: {category_url}, 错误: {e}")
                        return apis
            
            if not response or response.status_code != 200:
                return apis
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有指向API文档的链接
            all_links = soup.find_all('a', href=True)
            api_base_path = f"/api-{product_code}/"
            
            # 根据产品代码确定API URL模式
            # 支持多种格式：
            # - {product_code}_02_XXXX.html (常见格式，如ECS)
            # - {product_code}_api_XXXX.html (某些产品使用)
            # - 直接API名称.html (CodeArts Check等产品使用，如QueryOctopusResourcePools.html)
            # - topic_XXXXXX.html (某些产品的API格式)
            
            # 从分类URL推断API格式
            category_filename = category_url.split('/')[-1].split('.')[0]
            api_patterns = []
            
            if category_filename.startswith('topic_'):
                # CodeArts Check等产品：分类使用topic_格式，API使用直接名称
                api_patterns = [None]  # None表示接受所有/api-{product_code}/下的链接
            elif f"{product_code}_02_" in category_filename:
                api_patterns = [f"{product_code}_02_"]
            elif f"{product_code}_api_" in category_filename:
                api_patterns = [f"{product_code}_api_"]
            else:
                # 默认尝试所有格式
                api_patterns = [f"{product_code}_02_", f"{product_code}_api_", None]
            
            api_urls = []
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).strip()
                
                if not text or not href:
                    continue
                
                # 过滤掉明显的非API链接
                exclude_keywords = ['上一篇', '下一篇', '表', '查看PDF', 'PDF', '#', 'javascript:', '上一页', '下一页', 'API参考', '概览']
                if any(keyword in text for keyword in exclude_keywords):
                    continue
                
                # 检查是否是API链接
                if api_base_path in href:
                    full_url = urljoin(self.BASE_URL, href)
                    
                    # 跳过PDF和已访问的URL
                    if full_url.endswith('.pdf') or full_url in self.visited_urls:
                        continue
                    
                    filename = full_url.split('/')[-1].split('.')[0]
                    
                    # 排除分类页面本身
                    exclude_patterns = [
                        f"{product_code}_02_0000",
                        f"{product_code}_api_0000",
                        f"{product_code}_03_0000",
                        "topic_300000000",  # CodeArts Check的分类页面
                    ]
                    
                    if any(pattern in filename for pattern in exclude_patterns):
                        continue
                    
                    # 检查是否符合API模式
                    is_api = False
                    for api_pattern in api_patterns:
                        if api_pattern is None:
                            # 接受所有/api-{product_code}/下的链接（CodeArts Check格式）
                            # 但排除明显的非API链接
                            exclude_patterns = [
                                'api_0000',  # API目录页面
                                'api_1000',  # API概览页面
                                '_0000',     # 目录页面
                                'topic_300000',  # 分类页面
                            ]
                            if not any(exclude in filename for exclude in exclude_patterns):
                                # 排除链接文本为"API"的链接（通常是目录或概览页面）
                                if text.strip().upper() != 'API':
                                    is_api = True
                                    break
                        elif api_pattern in href:
                            # 排除分类页面本身（格式：{product_code}_XX_XX00.html，XX00表示分类）
                            if filename.endswith('00') and len(filename.split('_')) >= 3:
                                # 可能是分类页面，跳过
                                continue
                            # 排除链接文本为"API"的链接
                            if text.strip().upper() != 'API':
                                is_api = True
                                break
                    
                    if is_api:
                        api_urls.append((text, full_url))
            
            # 去重
            seen_urls = set()
            unique_api_urls = []
            for text, url in api_urls:
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_api_urls.append((text, url))
            
            # 访问每个API页面，提取API名称和URI
            for api_name, api_url in unique_api_urls:
                api_info = self._extract_api_info(api_url, api_name)
                if api_info:
                    apis.append(api_info)
            
        except Exception as e:
            logger.error(f"获取分类 {category_url} 的API列表时出错: {e}", exc_info=True)
        
        return apis
    
    def _extract_api_info(self, api_url, default_name):
        """
        从API页面提取API信息（名称和URI）
        
        Args:
            api_url: API页面URL
            default_name: 默认API名称（从链接文本获取）
            
        Returns:
            dict: API信息，包含name、uri、url
        """
        try:
            if api_url in self.visited_urls:
                return None
            
            self.visited_urls.add(api_url)
            
            # 添加重试机制
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = self.session.get(api_url, timeout=30, allow_redirects=True)
                    if response.status_code == 200:
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.debug(f"获取API页面失败，重试 {attempt + 1}/{max_retries}: {e}")
                        import time
                        time.sleep(1)
                    else:
                        logger.debug(f"获取API页面失败: {api_url}, 错误: {e}")
                        return {
                            'name': default_name,
                            'uri': '',
                            'url': api_url
                        }
            
            if not response or response.status_code != 200:
                return {
                    'name': default_name,
                    'uri': '',
                    'url': api_url
                }
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取API名称（从页面标题或H1标签）
            api_name = default_name
            h1_tags = soup.find_all('h1')
            if h1_tags:
                h1_text = h1_tags[0].get_text(strip=True)
                # 清理标题
                # 例如："创建云服务器- CreateServers" -> "创建云服务器"
                # 例如："重装弹性云服务器操作系统（安装Cloud-init）" -> "重装弹性云服务器操作系统（安装Cloud-init）"
                api_name = h1_text
                
                # 移除英文部分（如果有）
                # 匹配模式：中文 - 英文
                match = re.match(r'^(.+?)\s*-\s*[A-Z][a-zA-Z0-9_]+$', api_name)
                if match:
                    api_name = match.group(1).strip()
                
                # 移除末尾的英文括号内容（如果有）
                api_name = re.sub(r'\s*\([A-Z][a-zA-Z0-9_]+\)\s*$', '', api_name)
            
            # 提取API URI（HTTP方法和路径）
            api_uri = self._extract_api_uri(soup)
            
            return {
                'name': api_name,
                'uri': api_uri,
                'url': api_url
            }
            
        except Exception as e:
            logger.debug(f"提取API信息时出错 {api_url}: {e}")
            return {
                'name': default_name,
                'uri': '',
                'url': api_url
            }
    
    def _extract_api_uri(self, soup):
        """
        从API页面提取URI（HTTP方法和路径）
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            str: API URI，格式为 "METHOD /path"，如果未找到返回空字符串
        """
        # 首先尝试从代码块中查找（更准确）
        code_blocks = soup.find_all(['code', 'pre'])
        for code_block in code_blocks:
            code_text = code_block.get_text()
            # 查找 METHOD /path 模式
            matches = re.findall(r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s\n\)]+)', code_text, re.IGNORECASE)
            if matches:
                match = matches[0]
                uri = f"{match[0]} {match[1]}"
                # 清理URI，移除可能的换行和多余空格
                uri = re.sub(r'\s+', ' ', uri).strip()
                return uri
        
        # 如果代码块中没找到，从页面文本中查找
        text = soup.get_text()
        
        # 查找URI模式
        uri_patterns = [
            r'(GET|POST|PUT|DELETE|PATCH)\s+(/[^\s\n\)]+)',  # METHOD /path
            r'URI[：:]\s*(/[^\s\n]+)',  # URI: /path
            r'请求URI[：:]\s*(/[^\s\n]+)',  # 请求URI: /path
            r'接口URI[：:]\s*(/[^\s\n]+)',  # 接口URI: /path
        ]
        
        for pattern in uri_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                match = matches[0]
                if isinstance(match, tuple):
                    # 如果匹配到元组，组合成字符串
                    if len(match) == 2:
                        uri = f"{match[0]} {match[1]}"
                        # 清理URI
                        uri = re.sub(r'\s+', ' ', uri).strip()
                        return uri
                    else:
                        return match[0] if match[0] else ''
                else:
                    uri = match.strip()
                    # 如果URI没有HTTP方法，尝试从上下文查找
                    if not uri.startswith(('GET', 'POST', 'PUT', 'DELETE', 'PATCH')):
                        # 在URI前后查找HTTP方法
                        context_start = max(0, text.find(match) - 50)
                        context = text[context_start:text.find(match) + len(match) + 50]
                        method_match = re.search(r'(GET|POST|PUT|DELETE|PATCH)', context, re.IGNORECASE)
                        if method_match:
                            return f"{method_match.group(1)} {uri}"
                    return uri
        
        return ''
