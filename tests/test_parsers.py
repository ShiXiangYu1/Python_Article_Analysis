#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网站解析器单元测试
用于测试各种网站解析器的功能，包括文章列表解析、文章内容提取等
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import json
import tempfile
from bs4 import BeautifulSoup

from spider.parser import (
    BaseParser, 
    ZhihuParser,
    CSDNParser, 
    JianshuParser, 
    SinaNewsParser,
    GeneralParser,
    get_parser
)

class TestBaseParser(unittest.TestCase):
    """基础解析器测试类"""
    
    def setUp(self):
        """测试前准备工作"""
        self.parser = BaseParser('https://example.com')
        
    def test_init(self):
        """测试初始化方法"""
        self.assertEqual(self.parser.base_url, 'https://example.com')
        
    def test_parse_article_list(self):
        """测试文章列表解析方法(基类方法应当返回空列表)"""
        html = '<html><body><div class="article">Article 1</div></body></html>'
        result = self.parser.parse_article_list(html)
        self.assertEqual(result, [])
        
    def test_extract_article_links(self):
        """测试文章链接提取方法(基类方法应当返回空列表)"""
        html = '<html><body><a href="/article/1">Article 1</a></body></html>'
        result = self.parser.extract_article_links(html, 'https://example.com')
        self.assertEqual(result, [])
        
    def test_parse_article(self):
        """测试文章解析方法(基类方法应当返回None)"""
        html = '<html><body><h1>Title</h1><div class="content">Content</div></body></html>'
        result = self.parser.parse_article(html, 'https://example.com/article/1')
        self.assertIsNone(result)
        
    def test_clean_text(self):
        """测试文本清理方法"""
        text = '  测试文本\n\n带有空格和换行  '
        result = self.parser.clean_text(text)
        self.assertEqual(result, '测试文本 带有空格和换行')
        
    def test_normalize_url(self):
        """测试URL标准化方法"""
        # 测试相对路径
        url = '/article/123'
        result = self.parser.normalize_url(url)
        self.assertEqual(result, 'https://example.com/article/123')
        
        # 测试绝对路径
        url = 'https://other.com/article/456'
        result = self.parser.normalize_url(url)
        self.assertEqual(result, 'https://other.com/article/456')
        
        # 测试不完整URL
        url = '//example.com/article/789'
        result = self.parser.normalize_url(url)
        self.assertEqual(result, 'https://example.com/article/789')


class TestZhihuParser(unittest.TestCase):
    """知乎解析器测试类"""
    
    def setUp(self):
        """测试前准备工作"""
        self.parser = ZhihuParser('https://www.zhihu.com')
        
        # 模拟知乎文章列表HTML
        self.list_html = '''
        <html>
            <body>
                <div class="List-item">
                    <div class="ContentItem">
                        <h2 class="ContentItem-title">
                            <a href="/p/123456">知乎文章标题</a>
                        </h2>
                    </div>
                </div>
            </body>
        </html>
        '''
        
        # 模拟知乎文章内容HTML
        self.article_html = '''
        <html>
            <body>
                <h1 class="Post-Title">知乎文章标题</h1>
                <div class="Post-Author">
                    <div class="AuthorInfo">
                        <div class="AuthorInfo-name">作者名</div>
                    </div>
                </div>
                <div class="Post-RichTextContainer">
                    <div class="RichText">这是文章内容</div>
                </div>
                <div class="ContentItem-time">发布于 2023-09-01</div>
            </body>
        </html>
        '''
        
    def test_parse_article_list(self):
        """测试知乎文章列表解析"""
        result = self.parser.parse_article_list(self.list_html)
        self.assertTrue(len(result) > 0)
        self.assertTrue('/p/123456' in result[0] or 'https://www.zhihu.com/p/123456' in result[0])
        
    def test_extract_article_links(self):
        """测试知乎文章链接提取"""
        result = self.parser.extract_article_links(self.list_html, 'https://www.zhihu.com')
        self.assertTrue(len(result) > 0)
        self.assertTrue('https://www.zhihu.com/p/123456' in result)
        
    def test_parse_article(self):
        """测试知乎文章解析"""
        result = self.parser.parse_article(self.article_html, 'https://www.zhihu.com/p/123456')
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], '知乎文章标题')
        self.assertEqual(result['author'], '作者名')
        self.assertEqual(result['content'], '这是文章内容')
        self.assertTrue('date' in result)
        self.assertEqual(result['url'], 'https://www.zhihu.com/p/123456')


