#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为云API文档分类抓取模块
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class APICategoryFetcher:
    """华为云API文档分类抓取器"""
    
    BASE_URL = "https://support.huaweicloud.com"
    
    def __init__(self):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls = set()  # 记录已访问的URL，避免重复访问
    
    def fetch_api_categories(self, product_code, doc_url):
        """
        获取产品的API文档分类
        
        Args:
            product_code: 产品代码，如 'ecs'
            doc_url: 产品文档首页URL
            
        Returns:
            dict: API分类结构，包含分类名称、URL和子分类
        """
        logger.info(f"开始获取产品 {product_code} 的API文档分类")
        
        # 方法1: 尝试从产品文档首页找到API文档链接
        api_doc_url = self._find_api_doc_url(product_code, doc_url)
        
        if not api_doc_url:
            # 方法2: 尝试构建常见的API文档URL
            api_doc_url = self._build_api_doc_url(product_code)
        
        if not api_doc_url:
            logger.warning(f"未找到产品 {product_code} 的API文档URL")
            return None
        
        logger.info(f"找到API文档URL: {api_doc_url}")
        
        # 解析API文档页面，提取分类结构
        categories = self._parse_api_categories(api_doc_url, product_code)
        
        # 如果从API文档URL没找到，尝试直接从产品文档首页查找
        if not categories:
            logger.info(f"产品 {product_code} 从API文档URL未找到分类，尝试直接从产品文档首页查找")
            categories = self._parse_api_categories(doc_url, product_code)
        
        # 如果还是没找到，尝试从侧边栏菜单查找
        if not categories:
            logger.info(f"产品 {product_code} 从产品文档首页未找到分类，尝试从侧边栏菜单查找")
            categories = self._parse_api_categories_from_menu(doc_url, product_code)
        
        return {
            'product_code': product_code,
            'api_doc_url': api_doc_url,
            'categories': categories
        }
    
    def _find_api_doc_url(self, product_code, doc_url):
        """从产品文档首页找到API文档链接"""
        try:
            response = self.session.get(doc_url, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            all_links = soup.find_all('a', href=True)
            
            # 查找API文档链接
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # 检查是否包含API相关关键词
                if any(keyword in text.lower() for keyword in ['api', '接口', '参考', 'reference']):
                    # 检查URL是否指向API文档
                    if '/api-' in href.lower() or 'api-reference' in href.lower():
                        full_url = urljoin(self.BASE_URL, href)
                        return full_url
            
            return None
            
        except Exception as e:
            logger.error(f"查找API文档URL时出错: {e}")
            return None
    
    def _build_api_doc_url(self, product_code):
        """构建API文档URL"""
        # 常见的API文档URL格式
        possible_urls = [
            f"{self.BASE_URL}/api-{product_code}/",
            f"{self.BASE_URL}/api-{product_code}/index.html",
            f"{self.BASE_URL}/{product_code}/api-reference.html",
        ]
        
        for url in possible_urls:
            try:
                response = self.session.get(url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    return url
            except Exception:
                continue
        
        # 如果首页不存在，尝试访问一个已知的API页面来推断结构
        # 华为云的API文档通常使用这种格式：/api-{product_code}/zh-cn_topic_xxxxx.html
        # 或者：/api-{product_code}/{product_code}_xx_xxxx.html
        test_patterns = [
            f"{self.BASE_URL}/api-{product_code}/zh-cn_topic_0020805967.html",  # 常见的API参考页面格式
            f"{self.BASE_URL}/api-{product_code}/zh-cn_topic_0020212668.html",  # ECS示例
            f"{self.BASE_URL}/api-{product_code}/{product_code}_02_0001.html",  # 另一种格式
            f"{self.BASE_URL}/api-{product_code}/{product_code}_02_0000.html",  # API目录格式
        ]
        
        for test_url in test_patterns:
            try:
                response = self.session.get(test_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    # 返回API文档的基础URL
                    return f"{self.BASE_URL}/api-{product_code}/"
            except Exception:
                continue
        
        # 如果都失败，返回基础URL（让解析函数尝试访问）
        return f"{self.BASE_URL}/api-{product_code}/"
    
    def _parse_api_categories(self, api_doc_url, product_code):
        """
        解析API文档页面，提取分类结构
        
        只保留"API参考" -> "API" -> 子分类的结构，其他分类忽略
        
        Args:
            api_doc_url: API文档URL
            product_code: 产品代码
            
        Returns:
            list: 分类列表，只包含"API参考"下的"API"目录的子分类
        """
        categories = []
        api_base_path = f"/api-{product_code}/"
        
        try:
            # 第一步：找到"API参考"页面
            api_ref_category = self._find_api_reference_category(api_doc_url, product_code)
            
            if api_ref_category:
                logger.info(f"找到'API参考'分类: {api_ref_category['url']}")
                
                # 第二步：在"API参考"页面中找到"API"目录链接
                api_dir_url = self._find_api_directory_url(api_ref_category['url'], product_code)
                
                if api_dir_url:
                    logger.info(f"找到'API'目录: {api_dir_url}")
                    
                    # 第三步：访问"API"目录页面，获取所有子分类
                    subcategories = self._fetch_subcategories_from_api_dir(api_dir_url, product_code)
                    
                    logger.info(f"产品 {product_code} 在'API'目录下找到 {len(subcategories)} 个子分类")
                    
                    return subcategories
                else:
                    logger.warning(f"产品 {product_code} 在'API参考'中未找到'API'目录，尝试直接从API文档首页查找")
            else:
                logger.warning(f"产品 {product_code} 未找到'API参考'分类，尝试直接从API文档首页查找")
            
            # Fallback: 如果找不到"API参考"，尝试直接从API文档首页查找API目录
            api_dir_url = self._find_api_directory_url(api_doc_url, product_code)
            
            if api_dir_url:
                logger.info(f"从API文档首页找到'API'目录: {api_dir_url}")
                
                # 访问"API"目录页面，获取所有子分类
                subcategories = self._fetch_subcategories_from_api_dir(api_dir_url, product_code)
                
                logger.info(f"产品 {product_code} 在'API'目录下找到 {len(subcategories)} 个子分类")
                
                return subcategories
            else:
                logger.warning(f"产品 {product_code} 未找到API目录")
                return categories
            
        except Exception as e:
            logger.error(f"解析API分类时出错: {e}", exc_info=True)
        
        return categories
    
    def _find_api_reference_category(self, api_doc_url, product_code):
        """
        找到"API参考"分类
        
        Args:
            api_doc_url: API文档URL
            product_code: 产品代码
            
        Returns:
            dict: API参考分类信息，如果未找到返回None
        """
        api_base_path = f"/api-{product_code}/"
        
        # 尝试访问几个可能的API页面来查找"API参考"
        test_urls = [
            f"{self.BASE_URL}/api-{product_code}/zh-cn_topic_0020212668.html",  # ECS示例格式
            f"{self.BASE_URL}/api-{product_code}/{product_code}_02_0001.html",  # 另一种格式
            api_doc_url,  # 传入的URL
        ]
        
        for url in test_urls:
            try:
                resp = self.session.get(url, timeout=30, allow_redirects=True)
                if resp.status_code != 200:
                    continue
                
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 查找所有链接
                all_links = soup.find_all('a', href=True)
                
                # 优先级1: 查找完全匹配"API参考"的链接
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).strip()
                    
                    if api_base_path in href and ('API参考' in text or 'api参考' in text.lower()):
                        full_url = urljoin(self.BASE_URL, href)
                        
                        # 解析URL，提取分类信息
                        parsed = urlparse(full_url)
                        path_parts = [p for p in parsed.path.split('/') if p]
                        
                        if len(path_parts) >= 2:
                            filename = path_parts[-1].split('.')[0] if path_parts[-1] else path_parts[-2]
                            
                            logger.info(f"找到'API参考'分类（完全匹配）: {text} -> {full_url}")
                            return {
                                'name': text,
                                'url': full_url,
                                'category_id': filename
                            }
                
                # 优先级2: 查找包含"参考"或"reference"的链接
                # 排除非API参考的分类，如"如何调用API"、"API概览"等
                exclude_keywords = ['如何调用', '概览', '概述', '介绍', '说明', '指南', 'guide', 'overview', 'introduction']
                
                reference_candidates = []
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).strip()
                    
                    if not text or not href:
                        continue
                    
                    # 排除非API参考的分类
                    if any(keyword in text for keyword in exclude_keywords):
                        continue
                    
                    # 检查是否包含"参考"或"reference"关键词
                    if api_base_path in href and ('参考' in text or 'reference' in text.lower() or 'reference' in href.lower()):
                        full_url = urljoin(self.BASE_URL, href)
                        
                        # 解析URL，提取分类信息
                        parsed = urlparse(full_url)
                        path_parts = [p for p in parsed.path.split('/') if p]
                        
                        if len(path_parts) >= 2:
                            filename = path_parts[-1].split('.')[0] if path_parts[-1] else path_parts[-2]
                            
                            # 计算优先级：包含"API参考"的优先级更高
                            priority = 1 if ('API' in text or 'api' in text.lower()) and '参考' in text else 2
                            
                            reference_candidates.append({
                                'name': text,
                                'url': full_url,
                                'category_id': filename,
                                'priority': priority
                            })
                
                # 按优先级排序，返回优先级最高的
                if reference_candidates:
                    reference_candidates.sort(key=lambda x: x['priority'])
                    best_match = reference_candidates[0]
                    logger.info(f"找到'API参考'分类（模糊匹配）: {best_match['name']} -> {best_match['url']}")
                    return {
                        'name': best_match['name'],
                        'url': best_match['url'],
                        'category_id': best_match['category_id']
                    }
            except Exception:
                continue
        
        return None
    
    def _find_api_directory_url(self, api_ref_url, product_code):
        """
        在"API参考"页面中找到API目录链接
        
        支持多种命名方式：
        - "API"
        - "编译构建API"
        - "XXX API"
        - 其他包含"API"关键词的链接
        
        如果"API参考"页面中没有直接链接，尝试直接构建API目录URL
        
        Args:
            api_ref_url: API参考页面URL
            product_code: 产品代码
            
        Returns:
            str: API目录URL，如果未找到返回None
        """
        api_base_path = f"/api-{product_code}/"
        
        try:
            response = self.session.get(api_ref_url, timeout=30, allow_redirects=True)
            if response.status_code != 200:
                # 如果无法访问，尝试直接构建URL
                return self._build_api_directory_url(product_code)
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有链接
            all_links = soup.find_all('a', href=True)
            
            # 优先级1: 查找指向API目录的链接（格式：{product_code}_02_0000.html）
            api_dir_pattern = f"{product_code}_02_0000"
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).strip()
                
                if api_base_path in href and api_dir_pattern in href:
                    full_url = urljoin(self.BASE_URL, href)
                    # 验证URL是否可访问
                    if self._verify_url(full_url):
                        logger.info(f"通过URL模式找到API目录: {full_url}")
                        return full_url
            
            # 优先级2: 查找名称包含"API"且URL符合API目录模式的链接
            # 匹配模式：链接文本包含"API"，且URL包含 {product_code}_02_ 模式
            # 排除非API目录的分类，如"如何调用API"、"API概览"等
            exclude_keywords = ['如何调用', '概览', '概述', '介绍', '说明', '指南', 'guide', 'overview', 'introduction']
            
            api_candidates = []
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).strip()
                
                if not text or not href:
                    continue
                
                # 排除非API目录的分类
                if any(keyword in text for keyword in exclude_keywords):
                    continue
                
                # 检查是否是API相关链接
                if api_base_path in href and ('API' in text or 'api' in text.lower()):
                    # 检查URL模式（可能是API目录或子分类）
                    # 支持多种URL格式：_02_ 或 _api_
                    url_patterns = [
                        f"{product_code}_02_",
                        f"{product_code}_api_",
                    ]
                    
                    for url_pattern in url_patterns:
                        if url_pattern in href:
                            full_url = urljoin(self.BASE_URL, href)
                            # 优先选择可能是目录的URL（_XX_0000或_XX_00XX格式）
                            if f"{product_code}_02_00" in href or f"{product_code}_api_00" in href:
                                # 判断优先级：完全匹配目录模式的优先级更高
                                priority = 1 if (f"{product_code}_02_0000" in href or f"{product_code}_api_0000" in href) else 2
                                api_candidates.append({
                                    'text': text,
                                    'url': full_url,
                                    'href': href,
                                    'priority': priority
                                })
                            break
            
            # 按优先级排序
            api_candidates.sort(key=lambda x: x['priority'])
            
            # 验证候选URL，返回第一个可访问的
            for candidate in api_candidates:
                if self._verify_url(candidate['url']):
                    logger.info(f"通过链接文本找到API目录: {candidate['text']} -> {candidate['url']}")
                    return candidate['url']
            
            # 优先级3: 如果没找到，尝试直接构建URL
            built_url = self._build_api_directory_url(product_code)
            if built_url:
                logger.info(f"通过构建URL找到API目录: {built_url}")
                return built_url
            
            logger.warning(f"产品 {product_code} 未找到API目录链接")
            return None
            
        except Exception as e:
            logger.debug(f"查找API目录URL时出错: {e}")
            # 出错时也尝试直接构建URL
            return self._build_api_directory_url(product_code)
    
    def _build_api_directory_url(self, product_code):
        """
        直接构建API目录URL
        
        Args:
            product_code: 产品代码
            
        Returns:
            str: API目录URL，如果不可访问返回None
        """
        # 常见的API目录URL格式：{product_code}_02_0000.html
        possible_urls = [
            f"{self.BASE_URL}/api-{product_code}/{product_code}_02_0000.html",
            f"{self.BASE_URL}/api-{product_code}/api.html",
            f"{self.BASE_URL}/api-{product_code}/index.html",
        ]
        
        for url in possible_urls:
            if self._verify_url(url):
                return url
        
        return None
    
    def _verify_url(self, url):
        """
        验证URL是否可访问
        
        Args:
            url: 要验证的URL
            
        Returns:
            bool: URL是否可访问
        """
        try:
            # 使用GET请求，因为某些网站HEAD请求可能被阻止
            response = self.session.get(url, timeout=10, allow_redirects=True)
            return response.status_code == 200
        except Exception:
            return False
    
    def _fetch_subcategories_from_api_dir(self, api_dir_url, product_code):
        """
        从"API"目录页面获取所有子分类
        
        支持多种结构：
        1. 直接包含子分类（如ECS）：{product_code}_02_XXXX.html
        2. 包含"API概览"链接（如CodeArts Check）：需要先访问API概览页面
        
        Args:
            api_dir_url: API目录页面URL
            product_code: 产品代码
            
        Returns:
            list: 子分类列表
        """
        subcategories = []
        api_base_path = f"/api-{product_code}/"
        
        try:
            if api_dir_url in self.visited_urls:
                return subcategories
            
            self.visited_urls.add(api_dir_url)
            
            # 添加重试机制
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = self.session.get(api_dir_url, timeout=30, allow_redirects=True)
                    if response.status_code == 200:
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)
                    else:
                        logger.debug(f"访问API目录页面失败: {api_dir_url}, 错误: {e}")
                        return subcategories
            
            if not response or response.status_code != 200:
                return subcategories
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有链接
            all_links = soup.find_all('a', href=True)
            
            # 检查是否有"API概览"链接（CodeArts Check等产品的结构）
            api_overview_url = None
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).strip()
                
                if api_base_path in href and ('API概览' in text or '概览' in text) and '如何调用' not in text:
                    api_overview_url = urljoin(self.BASE_URL, href)
                    logger.info(f"找到'API概览'链接: {api_overview_url}")
                    break
            
            # 如果找到"API概览"链接，从该页面获取子分类
            if api_overview_url:
                return self._fetch_subcategories_from_overview(api_overview_url, product_code)
            
            # 否则，直接从当前页面获取子分类
            # 子分类通常格式为：
            # - {product_code}_02_XXXX.html (常见格式，如ECS)
            # - {product_code}_api_XXXX.html (某些产品使用)
            # - {product_code}_03_XXXX.html (某些产品使用)
            # - topic_300000XXX.html (CodeArts Check等产品使用)
            
            # 从当前API目录URL推断格式
            current_dir_format = None
            if f"{product_code}_02_0000" in api_dir_url:
                current_dir_format = f"{product_code}_02_"
            elif f"{product_code}_api_0000" in api_dir_url:
                current_dir_format = f"{product_code}_api_"
            
            # 如果无法推断，尝试所有可能的格式
            subcategory_patterns = [
                f"{product_code}_02_",
                f"{product_code}_api_",
                f"{product_code}_03_",
                "topic_",  # CodeArts Check等产品使用
            ]
            
            if current_dir_format:
                # 将当前格式放在最前面
                subcategory_patterns = [current_dir_format] + [p for p in subcategory_patterns if p != current_dir_format]
            
            # API目录本身的模式
            api_dir_patterns = [
                f"{product_code}_02_0000",
                f"{product_code}_api_0000",
                f"{product_code}_03_0000",
            ]
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).strip()
                
                if not text or not href:
                    continue
                
                # 过滤掉明显的非分类链接
                exclude_keywords = ['上一篇', '下一篇', '表', '查看PDF', 'PDF', '#', 'javascript:', '上一页', '下一页', '概览']
                if any(keyword in text for keyword in exclude_keywords):
                    continue
                
                # 检查是否是子分类链接（支持多种URL格式）
                if api_base_path in href:
                    is_subcategory = False
                    for subcategory_pattern in subcategory_patterns:
                        if subcategory_pattern in href:
                            # 排除API目录本身
                            if any(pattern in href for pattern in api_dir_patterns):
                                break
                            
                            full_url = urljoin(self.BASE_URL, href)
                            
                            # 跳过PDF和已访问的URL
                            if full_url.endswith('.pdf') or full_url in self.visited_urls:
                                break
                            
                            # 解析URL，提取分类信息
                            parsed = urlparse(full_url)
                            path_parts = [p for p in parsed.path.split('/') if p]
                            
                            if len(path_parts) >= 2:
                                filename = path_parts[-1].split('.')[0]
                                
                                # 检查是否是子分类
                                # 对于topic_格式，直接接受
                                # 对于其他格式，XXXX不是0000
                                if subcategory_pattern == "topic_":
                                    if filename.startswith("topic_"):
                                        subcategories.append({
                                            'name': text,
                                            'url': full_url,
                                            'category_id': filename,
                                            'subcategories': [],
                                            'apis': []
                                        })
                                        is_subcategory = True
                                        break
                                elif filename.startswith(subcategory_pattern) and not filename.endswith('_0000'):
                                    subcategories.append({
                                        'name': text,
                                        'url': full_url,
                                        'category_id': filename,
                                        'subcategories': [],
                                        'apis': []
                                    })
                                    is_subcategory = True
                                    break
                    
                    if is_subcategory:
                        continue
            
            # 去重
            seen_urls = set()
            unique_subcategories = []
            for subcat in subcategories:
                if subcat['url'] not in seen_urls:
                    seen_urls.add(subcat['url'])
                    unique_subcategories.append(subcat)
            
            return unique_subcategories
            
        except Exception as e:
            logger.error(f"获取API目录子分类时出错: {e}", exc_info=True)
        
        return subcategories
    
    def _fetch_subcategories_from_overview(self, overview_url, product_code):
        """
        从"API概览"页面获取子分类
        
        Args:
            overview_url: API概览页面URL
            product_code: 产品代码
            
        Returns:
            list: 子分类列表
        """
        subcategories = []
        api_base_path = f"/api-{product_code}/"
        
        try:
            if overview_url in self.visited_urls:
                return subcategories
            
            self.visited_urls.add(overview_url)
            
            # 添加重试机制
            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = self.session.get(overview_url, timeout=30, allow_redirects=True)
                    if response.status_code == 200:
                        break
                except Exception as e:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)
                    else:
                        logger.debug(f"访问API概览页面失败: {overview_url}, 错误: {e}")
                        return subcategories
            
            if not response or response.status_code != 200:
                return subcategories
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有链接
            all_links = soup.find_all('a', href=True)
            
            # CodeArts Check等产品的子分类使用topic_格式
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).strip()
                
                if not text or not href:
                    continue
                
                # 过滤掉明显的非分类链接
                exclude_keywords = ['上一篇', '下一篇', '表', '查看PDF', 'PDF', '#', 'javascript:', '上一页', '下一页', 'API参考', '概览']
                if any(keyword in text for keyword in exclude_keywords):
                    continue
                
                # 检查是否是子分类链接（topic_格式）
                if api_base_path in href and 'topic_' in href:
                    full_url = urljoin(self.BASE_URL, href)
                    
                    # 跳过PDF和已访问的URL
                    if full_url.endswith('.pdf') or full_url in self.visited_urls:
                        continue
                    
                    # 解析URL，提取分类信息
                    parsed = urlparse(full_url)
                    path_parts = [p for p in parsed.path.split('/') if p]
                    
                    if len(path_parts) >= 2:
                        filename = path_parts[-1].split('.')[0]
                        
                        # 检查是否是子分类（topic_格式）
                        if filename.startswith('topic_'):
                            subcategories.append({
                                'name': text,
                                'url': full_url,
                                'category_id': filename,
                                'subcategories': [],
                                'apis': []
                            })
            
            # 去重
            seen_urls = set()
            unique_subcategories = []
            for subcat in subcategories:
                if subcat['url'] not in seen_urls:
                    seen_urls.add(subcat['url'])
                    unique_subcategories.append(subcat)
            
            logger.info(f"从API概览页面找到 {len(unique_subcategories)} 个子分类")
            
            return unique_subcategories
            
        except Exception as e:
            logger.error(f"从API概览页面获取子分类时出错: {e}", exc_info=True)
        
        return subcategories
    
    def _organize_categories(self, categories, product_code):
        """
        组织分类层级结构
        
        Args:
            categories: 原始分类列表
            product_code: 产品代码
            
        Returns:
            list: 组织后的分类列表，包含层级结构
        """
        organized = []
        
        # 按URL模式分类
        # 模式1: {product_code}_XX_0000 通常是分类首页
        # 模式2: {product_code}_XX_XXXX 通常是具体的API
        # 模式3: zh-cn_topic_XXXXX 可能是分类或API
        
        main_categories = {}  # key: 分类编号（如02），value: 分类信息
        
        for cat in categories:
            category_id = cat['category_id']
            
            # 检查是否是分类首页（格式：{product_code}_XX_0000）
            if category_id.startswith(f"{product_code}_"):
                parts = category_id.split('_')
                if len(parts) >= 3:
                    category_num = parts[1]  # 如 "02"
                    api_num = parts[2]  # 如 "0000"
                    
                    if api_num == "0000":
                        # 这是分类首页
                        main_categories[category_num] = {
                            'name': cat['name'],
                            'url': cat['url'],
                            'category_id': category_id,
                            'category_num': category_num,
                            'subcategories': [],
                            'apis': []
                        }
                    else:
                        # 这是具体的API，需要找到对应的分类
                        if category_num not in main_categories:
                            # 创建分类
                            main_categories[category_num] = {
                                'name': f'分类{category_num}',
                                'url': f"{self.BASE_URL}/api-{product_code}/{product_code}_{category_num}_0000.html",
                                'category_id': f"{product_code}_{category_num}_0000",
                                'category_num': category_num,
                                'subcategories': [],
                                'apis': []
                            }
                        
                        # 添加到对应分类的API列表
                        main_categories[category_num]['apis'].append({
                            'name': cat['name'],
                            'url': cat['url'],
                            'api_id': category_id
                        })
            
            # 访问分类首页，获取完整的API列表
            for category_num, category_info in main_categories.items():
                category_url = category_info['url']
                if category_url not in self.visited_urls:
                    # 访问分类页面，获取该分类下的所有API
                    apis = self._fetch_apis_from_category(category_url, product_code, category_num)
                    if apis:
                        category_info['apis'].extend(apis)
                        # 去重
                        seen_api_urls = set()
                        unique_apis = []
                        for api in category_info['apis']:
                            if api['url'] not in seen_api_urls:
                                seen_api_urls.add(api['url'])
                                unique_apis.append(api)
                        category_info['apis'] = unique_apis
            
            else:
                # 其他格式的分类（如zh-cn_topic_xxx）
                # 作为独立分类
                organized.append({
                    'name': cat['name'],
                    'url': cat['url'],
                    'category_id': category_id,
                    'subcategories': [],
                    'apis': []
                })
        
        # 添加主分类
        organized.extend(sorted(main_categories.values(), key=lambda x: x['category_num']))
        
        return organized
    
    def _fetch_apis_from_category(self, category_url, product_code, category_num):
        """
        从分类页面获取该分类下的所有API
        
        Args:
            category_url: 分类页面URL
            product_code: 产品代码
            category_num: 分类编号
            
        Returns:
            list: API列表
        """
        apis = []
        
        try:
            if category_url in self.visited_urls:
                return apis
            
            self.visited_urls.add(category_url)
            
            response = self.session.get(category_url, timeout=30, allow_redirects=True)
            if response.status_code != 200:
                return apis
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有指向API文档的链接
            all_links = soup.find_all('a', href=True)
            api_base_path = f"/api-{product_code}/"
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).strip()
                
                if not text or not href:
                    continue
                
                # 过滤掉明显的非API链接
                exclude_keywords = ['上一篇', '下一篇', '表', '查看PDF', 'PDF', '#', 'javascript:']
                if any(keyword in text for keyword in exclude_keywords):
                    continue
                
                # 检查是否是API文档链接
                if api_base_path in href:
                    full_url = urljoin(self.BASE_URL, href)
                    
                    # 跳过PDF和已访问的URL
                    if full_url.endswith('.pdf') or full_url in self.visited_urls:
                        continue
                    
                    # 检查是否是当前分类下的API（通过URL模式）
                    # 例如：ecs_02_xxxx.html 属于分类02
                    parsed = urlparse(full_url)
                    path_parts = [p for p in parsed.path.split('/') if p]
                    
                    if len(path_parts) >= 2:
                        filename = path_parts[-1].split('.')[0]
                        
                        # 检查是否属于当前分类
                        if filename.startswith(f"{product_code}_{category_num}_"):
                            apis.append({
                                'name': text,
                                'url': full_url,
                                'api_id': filename
                            })
            
        except Exception as e:
            logger.debug(f"获取分类 {category_url} 的API列表时出错: {e}")
        
        return apis
    
    def _parse_api_categories_from_menu(self, doc_url, product_code):
        """
        从产品文档首页的侧边栏菜单查找API文档分类
        
        Args:
            doc_url: 产品文档首页URL
            product_code: 产品代码
            
        Returns:
            list: 分类列表
        """
        categories = []
        api_base_path = f"/api-{product_code}/"
        
        try:
            # 尝试访问侧边栏菜单
            # 常见的侧边栏菜单URL格式
            menu_urls = [
                urljoin(doc_url, 'v3_support_leftmenu_fragment.html'),
                urljoin(doc_url, '../v3_support_leftmenu_fragment.html'),
                urljoin(doc_url, 'leftmenu.html'),
            ]
            
            for menu_url in menu_urls:
                try:
                    response = self.session.get(menu_url, timeout=30, allow_redirects=True)
                    if response.status_code != 200:
                        continue
                    
                    response.encoding = 'utf-8'
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找所有链接
                    all_links = soup.find_all('a', href=True)
                    
                    # 查找"参考"链接
                    for link in all_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True).strip()
                        
                        if not text or not href or href.startswith('javascript:'):
                            continue
                        
                        # 查找包含"参考"的链接
                        if '参考' in text:
                            ref_url = urljoin(self.BASE_URL, href)
                            
                            # 访问参考页面
                            ref_response = self.session.get(ref_url, timeout=30, allow_redirects=True)
                            if ref_response.status_code == 200:
                                ref_response.encoding = 'utf-8'
                                
                                # 在参考页面中查找API目录
                                api_dir_url = self._find_api_directory_url(ref_url, product_code)
                                
                                if api_dir_url:
                                    logger.info(f"从侧边栏菜单找到'API'目录: {api_dir_url}")
                                    
                                    # 获取子分类
                                    subcategories = self._fetch_subcategories_from_api_dir(api_dir_url, product_code)
                                    
                                    logger.info(f"产品 {product_code} 在'API'目录下找到 {len(subcategories)} 个子分类")
                                    
                                    return subcategories
                    
                    # 如果找到了菜单但没找到参考链接，跳出循环
                    break
                    
                except Exception as e:
                    logger.debug(f"访问侧边栏菜单 {menu_url} 时出错: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"从侧边栏菜单查找API分类时出错: {e}")
        
        return categories
