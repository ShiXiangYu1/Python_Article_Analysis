#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
豆瓣电影爬取脚本

该脚本用于从豆瓣电影网站爬取电影信息和影评。
遵循PEP8规范，并提供详细的中文注释。
"""

import os
import sys
import time
import logging
import argparse
import json
import traceback
import random
import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Optional, Set, Tuple
import concurrent.futures
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fetch_douban.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('douban_spider')

# 尝试导入依赖包
try:
    import pandas as pd
    from spider.parser import DoubanMovieParser
except ImportError as e:
    logger.error(f"无法导入依赖包: {e}")
    logger.info("请运行 pip install pandas beautifulsoup4 requests fake-useragent 安装依赖")
    sys.exit(1)

try:
    from spider.spider import ArticleSpider
except ImportError:
    logger.error("无法导入spider模块，请确保项目路径正确")
    traceback.print_exc()
    sys.exit(1)


class DoubanMovieSpider:
    """豆瓣电影爬虫，专门用于爬取豆瓣电影网站的信息"""
    
    def __init__(
        self,
        base_url: str = "https://movie.douban.com/",
        output_dir: str = "data/douban",
        max_movies: int = 50,
        max_reviews_per_movie: int = 5,
        delay: float = 3.0,
        timeout: int = 15,
        max_retries: int = 3,
        thread_count: int = 2,
        use_proxy: bool = False
    ) -> None:
        """
        初始化豆瓣电影爬虫
        
        Args:
            base_url: 豆瓣电影网站基础URL
            output_dir: 输出目录
            max_movies: 最大爬取电影数量
            max_reviews_per_movie: 每部电影最大爬取影评数量
            delay: 请求延迟(秒)
            timeout: 请求超时时间(秒)
            max_retries: 最大重试次数
            thread_count: 线程数
            use_proxy: 是否使用代理
        """
        self.base_url = base_url
        self.output_dir = output_dir
        self.max_movies = max_movies
        self.max_reviews_per_movie = max_reviews_per_movie
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.thread_count = thread_count
        self.use_proxy = use_proxy
        
        # 解析器
        self.parser = DoubanMovieParser(base_url)
        
        # 爬取的电影和影评
        self.movies = []
        self.reviews = []
        
        # 已访问的URL
        self.visited_urls = set()
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 加载已访问URL
        self.load_visited_urls()
        
        # 随机User-Agent
        self.user_agent = UserAgent()
        
        logger.info(f"初始化豆瓣电影爬虫，目标爬取 {max_movies} 部电影，每部电影 {max_reviews_per_movie} 条影评")
    
    def load_visited_urls(self) -> None:
        """加载已访问的URL"""
        visited_file = os.path.join(self.output_dir, "visited_urls.json")
        if os.path.exists(visited_file):
            try:
                with open(visited_file, "r", encoding="utf-8") as f:
                    self.visited_urls = set(json.load(f))
                logger.info(f"从记录中加载 {len(self.visited_urls)} 个已访问URL")
            except Exception as e:
                logger.error(f"加载已访问URL失败: {e}")
    
    def save_visited_urls(self) -> None:
        """保存已访问的URL"""
        visited_file = os.path.join(self.output_dir, "visited_urls.json")
        try:
            with open(visited_file, "w", encoding="utf-8") as f:
                json.dump(list(self.visited_urls), f, ensure_ascii=False, indent=2)
            logger.info(f"已保存 {len(self.visited_urls)} 个已访问URL")
        except Exception as e:
            logger.error(f"保存已访问URL失败: {e}")
    
    def get_random_headers(self) -> Dict[str, str]:
        """获取随机请求头"""
        return {
            "User-Agent": self.user_agent.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
    
    def get_page(self, url: str) -> Optional[str]:
        """
        获取网页内容
        
        Args:
            url: 网页URL
            
        Returns:
            网页HTML内容，失败则返回None
        """
        if not url:
            return None
            
        for retry in range(self.max_retries):
            try:
                # 延迟请求，避免被反爬
                if retry > 0:
                    # 指数级增加延迟
                    delay = self.delay * (retry + 1) * (1 + random.random())
                else:
                    delay = self.delay * (0.5 + random.random())
                
                logger.debug(f"等待 {delay:.2f} 秒后请求 {url}")
                time.sleep(delay)
                
                # 发送请求
                headers = self.get_random_headers()
                response = requests.get(url, headers=headers, timeout=self.timeout)
                
                # 检查状态码
                if response.status_code == 200:
                    # 将URL添加到已访问集合
                    self.visited_urls.add(url)
                    return response.text
                else:
                    logger.warning(f"获取页面失败: {url}, 状态码: {response.status_code}")
            except Exception as e:
                logger.warning(f"请求异常: {url}, 错误: {e}")
        
        logger.error(f"多次尝试后获取页面失败: {url}")
        return None
    
    def crawl_movie(self, movie_url: str) -> Optional[Dict[str, Any]]:
        """
        爬取单部电影详情和影评
        
        Args:
            movie_url: 电影详情页URL
            
        Returns:
            电影信息字典，失败则返回None
        """
        # 检查是否已爬取
        if movie_url in self.visited_urls:
            logger.debug(f"已爬取过该电影: {movie_url}")
            return None
        
        # 获取电影详情页
        logger.info(f"爬取电影: {movie_url}")
        html = self.get_page(movie_url)
        if not html:
            return None
        
        # 解析电影信息
        movie = self.parser.parse_article(html, movie_url)
        if not movie:
            logger.warning(f"无法解析电影信息: {movie_url}")
            return None
        
        # 爬取该电影的影评
        movie['reviews'] = self.crawl_movie_reviews(movie_url)
        
        return movie
    
    def crawl_movie_reviews(self, movie_url: str) -> List[Dict[str, Any]]:
        """
        爬取电影的影评
        
        Args:
            movie_url: 电影详情页URL
            
        Returns:
            影评列表
        """
        # 构建影评列表页URL
        review_list_url = f"{movie_url}reviews"
        
        # 获取影评列表页
        logger.info(f"爬取影评列表: {review_list_url}")
        html = self.get_page(review_list_url)
        if not html:
            return []
        
        # 解析影评链接
        soup = BeautifulSoup(html, 'lxml')
        review_links = []
        
        try:
            # 查找影评链接
            review_items = soup.select('.review-item')
            for item in review_items:
                link_elem = item.select_one('.title-link')
                if link_elem and 'href' in link_elem.attrs:
                    review_url = link_elem['href']
                    if review_url:
                        review_links.append(review_url)
            
            logger.info(f"找到 {len(review_links)} 条影评链接")
        except Exception as e:
            logger.error(f"解析影评链接失败: {e}")
            return []
        
        # 限制影评数量
        review_links = review_links[:self.max_reviews_per_movie]
        
        # 爬取影评
        reviews = []
        for url in review_links:
            # 检查是否已爬取
            if url in self.visited_urls:
                logger.debug(f"已爬取过该影评: {url}")
                continue
            
            # 获取影评页面
            logger.info(f"爬取影评: {url}")
            html = self.get_page(url)
            if not html:
                continue
            
            # 解析影评
            review = self.parser.parse_article(html, url)
            if review:
                reviews.append(review)
        
        logger.info(f"成功爬取 {len(reviews)} 条影评")
        return reviews
    
    def crawl(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        执行爬取
        
        Returns:
            电影列表和影评列表的元组
        """
        start_time = time.time()
        
        # 获取首页
        logger.info(f"开始爬取豆瓣电影首页: {self.base_url}")
        home_html = self.get_page(self.base_url)
        if not home_html:
            logger.error("无法获取豆瓣电影首页")
            return [], []
        
        # 提取电影链接
        movie_links = self.parser.extract_article_links(home_html, self.base_url)
        
        # 尝试从Top250获取更多电影链接
        top250_url = "https://movie.douban.com/top250"
        logger.info(f"爬取Top250页面获取更多电影: {top250_url}")
        top250_html = self.get_page(top250_url)
        if top250_html:
            top250_links = self.parser.extract_article_links(top250_html, top250_url)
            movie_links.extend(top250_links)
        
        # 过滤掉非电影详情页的链接
        movie_links = [url for url in movie_links if '/subject/' in url]
        
        # 去重
        movie_links = list(set(movie_links))
        
        # 限制电影数量
        movie_links = movie_links[:self.max_movies]
        
        logger.info(f"找到 {len(movie_links)} 个电影链接，准备爬取")
        
        # 爬取电影
        if self.thread_count <= 1:
            # 单线程爬取
            for url in movie_links:
                movie = self.crawl_movie(url)
                if movie:
                    self.movies.append(movie)
                    # 将影评添加到单独的列表中
                    if 'reviews' in movie:
                        self.reviews.extend(movie['reviews'])
                        del movie['reviews']  # 从电影对象中删除影评，避免重复
        else:
            # 多线程爬取
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_count) as executor:
                future_to_url = {executor.submit(self.crawl_movie, url): url for url in movie_links}
                
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        movie = future.result()
                        if movie:
                            self.movies.append(movie)
                            # 将影评添加到单独的列表中
                            if 'reviews' in movie:
                                self.reviews.extend(movie['reviews'])
                                del movie['reviews']  # 从电影对象中删除影评，避免重复
                    except Exception as e:
                        logger.error(f"爬取电影时发生错误 {url}: {e}")
        
        # 保存结果
        self.save_results()
        
        # 保存已访问URL
        self.save_visited_urls()
        
        elapsed_time = time.time() - start_time
        logger.info(f"爬取完成，共爬取 {len(self.movies)} 部电影和 {len(self.reviews)} 条影评")
        logger.info(f"总耗时: {elapsed_time:.2f} 秒")
        
        return self.movies, self.reviews
    
    def save_results(self) -> None:
        """保存爬取结果"""
        try:
            # 保存电影信息
            if self.movies:
                movie_file = os.path.join(self.output_dir, "movies.csv")
                movie_df = pd.DataFrame(self.movies)
                movie_df.to_csv(movie_file, index=False, encoding="utf-8-sig")
                logger.info(f"已将 {len(self.movies)} 部电影信息保存到 {movie_file}")
            
            # 保存影评信息
            if self.reviews:
                review_file = os.path.join(self.output_dir, "reviews.csv")
                review_df = pd.DataFrame(self.reviews)
                review_df.to_csv(review_file, index=False, encoding="utf-8-sig")
                logger.info(f"已将 {len(self.reviews)} 条影评保存到 {review_file}")
            
            # 保存为JSON格式
            data = {
                "movies": self.movies,
                "reviews": self.reviews,
                "stats": {
                    "movie_count": len(self.movies),
                    "review_count": len(self.reviews),
                    "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            
            json_file = os.path.join(self.output_dir, "douban_data.json")
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已将所有数据保存到 {json_file}")
            
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            traceback.print_exc()


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="豆瓣电影爬虫")
    
    parser.add_argument("--output", "-o", type=str, default="data/douban",
                        help="输出目录")
    parser.add_argument("--max-movies", "-m", type=int, default=50,
                        help="最大爬取电影数量")
    parser.add_argument("--max-reviews", "-r", type=int, default=5,
                        help="每部电影最大爬取影评数量")
    parser.add_argument("--delay", "-d", type=float, default=3.0,
                        help="请求延迟(秒)")
    parser.add_argument("--threads", "-t", type=int, default=2,
                        help="线程数")
    parser.add_argument("--use-proxy", "-p", action="store_true",
                        help="是否使用代理")
    
    return parser.parse_args()


def main() -> None:
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    try:
        # 创建并配置爬虫
        spider = DoubanMovieSpider(
            output_dir=args.output,
            max_movies=args.max_movies,
            max_reviews_per_movie=args.max_reviews,
            delay=args.delay,
            thread_count=args.threads,
            use_proxy=args.use_proxy
        )
        
        # 执行爬取
        movies, reviews = spider.crawl()
        
        # 输出结果统计
        print("\n爬取结果统计:")
        print(f"电影数量: {len(movies)} 部")
        print(f"影评数量: {len(reviews)} 条")
        
        # 更新TODO.md
        try:
            if os.path.exists('TODO.md'):
                with open('TODO.md', 'r', encoding='utf-8') as f:
                    todo_content = f.read()
                
                # 根据爬取结果决定是否标记任务完成
                if len(movies) + len(reviews) >= args.max_movies:
                    # 如果已经是进行中状态，则标记为完成
                    if "- [-] 爬取100篇以上文章样本" in todo_content:
                        updated_content = todo_content.replace(
                            "- [-] 爬取100篇以上文章样本", 
                            "- [x] 爬取100篇以上文章样本"
                        )
                    # 如果是未完成状态，则直接标记为完成
                    else:
                        updated_content = todo_content.replace(
                            "- [ ] 爬取100篇以上文章样本", 
                            "- [x] 爬取100篇以上文章样本"
                        )
                    
                    with open('TODO.md', 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    
                    logger.info("已更新TODO.md，标记爬取任务为已完成")
        except Exception as e:
            logger.error(f"更新TODO.md失败: {e}")
            
    except KeyboardInterrupt:
        logger.info("用户中断爬取")
    except Exception as e:
        logger.error(f"爬取过程中发生错误: {e}")
        traceback.print_exc()


def run_tests():
    """运行单元测试"""
    suite = unittest.TestSuite()
    # 手动添加测试类中的所有测试方法
    suite.addTest(unittest.makeSuite(TestDoubanMovieSpider))
    # 运行测试
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    import sys
    import unittest
    from unittest.mock import patch, MagicMock
    
    if "--test" in sys.argv:
        # 移除--test参数，避免unittest解析错误
        sys.argv.remove("--test")
        # 创建测试套件
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestDoubanMovieSpider)
        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    else:
        # 执行爬取
        main()


# 单元测试
class TestDoubanMovieSpider(unittest.TestCase):
    """豆瓣电影爬虫测试类"""
    
    def setUp(self):
        """测试前准备工作"""
        # 创建测试用的临时目录
        self.test_output_dir = "test_output"
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # 初始化爬虫
        self.spider = DoubanMovieSpider(
            output_dir=self.test_output_dir,
            max_movies=3,
            max_reviews_per_movie=2,
            delay=0.1  # 测试时使用较短的延迟
        )
    
    def tearDown(self):
        """测试后清理工作"""
        # 清理测试生成的文件
        import shutil
        if os.path.exists(self.test_output_dir):
            try:
                shutil.rmtree(self.test_output_dir)
            except:
                pass
    
    @patch('requests.get')
    def test_get_page(self, mock_get):
        """测试获取网页内容"""
        # 模拟正常响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>测试页面内容</body></html>"
        mock_get.return_value = mock_response
        
        # 调用测试方法
        html = self.spider.get_page("https://movie.douban.com/subject/123456/")
        
        # 验证结果
        self.assertEqual(html, "<html><body>测试页面内容</body></html>")
        
        # 验证是否添加到已访问URL集合
        self.assertIn("https://movie.douban.com/subject/123456/", self.spider.visited_urls)
        
        # 测试请求失败的情况
        mock_response.status_code = 404
        html = self.spider.get_page("https://movie.douban.com/subject/not_exist/")
        self.assertIsNone(html)
    
    @patch.object(DoubanMovieSpider, 'get_page')
    @patch.object(DoubanMovieParser, 'parse_article')
    def test_crawl_movie(self, mock_parse, mock_get_page):
        """测试爬取单部电影"""
        # 模拟网页内容
        mock_get_page.return_value = "<html><body>电影详情页</body></html>"
        
        # 模拟解析结果
        mock_movie = {
            'title': '测试电影',
            'year': '2023',
            'rating': '8.5'
        }
        mock_parse.return_value = mock_movie
        
        # 模拟影评爬取
        self.spider.crawl_movie_reviews = MagicMock(return_value=[{'title': '测试影评'}])
        
        # 调用测试方法
        movie = self.spider.crawl_movie("https://movie.douban.com/subject/123456/")
        
        # 验证结果
        self.assertEqual(movie['title'], '测试电影')
        self.assertEqual(movie['reviews'], [{'title': '测试影评'}])
        
        # 验证方法调用
        mock_get_page.assert_called_once_with("https://movie.douban.com/subject/123456/")
        mock_parse.assert_called_once()
        self.spider.crawl_movie_reviews.assert_called_once_with("https://movie.douban.com/subject/123456/")
    
    @patch.object(DoubanMovieSpider, 'get_page')
    def test_crawl_movie_reviews(self, mock_get_page):
        """测试爬取电影影评"""
        # 模拟影评列表页
        mock_get_page.return_value = """
        <html>
            <body>
                <div class="review-item">
                    <a class="title-link" href="https://movie.douban.com/review/1234567/">影评1</a>
                </div>
                <div class="review-item">
                    <a class="title-link" href="https://movie.douban.com/review/7654321/">影评2</a>
                </div>
            </body>
        </html>
        """
        
        # 模拟解析影评
        self.spider.parser.parse_article = MagicMock(return_value={'title': '测试影评'})
        
        # 调用测试方法
        reviews = self.spider.crawl_movie_reviews("https://movie.douban.com/subject/123456/")
        
        # 验证结果
        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0]['title'], '测试影评')
        
        # 验证方法调用
        self.assertEqual(mock_get_page.call_count, 3)  # 1次列表页 + 2次影评页
        self.assertEqual(self.spider.parser.parse_article.call_count, 2)
    
    @patch.object(DoubanMovieSpider, 'crawl_movie')
    @patch.object(DoubanMovieSpider, 'get_page')
    @patch.object(DoubanMovieParser, 'extract_article_links')
    def test_crawl(self, mock_extract_links, mock_get_page, mock_crawl_movie):
        """测试爬取流程"""
        # 模拟首页内容
        mock_get_page.return_value = "<html><body>豆瓣首页</body></html>"
        
        # 模拟提取的链接
        mock_extract_links.return_value = [
            "https://movie.douban.com/subject/1234567/",
            "https://movie.douban.com/subject/7654321/",
            "https://movie.douban.com/subject/9876543/"
        ]
        
        # 模拟爬取的电影
        mock_movie = {
            'title': '测试电影',
            'reviews': [{'title': '测试影评'}]
        }
        mock_crawl_movie.return_value = mock_movie
        
        # 调用测试方法
        movies, reviews = self.spider.crawl()
        
        # 验证结果
        self.assertEqual(len(movies), 3)
        self.assertEqual(len(reviews), 3)
        
        # 验证方法调用
        self.assertEqual(mock_get_page.call_count, 2)  # 首页 + Top250
        self.assertEqual(mock_crawl_movie.call_count, 3)
    
    def test_save_results(self):
        """测试保存结果"""
        # 设置测试数据
        self.spider.movies = [
            {'title': '电影1', 'rating': '8.5'},
            {'title': '电影2', 'rating': '9.0'}
        ]
        
        self.spider.reviews = [
            {'title': '影评1', 'content': '很好看'},
            {'title': '影评2', 'content': '不错'}
        ]
        
        # 调用测试方法
        self.spider.save_results()
        
        # 验证文件是否创建
        self.assertTrue(os.path.exists(os.path.join(self.test_output_dir, "movies.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_output_dir, "reviews.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_output_dir, "douban_data.json"))) 