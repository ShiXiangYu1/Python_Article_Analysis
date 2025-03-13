"""
网页解析器

为不同的目标网站提供特定的解析逻辑
"""

from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import logging
import re
import time
from urllib.parse import urljoin, urlparse, parse_qs
import json

logger = logging.getLogger('parser')

class BaseParser:
    """
    解析器基类
    
    所有特定网站的解析器都应继承此类
    """
    
    def __init__(self, base_url: str) -> None:
        """
        初始化解析器
        
        Args:
            base_url: 目标网站的基础URL
        """
        self.base_url = base_url
    
    def parse_article_list(self, html: str) -> List[str]:
        """
        解析文章列表页，提取文章URL
        
        Args:
            html: 列表页HTML内容
            
        Returns:
            文章URL列表
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def extract_article_links(self, html: str, url: str) -> List[str]:
        """
        提取文章链接
        
        Args:
            html: 网页HTML内容
            url: 网页URL
            
        Returns:
            文章URL列表
        """
        # 默认实现调用parse_article_list，向后兼容
        return self.parse_article_list(html)
    
    def parse_article(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        解析文章页面，提取内容
        
        Args:
            html: 文章页HTML内容
            url: 文章URL
            
        Returns:
            包含文章信息的字典，失败则返回None
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def clean_text(self, text: str) -> str:
        """
        清理文本，去除多余空白字符等
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 去除HTML标签
        text = re.sub(r'<[^>]+>', ' ', text)
        # 替换多个空白字符为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除首尾空白
        return text.strip()
    
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
        
        return url


