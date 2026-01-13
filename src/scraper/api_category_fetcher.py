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
import os

# 配置日志
# 可以通过环境变量控制日志级别，默认INFO，调试时设置为DEBUG
log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
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
        logger.debug(f"[调试] fetch_api_categories: API文档URL = {api_doc_url}")
        
        # 优先尝试从progressive_knowledge页面查找（某些产品的API文档入口在这里）
        logger.debug(f"[调试] fetch_api_categories: 优先尝试从progressive_knowledge页面查找")
        categories = self._parse_api_categories_from_progressive_knowledge(product_code, doc_url)
        logger.debug(f"[调试] fetch_api_categories: progressive_knowledge方法返回 {len(categories)} 个分类")
        
        # 如果从progressive_knowledge页面没找到，尝试解析API文档页面
        if not categories:
            logger.info(f"产品 {product_code} 从progressive_knowledge页面未找到分类，尝试解析API文档页面")
            logger.debug(f"[调试] fetch_api_categories: 开始解析API分类")
            categories = self._parse_api_categories(api_doc_url, product_code)
            logger.debug(f"[调试] fetch_api_categories: 解析结果: 找到 {len(categories)} 个分类")
        
        # 如果还是没找到，尝试直接从产品文档首页查找
        if not categories:
            logger.info(f"产品 {product_code} 从progressive_knowledge页面未找到分类，尝试直接从产品文档首页查找")
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
            
            logger.debug(f"[调试] _find_api_doc_url: 从产品文档首页查找API文档链接，找到 {len(all_links)} 个链接")
            
            # 查找API文档链接
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # 检查是否包含API相关关键词
                if any(keyword in text.lower() for keyword in ['api', '接口', '参考', 'reference']):
                    # 检查URL是否指向API文档
                    if '/api-' in href.lower() or 'api-reference' in href.lower():
                        full_url = urljoin(self.BASE_URL, href)
                        logger.debug(f"[调试] _find_api_doc_url: 找到API文档链接: {text} -> {full_url}")
                        return full_url
            
            # 也查找progressive_knowledge链接（某些产品的API文档入口在这里）
            logger.debug(f"[调试] _find_api_doc_url: 未找到API文档链接，尝试查找progressive_knowledge链接")
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if 'progressive_knowledge' in href.lower() or 'progressive' in href.lower():
                    full_url = urljoin(self.BASE_URL, href)
                    logger.debug(f"[调试] _find_api_doc_url: 找到progressive_knowledge链接: {text} -> {full_url}")
                    # progressive_knowledge链接本身不是API文档URL，但可以用于查找API分类
                    # 这里返回None，让后续流程处理
                    return None
            
            # 从JavaScript中查找progressive_knowledge链接
            import re
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # 查找progressive_knowledge URL
                    url_pattern = r'https?://[^"\'\s]+progressive[^"\'\s]*'
                    urls = re.findall(url_pattern, script.string, re.I)
                    if urls:
                        prog_url = urls[0].rstrip("';\"")
                        logger.debug(f"[调试] _find_api_doc_url: 从JavaScript中找到progressive_knowledge链接: {prog_url}")
                        # 同样返回None，让后续流程处理
                        return None
                    
                    # 查找相对路径
                    rel_pattern = r'/progressive[^"\'\s]*'
                    rel_paths = re.findall(rel_pattern, script.string, re.I)
                    if rel_paths:
                        rel_path = rel_paths[0].rstrip("';\"")
                        prog_url = urljoin(self.BASE_URL, rel_path)
                        logger.debug(f"[调试] _find_api_doc_url: 从JavaScript中找到progressive_knowledge相对路径: {rel_path} -> {prog_url}")
                        return None
            
            return None
            
        except Exception as e:
            logger.error(f"查找API文档URL时出错: {e}")
            return None
    
    def _build_api_doc_url(self, product_code):
        """构建API文档URL"""
        logger.debug(f"[调试] _build_api_doc_url: 开始为产品 {product_code} 构建API文档URL")
        
        # 常见的API文档URL格式（按优先级排序）
        # 格式1: /api-{product_code}/ (大多数产品使用)
        # 格式2: /api/{product_code}/ (某些产品使用，如cloudpipeline)
        possible_urls = [
            f"{self.BASE_URL}/api-{product_code}/",
            f"{self.BASE_URL}/api-{product_code}/index.html",
            f"{self.BASE_URL}/api/{product_code}/",  # cloudpipeline等产品使用此格式
            f"{self.BASE_URL}/api/{product_code}/index.html",
            f"{self.BASE_URL}/{product_code}/api-reference.html",
        ]
        
        logger.debug(f"[调试] _build_api_doc_url: 尝试以下URL: {possible_urls}")
        
        for url in possible_urls:
            try:
                logger.debug(f"[调试] _build_api_doc_url: 测试URL {url}")
                response = self.session.get(url, timeout=10, allow_redirects=True)
                logger.debug(f"[调试] _build_api_doc_url: URL {url} 响应: 状态码={response.status_code}, 内容长度={len(response.text)}")
                
                if response.status_code == 200:
                    # 检查是否是有效的API文档页面（不是404页面）
                    is_404 = '404' in response.text[:500].lower()
                    is_valid = len(response.text) > 1000 and not is_404
                    logger.debug(f"[调试] _build_api_doc_url: URL {url} 验证结果: 长度检查={len(response.text) > 1000}, 404检查={not is_404}, 有效={is_valid}")
                    
                    if is_valid:
                        logger.debug(f"[调试] _build_api_doc_url: 找到有效的API文档URL: {url}")
                        return url
                    else:
                        logger.debug(f"[调试] _build_api_doc_url: URL {url} 无效（404或内容太短）")
            except Exception as e:
                logger.debug(f"[调试] _build_api_doc_url: URL {url} 访问出错: {e}")
                continue
        
        # 如果首页不存在，尝试访问一个已知的API页面来推断结构
        # 华为云的API文档通常使用这种格式：
        # - /api-{product_code}/zh-cn_topic_xxxxx.html (格式1)
        # - /api-{product_code}/{product_code}_xx_xxxx.html (格式1)
        # - /api/{product_code}/{product_code}_xx_xxxx.html (格式2)
        test_patterns = [
            # 格式1: /api-{product_code}/
            f"{self.BASE_URL}/api-{product_code}/zh-cn_topic_0020805967.html",
            f"{self.BASE_URL}/api-{product_code}/zh-cn_topic_0020212668.html",
            f"{self.BASE_URL}/api-{product_code}/{product_code}_02_0001.html",
            f"{self.BASE_URL}/api-{product_code}/{product_code}_02_0000.html",
            # 格式2: /api/{product_code}/
            f"{self.BASE_URL}/api/{product_code}/{product_code}_02_0001.html",
            f"{self.BASE_URL}/api/{product_code}/{product_code}_02_0000.html",
        ]
        
        logger.debug(f"[调试] _build_api_doc_url: 尝试测试模式URL: {test_patterns}")
        
        for test_url in test_patterns:
            try:
                logger.debug(f"[调试] _build_api_doc_url: 测试模式URL {test_url}")
                response = self.session.get(test_url, timeout=10, allow_redirects=True)
                logger.debug(f"[调试] _build_api_doc_url: 模式URL {test_url} 响应: 状态码={response.status_code}, 内容长度={len(response.text)}")
                
                if response.status_code == 200 and '404' not in response.text[:500].lower():
                    # 根据URL格式返回对应的基础URL
                    if f"/api/{product_code}/" in test_url:
                        result_url = f"{self.BASE_URL}/api/{product_code}/"
                        logger.debug(f"[调试] _build_api_doc_url: 通过模式URL找到格式2的API文档URL: {result_url}")
                        return result_url
                    else:
                        result_url = f"{self.BASE_URL}/api-{product_code}/"
                        logger.debug(f"[调试] _build_api_doc_url: 通过模式URL找到格式1的API文档URL: {result_url}")
                        return result_url
            except Exception as e:
                logger.debug(f"[调试] _build_api_doc_url: 模式URL {test_url} 访问出错: {e}")
                continue
        
        # 如果都失败，优先尝试格式2（/api/{product_code}/），因为某些产品使用此格式
        fallback_url = f"{self.BASE_URL}/api/{product_code}/"
        logger.debug(f"[调试] _build_api_doc_url: 所有URL都失败，使用fallback URL: {fallback_url}")
        return fallback_url
    
    def _get_api_base_path(self, api_doc_url, product_code):
        """
        根据API文档URL确定基础路径
        
        Args:
            api_doc_url: API文档URL
            product_code: 产品代码
            
        Returns:
            str: API基础路径
        """
        if api_doc_url and f"/api/{product_code}/" in api_doc_url:
            return f"/api/{product_code}/"
        else:
            return f"/api-{product_code}/"
    
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
        api_base_path = self._get_api_base_path(api_doc_url, product_code)
        
        logger.debug(f"[调试] _parse_api_categories: API基础路径={api_base_path}, API文档URL={api_doc_url}")
        
        try:
            # 注意：多数服务的API参考没有对应页面链接，所以直接基于标准格式构建URL
            # 标准结构：API参考 -> API -> 子分类
            # 标准URL格式：{api_base_path}{product_code}_02_0000.html (API目录)
            
            # 直接构建标准的API目录URL（不依赖页面链接查找）
            logger.info(f"产品 {product_code} 直接构建标准API目录URL（多数服务没有API参考页面链接）")
            standard_api_dir_url = f"{self.BASE_URL}{api_base_path}{product_code}_02_0000.html"
            logger.debug(f"[调试] 构建的标准API目录URL: {standard_api_dir_url}")
            logger.debug(f"[调试] API基础路径: {api_base_path}, 产品代码: {product_code}")
            
            # 尝试访问标准API目录页面，获取所有子分类
            # 即使页面有重定向或验证码，也尝试直接构建子分类URL
            logger.info(f"尝试访问标准API目录URL: {standard_api_dir_url}")
            logger.debug(f"[调试] 调用 _fetch_subcategories_from_api_dir，URL: {standard_api_dir_url}")
            subcategories = self._fetch_subcategories_from_api_dir(standard_api_dir_url, product_code)
            logger.debug(f"[调试] _fetch_subcategories_from_api_dir 返回 {len(subcategories)} 个子分类")
            
            if subcategories:
                logger.info(f"产品 {product_code} 通过标准URL找到 {len(subcategories)} 个子分类")
                return subcategories
            
            # 如果标准URL没有找到子分类，尝试从页面查找（作为fallback）
            logger.debug(f"[调试] 标准URL未找到子分类，尝试从页面查找（fallback）")
            
            # 第一步：尝试找到"API参考"页面（可选，很多服务没有）
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
                    
                    if subcategories:
                        return subcategories
            
            # Fallback: 如果找不到"API参考"，尝试直接从API文档首页查找API目录
            logger.debug(f"[调试] 尝试直接从API文档首页查找API目录")
            api_dir_url = self._find_api_directory_url(api_doc_url, product_code)
            
            if api_dir_url:
                logger.info(f"从API文档首页找到'API'目录: {api_dir_url}")
                
                # 访问"API"目录页面，获取所有子分类
                subcategories = self._fetch_subcategories_from_api_dir(api_dir_url, product_code)
                
                logger.info(f"产品 {product_code} 在'API'目录下找到 {len(subcategories)} 个子分类")
                
                if subcategories:
                    return subcategories
            
            # 如果所有方法都失败，返回空列表
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
        api_base_path = self._get_api_base_path(api_doc_url, product_code)
        logger.debug(f"[调试] 查找API参考分类，API基础路径: {api_base_path}, URL: {api_doc_url}")
        
        # 尝试访问几个可能的API页面来查找"API参考"
        test_urls = [
            f"{self.BASE_URL}/api-{product_code}/zh-cn_topic_0020212668.html",  # ECS示例格式
            f"{self.BASE_URL}/api-{product_code}/{product_code}_02_0001.html",  # 另一种格式
            api_doc_url,  # 传入的URL
        ]
        
        logger.debug(f"[调试] 尝试访问以下URL查找API参考: {test_urls}")
        
        for url in test_urls:
            try:
                logger.debug(f"[调试] 访问URL: {url}")
                resp = self.session.get(url, timeout=30, allow_redirects=True)
                logger.debug(f"[调试] URL {url} 响应: 状态码={resp.status_code}, 内容长度={len(resp.text)}")
                
                if resp.status_code != 200:
                    logger.debug(f"[调试] URL {url} 状态码不是200，跳过")
                    continue
                
                resp.encoding = 'utf-8'
                
                # 检查是否是验证码页面
                is_captcha = 'captcha' in resp.text.lower() or 'tcaptcha' in resp.text.lower() or len(resp.text) < 1000
                if is_captcha:
                    logger.debug(f"[调试] URL {url} 是验证码页面，内容长度={len(resp.text)}")
                    logger.debug(f"[调试] 页面内容预览: {resp.text[:200]}")
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # 查找所有链接
                all_links = soup.find_all('a', href=True)
                logger.debug(f"[调试] URL {url} 找到 {len(all_links)} 个链接")
                
                # 优先级1: 查找完全匹配"API参考"的链接
                logger.debug(f"[调试] 优先级1: 查找完全匹配'API参考'的链接，API基础路径: {api_base_path}")
                api_ref_candidates = []
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).strip()
                    
                    # 调试：显示所有包含api_base_path的链接
                    if api_base_path in href:
                        logger.debug(f"[调试] 找到包含API基础路径的链接: '{text}' -> {href}")
                    
                    if api_base_path in href and ('API参考' in text or 'api参考' in text.lower()):
                        full_url = urljoin(self.BASE_URL, href)
                        
                        # 解析URL，提取分类信息
                        parsed = urlparse(full_url)
                        path_parts = [p for p in parsed.path.split('/') if p]
                        
                        if len(path_parts) >= 2:
                            filename = path_parts[-1].split('.')[0] if path_parts[-1] else path_parts[-2]
                            
                            logger.info(f"找到'API参考'分类（完全匹配）: {text} -> {full_url}")
                            logger.debug(f"[调试] API参考分类详情: name={text}, url={full_url}, category_id={filename}")
                            return {
                                'name': text,
                                'url': full_url,
                                'category_id': filename
                            }
                
                if not api_ref_candidates:
                    logger.debug(f"[调试] 优先级1: 未找到完全匹配'API参考'的链接")
                
                # 优先级2: 查找包含"参考"或"reference"的链接
                # 排除非API参考的分类，如"如何调用API"、"API概览"等
                exclude_keywords = ['如何调用', '概览', '概述', '介绍', '说明', '指南', 'guide', 'overview', 'introduction']
                
                logger.debug(f"[调试] 优先级2: 查找包含'参考'或'reference'的链接")
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
                            
                            logger.debug(f"[调试] 找到候选API参考链接: '{text}' -> {full_url}, 优先级={priority}")
                            reference_candidates.append({
                                'name': text,
                                'url': full_url,
                                'category_id': filename,
                                'priority': priority
                            })
                
                logger.debug(f"[调试] 优先级2: 找到 {len(reference_candidates)} 个候选链接")
                
                # 按优先级排序，返回优先级最高的
                if reference_candidates:
                    reference_candidates.sort(key=lambda x: x['priority'])
                    best_match = reference_candidates[0]
                    logger.info(f"找到'API参考'分类（模糊匹配）: {best_match['name']} -> {best_match['url']}")
                    logger.debug(f"[调试] 选择最佳匹配: {best_match}")
                    return {
                        'name': best_match['name'],
                        'url': best_match['url'],
                        'category_id': best_match['category_id']
                    }
                else:
                    logger.debug(f"[调试] 优先级2: 未找到候选链接")
            except Exception as e:
                logger.debug(f"[调试] 访问URL {url} 时出错: {e}")
                import traceback
                logger.debug(f"[调试] 错误详情: {traceback.format_exc()}")
                continue
        
        logger.debug(f"[调试] 所有URL都未找到API参考分类")
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
        api_base_path = self._get_api_base_path(api_ref_url, product_code)
        logger.debug(f"[调试] 查找API目录URL，API参考URL: {api_ref_url}, API基础路径: {api_base_path}")
        
        try:
            logger.debug(f"[调试] 访问API参考页面: {api_ref_url}")
            response = self.session.get(api_ref_url, timeout=30, allow_redirects=True)
            logger.debug(f"[调试] API参考页面响应: 状态码={response.status_code}, 内容长度={len(response.text)}")
            
            if response.status_code != 200:
                logger.debug(f"[调试] API参考页面状态码不是200，尝试直接构建URL")
                # 如果无法访问，尝试直接构建URL
                return self._build_api_directory_url(product_code, api_base_path)
            
            response.encoding = 'utf-8'
            
            # 检查是否是验证码页面
            is_captcha = 'captcha' in response.text.lower() or 'tcaptcha' in response.text.lower() or len(response.text) < 1000
            if is_captcha:
                logger.debug(f"[调试] API参考页面是验证码页面，内容长度={len(response.text)}")
                logger.debug(f"[调试] 页面内容预览: {response.text[:300]}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有链接
            all_links = soup.find_all('a', href=True)
            logger.debug(f"[调试] API参考页面找到 {len(all_links)} 个链接")
            
            # 优先级1: 查找指向API目录的链接（格式：{product_code}_02_0000.html）
            api_dir_pattern = f"{product_code}_02_0000"
            logger.debug(f"[调试] 优先级1: 查找包含API目录模式的链接，模式: {api_dir_pattern}")
            
            # 显示所有包含api_base_path的链接（用于调试）
            matching_links = []
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).strip()
                if api_base_path in href:
                    matching_links.append((text, href))
            
            logger.debug(f"[调试] 找到 {len(matching_links)} 个包含API基础路径的链接:")
            for text, href in matching_links[:10]:  # 只显示前10个
                logger.debug(f"[调试]   '{text}' -> {href}")
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).strip()
                
                if api_base_path in href and api_dir_pattern in href:
                    full_url = urljoin(self.BASE_URL, href)
                    logger.debug(f"[调试] 找到匹配API目录模式的链接: '{text}' -> {full_url}")
                    # 验证URL是否可访问
                    if self._verify_url(full_url):
                        logger.info(f"通过URL模式找到API目录: {full_url}")
                        return full_url
                    else:
                        logger.debug(f"[调试] URL验证失败: {full_url}")
            
            # 优先级2: 查找名称包含"API"且URL符合API目录模式的链接
            # 匹配模式：链接文本包含"API"，且URL包含 {product_code}_02_ 模式
            # 排除非API目录的分类，如"如何调用API"、"API概览"等
            exclude_keywords = ['如何调用', '概览', '概述', '介绍', '说明', '指南', 'guide', 'overview', 'introduction']
            
            logger.debug(f"[调试] 优先级2: 查找名称包含'API'的链接")
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
                                logger.debug(f"[调试] 找到候选API目录链接: '{text}' -> {full_url}, 优先级={priority}")
                                api_candidates.append({
                                    'text': text,
                                    'url': full_url,
                                    'href': href,
                                    'priority': priority
                                })
                            break
            
            logger.debug(f"[调试] 优先级2: 找到 {len(api_candidates)} 个候选链接")
            
            # 按优先级排序
            api_candidates.sort(key=lambda x: x['priority'])
            
            # 验证候选URL，返回第一个可访问的
            for candidate in api_candidates:
                logger.debug(f"[调试] 验证候选URL: {candidate['url']}")
                if self._verify_url(candidate['url']):
                    logger.info(f"通过链接文本找到API目录: {candidate['text']} -> {candidate['url']}")
                    return candidate['url']
                else:
                    logger.debug(f"[调试] 候选URL验证失败: {candidate['url']}")
            
            # 优先级3: 如果没找到，尝试直接构建URL
            logger.debug(f"[调试] 优先级3: 尝试直接构建API目录URL")
            built_url = self._build_api_directory_url(product_code, api_base_path)
            if built_url:
                logger.info(f"通过构建URL找到API目录: {built_url}")
                return built_url
            else:
                logger.debug(f"[调试] 直接构建URL失败")
            
            logger.warning(f"产品 {product_code} 未找到API目录链接")
            logger.debug(f"[调试] 所有方法都未找到API目录链接")
            return None
            
        except Exception as e:
            logger.debug(f"查找API目录URL时出错: {e}")
            # 出错时也尝试直接构建URL
            return self._build_api_directory_url(product_code)
    
    def _build_api_directory_url(self, product_code, api_base_path=None):
        """
        直接构建API目录URL
        
        Args:
            product_code: 产品代码
            api_base_path: API基础路径，如果为None则使用默认格式
            
        Returns:
            str: API目录URL，如果不可访问返回None
        """
        if api_base_path is None:
            # 默认使用格式1，但会在调用时根据实际URL调整
            api_base_path = f"/api-{product_code}/"
        
        # 常见的API目录URL格式：{product_code}_02_0000.html
        possible_urls = [
            f"{self.BASE_URL}{api_base_path}{product_code}_02_0000.html",
            f"{self.BASE_URL}{api_base_path}api.html",
            f"{self.BASE_URL}{api_base_path}index.html",
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
            is_200 = response.status_code == 200
            # 检查是否是有效的API文档页面（不是重定向页面）
            if is_200:
                # 检查是否有JavaScript重定向（说明页面无效）
                has_redirect = 'window.location.href' in response.text[:1000] or 'location.href' in response.text[:1000]
                is_valid = len(response.text) > 1000 and not has_redirect
                logger.debug(f"[调试] _verify_url: {url} - 状态码={response.status_code}, 长度={len(response.text)}, 有重定向={has_redirect}, 有效={is_valid}")
                return is_valid
            else:
                logger.debug(f"[调试] _verify_url: {url} - 状态码={response.status_code}, 无效")
                return False
        except Exception as e:
            logger.debug(f"[调试] _verify_url: {url} - 访问出错: {e}")
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
        api_base_path = self._get_api_base_path(api_dir_url, product_code)
        
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
            
            # 检查是否是验证码页面或重定向页面
            page_text = response.text.lower()
            is_captcha_page = 'captcha' in page_text or 'tcaptcha' in page_text or len(response.text) < 1000
            has_redirect = 'window.location.href' in response.text[:1000] or 'location.href' in response.text[:1000]
            
            logger.debug(f"[调试] API目录页面检查: URL={api_dir_url}, 状态码={response.status_code}, 内容长度={len(response.text)}, 是验证码页面={is_captcha_page}, 有重定向={has_redirect}")
            
            if has_redirect:
                logger.warning(f"[调试] API目录页面包含JavaScript重定向，页面可能无效")
                # 提取重定向目标
                import re
                redirect_pattern = r'location\.href\s*=\s*["\']([^"\']+)["\']'
                redirects = re.findall(redirect_pattern, response.text)
                if redirects:
                    logger.debug(f"[调试] 重定向目标: {redirects[:3]}")
            
            if is_captcha_page or has_redirect:
                logger.warning(f"检测到验证码页面或重定向页面，尝试直接构建API子分类URL")
                logger.debug(f"[调试] 页面内容预览: {response.text[:500]}")
                # 即使有验证码或重定向，也尝试直接构建可能的API子分类URL
                # 标准格式：{product_code}_02_XXXX.html
                # 注意：多数服务的API参考没有页面链接，所以直接基于标准格式构建
                logger.debug(f"[调试] 调用 _try_build_subcategories_directly")
                result = self._try_build_subcategories_directly(product_code, api_dir_url)
                logger.debug(f"[调试] _try_build_subcategories_directly 返回 {len(result)} 个子分类")
                return result
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有链接
            all_links = soup.find_all('a', href=True)
            logger.debug(f"[调试] _fetch_subcategories_from_api_dir: 找到 {len(all_links)} 个链接")
            
            # 显示前20个链接用于调试
            if len(all_links) > 0:
                logger.debug(f"[调试] 前20个链接:")
                for i, link in enumerate(all_links[:20]):
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    logger.debug(f"[调试]   {i+1}. '{text[:50]}' -> {href[:80]}")
            else:
                logger.warning(f"[调试] 页面没有找到任何链接！可能是JavaScript动态加载或重定向页面")
            
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
        api_base_path = self._get_api_base_path(overview_url, product_code)
        
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
    
    def _try_build_subcategories_directly(self, product_code, api_dir_url):
        """
        当遇到验证码页面或重定向页面时，尝试直接构建API子分类URL
        
        注意：多数服务的API参考没有对应页面链接，所以直接基于标准格式构建URL
        
        标准格式：{product_code}_02_XXXX.html
        常见的子分类编号：0001, 0002, 0003, 0100, 0200等
        
        Args:
            product_code: 产品代码
            api_dir_url: API目录URL
            
        Returns:
            list: 子分类列表
        """
        subcategories = []
        api_base_path = self._get_api_base_path(api_dir_url, product_code)
        logger.debug(f"[调试] _try_build_subcategories_directly: 产品={product_code}, API基础路径={api_base_path}, API目录URL={api_dir_url}")
        
        try:
            # 从API目录URL推断格式
            if f"{product_code}_02_0000" in api_dir_url:
                pattern = f"{product_code}_02_"
            elif f"{product_code}_api_0000" in api_dir_url:
                pattern = f"{product_code}_api_"
            else:
                # 默认使用标准格式
                pattern = f"{product_code}_02_"
            
            logger.debug(f"[调试] _try_build_subcategories_directly: 使用模式={pattern}")
            
            # 尝试常见的子分类编号
            # 通常从0001开始，但有些产品可能从0100或0200开始
            # 由于验证码保护或重定向，我们限制尝试的数量，只尝试最常见的编号
            test_numbers = []
            
            # 先尝试最常见的几个编号（0001-0010，扩大范围）
            for i in range(1, 11):
                test_numbers.append(f"{i:04d}")
            
            # 再尝试0100-1000（某些产品使用，步长为100）
            for i in range(1, 11):
                test_numbers.append(f"{i:02d}00")
            
            logger.debug(f"[调试] _try_build_subcategories_directly: 将尝试 {len(test_numbers)} 个编号: {test_numbers[:10]}...")
            
            # 尝试访问这些URL，如果可访问则添加到子分类列表
            # 即使遇到验证码页面，也尝试构建基本的API分类结构
            for num in test_numbers:
                test_url = f"{self.BASE_URL}{api_base_path}{pattern}{num}.html"
                
                try:
                    # 快速检查URL是否存在（使用HEAD请求，如果失败则用GET）
                    response = self.session.head(test_url, timeout=5, allow_redirects=True)
                    status_ok = response.status_code == 200
                    
                    if not status_ok:
                        # HEAD可能不被支持，尝试GET但只读取部分内容
                        response = self.session.get(test_url, timeout=5, allow_redirects=True, stream=True)
                        # 只读取前1KB来判断是否是有效页面
                        content = next(response.iter_content(1024), b'')
                        response.close()
                        
                        status_ok = response.status_code == 200
                        
                        # 检查页面类型（验证码、重定向等）
                        content_text = content.decode('utf-8', errors='ignore').lower()
                        is_captcha = 'captcha' in content_text or 'tcaptcha' in content_text
                        has_redirect = 'window.location.href' in content_text or 'location.href' in content_text
                        
                        logger.debug(f"[调试] _try_build_subcategories_directly: URL {test_url} - 状态码={response.status_code}, 验证码={is_captcha}, 重定向={has_redirect}")
                        
                        # 如果状态码是200，即使有验证码或重定向也尝试构建分类
                        # 注意：多数服务的API参考没有页面链接，URL格式正确就应该构建分类
                        if status_ok:
                            try:
                                full_response = self.session.get(test_url, timeout=10, allow_redirects=True)
                                if full_response.status_code == 200:
                                    full_response.encoding = 'utf-8'
                                    
                                    # 检查页面类型
                                    content_lower = full_response.text.lower()
                                    is_captcha_page = 'captcha' in content_lower or 'tcaptcha' in content_lower
                                    has_redirect_page = 'window.location.href' in full_response.text[:1000] or 'location.href' in full_response.text[:1000]
                                    is_small_page = len(full_response.text) < 1000
                                    is_help_center = '帮助中心' in full_response.text[:500] or 'help center' in content_lower[:500]
                                    
                                    # 如果页面是验证码、重定向、内容很少或是帮助中心页面，基于标准格式构建分类
                                    # 因为多数服务的API参考没有页面链接，URL格式正确就应该构建
                                    if is_captcha_page or has_redirect_page or is_small_page or is_help_center:
                                        title = f"API分类 {num}"
                                        subcategories.append({
                                            'name': title,
                                            'url': test_url,
                                            'category_id': f"{pattern}{num}",
                                            'subcategories': [],
                                            'apis': []
                                        })
                                        page_type = []
                                        if is_captcha_page:
                                            page_type.append('验证码')
                                        if has_redirect_page:
                                            page_type.append('重定向')
                                        if is_small_page:
                                            page_type.append('内容少')
                                        if is_help_center:
                                            page_type.append('帮助中心')
                                        logger.info(f"基于标准格式构建子分类（URL格式正确，页面类型: {', '.join(page_type)}）: {title} -> {test_url}")
                                        continue
                                    
                                    soup = BeautifulSoup(full_response.text, 'html.parser')
                                    
                                    # 获取页面标题
                                    title_tag = soup.find('title')
                                    title = title_tag.get_text(strip=True) if title_tag else f"API分类 {num}"
                                    
                                    # 过滤掉明显的错误页面和帮助中心页面
                                    if '404' not in title.lower() and 'error' not in title.lower() and '帮助中心' not in title:
                                        subcategories.append({
                                            'name': title,
                                            'url': test_url,
                                            'category_id': f"{pattern}{num}",
                                            'subcategories': [],
                                            'apis': []
                                        })
                                        logger.info(f"通过直接构建找到子分类: {title} -> {test_url}")
                            except Exception as e:
                                # 如果无法获取页面内容，但URL存在，也构建基本分类
                                # 因为多数服务的API参考没有页面链接，URL格式正确就应该构建
                                logger.debug(f"无法获取页面内容，但URL存在，构建基本分类: {test_url}, 错误: {e}")
                                title = f"API分类 {num}"
                                subcategories.append({
                                    'name': title,
                                    'url': test_url,
                                    'category_id': f"{pattern}{num}",
                                    'subcategories': [],
                                    'apis': []
                                })
                                logger.info(f"基于标准格式构建子分类（无法获取内容，但URL格式正确）: {title} -> {test_url}")
                except Exception as e:
                    # 忽略单个URL的错误，继续尝试下一个
                    logger.debug(f"尝试访问 {test_url} 时出错: {e}")
                    continue
            
            # 如果找到了一些子分类，返回它们
            if subcategories:
                logger.info(f"通过直接构建找到 {len(subcategories)} 个子分类")
                return subcategories
            else:
                logger.warning(f"无法通过直接构建找到子分类，可能需要手动访问页面")
                return []
                
        except Exception as e:
            logger.error(f"直接构建子分类时出错: {e}", exc_info=True)
        
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
        # 从侧边栏菜单无法直接确定API基础路径，使用默认格式
        # 实际会在找到API链接后根据链接调整
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
    
    def _parse_api_categories_from_progressive_knowledge(self, product_code, doc_url):
        """
        从progressive_knowledge页面查找API文档分类
        
        某些产品（如pipeline）的API文档入口在progressive_knowledge页面
        
        Args:
            product_code: 产品代码
            doc_url: 产品文档首页URL
            
        Returns:
            list: 分类列表
        """
        categories = []
        
        try:
            # 产品代码映射：某些产品的API文档使用不同的产品代码
            # 例如：cloudpipeline -> pipeline
            api_product_code = self._get_api_product_code(product_code)
            logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 产品代码映射 {product_code} -> {api_product_code}")
            
            # 首先尝试从产品文档首页查找progressive_knowledge链接
            prog_knowledge_url = None
            
            try:
                response = self.session.get(doc_url, timeout=30)
                if response.status_code == 200:
                    response.encoding = 'utf-8'
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 从链接中查找
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        href = link.get('href', '')
                        if 'progressive_knowledge' in href.lower():
                            prog_knowledge_url = urljoin(self.BASE_URL, href)
                            logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 从产品文档首页找到progressive_knowledge链接: {prog_knowledge_url}")
                            break
                    
                    # 如果没找到，从JavaScript中查找
                    if not prog_knowledge_url:
                        import re
                        scripts = soup.find_all('script')
                        for script in scripts:
                            if script.string:
                                # 查找完整URL
                                url_pattern = r'https?://[^"\'\s]+progressive[^"\'\s]*'
                                urls = re.findall(url_pattern, script.string, re.I)
                                if urls:
                                    prog_knowledge_url = urls[0].rstrip("';\"")
                                    logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 从JavaScript中找到progressive_knowledge URL: {prog_knowledge_url}")
                                    break
                                
                                # 查找相对路径
                                rel_pattern = r'/progressive[^"\'\s]*'
                                rel_paths = re.findall(rel_pattern, script.string, re.I)
                                if rel_paths:
                                    rel_path = rel_paths[0].rstrip("';\"")
                                    prog_knowledge_url = urljoin(self.BASE_URL, rel_path)
                                    logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 从JavaScript中找到progressive_knowledge相对路径: {rel_path} -> {prog_knowledge_url}")
                                    break
            except Exception as e:
                logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 从产品文档首页查找progressive_knowledge链接时出错: {e}")
            
            # 如果没找到，构建progressive_knowledge URL
            # 格式：/progressive_knowledge/{api_product_code}.html
            if not prog_knowledge_url:
                prog_knowledge_url = f"{self.BASE_URL}/progressive_knowledge/{api_product_code}.html"
                logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 构建progressive_knowledge URL: {prog_knowledge_url}")
            
            logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 访问URL {prog_knowledge_url}")
            
            try:
                response = self.session.get(prog_knowledge_url, timeout=30, allow_redirects=True)
                logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 响应状态码={response.status_code}, 内容长度={len(response.text)}")
                
                if response.status_code != 200:
                    logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: URL不可访问")
                    return categories
                
                response.encoding = 'utf-8'
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 查找指向API概览的链接
                all_links = soup.find_all('a', href=True)
                api_overview_url = None
                
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).strip()
                    
                    # 查找"API概览"链接
                    if '/api-' in href and ('概览' in text or 'overview' in text.lower()):
                        api_overview_url = urljoin(self.BASE_URL, href)
                        logger.info(f"从progressive_knowledge页面找到API概览链接: {api_overview_url}")
                        break
                
                # 如果找到API概览链接，从该页面提取API分类
                if api_overview_url:
                    categories = self._extract_categories_from_api_overview(api_overview_url, api_product_code)
                    if categories:
                        logger.info(f"从API概览页面提取到 {len(categories)} 个API分类")
                        return categories
                
                # 如果没有找到API概览，尝试直接构建API概览URL
                # 某些产品使用 pipeline_03_0005.html 格式
                possible_api_overview_urls = [
                    f"{self.BASE_URL}/api-{api_product_code}/{api_product_code}_03_0005.html",
                    f"{self.BASE_URL}/api-{api_product_code}/{api_product_code}_03_0000.html",
                    f"{self.BASE_URL}/api-{api_product_code}/{api_product_code}_02_0000.html",
                ]
                
                for overview_url in possible_api_overview_urls:
                    logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 尝试直接访问API概览URL {overview_url}")
                    categories = self._extract_categories_from_api_overview(overview_url, api_product_code)
                    if categories:
                        logger.info(f"从API概览URL {overview_url} 提取到 {len(categories)} 个API分类")
                        return categories
                
                # 对于pipeline产品，如果从概览页面没找到，尝试直接从progressive_knowledge页面提取所有分类链接
                if api_product_code == 'pipeline':
                    logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 尝试直接从progressive_knowledge页面提取pipeline分类链接")
                    api_base_path = f"/api-{api_product_code}/"
                    all_links = soup.find_all('a', href=True)
                    
                    seen_urls = set()
                    for link in all_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True).strip()
                        
                        if not text or not href:
                            continue
                        
                        # 过滤掉明显的非分类链接
                        exclude_keywords = ['上一篇', '下一篇', '表', '查看PDF', 'PDF', '#', 'javascript:', '上一页', '下一页', 'API参考', '概览', '如何调用']
                        if any(keyword in text for keyword in exclude_keywords):
                            continue
                        
                        # 检查是否是分类链接（pipeline产品使用pipeline_03_XXXX.html格式）
                        if api_base_path in href:
                            full_url = urljoin(self.BASE_URL, href)
                            
                            if full_url.endswith('.pdf') or full_url in seen_urls:
                                continue
                            
                            filename = full_url.split('/')[-1].split('.')[0]
                            
                            # 检查是否是分类页面（pipeline_03_XXXX.html，XXXX不是0000或0005）
                            is_category = False
                            if f"{api_product_code}_03_" in filename:
                                # 排除概览页面和目录页面
                                if not filename.endswith('_0000') and not filename.endswith('_0005'):
                                    is_category = True
                            
                            if is_category:
                                seen_urls.add(full_url)
                                category_id = filename
                                categories.append({
                                    'name': text,
                                    'url': full_url,
                                    'category_id': category_id,
                                    'subcategories': [],
                                    'apis': []
                                })
                                logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 从progressive_knowledge页面提取到分类: {text} -> {full_url}")
                    
                    if categories:
                        logger.info(f"从progressive_knowledge页面直接提取到 {len(categories)} 个API分类")
                        return categories
                
            except Exception as e:
                logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 访问progressive_knowledge页面出错: {e}")
                import traceback
                logger.debug(f"[调试] 错误详情: {traceback.format_exc()}")
                
        except Exception as e:
            logger.debug(f"[调试] _parse_api_categories_from_progressive_knowledge: 出错: {e}")
            import traceback
            logger.debug(f"[调试] 错误详情: {traceback.format_exc()}")
        
        return categories
    
    def _get_api_product_code(self, product_code):
        """
        获取API文档使用的产品代码（可能需要映射）
        
        某些产品的API文档使用不同的产品代码
        例如：cloudpipeline -> pipeline
        
        Args:
            product_code: 原始产品代码
            
        Returns:
            str: API文档使用的产品代码
        """
        # 产品代码映射表
        code_mapping = {
            'cloudpipeline': 'pipeline',  # cloudpipeline的API文档使用pipeline
        }
        
        return code_mapping.get(product_code, product_code)
    
    def _extract_categories_from_api_overview(self, api_overview_url, api_product_code):
        """
        从API概览页面提取API分类列表
        
        API概览页面通常包含一个表格，列出所有API分类
        
        Args:
            api_overview_url: API概览页面URL
            api_product_code: API文档使用的产品代码
            
        Returns:
            list: API分类列表
        """
        categories = []
        
        try:
            logger.debug(f"[调试] _extract_categories_from_api_overview: 访问API概览页面 {api_overview_url}")
            
            response = self.session.get(api_overview_url, timeout=30, allow_redirects=True)
            if response.status_code != 200:
                logger.debug(f"[调试] _extract_categories_from_api_overview: 页面不可访问，状态码={response.status_code}")
                return categories
            
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 方法1: 查找表格（API分类通常在表格中）
            tables = soup.find_all('table')
            logger.debug(f"[调试] _extract_categories_from_api_overview: 找到 {len(tables)} 个表格")
            
            for table in tables:
                rows = table.find_all('tr')
                
                # 查找表头，确认是否是API分类表格
                headers = []
                if rows:
                    header_row = rows[0]
                    header_cells = header_row.find_all(['th', 'td'])
                    headers = [cell.get_text(strip=True) for cell in header_cells]
                    
                    # 检查是否包含"分类"、"接口"等关键词
                    if any(keyword in ' '.join(headers).lower() for keyword in ['分类', '接口', 'category', 'api']):
                        logger.debug(f"[调试] _extract_categories_from_api_overview: 找到API分类表格，表头: {headers}")
                        
                        # 从表格行中提取API分类
                        for row in rows[1:]:  # 跳过表头
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 1:  # 至少有一列
                                # 第一列通常是分类名称
                                category_name = cells[0].get_text(strip=True)
                                
                                # 查找分类链接
                                category_link = cells[0].find('a', href=True)
                                if not category_link:
                                    # 如果第一列没有链接，尝试在整个行中查找
                                    category_link = row.find('a', href=True)
                                
                                if category_link:
                                    href = category_link.get('href', '')
                                    category_url = urljoin(self.BASE_URL, href)
                                    
                                    # 提取分类ID（从URL中）
                                    category_id = href.split('/')[-1].split('.')[0] if href else category_name.lower().replace(' ', '_')
                                    
                                    # 排除导航链接和PDF链接
                                    if not category_url.endswith('.pdf') and '/api-' in category_url:
                                        # 检查是否已存在（去重）
                                        if not any(cat['url'] == category_url for cat in categories):
                                            categories.append({
                                                'name': category_name,
                                                'url': category_url,
                                                'category_id': category_id,
                                                'subcategories': [],
                                                'apis': []
                                            })
                                            logger.debug(f"[调试] _extract_categories_from_api_overview: 提取到分类: {category_name} -> {category_url}")
            
            # 方法2: 如果表格方法没找到，尝试从链接列表提取（某些产品使用列表而非表格）
            if not categories:
                logger.debug(f"[调试] _extract_categories_from_api_overview: 表格方法未找到分类，尝试从链接列表提取")
                api_base_path = f"/api-{api_product_code}/"
                all_links = soup.find_all('a', href=True)
                
                seen_urls = set()
                for link in all_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True).strip()
                    
                    if not text or not href:
                        continue
                    
                    # 过滤掉明显的非分类链接
                    exclude_keywords = ['上一篇', '下一篇', '表', '查看PDF', 'PDF', '#', 'javascript:', '上一页', '下一页', 'API参考', '概览', '如何调用']
                    if any(keyword in text for keyword in exclude_keywords):
                        continue
                    
                    # 检查是否是分类链接（pipeline产品使用pipeline_03_XXXX.html格式）
                    if api_base_path in href:
                        full_url = urljoin(self.BASE_URL, href)
                        
                        if full_url.endswith('.pdf') or full_url in seen_urls:
                            continue
                        
                        filename = full_url.split('/')[-1].split('.')[0]
                        
                        # 检查是否是分类页面（pipeline_03_XXXX.html，XXXX不是0000或0005）
                        is_category = False
                        if f"{api_product_code}_03_" in filename:
                            # 排除概览页面和目录页面
                            if not filename.endswith('_0000') and not filename.endswith('_0005'):
                                is_category = True
                        
                        if is_category:
                            seen_urls.add(full_url)
                            category_id = filename
                            categories.append({
                                'name': text,
                                'url': full_url,
                                'category_id': category_id,
                                'subcategories': [],
                                'apis': []
                            })
                            logger.debug(f"[调试] _extract_categories_from_api_overview: 从链接列表提取到分类: {text} -> {full_url}")
            
            logger.debug(f"[调试] _extract_categories_from_api_overview: 共提取到 {len(categories)} 个分类")
            
        except Exception as e:
            logger.debug(f"[调试] _extract_categories_from_api_overview: 出错: {e}")
            import traceback
            logger.debug(f"[调试] 错误详情: {traceback.format_exc()}")
        
        return categories
