#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试多线程爬虫功能
"""

import os
import sys
import unittest
import tempfile
import shutil
import threading
import time
from unittest.mock import patch, MagicMock

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目模块
from spider.spider import ArticleSpider


class TestMultithreadSpider(unittest.TestCase):
    """测试多线程爬虫功能"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试爬虫
        self.spider = ArticleSpider(
            base_url='https://example.com',
            parser_name='test',
            delay=0.1,
            max_articles=10,
            output_dir=self.test_dir,
            thread_count=3,  # 使用3个线程
            timeout=5,
            max_retries=1,
            incremental=False,
            use_proxy=False
        )
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch('spider.spider.ArticleSpider._fetch_html')
    @patch('spider.parser.create_parser')
    def test_multithread_crawl(self, mock_create_parser, mock_fetch_html):
        """测试多线程爬取"""
        # 模拟解析器
        mock_parser = MagicMock()
        mock_create_parser.return_value = mock_parser
        
        # 模拟解析列表页，返回多个URL
        mock_parser.parse_list_page.return_value = [
            f'https://example.com/article/{i}' for i in range(1, 11)
        ]
        
        # 模拟解析文章页，记录线程ID
        thread_ids = []
        
        def mock_parse_article(html, url):
            thread_id = threading.get_ident()
            thread_ids.append(thread_id)
            time.sleep(0.1)  # 模拟网络延迟
            return {
                'title': f'文章{url[-1]}',
                'content': f'这是文章{url[-1]}的内容',
                'url': url,
                'thread_id': thread_id
            }
        
        mock_parser.parse_article.side_effect = mock_parse_article
        
        # 模拟获取HTML
        mock_fetch_html.return_value = '<html><body>测试页面</body></html>'
        
        # 执行爬取
        articles = self.spider.crawl()
        
        # 验证结果
        self.assertEqual(len(articles), 10)  # 爬取了10篇文章
        
        # 验证使用了多个线程
        unique_thread_ids = set(thread_ids)
        self.assertGreater(len(unique_thread_ids), 1)  # 至少使用了2个线程
    
    @patch('spider.spider.ArticleSpider._fetch_html')
    @patch('spider.parser.create_parser')
    def test_thread_count(self, mock_create_parser, mock_fetch_html):
        """测试线程数量"""
        # 模拟解析器
        mock_parser = MagicMock()
        mock_create_parser.return_value = mock_parser
        
        # 模拟解析列表页，返回多个URL
        mock_parser.parse_list_page.return_value = [
            f'https://example.com/article/{i}' for i in range(1, 21)
        ]
        
        # 模拟解析文章页，记录活动线程数
        max_active_threads = [0]  # 使用列表存储，以便在闭包中修改
        thread_lock = threading.Lock()
        active_threads = set()
        
        def mock_parse_article(html, url):
            thread_id = threading.get_ident()
            
            with thread_lock:
                active_threads.add(thread_id)
                current_active = len(active_threads)
                if current_active > max_active_threads[0]:
                    max_active_threads[0] = current_active
            
            time.sleep(0.2)  # 模拟网络延迟
            
            with thread_lock:
                active_threads.remove(thread_id)
            
            return {
                'title': f'文章{url[-1]}',
                'content': f'这是文章{url[-1]}的内容',
                'url': url
            }
        
        mock_parser.parse_article.side_effect = mock_parse_article
        
        # 模拟获取HTML
        mock_fetch_html.return_value = '<html><body>测试页面</body></html>'
        
        # 执行爬取
        articles = self.spider.crawl()
        
        # 验证结果
        self.assertEqual(len(articles), 20)  # 爬取了20篇文章
        
        # 验证最大活动线程数不超过配置的线程数
        self.assertLessEqual(max_active_threads[0], self.spider.thread_count)
        
        # 验证最大活动线程数接近配置的线程数
        self.assertGreaterEqual(max_active_threads[0], self.spider.thread_count - 1)


if __name__ == '__main__':
    unittest.main() 