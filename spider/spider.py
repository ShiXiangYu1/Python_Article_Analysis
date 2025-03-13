"""
爬虫主程序

用于爬取指定网站的文章内容
"""

import os
import time
import random
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import List, Dict, Optional, Any, Set
import logging
import pandas as pd
import threading
import queue
import concurrent.futures
import hashlib
import json
from urllib.parse import urljoin, urlparse
from datetime import datetime

# 导入解析器
from spider.parser import get_parser
from spider.proxy_pool import ProxyPool, Proxy

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('spider')

class ArticleSpider:
    """
    文章爬虫类
    
    用于爬取指定网站的文章内容
    """
    
    def __init__(
        self,
        base_url: str,
        parser_name: str = 'default',
        delay: float = 1.0,
        max_articles: int = 10,
        output_dir: str = 'data',
        thread_count: int = 1,
        queue_size: int = 100,
        timeout: int = 10,
        max_retries: int = 3,
        incremental: bool = False,
        use_proxy: bool = False,
        proxy_file: str = 'proxies.json',
        proxy_pool: Optional[ProxyPool] = None
    ):
        """
        初始化爬虫

        Args:
            base_url: 网站基础URL
            parser_name: 使用的解析器名称
            delay: 请求之间的延迟（秒）
            max_articles: 最大爬取文章数量
            output_dir: 输出目录
            thread_count: 爬取线程数
            queue_size: 文章队列大小
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            incremental: 是否增量爬取（跳过已爬取的文章）
            use_proxy: 是否使用代理
            proxy_file: 代理文件路径
            proxy_pool: 外部提供的代理池，如果为None则内部创建
        """
        self.base_url = base_url
        self.parser_name = parser_name
        self.delay = delay
        self.max_articles = max_articles
        self.output_dir = output_dir
        self.thread_count = thread_count
        self.queue_size = queue_size
        self.timeout = timeout
        self.max_retries = max_retries
        self.incremental = incremental
        self.use_proxy = use_proxy
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 初始化解析器
        self.parser = get_parser(parser_name, base_url)
        
        # 初始化队列和锁
        self.article_queue = queue.Queue(maxsize=queue_size)
        self.visited_urls: Set[str] = set()
        self.articles: List[Dict[str, Any]] = []
        self.lock = threading.RLock()
        
        # 爬取状态
        self.is_running = False
        self.has_error = False
        self.error_message = ""
        
        # 用于增量爬取的数据
        if incremental:
            self.load_visited_urls()
            self.load_existing_articles()
        
        # 初始化代理池
        if use_proxy:
            if proxy_pool:
                self.proxy_pool = proxy_pool
            else:
                self.proxy_pool = ProxyPool(proxy_file=proxy_file)
                # 初始获取一些代理
                self.proxy_pool.fetch_proxies_from_sources()
        else:
            self.proxy_pool = None
        
        logger.info(f"爬虫初始化完成: {base_url}, 线程数: {thread_count}, "
                   f"最大文章数: {max_articles}, 使用代理: {use_proxy}")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 已访问URL集合
        self.visited_urls = set()
        
        # 初始化文章列表和线程安全锁
        self.articles = []
        self.articles_lock = threading.Lock()
        self.article_count = 0
        
        # 初始化URL队列
        self.url_queue = queue.Queue(maxsize=queue_size)
    
    def get_random_headers(self) -> Dict[str, str]:
        """
        获取随机User-Agent的请求头
        
        Returns:
            包含随机User-Agent的请求头字典
        """
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def get_page(self, url: str) -> Optional[str]:
        """
        获取页面内容
        
        Args:
            url: 页面URL
            
        Returns:
            页面HTML内容，失败则返回None
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        
        retries = 0
        
        while retries < self.max_retries:
            try:
                # 是否使用代理
                proxy = None
                proxies = None
                
                if self.use_proxy and self.proxy_pool:
                    proxy = self.proxy_pool.get_proxy(check=True)
                    if proxy:
                        proxies = {
                            'http': f"{proxy.protocol}://{proxy.url}",
                            'https': f"{proxy.protocol}://{proxy.url}"
                        }
                        logger.debug(f"使用代理: {proxy.url}")
                
                # 发送请求
                start_time = time.time()
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=self.timeout,
                    proxies=proxies
                )
                response_time = time.time() - start_time
                
                # 报告代理使用结果
                if proxy and self.proxy_pool:
                    success = 200 <= response.status_code < 300
                    self.proxy_pool.report_proxy_result(proxy.url, success, response_time)
                
                # 检查响应状态
                if response.status_code == 200:
                    logger.debug(f"获取页面成功: {url}, 代理: {proxy.url if proxy else '无'}")
                    return response.text
                else:
                    logger.warning(f"获取页面失败: {url}, 状态码: {response.status_code}")
                    retries += 1
                    
                    # 如果使用代理且失败，尝试使用其他代理或不使用代理
                    if proxy and retries < self.max_retries:
                        self.proxy_pool.remove_proxy(proxy.url)
                        logger.debug(f"移除无效代理: {proxy.url}")
                    
                    time.sleep(self.delay * (retries + 1))  # 指数退避
            
            except requests.RequestException as e:
                # 处理请求异常
                logger.warning(f"请求异常: {url}, 错误: {str(e)}")
                retries += 1
                
                # 报告代理使用失败
                if proxy and self.proxy_pool:
                    self.proxy_pool.report_proxy_result(proxy.url, False)
                
                time.sleep(self.delay * (retries + 1))  # 指数退避
        
        return None
    
    def normalize_url(self, url: str) -> str:
        """
        标准化URL，处理相对路径等
        
        Args:
            url: 原始URL
            
        Returns:
            标准化后的URL
        """
        if not url:
            return ""
            
        # 处理相对URL
        if not url.startswith('http'):
            url = urljoin(self.base_url, url)
        
        # 移除URL中的锚点部分
        url = url.split('#')[0]
        
        return url
    
    def is_same_domain(self, url: str) -> bool:
        """
        检查URL是否属于同一域名
        
        Args:
            url: 要检查的URL
            
        Returns:
            是否属于同一域名
        """
        base_domain = urlparse(self.base_url).netloc
        url_domain = urlparse(url).netloc
        
        # 允许子域名
        return url_domain == base_domain or url_domain.endswith('.' + base_domain)
    
    def load_visited_urls(self) -> None:
        """
        加载已访问过的URL
        用于增量爬取时跳过已爬取的文章
        """
        # 已爬取文章的记录文件
        visited_file = os.path.join(self.output_dir, 'visited_urls.json')
        
        # 已爬取的CSV文件
        csv_file = os.path.join(self.output_dir, 'articles.csv')
        
        # 从文件加载已访问URL
        if os.path.exists(visited_file):
            try:
                with open(visited_file, 'r', encoding='utf-8') as f:
                    self.visited_urls = set(json.load(f))
                logger.info(f"从记录中加载 {len(self.visited_urls)} 个已访问URL")
            except Exception as e:
                logger.warning(f"加载已访问URL失败: {e}")
        
        # 从CSV文件中提取URL（兼容旧数据）
        if os.path.exists(csv_file) and not self.visited_urls:
            try:
                df = pd.read_csv(csv_file)
                if 'url' in df.columns:
                    urls = df['url'].dropna().unique().tolist()
                    self.visited_urls.update(urls)
                    logger.info(f"从CSV文件中加载 {len(urls)} 个已访问URL")
            except Exception as e:
                logger.warning(f"从CSV文件加载URL失败: {e}")
    
    def save_visited_urls(self) -> None:
        """
        保存已访问过的URL
        用于增量爬取时跳过已爬取的文章
        """
        # 已爬取文章的记录文件
        visited_file = os.path.join(self.output_dir, 'visited_urls.json')
        
        try:
            with open(visited_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.visited_urls), f)
            logger.info(f"已保存 {len(self.visited_urls)} 个已访问URL")
        except Exception as e:
            logger.error(f"保存已访问URL失败: {e}")
    
    def load_existing_articles(self) -> None:
        """
        加载已存在的文章数据
        用于增量爬取时合并新旧数据
        """
        # 已爬取的CSV文件
        csv_file = os.path.join(self.output_dir, 'articles.csv')
        
        if not os.path.exists(csv_file):
            return
        
        try:
            df = pd.read_csv(csv_file)
            articles = df.to_dict('records')
            
            with self.articles_lock:
                self.articles = articles
                logger.info(f"加载 {len(articles)} 篇已存在的文章")
        except Exception as e:
            logger.error(f"加载已存在的文章失败: {e}")
    
    def get_url_hash(self, url: str) -> str:
        """
        获取URL的哈希值
        用于唯一标识已访问的URL
        
        Args:
            url: 要哈希的URL
            
        Returns:
            URL的MD5哈希值
        """
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    def crawl_article_worker(self) -> None:
        """
        爬取文章的工作线程
        从队列获取URL并爬取文章，直到队列为空或达到最大文章数
        """
        logger.info("工作线程已启动")
        
        while True:
            try:
                # 从队列获取文章URL
                url = self.url_queue.get(timeout=5)
                
                # 检查是否需要继续爬取
                with self.articles_lock:
                    if len(self.articles) >= self.max_articles:
                        self.url_queue.task_done()
                        break
                
                # 在增量模式下检查是否已访问
                if self.incremental and url in self.visited_urls:
                    logger.debug(f"跳过已爬取的文章: {url}")
                    self.url_queue.task_done()
                    continue
                
                # 爬取文章
                logger.info(f"爬取文章: {url}")
                article_html = self.get_page(url)
                if not article_html:
                    self.url_queue.task_done()
                    continue
                
                # 解析文章
                try:
                    article_data = self.parser.parse_article(article_html, url)
                    if not article_data:
                        logger.warning(f"解析文章失败: {url}")
                        self.url_queue.task_done()
                        continue
                    
                    # 添加URL和时间戳
                    article_data['url'] = url
                    article_data['crawl_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 线程安全地添加到文章列表
                    with self.articles_lock:
                        self.articles.append(article_data)
                        article_count = len(self.articles)
                        
                    # 标记为已访问
                    self.visited_urls.add(url)
                    
                    # 记录进度
                    logger.info(f"已爬取 {article_count} 篇文章，最新: {article_data.get('title', '无标题')}")
                    
                    # 定期保存数据
                    if article_count % 10 == 0:
                        self.save_to_csv()
                        
                except Exception as e:
                    logger.error(f"解析文章时发生错误: {url}, {str(e)}")
                
                # 标记任务完成
                self.url_queue.task_done()
                
                # 延迟避免请求过快
                time.sleep(self.delay)
                
            except queue.Empty:
                # 队列为空，检查是否需要退出
                logger.debug("文章队列为空，工作线程等待...")
                time.sleep(1)
                
                # 如果队列持续为空，退出线程
                if self.url_queue.empty():
                    logger.info("没有更多文章，工作线程退出")
                    break
            
            except Exception as e:
                logger.error(f"爬取文章时发生错误: {e}")
                self.url_queue.task_done()
                
        logger.info("工作线程已结束")
    
    def find_article_links(self, list_url: str) -> List[str]:
        """
        从列表页面查找文章链接
        
        Args:
            list_url: 列表页URL
            
        Returns:
            文章URL列表
        """
        if not self.parser:
            logger.error("未找到解析器，无法提取文章链接")
            return []
        
        logger.info(f"从列表页面收集文章链接: {list_url}")
        article_urls = []
        
        # 获取列表页面内容
        html = self.get_page(list_url)
        if not html:
            return []
        
        try:
            # 使用解析器提取文章链接
            raw_urls = self.parser.extract_article_links(html, list_url)
            
            # 规范化URL
            normalized_urls = []
            for url in raw_urls:
                normalized_url = self.normalize_url(url)
                if not normalized_url:
                    continue
                
                # 只保留同域名的URL
                if not self.is_same_domain(normalized_url):
                    continue
                
                # 在增量模式下跳过已访问的URL
                if self.incremental and normalized_url in self.visited_urls:
                    logger.debug(f"跳过已访问的URL: {normalized_url}")
                    continue
                
                normalized_urls.append(normalized_url)
            
            # 添加到队列
            for url in normalized_urls:
                try:
                    # 标记为已访问
                    self.visited_urls.add(url)
                    
                    # 添加到队列
                    self.url_queue.put(url, block=False)
                    article_urls.append(url)
                except queue.Full:
                    logger.warning("文章队列已满，停止添加")
                    break
            
            logger.info(f"从列表页 {list_url} 收集到 {len(article_urls)} 个文章链接")
            
        except Exception as e:
            logger.error(f"提取文章链接时发生错误: {e}")
        
        return article_urls
    
    def collect_article_urls(self, start_url: str, max_pages: int = 20) -> None:
        """
        收集文章URL并添加到队列
        
        Args:
            start_url: 起始URL
            max_pages: 最大爬取列表页数
        """
        # 当前页码
        page_num = 1
        # 已爬取的列表页数
        list_pages_crawled = 0
        
        while list_pages_crawled < max_pages:
            # 构建列表页URL
            if page_num == 1:
                list_url = start_url
            else:
                # 根据不同网站的分页规则构建URL
                if self.parser_name == 'zhihu':
                    list_url = f"{start_url}?page={page_num}"
                elif self.parser_name == 'csdn':
                    list_url = f"{start_url}/article/list/{page_num}"
                elif self.parser_name == 'jianshu':
                    list_url = f"{start_url}?page={page_num}"
                else:
                    # 默认分页规则
                    list_url = f"{start_url}/page/{page_num}"
            
            # 查找文章链接
            article_urls = self.find_article_links(list_url)
            
            # 如果没有找到文章链接，可能已到达最后页
            if not article_urls:
                logger.warning(f"未在列表页找到文章链接，可能已到达最后页或页面结构变化: {list_url}")
                break
            
            # 将文章URL添加到队列
            for url in article_urls:
                try:
                    self.url_queue.put(url, block=False)
                except queue.Full:
                    logger.warning("文章队列已满，停止添加")
                    break
            
            # 检查是否已达到最大文章数
            if self.url_queue.qsize() >= self.queue_size:
                logger.info(f"已收集足够的文章URL: {self.url_queue.qsize()}")
                break
            
            # 增加页码和计数
            page_num += 1
            list_pages_crawled += 1
            
            # 延迟，避免被反爬
            time.sleep(self.delay)
    
    def crawl(self) -> List[Dict[str, Any]]:
        """
        爬取文章
        
        Returns:
            爬取到的文章列表
        """
        try:
            self.is_running = True
            
            if self.thread_count <= 1:
                # 单线程爬取
                return self.crawl_single_thread()
            else:
                # 多线程爬取
                return self.crawl_multi_thread()
                
        except Exception as e:
            logger.error(f"爬取过程中发生错误: {str(e)}", exc_info=True)
            self.has_error = True
            self.error_message = str(e)
            return self.articles
        finally:
            self.is_running = False
            
            # 保存爬取结果到CSV文件
            self.save_to_csv()
            
            # 如果使用了增量爬取，保存已访问URL
            if self.incremental:
                self.save_visited_urls()
                
            # 如果使用了代理池，保存代理
            if self.use_proxy and self.proxy_pool:
                self.proxy_pool.save_proxies()
    
    def crawl_single_thread(self) -> List[Dict[str, Any]]:
        """
        单线程爬取文章
        
        Returns:
            爬取的文章列表
        """
        start_time = time.time()
        logger.info(f"开始爬取网站: {self.base_url}")
        
        # 收集文章URL
        self.collect_article_urls(self.base_url)
        
        # 爬取文章
        self.crawl_article_worker()
        
        end_time = time.time()
        elapsed = end_time - start_time
        article_count = len(self.articles)
        logger.info(f"爬取完成，共获取 {article_count} 篇文章，用时 {elapsed:.2f} 秒")
        
        if article_count > 0:
            avg_time = elapsed / article_count
            logger.info(f"平均每篇文章爬取用时 {avg_time:.2f} 秒")
        
        return self.articles
    
    def crawl_multi_thread(self) -> List[Dict[str, Any]]:
        """
        多线程爬取文章
        
        Returns:
            爬取的文章列表
        """
        start_time = time.time()
        logger.info(f"开始爬取 {self.parser_name}: {self.base_url}")
        
        # 收集文章URL的线程
        collector_thread = threading.Thread(
            target=self.collect_article_urls, 
            args=(self.base_url, 30),  # 最多爬取30个列表页
            daemon=True
        )
        collector_thread.start()
        
        # 等待一段时间，让收集器先填充一些URL
        time.sleep(2)
        
        # 创建线程池
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            # 获取所有文章URL
            article_urls = []
            while not self.url_queue.empty() and len(article_urls) < self.queue_size:
                try:
                    url = self.url_queue.get_nowait()
                    article_urls.append(url)
                    self.url_queue.task_done()
                except queue.Empty:
                    break
            
            # 提交爬取任务
            future_to_url = {}
            for url in article_urls:
                # 使用随机延迟避免被反爬
                time.sleep(self.delay * random.random())
                
                future = executor.submit(self._crawl_article, url)
                future_to_url[future] = url
            
            # 处理结果
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article = future.result()
                    if article:
                        with self.articles_lock:
                            self.articles.append(article)
                            self.article_count += 1
                            
                            if self.article_count % 10 == 0:
                                self.save_to_csv()
                                logger.info(f"已获取 {self.article_count}/{self.max_articles} 篇文章")
                except Exception as e:
                    logger.error(f"处理文章 {url} 时发生错误: {e}")
        
        # 完成后保存一次
        self.save_to_csv()
        
        logger.info(f"爬取完成，共获取 {len(self.articles)} 篇文章，耗时 {time.time() - start_time:.2f} 秒")
        return self.articles
    
    def _crawl_article(self, url: str) -> Optional[Dict[str, Any]]:
        """
        爬取单个文章(用于线程池)
        
        Args:
            url: 文章URL
            
        Returns:
            文章信息字典，失败则返回None
        """
        # 获取文章页面
        article_html = self.get_page(url)
        if not article_html:
            return None
        
        # 解析文章
        article = self.parser.parse_article(article_html, url)
        return article
    
    def save_to_csv(self) -> None:
        """将爬取的文章保存为CSV文件"""
        if not self.articles:
            logger.info("没有文章需要保存")
            return
        
        # 文章输出文件
        csv_file = os.path.join(self.output_dir, 'articles.csv')
        
        try:
            df = pd.DataFrame(self.articles)
            df.to_csv(csv_file, index=False, encoding='utf-8')
            logger.info(f"已将 {len(self.articles)} 篇文章保存到 {csv_file}")
        except Exception as e:
            logger.error(f"保存文章数据失败: {e}")

    def __del__(self):
        """析构函数，确保资源被释放"""
        try:
            # 关闭代理池
            if self.use_proxy and self.proxy_pool:
                self.proxy_pool.shutdown()
        except:
            pass


# 示例爬虫调用
if __name__ == "__main__":
    # 根据实际需求修改参数
    spider = ArticleSpider(
        base_url="https://example.com",  # 替换为实际目标网站
        parser_name="general",               # 网站类型
        delay=2.0,                       # 请求间隔，根据网站反爬策略调整
        max_articles=100,                # 爬取文章数量
        thread_count=5                   # 线程数量
    )
    articles = spider.crawl() 