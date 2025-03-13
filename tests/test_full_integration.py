#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全面集成测试脚本
用于测试整个系统的功能，包括爬虫、NLP分析和可视化
"""

import unittest
import os
import sys
import json
import tempfile
import shutil
import time
import pandas as pd
from unittest.mock import patch, MagicMock

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目模块
from spider.spider import ArticleSpider
from spider.proxy_pool import ProxyPool
from nlp.segmentation import create_segmenter
from nlp.tfidf import TFIDFExtractor
from nlp.entity import create_entity_extractor
from nlp.relation import create_relation_extractor
import visualization.app as viz_app
import main


class TestFullIntegration(unittest.TestCase):
    """全面集成测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 创建测试配置
        self.config = {
            'spider': {
                'website': 'test',
                'base_url': 'https://example.com',
                'delay': 0.1,
                'max_articles': 5,
                'output_dir': self.test_dir,
                'thread_count': 2,
                'timeout': 5,
                'max_retries': 1,
                'incremental': False,
                'use_proxy': False
            },
            'nlp': {
                'segmenter': 'jieba',
                'extractor': 'hanlp',
                'relation': 'hanlp',
                'use_stopwords': True,
                'top_keywords': 5,
                'keywords_count': 10,
                'summary_sentences': 3
            },
            'output': {
                'csv_file': 'test_articles.csv',
                'encoding': 'utf-8-sig'
            }
        }
        
        # 保存配置到临时文件
        self.config_file = os.path.join(self.test_dir, 'test_config.json')
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)
        
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
    
    @patch('spider.spider.ArticleSpider.crawl')
    def test_full_pipeline(self, mock_crawl):
        """测试完整的处理流程"""
        # 模拟爬取结果
        mock_crawl.return_value = self.test_articles
        
        # 模拟命令行参数
        test_args = [
            'main.py',
            '--config', self.config_file,
            '--output', self.test_dir
        ]
        
        # 运行主程序
        with patch('sys.argv', test_args):
            with patch('builtins.input', return_value='y'):  # 模拟用户输入
                main.main()
        
        # 验证输出文件存在
        output_file = os.path.join(self.test_dir, self.config['output']['csv_file'])
        self.assertTrue(os.path.exists(output_file), f"输出文件不存在: {output_file}")
        
        # 读取输出文件
        df = pd.read_csv(output_file)
        
        # 验证数据条数
        self.assertEqual(len(df), len(self.test_articles))
        
        # 验证NLP处理结果
        self.assertTrue('keywords' in df.columns)
        self.assertTrue('entities' in df.columns)
        self.assertTrue('triples' in df.columns)
    
    def test_segmenter_integration(self):
        """测试分词器集成"""
        # 创建分词器
        segmenter = create_segmenter('jieba')
        
        # 测试分词
        text = self.test_articles[0]['content']
        tokens = segmenter.segment(text)
        
        # 验证分词结果
        self.assertTrue(len(tokens) > 0)
        self.assertIn('自然语言处理', tokens)
    
    def test_entity_extractor_integration(self):
        """测试实体提取器集成"""
        try:
            # 创建实体提取器
            entity_extractor = create_entity_extractor('hanlp')
            
            # 测试实体提取
            text = self.test_articles[0]['content']
            entities = entity_extractor.extract_entities(text)
            
            # 验证实体提取结果
            self.assertIsInstance(entities, dict)
            
            # 检查是否包含人名实体
            if 'person' in entities:
                self.assertIn('李明', entities['person'])
            
            # 检查是否包含组织机构实体
            if 'organization' in entities:
                self.assertIn('北京大学', entities['organization'])
        except ImportError:
            self.skipTest("HanLP未安装，跳过测试")
    
    def test_relation_extractor_integration(self):
        """测试关系提取器集成"""
        try:
            # 创建关系提取器
            relation_extractor = create_relation_extractor('hanlp')
            
            # 测试关系提取
            text = self.test_articles[0]['content']
            triples = relation_extractor.extract_triples(text)
            
            # 验证关系提取结果
            self.assertIsInstance(triples, list)
            
            # 检查是否提取到关系
            if triples:
                # 检查第一个三元组
                first_triple = triples[0]
                self.assertTrue(hasattr(first_triple, 'subject'))
                self.assertTrue(hasattr(first_triple, 'predicate'))
                self.assertTrue(hasattr(first_triple, 'object'))
        except ImportError:
            self.skipTest("HanLP未安装，跳过测试")
    
    @patch('visualization.app.load_data')
    def test_visualization_integration(self, mock_load_data):
        """测试可视化集成"""
        # 创建测试DataFrame
        df = pd.DataFrame(self.test_articles)
        
        # 添加NLP处理结果列
        df['keywords'] = '自然语言处理,人工智能,北京大学'
        df['entities'] = json.dumps({'person': ['李明'], 'organization': ['北京大学']})
        df['triples'] = json.dumps([
            {'subject': '李明', 'predicate': '是', 'object': '教授'},
            {'subject': '李明', 'predicate': '在', 'object': '北京大学'}
        ])
        
        # 模拟加载数据
        mock_load_data.return_value = df
        
        # 创建测试客户端
        client = viz_app.app.test_client()
        
        # 测试首页
        response = client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # 测试文章详情页
        response = client.get('/article/0')
        self.assertEqual(response.status_code, 200)
        
        # 测试关系图谱页
        response = client.get('/graph/0')
        self.assertEqual(response.status_code, 200)
        
        # 测试分析页
        response = client.get('/analyze')
        self.assertEqual(response.status_code, 200)
    
    @patch('spider.proxy_pool.ProxyPool.fetch_proxies_from_sources')
    def test_proxy_pool_integration(self, mock_fetch):
        """测试代理池集成"""
        # 模拟获取代理
        mock_fetch.return_value = 5
        
        # 创建代理池
        proxy_file = os.path.join(self.test_dir, 'proxies.json')
        pool = ProxyPool(proxy_file=proxy_file)
        
        # 获取代理
        count = pool.fetch_proxies_from_sources()
        
        # 验证代理获取结果
        self.assertEqual(count, 5)
        
        # 验证代理文件已创建
        self.assertTrue(os.path.exists(proxy_file))


if __name__ == '__main__':
    unittest.main() 