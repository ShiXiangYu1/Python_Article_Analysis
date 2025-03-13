#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
整合测试脚本
用于验证爬虫、NLP和可视化模块的整合功能
"""

import unittest
import os
import sys
import json
import tempfile
import shutil
import threading
import time
from unittest.mock import patch, MagicMock

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目模块
from spider.spider import ArticleSpider
from spider.proxy_pool import Proxy, ProxyPool
from nlp.segmenter import Segmenter
from nlp.tfidf import KeywordExtractor
from nlp.entity_recognition import EntityRecognizer
from nlp.relation_extractor import RelationExtractor
from nlp.relation_enhancer import RelationEnhancer
import visualization.app as viz_app


class TestModuleIntegration(unittest.TestCase):
    """测试模块整合"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试配置
        self.config = {
            'max_articles': 5,
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
        
        # 创建测试文章
        self.test_articles = [
            {
                'title': '测试文章1',
                'author': '作者1',
                'content': '自然语言处理是人工智能的一个重要分支。李明是北京大学的教授，他在自然语言处理领域做出了重要贡献。',
                'url': 'https://example.com/article/1',
                'date': '2023-09-01'
            },
            {
                'title': '测试文章2',
                'author': '作者2',
                'content': '机器学习是实现自然语言处理的重要方法。张伟在清华大学开设了机器学习课程。',
                'url': 'https://example.com/article/2',
                'date': '2023-09-02'
            }
        ]
        
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    @patch.object(ArticleSpider, 'crawl')
    def test_crawl_and_save(self, mock_crawl):
        """测试爬取和保存文章"""
        # 模拟爬取结果
        mock_crawl.return_value = self.test_articles
        
        # 创建爬虫实例
        spider = ArticleSpider(self.config)
        
        # 执行爬取
        articles = spider.crawl('https://example.com')
        
        # 保存文章
        spider.save_articles_to_csv(articles, self.config['articles_file'])
        
        # 验证文件已创建
        self.assertTrue(os.path.exists(self.config['articles_file']))
        
        # 读取保存的文件验证内容
        import pandas as pd
        df = pd.read_csv(self.config['articles_file'])
        
        # 验证数据条数
        self.assertEqual(len(df), len(self.test_articles))
        
        # 验证内容一致
        self.assertEqual(df.iloc[0]['title'], self.test_articles[0]['title'])
        self.assertEqual(df.iloc[1]['content'], self.test_articles[1]['content'])
    
    def test_nlp_pipeline(self):
        """测试NLP处理流程"""
        # 创建分词器
        segmenter = Segmenter()
        
        # 创建关键词提取器
        keyword_extractor = KeywordExtractor()
        
        # 创建实体识别器
        entity_recognizer = EntityRecognizer()
        
        # 创建关系提取器
        relation_extractor = RelationExtractor()
        
        # 创建关系增强器
        relation_enhancer = RelationEnhancer()
        
        # 添加同义词
        relation_enhancer.add_synonym("李明", "小明")
        relation_enhancer.add_synonym("北京大学", "北大")
        
        # 处理第一篇文章
        text = self.test_articles[0]['content']
        
        # 1. 分词
        tokens = segmenter.segment(text)
        self.assertTrue(len(tokens) > 0)
        self.assertIn("自然语言处理", tokens)
        
        # 2. 提取关键词
        keywords = keyword_extractor.extract_keywords(text, top_k=3)
        self.assertTrue(len(keywords) > 0)
        self.assertTrue(any("自然语言处理" in kw[0] for kw in keywords))
        
        # 3. 识别实体
        entities = entity_recognizer.extract_entities(text)
        self.assertIsInstance(entities, dict)
        self.assertTrue(any(category in entities for category in ["person", "place", "organization"]))
        
        # 4. 提取关系
        relations = relation_extractor.extract_triples(text)
        self.assertIsInstance(relations, list)
        
        # 5. 增强关系
        enhanced_relations = relation_enhancer.enhance_triples(relations)
        self.assertIsInstance(enhanced_relations, list)
        
        # 返回处理结果
        result = {
            'text': text,
            'tokens': tokens,
            'keywords': [kw[0] for kw in keywords],
            'entities': entities,
            'relations': relations,
            'enhanced_relations': enhanced_relations
        }
        
        # 验证处理结果包含所有必要字段
        self.assertTrue(all(field in result for field in ['text', 'tokens', 'keywords', 'entities', 'relations', 'enhanced_relations']))
    
    @patch('pandas.read_csv')
    def test_visualization_data_loading(self, mock_read_csv):
        """测试可视化数据加载"""
        # 模拟DataFrame
        mock_df = MagicMock()
        mock_df.empty = False
        mock_read_csv.return_value = mock_df
        
        # 使用测试文件路径
        test_file = os.path.join(self.test_dir, 'test_articles.csv')
        
        # 调用加载函数
        result = viz_app.load_data(test_file)
        
        # 验证pandas.read_csv被调用且使用了正确的文件路径
        mock_read_csv.assert_called_once_with(test_file)
        
        # 验证返回结果是mock_df
        self.assertEqual(result, mock_df)
    
    def test_relation_graph_generation(self):
        """测试关系图谱生成"""
        # 准备测试三元组
        triples = [
            {'subject': '李明', 'predicate': '是', 'object': '教授'},
            {'subject': '李明', 'predicate': '在', 'object': '北京大学'},
            {'subject': '张伟', 'predicate': '开设', 'object': '机器学习课程'}
        ]
        
        # 生成关系图谱
        graph = viz_app.generate_relation_graph(triples)
        
        # 验证图谱生成成功
        self.assertEqual(type(graph).__name__, 'Graph')
        
        # 验证图谱包含所有实体和关系
        html = graph.render_embed()
        for triple in triples:
            self.assertIn(triple['subject'], html)
            self.assertIn(triple['predicate'], html)
            self.assertIn(triple['object'], html)
    
    @patch('requests.get')
    def test_proxy_integration(self, mock_get):
        """测试代理池与爬虫整合"""
        # 创建代理池
        pool = ProxyPool(
            proxies_file=os.path.join(self.test_dir, 'proxies.json'),
            check_interval=60
        )
        
        # 添加测试代理
        proxy = Proxy('http://127.0.0.1:8080')
        pool.add_proxy(proxy)
        
        # 修改配置使用代理
        self.config['use_proxy'] = True
        
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<html><body><h1>测试页面</h1></body></html>'
        mock_get.return_value = mock_response
        
        # 创建爬虫实例
        spider = ArticleSpider(self.config)
        spider.proxy_pool = pool
        
        # 执行爬取
        html = spider._fetch_html('https://example.com')
        
        # 验证结果
        self.assertEqual(html, mock_response.text)
        
        # 验证requests.get被调用
        mock_get.assert_called_once()
        
        # 验证代理被使用
        call_kwargs = mock_get.call_args[1]
        self.assertIn('proxies', call_kwargs)
    
    def test_flask_routes(self):
        """测试Flask路由"""
        # 创建测试客户端
        client = viz_app.app.test_client()
        
        # 模拟加载数据
        with patch('visualization.app.load_data') as mock_load:
            # 模拟返回非空DataFrame
            mock_df = MagicMock()
            mock_df.empty = False
            mock_df.__len__.return_value = 2  # 模拟2篇文章
            # 模拟to_dict方法返回测试文章数据
            mock_df.iloc.__getitem__.return_value.to_dict.return_value = self.test_articles[0]
            mock_load.return_value = mock_df
            
            # 测试首页路由
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'<!DOCTYPE html>', response.data)
            
            # 测试文章详情路由
            with patch('visualization.app.parse_triples') as mock_parse:
                mock_parse.return_value = [
                    {'subject': '李明', 'predicate': '是', 'object': '教授'}
                ]
                response = client.get('/article/0')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'<!DOCTYPE html>', response.data)
                
            # 测试关系图谱路由
            with patch('visualization.app.generate_relation_graph') as mock_graph:
                mock_graph_instance = MagicMock()
                mock_graph.return_value = mock_graph_instance
                mock_graph_instance.render_embed.return_value = '<div id="chart"></div>'
                
                response = client.get('/graph/0')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'<!DOCTYPE html>', response.data)
                
            # 测试数据分析路由
            with patch('visualization.app.generate_keyword_cloud') as mock_cloud, \
                 patch('visualization.app.generate_entity_bar') as mock_bar, \
                 patch('visualization.app.generate_sentiment_pie') as mock_pie, \
                 patch('visualization.app.generate_topic_distribution') as mock_topic, \
                 patch('visualization.app.generate_article_length_histogram') as mock_hist, \
                 patch('visualization.app.generate_time_trend') as mock_trend:
                
                # 配置所有模拟图表
                for mock_chart in [mock_cloud, mock_bar, mock_pie, mock_topic, mock_hist, mock_trend]:
                    chart_instance = MagicMock()
                    mock_chart.return_value = chart_instance
                    chart_instance.render_embed.return_value = '<div class="chart"></div>'
                
                response = client.get('/analyze')
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'<!DOCTYPE html>', response.data)


if __name__ == '__main__':
    unittest.main() 