class TestCSDNParser(unittest.TestCase):
    """CSDN解析器测试类"""
    
    def setUp(self):
        """测试前准备工作"""
        self.parser = CSDNParser('https://blog.csdn.net')
        
        # 模拟CSDN文章列表HTML
        self.list_html = '''
        <html>
            <body>
                <div class="article-list">
                    <div class="article-item-box">
                        <h4>
                            <a href="/username/article/12345">CSDN文章标题</a>
                        </h4>
                    </div>
                </div>
            </body>
        </html>
        '''
        
        # 模拟CSDN文章内容HTML
        self.article_html = '''
        <html>
            <body>
                <h1 class="title-article">CSDN文章标题</h1>
                <a class="follow-nickName">作者名</a>
                <div class="article-info-box">
                    <span class="time">2023-09-01 10:00:00</span>
                </div>
                <div id="content_views" class="markdown_views">
                    这是文章内容
                </div>
            </body>
        </html>
        '''
        
    def test_parse_article_list(self):
        """测试CSDN文章列表解析"""
        result = self.parser.parse_article_list(self.list_html)
        self.assertTrue(len(result) > 0)
        self.assertTrue('/username/article/12345' in result[0] or 'https://blog.csdn.net/username/article/12345' in result[0])
        
    def test_extract_article_links(self):
        """测试CSDN文章链接提取"""
        result = self.parser.extract_article_links(self.list_html, 'https://blog.csdn.net')
        self.assertTrue(len(result) > 0)
        self.assertTrue('https://blog.csdn.net/username/article/12345' in result)
        
    def test_parse_article(self):
        """测试CSDN文章解析"""
        result = self.parser.parse_article(self.article_html, 'https://blog.csdn.net/username/article/12345')
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], 'CSDN文章标题')
        self.assertEqual(result['author'], '作者名')
        self.assertEqual(result['content'], '这是文章内容')
        self.assertTrue('date' in result)
        self.assertEqual(result['url'], 'https://blog.csdn.net/username/article/12345')


class TestJianshuParser(unittest.TestCase):
    """简书解析器测试类"""
    
    def setUp(self):
        """测试前准备工作"""
        self.parser = JianshuParser('https://www.jianshu.com')
        
        # 模拟简书文章列表HTML
        self.list_html = '''
        <html>
            <body>
                <div class="note-list">
                    <li class="have-img">
                        <a class="title" href="/p/abcdef">简书文章标题</a>
                    </li>
                </div>
            </body>
        </html>
        '''
        
        # 模拟简书文章内容HTML
        self.article_html = '''
        <html>
            <body>
                <h1 class="title">简书文章标题</h1>
                <div class="author">
                    <div class="name">作者名</div>
                </div>
                <div class="publish-time">2023.09.01 10:00</div>
                <article class="article">
                    <div class="show-content">这是文章内容</div>
                </article>
            </body>
        </html>
        '''
        
    def test_parse_article_list(self):
        """测试简书文章列表解析"""
        result = self.parser.parse_article_list(self.list_html)
        self.assertTrue(len(result) > 0)
        self.assertTrue('/p/abcdef' in result[0] or 'https://www.jianshu.com/p/abcdef' in result[0])
        
    def test_extract_article_links(self):
        """测试简书文章链接提取"""
        result = self.parser.extract_article_links(self.list_html, 'https://www.jianshu.com')
        self.assertTrue(len(result) > 0)
        self.assertTrue('https://www.jianshu.com/p/abcdef' in result)
        
    def test_parse_article(self):
        """测试简书文章解析"""
        result = self.parser.parse_article(self.article_html, 'https://www.jianshu.com/p/abcdef')
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], '简书文章标题')
        self.assertEqual(result['author'], '作者名')
        self.assertEqual(result['content'], '这是文章内容')
        self.assertTrue('date' in result)
        self.assertEqual(result['url'], 'https://www.jianshu.com/p/abcdef')


