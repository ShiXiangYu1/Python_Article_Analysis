#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬虫模块单元测试
测试ArticleSpider类的各种功能，包括文章列表爬取、文章内容提取、多线程爬取、增量爬取等
"""

import os
import sys
import unittest
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
import threading
import queue

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入爬虫模块
from spider.spider import ArticleSpider, ArticleURLManager
from spider.parser import BaseParser


class TestArticleURLManager(unittest.TestCase):
    """测试文章URL管理器"""
    
    def setUp(self):
        """测试前准备"""
        self.url_manager = ArticleURLManager()
        
    def test_add_url(self):
        """测试添加URL"""
        # 测试添加单个URL
        self.url_manager.add_url('https://example.com/article/1')
        self.assertEqual(len(self.url_manager.urls_to_crawl), 1)
        self.assertEqual(len(self.url_manager.visited_urls), 0)
        
        # 测试添加重复URL
        self.url_manager.add_url('https://example.com/article/1')
        self.assertEqual(len(self.url_manager.urls_to_crawl), 1)  # 重复URL不会被添加
        
        # 测试添加多个URL
        self.url_manager.add_urls(['https://example.com/article/2', 'https://example.com/article/3'])
        self.assertEqual(len(self.url_manager.urls_to_crawl), 3)
        
    def test_has_next_url(self):
        """测试是否有下一个URL"""
        # 初始状态
        self.assertFalse(self.url_manager.has_next_url())
        
        # 添加URL后
        self.url_manager.add_url('https://example.com/article/1')
        self.assertTrue(self.url_manager.has_next_url())
        
        # 获取所有URL后
        _ = self.url_manager.get_url()
        self.assertFalse(self.url_manager.has_next_url())
        
    def test_get_url(self):
        """测试获取URL"""
        # 添加URL
        self.url_manager.add_url('https://example.com/article/1')
        
        # 获取URL
        url = self.url_manager.get_url()
        self.assertEqual(url, 'https://example.com/article/1')
        
        # 检查是否已移至已访问列表
        self.assertEqual(len(self.url_manager.urls_to_crawl), 0)
        self.assertEqual(len(self.url_manager.visited_urls), 1)
        self.assertTrue('https://example.com/article/1' in self.url_manager.visited_urls)
        
        # 当没有更多URL时
        url = self.url_manager.get_url()
        self.assertIsNone(url)
        
    def test_save_progress(self):
        """测试保存进度"""
        # 准备数据
        self.url_manager.add_urls(['https://example.com/article/1', 'https://example.com/article/2'])
        _ = self.url_manager.get_url()  # 获取一个URL，移至已访问列表
        
        # 使用临时文件测试保存
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            temp_path = temp_file.name
            
        try:
            # 保存进度
            self.url_manager.save_progress(temp_path)
            
            # 检查文件内容
            with open(temp_path, 'r') as f:
                progress = json.load(f)
                
            self.assertEqual(len(progress['urls_to_crawl']), 1)
            self.assertEqual(len(progress['visited_urls']), 1)
            self.assertEqual(progress['visited_urls'][0], 'https://example.com/article/1')
            self.assertEqual(progress['urls_to_crawl'][0], 'https://example.com/article/2')
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    def test_load_progress(self):
        """测试加载进度"""
        # 准备测试数据
        progress_data = {
            'urls_to_crawl': ['https://example.com/article/3', 'https://example.com/article/4'],
            'visited_urls': ['https://example.com/article/1', 'https://example.com/article/2']
        }
        
        # 使用临时文件保存测试数据
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
            json.dump(progress_data, temp_file)
            temp_path = temp_file.name
            
        try:
            # 加载进度
            self.url_manager.load_progress(temp_path)
            
            # 检查是否正确加载
            self.assertEqual(len(self.url_manager.urls_to_crawl), 2)
            self.assertEqual(len(self.url_manager.visited_urls), 2)
            self.assertTrue('https://example.com/article/1' in self.url_manager.visited_urls)
            self.assertTrue('https://example.com/article/3' in self.url_manager.urls_to_crawl)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class MockParser(BaseParser):
    """模拟解析器，用于测试"""
    
    def __init__(self, base_url):
        super().__init__(base_url)
        
    def extract_article_links(self, html, url):
        """模拟提取文章链接"""
        # 返回一些测试用的链接
        return ['https://example.com/article/1', 'https://example.com/article/2']
        
    def parse_article(self, html, url):
        """模拟解析文章"""
        # 返回一个测试用的文章数据
        return {
            'title': '测试文章标题',
            'author': '测试作者',
            'date': '2023-09-01',
            'content': '这是测试文章的内容。',
            'url': url
        }


class TestArticleSpider(unittest.TestCase):
    """测试文章爬虫"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试配置
        self.config = {
            'max_articles': 10,
            'max_threads': 2,
            'request_delay': 0.1,
            'timeout': 5,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'data_dir': self.test_dir,
            'url_manager_file': os.path.join(self.test_dir, 'url_manager.json'),
            'articles_file': os.path.join(self.test_dir, 'articles.csv'),
            'proxies': []
        }
        
        # 创建爬虫实例
        self.spider = ArticleSpider(self.config)
        
        # 替换解析器为模拟解析器
        self.spider.parser = MockParser('https://example.com')
        
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
    @patch('requests.get')
    def test_crawl_article(self, mock_get):
        """测试爬取单篇文章"""
        # 模拟请求响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>测试文章标题</h1><div>这是测试文章的内容。</div></body></html>'
        mock_get.return_value = mock_response
        
        # 执行爬取
        article = self.spider.crawl_article('https://example.com/article/1')
        
        # 验证结果
        self.assertIsNotNone(article)
        self.assertEqual(article['title'], '测试文章标题')
        self.assertEqual(article['url'], 'https://example.com/article/1')
        
        # 验证请求被调用
        mock_get.assert_called_once()
        
    @patch('requests.get')
    def test_crawl_article_failure(self, mock_get):
        """测试爬取文章失败的情况"""
        # 模拟请求失败
        mock_get.side_effect = Exception("Connection error")
        
        # 执行爬取
        article = self.spider.crawl_article('https://example.com/article/1')
        
        # 验证结果 - 应当返回None
        self.assertIsNone(article)
        
        # 验证请求被调用
        mock_get.assert_called_once()
        
    @patch('requests.get')
    def test_find_article_links(self, mock_get):
        """测试查找文章链接"""
        # 模拟请求响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><a href="/article/1">文章1</a><a href="/article/2">文章2</a></body></html>'
        mock_get.return_value = mock_response
        
        # 执行查找
        links = self.spider.find_article_links('https://example.com')
        
        # 验证结果
        self.assertEqual(len(links), 2)
        self.assertTrue('https://example.com/article/1' in links)
        
        # 验证请求被调用
        mock_get.assert_called_once()
        
    @patch('requests.get')
    def test_crawl_article_worker(self, mock_get):
        """测试文章爬取工作线程"""
        # 模拟请求响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>测试文章标题</h1><div>这是测试文章的内容。</div></body></html>'
        mock_get.return_value = mock_response
        
        # 创建测试队列
        url_queue = queue.Queue()
        result_queue = queue.Queue()
        
        # 添加测试URL到队列
        url_queue.put('https://example.com/article/1')
        url_queue.put(None)  # 结束信号
        
        # 运行工作线程
        self.spider.crawl_article_worker(url_queue, result_queue, incremental=False)
        
        # 验证结果
        self.assertEqual(result_queue.qsize(), 1)
        article = result_queue.get()
        self.assertEqual(article['title'], '测试文章标题')
        
    @patch.object(ArticleSpider, 'crawl_article')
    @patch.object(ArticleSpider, 'find_article_links')
    def test_crawl_multi_thread(self, mock_find_links, mock_crawl):
        """测试多线程爬取"""
        # 模拟查找链接
        mock_find_links.return_value = [
            'https://example.com/article/1',
            'https://example.com/article/2',
            'https://example.com/article/3'
        ]
        
        # 模拟爬取文章
        mock_crawl.side_effect = [
            {
                'title': '测试文章1',
                'author': '作者1',
                'content': '内容1',
                'url': 'https://example.com/article/1'
            },
            {
                'title': '测试文章2',
                'author': '作者2',
                'content': '内容2',
                'url': 'https://example.com/article/2'
            },
            {
                'title': '测试文章3',
                'author': '作者3',
                'content': '内容3',
                'url': 'https://example.com/article/3'
            }
        ]
        
        # 执行爬取
        result = self.spider.crawl('https://example.com', incremental=False)
        
        # 验证结果
        self.assertEqual(len(result), 3)
        
        # 验证方法被调用
        mock_find_links.assert_called_once()
        self.assertEqual(mock_crawl.call_count, 3)
        
    def test_save_articles_to_csv(self):
        """测试保存文章到CSV"""
        # 准备测试数据
        articles = [
            {
                'title': '测试文章1',
                'author': '作者1',
                'content': '内容1',
                'url': 'https://example.com/article/1',
                'date': '2023-09-01'
            },
            {
                'title': '测试文章2',
                'author': '作者2',
                'content': '内容2',
                'url': 'https://example.com/article/2',
                'date': '2023-09-02'
            }
        ]
        
        # 保存文章
        csv_path = os.path.join(self.test_dir, 'test_articles.csv')
        self.spider.save_articles_to_csv(articles, csv_path)
        
        # 验证文件已创建
        self.assertTrue(os.path.exists(csv_path))
        
        # 读取文件内容进行验证
        import pandas as pd
        df = pd.read_csv(csv_path)
        
        # 验证数据条数和列
        self.assertEqual(len(df), 2)
        self.assertTrue('title' in df.columns)
        self.assertTrue('author' in df.columns)
        self.assertTrue('content' in df.columns)
        
        # 验证具体数据
        self.assertEqual(df.iloc[0]['title'], '测试文章1')
        self.assertEqual(df.iloc[1]['author'], '作者2')
        
    @patch.object(ArticleSpider, 'crawl_multi_thread')
    def test_crawl_incremental(self, mock_crawl_multi):
        """测试增量爬取"""
        # 模拟多线程爬取结果
        mock_crawl_multi.return_value = [
            {
                'title': '新文章1',
                'author': '作者1',
                'content': '内容1',
                'url': 'https://example.com/article/new1'
            },
            {
                'title': '新文章2',
                'author': '作者2',
                'content': '内容2',
                'url': 'https://example.com/article/new2'
            }
        ]
        
        # 准备已有文章数据
        existing_articles = [
            {
                'title': '已有文章1',
                'author': '作者3',
                'content': '内容3',
                'url': 'https://example.com/article/old1'
            }
        ]
        
        # 保存已有文章
        articles_file = os.path.join(self.test_dir, 'articles.csv')
        self.spider.save_articles_to_csv(existing_articles, articles_file)
        self.spider.articles_file = articles_file
        
        # 准备URL管理器数据
        url_manager_data = {
            'urls_to_crawl': ['https://example.com/article/new1', 'https://example.com/article/new2'],
            'visited_urls': ['https://example.com/article/old1']
        }
        
        # 保存URL管理器数据
        url_manager_file = os.path.join(self.test_dir, 'url_manager.json')
        with open(url_manager_file, 'w') as f:
            json.dump(url_manager_data, f)
        self.spider.url_manager_file = url_manager_file
        
        # 执行增量爬取
        result = self.spider.crawl('https://example.com', incremental=True)
        
        # 验证结果包含新文章和旧文章
        self.assertEqual(len(result), 3)  # 1个旧文章 + 2个新文章
        
        # 验证多线程爬取被调用时使用了增量模式
        mock_crawl_multi.assert_called_once_with(True)


if __name__ == '__main__':
    unittest.main() 