#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试增量爬虫功能
"""

import os
import sys
import json
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目模块
from spider.spider import ArticleSpider


class TestIncrementalSpider(unittest.TestCase):
    """测试增量爬虫功能"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试URL管理器文件
        self.url_manager_file = os.path.join(self.test_dir, 'visited_urls.json')
        with open(self.url_manager_file, 'w', encoding='utf-8') as f:
            json.dump([
                'https://example.com/article/1',
                'https://example.com/article/2',
                'https://example.com/article/3'
            ], f)
        
        # 创建测试爬虫
        self.spider = ArticleSpider(
            base_url='https://example.com',
            parser_name='test',
            delay=0.1,
            max_articles=10,
            output_dir=self.test_dir,
            thread_count=1,
            timeout=5,
            max_retries=1,
            incremental=True,
            use_proxy=False
        )
        
        # 加载已访问URL
        self.spider.load_visited_urls()
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_load_visited_urls(self):
        """测试加载已访问URL"""
        # 验证已访问URL已加载
        self.assertEqual(len(self.spider.visited_urls), 3)
        self.assertIn('https://example.com/article/1', self.spider.visited_urls)
        self.assertIn('https://example.com/article/2', self.spider.visited_urls)
        self.assertIn('https://example.com/article/3', self.spider.visited_urls)
    
    def test_save_visited_urls(self):
        """测试保存已访问URL"""
        # 添加新的URL
        self.spider.visited_urls.add('https://example.com/article/4')
        
        # 保存已访问URL
        self.spider.save_visited_urls()
        
        # 验证URL已保存
        with open(self.url_manager_file, 'r', encoding='utf-8') as f:
            visited_urls = json.load(f)
        
        self.assertEqual(len(visited_urls), 4)
        self.assertIn('https://example.com/article/1', visited_urls)
        self.assertIn('https://example.com/article/2', visited_urls)
        self.assertIn('https://example.com/article/3', visited_urls)
        self.assertIn('https://example.com/article/4', visited_urls)
    
    def test_is_url_visited(self):
        """测试URL是否已访问"""
        # 已访问的URL
        self.assertTrue(self.spider.is_url_visited('https://example.com/article/1'))
        self.assertTrue(self.spider.is_url_visited('https://example.com/article/2'))
        self.assertTrue(self.spider.is_url_visited('https://example.com/article/3'))
        
        # 未访问的URL
        self.assertFalse(self.spider.is_url_visited('https://example.com/article/4'))
        self.assertFalse(self.spider.is_url_visited('https://example.com/article/5'))
    
    @patch('spider.spider.ArticleSpider._fetch_html')
    @patch('spider.parser.create_parser')
    def test_incremental_crawl(self, mock_create_parser, mock_fetch_html):
        """测试增量爬取"""
        # 模拟解析器
        mock_parser = MagicMock()
        mock_create_parser.return_value = mock_parser
        
        # 模拟解析列表页，返回已访问和未访问的URL
        mock_parser.parse_list_page.return_value = [
            'https://example.com/article/1',  # 已访问
            'https://example.com/article/2',  # 已访问
            'https://example.com/article/4',  # 未访问
            'https://example.com/article/5'   # 未访问
        ]
        
        # 模拟解析文章页
        mock_parser.parse_article.side_effect = lambda html, url: {
            'title': f'文章{url[-1]}',
            'content': f'这是文章{url[-1]}的内容',
            'url': url
        }
        
        # 模拟获取HTML
        mock_fetch_html.return_value = '<html><body>测试页面</body></html>'
        
        # 执行爬取
        articles = self.spider.crawl()
        
        # 验证结果
        self.assertEqual(len(articles), 2)  # 只爬取了2篇未访问的文章
        self.assertEqual(articles[0]['title'], '文章4')
        self.assertEqual(articles[1]['title'], '文章5')
        
        # 验证已访问URL已更新
        self.assertEqual(len(self.spider.visited_urls), 5)
        self.assertIn('https://example.com/article/4', self.spider.visited_urls)
        self.assertIn('https://example.com/article/5', self.spider.visited_urls)


if __name__ == '__main__':
    unittest.main() 