class TestSinaNewsParser(unittest.TestCase):
    """新浪新闻解析器测试类"""
    
    def setUp(self):
        """测试前准备工作"""
        self.parser = SinaNewsParser('https://news.sina.com.cn')
        
        # 模拟新浪新闻文章列表HTML
        self.list_html = '''
        <html>
            <body>
                <div class="news-list">
                    <div class="news-item">
                        <h2><a href="https://news.sina.com.cn/c/2023-09-01/doc-imaznpen9876543.shtml">新浪新闻标题</a></h2>
                    </div>
                </div>
            </body>
        </html>
        '''
        
        # 模拟新浪新闻文章内容HTML
        self.article_html = '''
        <html>
            <body>
                <h1 class="main-title">新浪新闻标题</h1>
                <div class="date">2023年09月01日 10:00</div>
                <div class="author">作者名</div>
                <div id="article" class="article">
                    <p>这是文章内容</p>
                </div>
            </body>
        </html>
        '''
        
    def test_extract_article_links(self):
        """测试新浪新闻文章链接提取"""
        result = self.parser.extract_article_links(self.list_html, 'https://news.sina.com.cn')
        self.assertTrue(len(result) > 0)
        self.assertTrue('https://news.sina.com.cn/c/2023-09-01/doc-imaznpen9876543.shtml' in result)
        
    def test_is_news_article_url(self):
        """测试是否为新闻文章URL的判断"""
        # 有效的新闻URL
        self.assertTrue(self.parser._is_news_article_url('https://news.sina.com.cn/c/2023-09-01/doc-abc123.shtml'))
        
        # 无效的URL，不是新闻文章页
        self.assertFalse(self.parser._is_news_article_url('https://news.sina.com.cn/index.shtml'))
        self.assertFalse(self.parser._is_news_article_url('https://sports.sina.com.cn/article.html'))
        
    def test_parse_article(self):
        """测试新浪新闻文章解析"""
        result = self.parser.parse_article(self.article_html, 'https://news.sina.com.cn/c/2023-09-01/doc-imaznpen9876543.shtml')
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], '新浪新闻标题')
        self.assertTrue('author' in result)
        self.assertEqual(result['content'], '这是文章内容')
        self.assertTrue('date' in result)
        self.assertEqual(result['url'], 'https://news.sina.com.cn/c/2023-09-01/doc-imaznpen9876543.shtml')


class TestGeneralParser(unittest.TestCase):
    """通用解析器测试类"""
    
    def setUp(self):
        """测试前准备工作"""
        self.parser = GeneralParser('https://example.com')
        
        # 模拟通用文章列表HTML
        self.list_html = '''
        <html>
            <body>
                <div class="article-list">
                    <div class="article">
                        <h2><a href="/article/123">通用文章标题</a></h2>
                    </div>
                </div>
            </body>
        </html>
        '''
        
        # 模拟通用文章内容HTML
        self.article_html = '''
        <html>
            <body>
                <article>
                    <h1>通用文章标题</h1>
                    <div class="meta">
                        <span class="author">作者名</span>
                        <span class="date">2023-09-01</span>
                    </div>
                    <div class="content">
                        <p>这是文章内容</p>
                    </div>
                </article>
            </body>
        </html>
        '''
        
    def test_extract_article_links(self):
        """测试通用文章链接提取"""
        result = self.parser.extract_article_links(self.list_html, 'https://example.com')
        self.assertTrue(len(result) > 0)
        self.assertTrue('https://example.com/article/123' in result)
        
    def test_is_article_url(self):
        """测试是否为文章URL的判断"""
        # 可能的文章URL
        self.assertTrue(self.parser._is_article_url('https://example.com/article/123'))
        self.assertTrue(self.parser._is_article_url('https://example.com/blog/post/123'))
        self.assertTrue(self.parser._is_article_url('https://example.com/news/2023/09/01/title.html'))
        
        # 不太可能是文章URL的路径
        self.assertFalse(self.parser._is_article_url('https://example.com/index.html'))
        self.assertFalse(self.parser._is_article_url('https://example.com/about'))
        self.assertFalse(self.parser._is_article_url('https://example.com/contact'))
        
    def test_parse_article(self):
        """测试通用文章解析"""
        result = self.parser.parse_article(self.article_html, 'https://example.com/article/123')
        self.assertIsNotNone(result)
        self.assertEqual(result['title'], '通用文章标题')
        self.assertTrue('content' in result)
        self.assertTrue('url' in result)
        self.assertEqual(result['url'], 'https://example.com/article/123')


class TestGetParser(unittest.TestCase):
    """测试获取解析器的工厂函数"""
    
    def test_get_parser(self):
        """测试获取各种解析器"""
        # 测试获取知乎解析器
        parser = get_parser('zhihu', 'https://www.zhihu.com')
        self.assertIsInstance(parser, ZhihuParser)
        
        # 测试获取CSDN解析器
        parser = get_parser('csdn', 'https://blog.csdn.net')
        self.assertIsInstance(parser, CSDNParser)
        
        # 测试获取简书解析器
        parser = get_parser('jianshu', 'https://www.jianshu.com')
        self.assertIsInstance(parser, JianshuParser)
        
        # 测试获取新浪新闻解析器
        parser = get_parser('sina', 'https://news.sina.com.cn')
        self.assertIsInstance(parser, SinaNewsParser)
        
        # 测试获取通用解析器
        parser = get_parser('general', 'https://example.com')
        self.assertIsInstance(parser, GeneralParser)
        
        # 测试使用无效的解析器名称，应当返回通用解析器
        parser = get_parser('invalid_parser', 'https://example.com')
        self.assertIsInstance(parser, GeneralParser)


if __name__ == '__main__':
    unittest.main() 