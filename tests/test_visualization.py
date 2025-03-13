#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试可视化模块功能

对visualization/app.py中的功能进行单元测试
"""

import os
import sys
import unittest
import json
import tempfile
import pandas as pd
from bs4 import BeautifulSoup
from flask import Flask
import numpy as np
from unittest.mock import patch, MagicMock

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入可视化模块
from visualization.app import app, load_data, parse_triples, generate_relation_graph
from visualization.app import generate_keyword_cloud, generate_entity_bar, generate_sentiment_pie
from visualization.app import generate_topic_distribution, generate_article_length_histogram
from visualization.app import generate_time_trend, get_entity_network

class TestVisualizationApp(unittest.TestCase):
    """测试可视化应用程序功能"""
    
    def setUp(self):
        """测试前准备"""
        # 设置Flask应用为测试模式
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # 创建测试数据
        self.test_data = pd.DataFrame({
            'title': ['测试文章1', '测试文章2', '测试文章3'],
            'author': ['作者1', '作者2', '作者3'],
            'content': ['这是测试文章1的内容。' * 10, '这是测试文章2的内容。' * 20, '这是测试文章3的内容。' * 30],
            'url': ['http://example.com/1', 'http://example.com/2', 'http://example.com/3'],
            'crawl_time': ['2023-01-01 10:00:00', '2023-01-02 11:00:00', '2023-01-03 12:00:00'],
            'keywords': ['关键词1,关键词2,关键词3', '关键词2,关键词4,关键词5', '关键词3,关键词6,关键词7'],
            'entities': [
                json.dumps({'person': ['人物1', '人物2'], 'place': ['地点1'], 'organization': ['组织1']}),
                json.dumps({'person': ['人物2', '人物3'], 'place': ['地点2'], 'organization': ['组织2']}),
                json.dumps({'person': ['人物1', '人物3'], 'place': ['地点3'], 'organization': ['组织3']})
            ],
            'sentiment': [0.8, 0.5, 0.2],
            'triples': [
                json.dumps([{'subject': '主语1', 'predicate': '谓语1', 'object': '宾语1'},
                          {'subject': '主语2', 'predicate': '谓语2', 'object': '宾语2'}]),
                json.dumps([{'subject': '主语3', 'predicate': '谓语3', 'object': '宾语3'}]),
                json.dumps([{'subject': '主语4', 'predicate': '谓语4', 'object': '宾语4'},
                          {'subject': '主语5', 'predicate': '谓语5', 'object': '宾语5'}])
            ]
        })
        
        # 创建临时CSV文件
        fd, self.temp_csv = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        self.test_data.to_csv(self.temp_csv, index=False)
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时文件
        if hasattr(self, 'temp_csv') and os.path.exists(self.temp_csv):
            os.unlink(self.temp_csv)
    
    def test_load_data(self):
        """测试加载数据函数"""
        # 测试加载有效文件
        df = load_data(self.temp_csv)
        self.assertEqual(len(df), 3)
        self.assertEqual(df.iloc[0]['title'], '测试文章1')
        
        # 测试加载不存在的文件
        df = load_data('不存在的文件.csv')
        self.assertTrue(df.empty)
    
    def test_parse_triples(self):
        """测试解析三元组函数"""
        # 测试解析JSON格式
        json_triples = '''[{"subject": "主语1", "predicate": "谓语1", "object": "宾语1"}]'''
        result = parse_triples(json_triples)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['subject'], '主语1')
        
        # 测试解析自定义格式
        custom_triples = '(主语1, 谓语1, 宾语1); (主语2, 谓语2, 宾语2)'
        result = parse_triples(custom_triples)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['subject'], '主语1')
        self.assertEqual(result[1]['predicate'], '谓语2')
        
        # 测试空值
        result = parse_triples('')
        self.assertEqual(len(result), 0)
        
        # 测试None值
        result = parse_triples(None)
        self.assertEqual(len(result), 0)
    
    def test_generate_relation_graph(self):
        """测试生成关系图谱函数"""
        triples = [
            {'subject': '主语1', 'predicate': '谓语1', 'object': '宾语1'},
            {'subject': '主语1', 'predicate': '谓语2', 'object': '宾语2'}
        ]
        
        graph = generate_relation_graph(triples)
        
        # 测试图表类型
        self.assertEqual(type(graph).__name__, 'Graph')
        
        # 测试输出HTML
        html = graph.render_embed()
        self.assertTrue(isinstance(html, str))
        self.assertIn('echarts', html.lower())
    
    def test_generate_keyword_cloud(self):
        """测试生成关键词云图函数"""
        with patch('visualization.app.WordCloud') as mock_wordcloud:
            # 配置模拟对象
            mock_instance = MagicMock()
            mock_wordcloud.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.set_global_opts.return_value = mock_instance
            
            # 调用函数
            result = generate_keyword_cloud(self.test_data)
            
            # 验证调用
            self.assertEqual(result, mock_instance)
            mock_wordcloud.assert_called_once()
            self.assertTrue(mock_instance.add.called)
            self.assertTrue(mock_instance.set_global_opts.called)
    
    def test_generate_entity_bar(self):
        """测试生成实体统计柱状图函数"""
        with patch('visualization.app.Bar') as mock_bar:
            # 配置模拟对象
            mock_instance = MagicMock()
            mock_bar.return_value = mock_instance
            mock_instance.add_xaxis.return_value = mock_instance
            mock_instance.add_yaxis.return_value = mock_instance
            mock_instance.reversal_axis.return_value = mock_instance
            mock_instance.set_series_opts.return_value = mock_instance
            mock_instance.set_global_opts.return_value = mock_instance
            
            # 调用函数
            result = generate_entity_bar(self.test_data)
            
            # 验证调用
            self.assertEqual(result, mock_instance)
            mock_bar.assert_called_once()
            self.assertTrue(mock_instance.add_xaxis.called)
            self.assertTrue(mock_instance.add_yaxis.called)
            self.assertTrue(mock_instance.reversal_axis.called)
            self.assertTrue(mock_instance.set_series_opts.called)
            self.assertTrue(mock_instance.set_global_opts.called)
    
    def test_generate_sentiment_pie(self):
        """测试生成情感分析饼图函数"""
        with patch('visualization.app.Pie') as mock_pie:
            # 配置模拟对象
            mock_instance = MagicMock()
            mock_pie.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.set_global_opts.return_value = mock_instance
            
            # 调用函数
            result = generate_sentiment_pie(self.test_data)
            
            # 验证调用
            self.assertEqual(result, mock_instance)
            mock_pie.assert_called_once()
            self.assertTrue(mock_instance.add.called)
            self.assertTrue(mock_instance.set_global_opts.called)
    
    def test_generate_topic_distribution(self):
        """测试生成主题分布图函数"""
        with patch('visualization.app.Pie') as mock_pie:
            # 配置模拟对象
            mock_instance = MagicMock()
            mock_pie.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.set_global_opts.return_value = mock_instance
            
            # 调用函数
            result = generate_topic_distribution(self.test_data)
            
            # 验证调用
            self.assertEqual(result, mock_instance)
            mock_pie.assert_called_once()
            self.assertTrue(mock_instance.add.called)
            self.assertTrue(mock_instance.set_global_opts.called)
    
    def test_generate_article_length_histogram(self):
        """测试生成文章长度直方图函数"""
        with patch('visualization.app.Bar') as mock_bar:
            # 配置模拟对象
            mock_instance = MagicMock()
            mock_bar.return_value = mock_instance
            mock_instance.add_xaxis.return_value = mock_instance
            mock_instance.add_yaxis.return_value = mock_instance
            mock_instance.set_global_opts.return_value = mock_instance
            
            # 调用函数
            result = generate_article_length_histogram(self.test_data)
            
            # 验证调用
            self.assertEqual(result, mock_instance)
            mock_bar.assert_called_once()
            self.assertTrue(mock_instance.add_xaxis.called)
            self.assertTrue(mock_instance.add_yaxis.called)
            self.assertTrue(mock_instance.set_global_opts.called)
            
            # 测试空数据
            empty_df = pd.DataFrame()
            with patch('visualization.app.Bar') as mock_bar_empty:
                mock_instance_empty = MagicMock()
                mock_bar_empty.return_value = mock_instance_empty
                mock_instance_empty.set_global_opts.return_value = mock_instance_empty
                
                result_empty = generate_article_length_histogram(empty_df)
                self.assertEqual(result_empty, mock_instance_empty)
                mock_bar_empty.assert_called_once()
    
    def test_generate_time_trend(self):
        """测试生成时间趋势图函数"""
        with patch('visualization.app.Line') as mock_line:
            # 配置模拟对象
            mock_instance = MagicMock()
            mock_line.return_value = mock_instance
            mock_instance.add_xaxis.return_value = mock_instance
            mock_instance.add_yaxis.return_value = mock_instance
            mock_instance.set_global_opts.return_value = mock_instance
            
            # 调用函数
            result = generate_time_trend(self.test_data)
            
            # 验证调用
            self.assertEqual(result, mock_instance)
            mock_line.assert_called_once()
            self.assertTrue(mock_instance.add_xaxis.called)
            self.assertTrue(mock_instance.add_yaxis.called)
            self.assertTrue(mock_instance.set_global_opts.called)
            
            # 测试空数据
            empty_df = pd.DataFrame()
            with patch('visualization.app.Line') as mock_line_empty:
                mock_instance_empty = MagicMock()
                mock_line_empty.return_value = mock_instance_empty
                mock_instance_empty.set_global_opts.return_value = mock_instance_empty
                
                result_empty = generate_time_trend(empty_df)
                self.assertEqual(result_empty, mock_instance_empty)
                mock_line_empty.assert_called_once()
    
    def test_get_entity_network(self):
        """测试生成实体网络图函数"""
        with patch('visualization.app.Graph') as mock_graph:
            # 配置模拟对象
            mock_instance = MagicMock()
            mock_graph.return_value = mock_instance
            mock_instance.add.return_value = mock_instance
            mock_instance.set_global_opts.return_value = mock_instance
            
            # 调用函数
            result = get_entity_network(self.test_data)
            
            # 验证调用
            self.assertEqual(result, mock_instance)
            mock_graph.assert_called_once()
            self.assertTrue(mock_instance.add.called)
            self.assertTrue(mock_instance.set_global_opts.called)
    
    def test_index_route(self):
        """测试首页路由"""
        with patch('visualization.app.load_data') as mock_load_data:
            # 配置模拟函数返回测试数据
            mock_load_data.return_value = self.test_data
            
            # 发送请求
            response = self.client.get('/')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'<!DOCTYPE html>', response.data)
            self.assertIn(b'文章分析系统', response.data)
    
    def test_article_detail_route(self):
        """测试文章详情路由"""
        with patch('visualization.app.load_data') as mock_load_data:
            # 配置模拟函数返回测试数据
            mock_load_data.return_value = self.test_data
            
            # 发送请求
            response = self.client.get('/article/0')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'<!DOCTYPE html>', response.data)
            self.assertIn(b'文章详情', response.data)
            
            # 测试无效文章ID
            response_invalid = self.client.get('/article/999')
            self.assertEqual(response_invalid.status_code, 404)
    
    def test_article_graph_route(self):
        """测试文章图谱路由"""
        with patch('visualization.app.load_data') as mock_load_data, \
             patch('visualization.app.generate_relation_graph') as mock_graph:
            # 配置模拟函数
            mock_load_data.return_value = self.test_data
            
            mock_graph_instance = MagicMock()
            mock_graph.return_value = mock_graph_instance
            mock_graph_instance.render_embed.return_value = '<div id="chart"></div>'
            
            # 发送请求
            response = self.client.get('/graph/0')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'<!DOCTYPE html>', response.data)
            self.assertIn(b'关系图谱', response.data)
            
            # 测试无效文章ID
            response_invalid = self.client.get('/graph/999')
            self.assertEqual(response_invalid.status_code, 404)
    
    def test_full_graph_route(self):
        """测试全局图谱路由"""
        with patch('visualization.app.load_data') as mock_load_data, \
             patch('visualization.app.generate_relation_graph') as mock_graph:
            # 配置模拟函数
            mock_load_data.return_value = self.test_data
            
            mock_graph_instance = MagicMock()
            mock_graph.return_value = mock_graph_instance
            mock_graph_instance.render_embed.return_value = '<div id="chart"></div>'
            
            # 发送请求
            response = self.client.get('/full_graph')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'<!DOCTYPE html>', response.data)
            self.assertIn(b'全部文章关系图谱', response.data)
    
    def test_analyze_route(self):
        """测试数据分析路由"""
        with patch('visualization.app.load_data') as mock_load_data, \
             patch('visualization.app.generate_keyword_cloud') as mock_keyword_cloud, \
             patch('visualization.app.generate_entity_bar') as mock_entity_bar, \
             patch('visualization.app.generate_sentiment_pie') as mock_sentiment_pie, \
             patch('visualization.app.generate_topic_distribution') as mock_topic_pie, \
             patch('visualization.app.generate_article_length_histogram') as mock_length_histogram, \
             patch('visualization.app.generate_time_trend') as mock_time_trend:
            
            # 配置模拟函数
            mock_load_data.return_value = self.test_data
            
            # 配置图表模拟对象
            for mock_chart in [mock_keyword_cloud, mock_entity_bar, mock_sentiment_pie, 
                              mock_topic_pie, mock_length_histogram, mock_time_trend]:
                chart_instance = MagicMock()
                mock_chart.return_value = chart_instance
                chart_instance.render_embed.return_value = '<div id="chart"></div>'
            
            # 发送请求
            response = self.client.get('/analyze')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'<!DOCTYPE html>', response.data)
            self.assertIn(b'文章数据分析', response.data)
    
    def test_entity_network_route(self):
        """测试实体网络路由"""
        with patch('visualization.app.load_data') as mock_load_data, \
             patch('visualization.app.get_entity_network') as mock_entity_network:
            
            # 配置模拟函数
            mock_load_data.return_value = self.test_data
            
            # 配置图表模拟对象
            network_instance = MagicMock()
            mock_entity_network.return_value = network_instance
            network_instance.render_embed.return_value = '<div id="chart"></div>'
            
            # 发送请求
            response = self.client.get('/entity_network')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'<!DOCTYPE html>', response.data)
            self.assertIn(b'实体关系网络图', response.data)
    
    def test_api_keywords_analysis(self):
        """测试关键词分析API"""
        with patch('visualization.app.load_data') as mock_load_data:
            # 配置模拟函数返回测试数据
            mock_load_data.return_value = self.test_data
            
            # 发送请求
            response = self.client.get('/api/analysis/keywords')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(isinstance(data, list))
            self.assertGreater(len(data), 0)
            self.assertTrue(all('keyword' in item and 'count' in item for item in data))
    
    def test_api_entities_analysis(self):
        """测试实体分析API"""
        with patch('visualization.app.load_data') as mock_load_data:
            # 配置模拟函数返回测试数据
            mock_load_data.return_value = self.test_data
            
            # 发送请求 - 所有实体
            response = self.client.get('/api/analysis/entities')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(isinstance(data, list))
            self.assertGreater(len(data), 0)
            self.assertTrue(all('entity' in item and 'count' in item and 'type' in item for item in data))
            
            # 发送请求 - 人物实体
            response = self.client.get('/api/analysis/entities?type=person')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(isinstance(data, list))
            self.assertTrue(all(item['type'] == 'person' for item in data if data))
    
    def test_api_triples_analysis(self):
        """测试三元组分析API"""
        with patch('visualization.app.load_data') as mock_load_data:
            # 配置模拟函数返回测试数据
            mock_load_data.return_value = self.test_data
            
            # 发送请求
            response = self.client.get('/api/analysis/triples')
            
            # 验证响应
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertTrue(isinstance(data, dict))
            self.assertIn('predicates', data)
            self.assertIn('subjects', data)
            self.assertIn('objects', data)
            self.assertTrue(all(isinstance(v, list) for v in data.values()))


if __name__ == '__main__':
    unittest.main() 