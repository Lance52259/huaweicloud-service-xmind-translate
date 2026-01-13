#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
华为云产品列表抓取模块
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductFetcher:
    """华为云产品列表抓取器"""
    
    BASE_URL = "https://support.huaweicloud.com"
    PRODUCT_PAGE_URL = "https://www.huaweicloud.com/product/"
    
    def __init__(self):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch_all_products(self):
        """
        从华为云产品页面获取所有产品列表
        
        Returns:
            list: 产品列表，每个产品包含 name, url, doc_url 等信息
        """
        products = []
        
        # 方法1: 从产品页面获取产品列表
        logger.info(f"开始访问产品页面: {self.PRODUCT_PAGE_URL}")
        products_from_product_page = self._fetch_from_product_page()
        products.extend(products_from_product_page)
        
        # 方法2: 从支持中心首页获取产品列表（作为补充）
        logger.info(f"开始访问支持中心: {self.BASE_URL}")
        products_from_support = self._fetch_from_support_page()
        products.extend(products_from_support)
        
        # 去重
        products = self._deduplicate_products(products)
        
        # 过滤掉非产品链接
        products = self._filter_products(products)
        
        logger.info(f"共找到 {len(products)} 个产品")
        return products
    
    def _fetch_from_product_page(self):
        """从产品页面获取产品列表"""
        products = []
        
        try:
            response = self.session.get(self.PRODUCT_PAGE_URL, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.error(f"请求产品页面失败，状态码: {response.status_code}")
                return []
            
            logger.info("产品页面获取成功，开始解析...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找所有产品链接
            all_links = soup.find_all('a', href=True)
            
            seen_urls = set()  # 用于去重
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if not href or not text or len(text.strip()) < 2:
                    continue
                
                # 规范化href
                if href.startswith('//'):
                    href = f"https:{href}"
                elif href.startswith('/'):
                    href = f"https://www.huaweicloud.com{href}"
                elif not href.startswith('http'):
                    continue
                
                # 查找产品页面链接（www.huaweicloud.com/product/xxx.html）
                href_lower = href.lower()
                if 'www.huaweicloud.com/product/' in href_lower and href_lower.endswith('.html'):
                    # 去重：如果URL已经处理过，跳过
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    # 提取产品代码（从URL中）
                    product_code = self._extract_product_code_from_url(href)
                    
                    if product_code:
                        # 构建文档URL（通常格式为 support.huaweicloud.com/{product_code}/）
                        doc_url = f"{self.BASE_URL}/{product_code}/index.html"
                        
                        products.append({
                            'name': text.strip(),
                            'url': href,
                            'doc_url': doc_url,
                            'product_code': product_code,
                            'source': 'product_page'
                        })
            
            logger.info(f"从产品页面找到 {len(products)} 个产品")
            return products
            
        except Exception as e:
            logger.error(f"解析产品页面异常: {e}", exc_info=True)
            return []
    
    def _fetch_from_support_page(self):
        """从支持中心首页获取产品列表"""
        products = []
        
        try:
            response = self.session.get(self.BASE_URL, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                logger.error(f"请求支持页面失败，状态码: {response.status_code}")
                return []
            
            logger.info("支持页面获取成功，开始解析...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试多种方式查找产品链接
            # 方法1: 从导航菜单
            products.extend(self._extract_products_from_nav(soup))
            
            # 方法2: 从所有链接
            products.extend(self._extract_products_from_links(soup))
            
            # 方法3: 从所有链接（更全面）
            products.extend(self._extract_products_from_all_links(soup))
            
            logger.info(f"从支持页面找到 {len(products)} 个产品")
            return products
            
        except Exception as e:
            logger.error(f"解析支持页面异常: {e}", exc_info=True)
            return []
    
    def _extract_product_code_from_url(self, url):
        """
        从产品URL中提取产品代码
        
        Args:
            url: 产品URL，如 https://www.huaweicloud.com/product/ecs.html
            
        Returns:
            str: 产品代码，如 'ecs'
        """
        try:
            # 提取URL中的产品代码
            # 格式: https://www.huaweicloud.com/product/{product_code}.html
            if '/product/' in url:
                parts = url.split('/product/')
                if len(parts) > 1:
                    product_part = parts[1].split('.')[0].split('/')[0]
                    return product_part.lower()
        except Exception:
            pass
        
        return None
    
    def _extract_products_from_nav(self, soup):
        """从导航菜单中提取产品"""
        products = []
        
        # 查找常见的导航菜单选择器
        nav_selectors = [
            'nav a',
            '.nav a',
            '.navbar a',
            '.menu a',
            '.product-list a',
            '.service-list a',
            '[class*="product"] a',
            '[class*="service"] a',
        ]
        
        for selector in nav_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href and text and self._is_product_link(href):
                    full_url = urljoin(self.BASE_URL, href)
                    products.append({
                        'name': text,
                        'url': full_url,
                        'source': 'nav'
                    })
        
        return products
    
    def _extract_products_from_links(self, soup):
        """从所有链接中提取产品"""
        products = []
        
        # 查找所有链接
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # 过滤条件：链接指向support.huaweicloud.com域名下的产品页面
            if href and text and self._is_product_link(href):
                full_url = urljoin(self.BASE_URL, href)
                
                # 避免重复添加
                if not any(p['url'] == full_url for p in products):
                    products.append({
                        'name': text,
                        'url': full_url,
                        'source': 'link'
                    })
        
        return products
    
    def _is_product_link(self, href):
        """
        判断链接是否是产品链接
        
        Args:
            href: 链接地址
            
        Returns:
            bool: 是否是产品链接
        """
        if not href:
            return False
        
        # 排除一些明显不是产品链接的URL
        exclude_patterns = [
            'javascript:',
            'mailto:',
            '#',
            '/api/',
            '/sdk/',
            '/cli/',
            '/faq/',
            '/troubleshooting/',
        ]
        
        for pattern in exclude_patterns:
            if pattern in href.lower():
                return False
        
        # 包含产品相关关键词的链接
        product_keywords = [
            'product',
            'service',
            'console',
            'usermanual',
            'devguide',
            'api-reference',
        ]
        
        href_lower = href.lower()
        parsed = urlparse(href)
        
        # 如果链接指向support.huaweicloud.com域名
        if 'support.huaweicloud.com' in href_lower or href.startswith('/'):
            # 检查路径中是否包含产品相关关键词
            path = parsed.path.lower()
            if any(keyword in path for keyword in product_keywords):
                return True
            
            # 或者路径看起来像产品页面（有多个层级）
            path_parts = [p for p in path.split('/') if p]
            if len(path_parts) >= 2:  # 至少有两级路径
                return True
        
        return False
    
    def _extract_products_from_all_links(self, soup):
        """从所有链接中提取产品（更全面的方法）"""
        products = []
        
        # 查找所有链接
        all_links = soup.find_all('a', href=True)
        
        # 已知的常见产品路径前缀（用于快速识别）
        common_product_prefixes = [
            '/ecs/', '/obs/', '/rds/', '/cce/', '/vpc/', '/elb/', '/eip/',
            '/evs/', '/ims/', '/as/', '/dns/', '/waf/', '/ddos/', '/hss/',
            '/sfs/', '/dms/', '/dds/', '/gaussdb/', '/redis/', '/drs/',
            '/rms/', '/iam/', '/cts/', '/aom/', '/apm/', '/lts/', '/ces/',
            '/smn/', '/dgc/', '/dli/', '/mrs/', '/css/', '/cdm/', '/dis/',
            '/modelarts/', '/eihealth/', '/devcloud/', '/codearts/', '/swr/',
            '/functiongraph/', '/apig/', '/roma/', '/cse/', '/servicestage/',
            '/cph/', '/cloudide/', '/cloudtest/', '/codecheck/', '/cloudpipeline/',
            '/clouddeploy/', '/codehub/', '/codeartsrepo/', '/codeartsfactory/',
            '/bcs/', '/cgs/', '/cbr/', '/sfs-turbo/', '/dws/',
        ]
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if not href or not text or len(text.strip()) < 2:
                continue
            
            href_lower = href.lower()
            is_product = False
            
            # 方法1: 检查是否包含已知的产品路径前缀
            for prefix in common_product_prefixes:
                if prefix in href_lower:
                    is_product = True
                    break
            
            # 方法2: 检查是否是support.huaweicloud.com下的文档链接
            if not is_product:
                if 'support.huaweicloud.com' in href_lower or href.startswith('/'):
                    # 排除一些明显不是产品的页面
                    exclude_keywords = [
                        'login', 'logout', 'register', 'account', 'cart', 'order',
                        'video', 'faq', 'troubleshooting', 'contact', 'about',
                        'privacy', 'terms', 'legal', 'copyright', 'sitemap',
                        'search', 'help', 'support', 'feedback', 'news', 'blog',
                        'download', 'mobile', 'app', '/api/', '/sdk/', '/cli/',
                        'console', '/home', '/index', '/main', '/default',
                        '/usermanual-account/', '/qs-', '/auth', '/portal',
                    ]
                    
                    if not any(keyword in href_lower for keyword in exclude_keywords):
                        # 检查路径深度（产品页面通常有2级或更多路径）
                        parsed = urlparse(href)
                        path_parts = [p for p in parsed.path.split('/') if p]
                        # 产品页面通常至少有2级路径，如 /ecs/index.html 或 /product/category/page
                        if len(path_parts) >= 2:
                            # 排除首页和根路径
                            if path_parts[0] not in ['', 'index', 'home', 'main']:
                                is_product = True
            
            if is_product:
                full_url = urljoin(self.BASE_URL, href)
                products.append({
                    'name': text.strip(),
                    'url': full_url,
                    'source': 'all_links'
                })
        
        return products
    
    def _filter_products(self, products):
        """过滤掉非产品链接"""
        filtered = []
        
        # 排除关键词（更精确的匹配）
        # 这些关键词应该作为完整词出现，而不是作为其他词的一部分
        exclude_patterns = [
            # 语言相关（完整匹配）
            r'\bDeutsch\b', r'\bEspañol\b', r'\bFrançais\b',
            r'\bNederlands\b', r'\bEnglish\b', r'\b日本語\b', r'\b한국어\b',
            r'\bРусский\b', r'\bภาษาไทย\b', r'\bTiếng Việt\b',
            r'\bBahasa Indonesia\b', r'\bPortuguês\b', r'\bالعربية\b',
            r'\bעברית\b', r'\bTürkçe\b', r'\bPolski\b', r'\bČeština\b',
            r'\bMagyar\b', r'\bRomână\b', r'\bБългарски\b',
            r'\bHrvatski\b', r'\bSlovenčina\b', r'\bSlovenščina\b',
            r'\bEesti\b', r'\bLatvieštu\b', r'\bLietuvių\b',
            r'\bSuomi\b', r'\bSvenska\b', r'\bNorsk\b', r'\bDansk\b',
            r'\bÍslenska\b', r'\bGaeilge\b', r'\bCymraeg\b',
            r'\bMalti\b', r'\bLuxembourgish\b',
            # 功能相关（完整匹配）
            r'\b登录\b', r'\b注册\b', r'\b购物车\b', r'\b退出\b',
            r'\b视频\b', r'\b教程\b', r'\bFAQ\b', r'\b常见问题\b',
            r'\b故障排除\b', r'\b联系我们\b', r'\b关于\b', r'\b隐私\b',
            r'\b条款\b', r'\b法律\b', r'\b版权\b', r'\b网站地图\b',
            r'\b搜索\b', r'\b帮助\b', r'\b支持\b', r'\b反馈\b',
            r'\b新闻\b', r'\b博客\b', r'\b下载\b', r'\b移动\b',
            r'\b控制台\b', r'\b首页\b', r'\b主页\b', r'\b默认\b',
            r'\b账户\b', r'\b订单\b',
        ]
        
        # 简单的字符串匹配（用于URL）
        exclude_url_keywords = [
            'login', 'logout', 'register', 'account', 'cart', 'order',
            'video', 'faq', 'troubleshooting', 'contact', 'about',
            'privacy', 'terms', 'legal', 'copyright', 'sitemap',
            'search', 'help', 'support', 'feedback', 'news', 'blog',
            'download', 'mobile', 'app', '/api/', '/sdk/', '/cli/',
            'console', '/home', '/index', '/main', '/default',
            '/usermanual-account/', '/qs-', '/auth', '/portal',
        ]
        
        import re
        
        for product in products:
            name = product.get('name', '')
            url = product.get('url', '').lower()
            
            # 检查名称是否匹配排除模式
            should_exclude = False
            
            # 检查名称中的排除模式（使用正则表达式，更精确）
            name_lower = name.lower()
            for pattern in exclude_patterns:
                if re.search(pattern, name_lower, re.IGNORECASE):
                    # 但是，如果这是产品名称的一部分（如"代码质量管理"），不应该排除
                    # 只有当这些词单独出现或作为功能词出现时才排除
                    # 例如："登录"、"注册"等应该排除，但"代码质量管理"不应该排除
                    # 这里简化处理：如果名称看起来像产品名称（包含产品相关关键词），不排除
                    if any(keyword in name_lower for keyword in ['产品', '服务', '云', '平台', '系统', '工具', '引擎']):
                        # 可能是产品名称，不排除
                        continue
                    should_exclude = True
                    break
            
            # 检查URL中的排除关键词
            if not should_exclude:
                for keyword in exclude_url_keywords:
                    if keyword in url:
                        should_exclude = True
                        break
            
            # 特殊处理：如果URL是产品页面（www.huaweicloud.com/product/），不应该被排除
            if should_exclude and 'www.huaweicloud.com/product/' in url:
                # 这是产品页面，不应该被排除
                should_exclude = False
            
            if not should_exclude:
                filtered.append(product)
        
        return filtered
    
    def _deduplicate_products(self, products):
        """去重产品列表"""
        seen_urls = set()
        unique_products = []
        
        for product in products:
            url = product['url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_products.append(product)
        
        return unique_products