class ZhihuParser(BaseParser):
    """
    知乎文章解析器
    """
    
    def parse_article_list(self, html: str) -> List[str]:
        """
        解析知乎文章列表页
        
        Args:
            html: 列表页HTML内容
            
        Returns:
            文章URL列表
        """
        soup = BeautifulSoup(html, 'lxml')
        article_links = []
        
        # 知乎专栏文章卡片
        for article_card in soup.select('.ArticleItem'):
            link_tag = article_card.select_one('a.Post-link')
            if link_tag and 'href' in link_tag.attrs:
                article_url = link_tag['href']
                article_url = self.normalize_url(article_url)
                if article_url and article_url not in article_links:
                    article_links.append(article_url)
        
        return article_links
    
    def extract_article_links(self, html: str, url: str) -> List[str]:
        """
        提取知乎文章链接
        
        Args:
            html: 网页HTML内容
            url: 网页URL
            
        Returns:
            文章URL列表
        """
        soup = BeautifulSoup(html, 'lxml')
        article_links = []
        
        # 知乎专栏文章卡片
        article_cards = soup.select('.ArticleItem')
        # 知乎首页文章
        if not article_cards:
            article_cards = soup.select('.ContentItem')
        
        for article_card in article_cards:
            link_tag = article_card.select_one('a.Post-link, a.ContentItem-title')
            if link_tag and 'href' in link_tag.attrs:
                article_url = link_tag['href']
                article_url = self.normalize_url(article_url)
                if article_url and article_url not in article_links:
                    article_links.append(article_url)
        
        # 热门推荐
        for link_tag in soup.select('.HotItem-content a'):
            if 'href' in link_tag.attrs:
                article_url = link_tag['href']
                article_url = self.normalize_url(article_url)
                if article_url and '/p/' in article_url and article_url not in article_links:
                    article_links.append(article_url)
        
        return article_links
    
    def parse_article(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        解析知乎文章页面
        
        Args:
            html: 文章页HTML内容
            url: 文章URL
            
        Returns:
            包含文章信息的字典，失败则返回None
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 提取标题
            title_tag = soup.select_one('h1.Post-Title')
            title = title_tag.get_text().strip() if title_tag else "未知标题"
            
            # 提取作者
            author_tag = soup.select_one('.AuthorInfo-name')
            author = author_tag.get_text().strip() if author_tag else "未知作者"
            
            # 提取文章内容
            content_tags = soup.select('.Post-RichTextContainer')
            content = '\n'.join([tag.get_text() for tag in content_tags]) if content_tags else ""
            content = self.clean_text(content)
            
            # 构建文章字典
            article = {
                'title': title,
                'author': author,
                'content': content,
                'url': url,
                'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return article
        except Exception as e:
            logger.error(f"解析知乎文章失败 {url}: {e}")
            return None


class CSDNParser(BaseParser):
    """
    CSDN博客解析器
    """
    
    def parse_article_list(self, html: str) -> List[str]:
        """
        解析CSDN博客列表页
        
        Args:
            html: 列表页HTML内容
            
        Returns:
            文章URL列表
        """
        soup = BeautifulSoup(html, 'lxml')
        article_links = []
        
        # CSDN文章列表
        for article_card in soup.select('.article-item-box'):
            link_tag = article_card.select_one('a.article-title')
            if link_tag and 'href' in link_tag.attrs:
                article_url = link_tag['href']
                if article_url and article_url not in article_links:
                    article_links.append(article_url)
        
        return article_links
    
    def extract_article_links(self, html: str, url: str) -> List[str]:
        """
        提取CSDN文章链接
        
        Args:
            html: 网页HTML内容
            url: 网页URL
            
        Returns:
            文章URL列表
        """
        soup = BeautifulSoup(html, 'lxml')
        article_links = []
        
        # CSDN文章列表
        for article_card in soup.select('.article-item-box'):
            link_tag = article_card.select_one('a.article-title')
            if link_tag and 'href' in link_tag.attrs:
                article_url = link_tag['href']
                if article_url and article_url not in article_links:
                    article_links.append(article_url)
        
        # 首页推荐文章
        for link_tag in soup.select('.recommended-item a.title'):
            if 'href' in link_tag.attrs:
                article_url = link_tag['href']
                if article_url and article_url not in article_links:
                    article_links.append(article_url)
        
        return article_links
    
    def parse_article(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        解析CSDN博客文章页面
        
        Args:
            html: 文章页HTML内容
            url: 文章URL
            
        Returns:
            包含文章信息的字典，失败则返回None
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 提取标题
            title_tag = soup.select_one('h1.title-article')
            title = title_tag.get_text().strip() if title_tag else "未知标题"
            
            # 提取作者
            author_tag = soup.select_one('.follow-nickName')
            author = author_tag.get_text().strip() if author_tag else "未知作者"
            
            # 提取文章内容
            content_tag = soup.select_one('#article_content')
            content = content_tag.get_text() if content_tag else ""
            content = self.clean_text(content)
            
            # 构建文章字典
            article = {
                'title': title,
                'author': author,
                'content': content,
                'url': url,
                'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return article
        except Exception as e:
            logger.error(f"解析CSDN文章失败 {url}: {e}")
            return None


class JianshuParser(BaseParser):
    """
    简书文章解析器
    """
    
    def parse_article_list(self, html: str) -> List[str]:
        """
        解析简书文章列表页
        
        Args:
            html: 列表页HTML内容
            
        Returns:
            文章URL列表
        """
        soup = BeautifulSoup(html, 'lxml')
        article_links = []
        
        # 简书文章列表
        for article_card in soup.select('.note-list li'):
            link_tag = article_card.select_one('a.title')
            if link_tag and 'href' in link_tag.attrs:
                article_url = link_tag['href']
                article_url = self.normalize_url(article_url)
                if article_url and article_url not in article_links:
                    article_links.append(article_url)
        
        return article_links
    
    def extract_article_links(self, html: str, url: str) -> List[str]:
        """
        提取简书文章链接
        
        Args:
            html: 网页HTML内容
            url: 网页URL
            
        Returns:
            文章URL列表
        """
        soup = BeautifulSoup(html, 'lxml')
        article_links = []
        
        # 简书文章列表
        for article_card in soup.select('.note-list li'):
            link_tag = article_card.select_one('a.title')
            if link_tag and 'href' in link_tag.attrs:
                article_url = link_tag['href']
                article_url = self.normalize_url(article_url)
                if article_url and article_url not in article_links:
                    article_links.append(article_url)
        
        # 首页推荐文章
        for link_tag in soup.select('.recommended-collection .title'):
            if 'href' in link_tag.attrs:
                article_url = link_tag['href']
                article_url = self.normalize_url(article_url)
                if article_url and article_url not in article_links:
                    article_links.append(article_url)
        
        return article_links
    
    def parse_article(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        解析简书文章页面
        
        Args:
            html: 文章页HTML内容
            url: 文章URL
            
        Returns:
            包含文章信息的字典，失败则返回None
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 提取标题
            title_tag = soup.select_one('h1.title')
            title = title_tag.get_text().strip() if title_tag else "未知标题"
            
            # 提取作者
            author_tag = soup.select_one('a.author')
            author = author_tag.get_text().strip() if author_tag else "未知作者"
            
            # 提取文章内容
            content_tag = soup.select_one('div.show-content')
            content = content_tag.get_text() if content_tag else ""
            content = self.clean_text(content)
            
            # 构建文章字典
            article = {
                'title': title,
                'author': author,
                'content': content,
                'url': url,
                'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return article
        except Exception as e:
            logger.error(f"解析简书文章失败 {url}: {e}")
            return None


class SinaNewsParser(BaseParser):
    """
    新浪新闻解析器
    """
    
    def extract_article_links(self, html: str, url: str) -> List[str]:
        """
        提取新浪新闻文章链接
        
        Args:
            html: 网页HTML内容
            url: 网页URL
            
        Returns:
            文章URL列表
        """
        soup = BeautifulSoup(html, 'lxml')
        article_links = []
        
        # 新闻列表页中的链接
        for link_tag in soup.select('a'):
            if not link_tag.get('href'):
                continue
                
            href = link_tag.get('href')
            
            # 过滤掉非文章链接
            if not self._is_news_article_url(href):
                continue
                
            article_url = self.normalize_url(href)
            
            if article_url and article_url not in article_links:
                article_links.append(article_url)
        
        logger.info(f"从新浪新闻页面提取到 {len(article_links)} 个文章链接")
        return article_links
    
    def _is_news_article_url(self, url: str) -> bool:
        """
        判断URL是否为新浪新闻文章链接
        
        Args:
            url: 要判断的URL
            
        Returns:
            是否为新浪新闻文章链接
        """
        # 新浪新闻文章URL通常包含特定路径
        patterns = [
            r'https?://news\.sina\.com\.cn/[a-z]/[\w-]+/\d+-\d+-\d+/doc-[a-z0-9]+\.shtml',  # 常规新闻
            r'https?://finance\.sina\.com\.cn/[a-z]/[\w-]+/\d+-\d+-\d+/doc-[a-z0-9]+\.shtml',  # 财经新闻
            r'https?://sports\.sina\.com\.cn/[a-z]/[\w-]+/\d+-\d+-\d+/doc-[a-z0-9]+\.shtml',  # 体育新闻
            r'https?://tech\.sina\.com\.cn/[a-z]/[\w-]+/\d+-\d+-\d+/doc-[a-z0-9]+\.shtml',  # 科技新闻
            r'https?://ent\.sina\.com\.cn/[a-z]/[\w-]+/\d+-\d+-\d+/doc-[a-z0-9]+\.shtml',  # 娱乐新闻
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        
        # 简化的模式也可以识别大部分新闻URL
        simplified_patterns = [
            r'https?://(news|finance|sports|tech|ent)\.sina\.com\.cn/.*\.shtml',
            r'https?://(news|finance|sports|tech|ent)\.sina\.com\.cn/.*\.html',
        ]
        
        for pattern in simplified_patterns:
            if re.match(pattern, url):
                return True
        
        return False
    
    def parse_article(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        解析新浪新闻文章页面
        
        Args:
            html: 文章页HTML内容
            url: 文章URL
            
        Returns:
            包含文章信息的字典，失败则返回None
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 提取标题
            title_tags = [
                soup.select_one('h1.main-title'),  # 常规新闻标题
                soup.select_one('h1.entry-title'),  # 部分新闻标题
                soup.select_one('h1.data-title'),   # 数据新闻标题
            ]
            
            title = "未知标题"
            for tag in title_tags:
                if tag:
                    title = tag.get_text().strip()
                    break
            
            # 提取作者/来源
            author = "未知作者"
            author_tags = [
                soup.select_one('a.source'),  # 常规新闻来源
                soup.select_one('span.source'),  # 部分新闻来源
                soup.select_one('div.date-source a'),  # 另一种格式
                soup.select_one('div.date-source span'),  # 另一种格式
            ]
            
            for tag in author_tags:
                if tag:
                    author = tag.get_text().strip()
                    break
            
            # 提取发布时间
            publish_time = ""
            time_tags = [
                soup.select_one('span.date'),  # 常规新闻发布时间
                soup.select_one('span.pub_date'),  # 部分新闻发布时间
                soup.select_one('div.date-source span.date'),  # 另一种格式
            ]
            
            for tag in time_tags:
                if tag:
                    publish_time = tag.get_text().strip()
                    break
            
            # 提取文章内容
            content = ""
            content_tags = [
                soup.select('div.article p'),  # 常规新闻内容
                soup.select('div.article-content p'),  # 部分新闻内容
                soup.select('div.content p'),  # 另一种格式
                soup.select('#artibody p'),  # 旧版格式
            ]
            
            for tags in content_tags:
                if tags:
                    paragraphs = [p.get_text().strip() for p in tags]
                    content = '\n'.join(paragraphs)
                    break
            
            content = self.clean_text(content)
            
            # 构建文章字典
            article = {
                'title': title,
                'author': author,
                'publish_time': publish_time,
                'content': content,
                'url': url,
                'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return article
        except Exception as e:
            logger.error(f"解析新浪新闻文章失败 {url}: {e}")
            return None


class GeneralParser(BaseParser):
    """
    通用网页解析器
    
    用于解析通用网页结构，提取标题、内容等
    """
    
    def extract_article_links(self, html: str, url: str) -> List[str]:
        """
        从通用网页中提取可能的文章链接
        
        Args:
            html: 网页HTML内容
            url: 网页URL
            
        Returns:
            文章URL列表
        """
        soup = BeautifulSoup(html, 'lxml')
        article_links = []
        
        # 查找所有链接
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            
            # 跳过空链接或锚点链接
            if not href or href.startswith('#'):
                continue
            
            # 标准化URL
            article_url = self.normalize_url(href)
            
            # 检查是否可能是文章链接
            if self._is_article_url(article_url):
                if article_url not in article_links:
                    article_links.append(article_url)
        
        logger.info(f"从页面提取到 {len(article_links)} 个可能的文章链接")
        return article_links
    
    def _is_article_url(self, url: str) -> bool:
        """
        判断URL是否可能是文章链接
        
        Args:
            url: 要判断的URL
            
        Returns:
            是否可能是文章链接
        """
        # 常见的文章URL特征
        article_indicators = [
            r'/article/', r'/articles/', r'/news/', r'/post/', r'/posts/',
            r'/blog/', r'/blogs/', r'/content/', r'/story/', r'/stories/',
            r'/view/', r'/read/', r'/detail/', r'/\d{4}/', r'/p/', r'/a/',
            r'\.html', r'\.shtml', r'\.htm', r'\.asp', r'\.aspx', r'\.php',
            r'/doc-', r'/newsdetail', r'/newsinfo',
        ]
        
        # 排除的URL特征
        exclude_indicators = [
            r'/tag/', r'/tags/', r'/category/', r'/categories/', r'/search/',
            r'/login', r'/register', r'/signup', r'/download', r'/about/',
            r'/contact', r'/help/', r'/support/', r'/faq', r'/terms/',
            r'/privacy', r'/sitemap', r'/rss/', r'/feed/', r'/comment/',
            r'/comments/', r'/page/', r'/pages/', r'/images?', r'/videos?/',
            r'/user/', r'/profile/', r'/member/', r'/members/', r'/author/',
        ]
        
        # 首先检查排除特征
        for pattern in exclude_indicators:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # 然后检查文章特征
        for pattern in article_indicators:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    def parse_article(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        解析通用网页，提取可能的文章内容
        
        Args:
            html: 文章页HTML内容
            url: 文章URL
            
        Returns:
            包含文章信息的字典，失败则返回None
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 尝试提取标题
            title = "未知标题"
            title_candidates = [
                soup.select_one('h1'),  # 大多数网站使用h1作为文章标题
                soup.select_one('header h1'),
                soup.select_one('article h1'),
                soup.select_one('.article h1'),
                soup.select_one('.post h1'),
                soup.select_one('.entry h1'),
                soup.select_one('.content h1'),
            ]
            
            for tag in title_candidates:
                if tag:
                    title = tag.get_text().strip()
                    break
            
            # 尝试提取作者
            author = "未知作者"
            author_candidates = [
                soup.select_one('.author'),
                soup.select_one('.byline'),
                soup.select_one('.meta .author'),
                soup.select_one('[rel="author"]'),
                soup.select_one('article .meta'),
            ]
            
            for tag in author_candidates:
                if tag:
                    author_text = tag.get_text().strip()
                    if author_text:
                        author = author_text
                        break
            
            # 尝试提取文章内容
            content = ""
            content_candidates = [
                soup.select('article p'),
                soup.select('.article p'),
                soup.select('.post-content p'),
                soup.select('.entry-content p'),
                soup.select('.content p'),
                soup.select('main p'),
            ]
            
            for tags in content_candidates:
                if tags:
                    paragraphs = [p.get_text().strip() for p in tags]
                    content = '\n'.join(paragraphs)
                    if len(content) > 200:  # 确保内容有一定长度
                        break
            
            # 如果没有找到足够长的内容，尝试获取所有p标签
            if len(content) < 200:
                paragraphs = [p.get_text().strip() for p in soup.select('p') if len(p.get_text().strip()) > 50]
                if paragraphs:
                    content = '\n'.join(paragraphs)
            
            content = self.clean_text(content)
            
            # 构建文章字典
            article = {
                'title': title,
                'author': author,
                'content': content,
                'url': url,
                'crawl_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 检查内容是否有效（标题不是"未知标题"或内容长度大于200）
            if title != "未知标题" or len(content) > 200:
                return article
            
            logger.warning(f"无法提取到有效内容: {url}")
            return None
            
        except Exception as e:
            logger.error(f"解析文章失败 {url}: {e}")
            return None


class DoubanMovieParser(BaseParser):
    """
    豆瓣电影解析器
    
    用于解析豆瓣电影网站的电影信息和影评
    """
    
    def extract_article_links(self, html: str, url: str) -> List[str]:
        """
        提取电影详情页链接
        
        Args:
            html: 网页HTML内容
            url: 网页URL
            
        Returns:
            电影URL列表
        """
        links = []
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 获取正在热映电影
            now_playing = soup.select('.screening-bd .ui-slide-item')
            for item in now_playing:
                a_tag = item.select_one('a')
                if a_tag and 'href' in a_tag.attrs:
                    movie_url = a_tag['href'].strip()
                    links.append(movie_url)
            
            # 获取热门电影
            hot_movies = soup.select('.ui-slide-item')
            for item in hot_movies:
                a_tag = item.select_one('a')
                if a_tag and 'href' in a_tag.attrs:
                    movie_url = a_tag['href'].strip()
                    links.append(movie_url)
            
            # 获取电影详情页中的影评链接
            review_links = soup.select('a.review-link')
            for link in review_links:
                if 'href' in link.attrs:
                    review_url = link['href'].strip()
                    if review_url.startswith('/review'):
                        review_url = urljoin(self.base_url, review_url)
                    links.append(review_url)
            
            # 提取排行榜链接
            rank_links = soup.select('a[href*="/top250"]')
            for link in rank_links:
                if 'href' in link.attrs:
                    rank_url = link['href'].strip()
                    rank_url = urljoin(self.base_url, rank_url)
                    links.append(rank_url)
            
            # 去重
            links = list(set(links))
            
            logger.info(f"从页面提取到 {len(links)} 个可能的电影或影评链接")
            return links
            
        except Exception as e:
            logger.error(f"提取电影链接失败 {url}: {e}")
            return []
    
    def parse_article(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        解析电影详情页或影评页面
        
        Args:
            html: 网页HTML内容
            url: 网页URL
            
        Returns:
            解析后的内容字典，包含标题、内容等信息
        """
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 判断页面类型
            is_movie = '/subject/' in url
            is_review = '/review/' in url
            
            article = {
                'url': url,
                'crawl_time': int(time.time())
            }
            
            if is_movie:
                # 电影详情页
                title_elem = soup.select_one('[property="v:itemreviewed"]')
                article['title'] = title_elem.text.strip() if title_elem else "未知电影"
                
                # 电影信息
                article['article_type'] = 'movie'
                
                # 提取电影信息
                year_elem = soup.select_one('.year')
                article['year'] = year_elem.text.strip('()') if year_elem else ""
                
                # 提取导演
                directors = []
                director_elems = soup.select('[rel="v:directedBy"]')
                for director in director_elems:
                    directors.append(director.text.strip())
                article['directors'] = directors
                
                # 提取主演
                actors = []
                actor_elems = soup.select('[rel="v:starring"]')
                for actor in actor_elems:
                    actors.append(actor.text.strip())
                article['actors'] = actors
                
                # 提取电影类型
                genres = []
                genre_elems = soup.select('[property="v:genre"]')
                for genre in genre_elems:
                    genres.append(genre.text.strip())
                article['genres'] = genres
                
                # 提取评分
                rating_elem = soup.select_one('[property="v:average"]')
                article['rating'] = rating_elem.text.strip() if rating_elem else "暂无评分"
                
                # 提取简介
                summary_elem = soup.select_one('[property="v:summary"]')
                article['content'] = summary_elem.text.strip() if summary_elem else ""
                
                # 提取海报
                poster_elem = soup.select_one('#mainpic img')
                article['poster'] = poster_elem['src'] if poster_elem and 'src' in poster_elem.attrs else ""
                
            elif is_review:
                # 影评页面
                article['article_type'] = 'review'
                
                # 提取标题
                title_elem = soup.select_one('h1[property="v:summary"]')
                article['title'] = title_elem.text.strip() if title_elem else "未知影评"
                
                # 提取作者
                author_elem = soup.select_one('.main-hd a')
                article['author'] = author_elem.text.strip() if author_elem else "匿名用户"
                
                # 提取评分
                rating_elem = soup.select_one('.main-title-rating')
                article['rating'] = rating_elem['title'] if rating_elem and 'title' in rating_elem.attrs else "暂无评分"
                
                # 提取内容
                content_elem = soup.select_one('.review-content')
                article['content'] = content_elem.text.strip() if content_elem else ""
                
                # 提取关联电影
                movie_elem = soup.select_one('.main-hd a[href*="/subject/"]')
                if movie_elem and 'href' in movie_elem.attrs:
                    article['movie_url'] = movie_elem['href']
                    article['movie_title'] = movie_elem.text.strip()
            else:
                # 其他页面，尝试通用提取
                title_elem = soup.select_one('h1')
                article['title'] = title_elem.text.strip() if title_elem else "未知标题"
                
                # 尝试提取正文内容
                content_elems = soup.select('.article') or soup.select('.content') or soup.select('article')
                article['content'] = '\n'.join([elem.text.strip() for elem in content_elems]) if content_elems else ""
                
                # 提取发布时间
                time_elem = soup.select_one('.created-at') or soup.select_one('.pub-date') or soup.select_one('[datetime]')
                article['publish_time'] = time_elem.text.strip() if time_elem else ""
                
                article['article_type'] = 'general'
            
            # 清理内容
            article['content'] = self.clean_text(article['content'])
            
            # 只有内容超过一定长度的文章才保留
            if article['title'] != "未知标题" or len(article['content']) > 200:
                return article
            
            logger.warning(f"无法提取到有效内容: {url}")
            return None
            
        except Exception as e:
            logger.error(f"解析文章失败 {url}: {e}")
            return None


# 解析器工厂，根据网站选择合适的解析器
def get_parser(website: str, base_url: str) -> BaseParser:
    """
    获取特定网站的解析器
    
    Args:
        website: 网站名称
        base_url: 网站基础URL
        
    Returns:
        对应的解析器实例
    """
    website = website.lower()
    
    # 网站类型与解析器映射
    parsers = {
        'zhihu': ZhihuParser,
        'csdn': CSDNParser,
        'jianshu': JianshuParser,
        'sina': SinaNewsParser,
        'sinacn': SinaNewsParser,
        'sina_news': SinaNewsParser,
        'douban_movie': DoubanMovieParser,
        'douban': DoubanMovieParser,
        'general': GeneralParser,
        'default': GeneralParser
    }
    
    # 根据域名自动识别网站类型
    if 'zhihu.com' in base_url:
        return ZhihuParser(base_url)
    elif 'csdn.net' in base_url:
        return CSDNParser(base_url)
    elif 'jianshu.com' in base_url:
        return JianshuParser(base_url)
    elif 'sina.com.cn' in base_url:
        return SinaNewsParser(base_url)
    elif 'douban.com/movie' in base_url or 'movie.douban.com' in base_url:
        return DoubanMovieParser(base_url)
    
    # 根据网站名称选择解析器
    parser_class = parsers.get(website, GeneralParser)
    
    # 创建并返回解析器实例
    parser = parser_class(base_url)
    
    logger.info(f"为网站 '{website}' 创建解析器: {parser.__class__.__name__}")
    return parser 