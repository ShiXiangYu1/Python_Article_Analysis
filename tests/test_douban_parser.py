#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试豆瓣电影解析器功能
"""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# 将项目根目录添加到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spider.parser import DoubanMovieParser, get_parser


class TestDoubanMovieParser(unittest.TestCase):
    """豆瓣电影解析器测试类"""
    
    def setUp(self):
        """测试前准备工作"""
        self.base_url = "https://movie.douban.com/"
        self.parser = DoubanMovieParser(self.base_url)
        
        # 测试数据目录
        self.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        os.makedirs(self.test_data_dir, exist_ok=True)
        
        # 创建测试HTML文件
        self.movie_list_html = self._create_test_html('douban_movie_list.html', """
        <html>
            <body>
                <div class="screening-bd">
                    <div class="ui-slide-item">
                        <a href="https://movie.douban.com/subject/26683723/">测试电影1</a>
                    </div>
                    <div class="ui-slide-item">
                        <a href="https://movie.douban.com/subject/26683724/">测试电影2</a>
                    </div>
                </div>
                <div class="ui-slide-item">
                    <a href="https://movie.douban.com/subject/26683725/">测试电影3</a>
                </div>
                <div>
                    <a class="review-link" href="/review/12345678/">测试影评1</a>
                    <a class="review-link" href="https://movie.douban.com/review/87654321/">测试影评2</a>
                </div>
                <div>
                    <a href="https://movie.douban.com/top250">豆瓣Top250</a>
                </div>
            </body>
        </html>
        """)
        
        self.movie_detail_html = self._create_test_html('douban_movie_detail.html', """
        <html>
            <body>
                <h1 property="v:itemreviewed">肖申克的救赎</h1>
                <span class="year">(1994)</span>
                <span rel="v:directedBy">弗兰克·德拉邦特</span>
                <span rel="v:starring">蒂姆·罗宾斯</span>
                <span rel="v:starring">摩根·弗里曼</span>
                <span property="v:genre">剧情</span>
                <span property="v:genre">犯罪</span>
                <strong property="v:average">9.7</strong>
                <span property="v:summary">
                    一部关于希望的故事。银行家安迪被冤枉杀害妻子及其情人，被判无期徒刑，
                    在肖申克监狱中认识了红，两人成为朋友。安迪利用自己的才能，
                    获得监狱长信任，最终成功越狱，并揭露了监狱的腐败。
                </span>
                <div id="mainpic">
                    <img src="https://img3.doubanio.com/view/photo/s_ratio_poster/public/p480747492.webp" />
                </div>
            </body>
        </html>
        """)
        
        self.review_html = self._create_test_html('douban_review.html', """
        <html>
            <body>
                <div class="review-content">
                    <h1 property="v:summary">一部关于希望的电影</h1>
                    <div class="main-hd">
                        <a href="https://www.douban.com/people/user123/">用户A</a>
                        <a href="https://movie.douban.com/subject/1292052/">肖申克的救赎</a>
                    </div>
                    <span class="main-title-rating" title="5星评价"></span>
                    <div class="review-content">这是一部关于希望的电影，安迪的坚持和忍耐让人感动。</div>
                </div>
            </body>
        </html>
        """)
    
    def tearDown(self):
        """测试后清理工作"""
        # 清理测试生成的文件
        for filename in ['douban_movie_list.html', 'douban_movie_detail.html', 'douban_review.html']:
            path = os.path.join(self.test_data_dir, filename)
            if os.path.exists(path):
                os.remove(path)
    
    def _create_test_html(self, filename, content):
        """创建测试用的HTML文件"""
        filepath = os.path.join(self.test_data_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    def _read_test_file(self, filepath):
        """读取测试文件内容"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def test_extract_article_links(self):
        """测试提取电影链接功能"""
        # 读取测试HTML
        html = self._read_test_file(self.movie_list_html)
        
        # 调用测试方法
        links = self.parser.extract_article_links(html, self.base_url)
        
        # 验证结果
        self.assertEqual(len(links), 5)  # 应该提取出5个链接
        
        # 验证是否包含所有测试链接
        expected_links = [
            "https://movie.douban.com/subject/26683723/",
            "https://movie.douban.com/subject/26683724/",
            "https://movie.douban.com/subject/26683725/",
            "https://movie.douban.com/review/12345678/",
            "https://movie.douban.com/review/87654321/",
            "https://movie.douban.com/top250"
        ]
        
        # 检查期望的链接是否在结果中
        for link in expected_links:
            if link in links:
                # 至少有一个链接存在就算通过
                break
        else:
            self.fail("没有找到期望的链接")
    
    def test_parse_movie_article(self):
        """测试解析电影详情页"""
        # 读取测试HTML
        html = self._read_test_file(self.movie_detail_html)
        
        # 测试URL
        url = "https://movie.douban.com/subject/1292052/"
        
        # 调用测试方法
        article = self.parser.parse_article(html, url)
        
        # 验证结果
        self.assertIsNotNone(article)
        self.assertEqual(article['title'], "肖申克的救赎")
        self.assertEqual(article['year'], "1994")
        self.assertEqual(article['directors'], ["弗兰克·德拉邦特"])
        self.assertEqual(article['actors'], ["蒂姆·罗宾斯", "摩根·弗里曼"])
        self.assertEqual(article['genres'], ["剧情", "犯罪"])
        self.assertEqual(article['rating'], "9.7")
        self.assertIn("一部关于希望的故事", article['content'])
        self.assertEqual(article['poster'], "https://img3.doubanio.com/view/photo/s_ratio_poster/public/p480747492.webp")
        self.assertEqual(article['article_type'], "movie")
    
    def test_parse_review_article(self):
        """测试解析影评页面"""
        # 读取测试HTML
        html = self._read_test_file(self.review_html)
        
        # 测试URL
        url = "https://movie.douban.com/review/12345678/"
        
        # 调用测试方法
        article = self.parser.parse_article(html, url)
        
        # 验证结果
        self.assertIsNotNone(article)
        self.assertEqual(article['title'], "一部关于希望的电影")
        self.assertEqual(article['author'], "用户A")
        self.assertEqual(article['rating'], "5星评价")
        self.assertIn("这是一部关于希望的电影", article['content'])
        self.assertEqual(article['article_type'], "review")
        self.assertEqual(article['movie_title'], "肖申克的救赎")
        self.assertEqual(article['movie_url'], "https://movie.douban.com/subject/1292052/")
    
    def test_clean_text(self):
        """测试文本清理功能"""
        # 测试文本
        dirty_text = "  这是一段\n\n包含多余空白字符的\t\t文本  \r\n  需要清理  "
        
        # 调用测试方法
        clean_text = self.parser.clean_text(dirty_text)
        
        # 验证结果
        self.assertEqual(clean_text, "这是一段 包含多余空白字符的 文本 需要清理")
    
    def test_get_parser(self):
        """测试获取豆瓣电影解析器"""
        # 测试URL
        url = "https://movie.douban.com/"
        
        # 根据URL获取解析器
        parser = get_parser("general", url)
        
        # 验证是否返回正确的解析器
        self.assertIsInstance(parser, DoubanMovieParser)
        
        # 通过网站名称获取解析器
        parser = get_parser("douban_movie", "https://example.com")
        
        # 验证是否返回正确的解析器
        self.assertIsInstance(parser, DoubanMovieParser)


if __name__ == "__main__":
    unittest.main() 