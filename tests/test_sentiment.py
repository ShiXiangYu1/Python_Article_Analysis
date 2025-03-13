#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试情感分析功能
"""

import os
import sys
import unittest

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目模块
from nlp.sentiment import SentimentAnalyzer


class TestSentimentAnalyzer(unittest.TestCase):
    """测试情感分析功能"""
    
    def setUp(self):
        """测试前准备"""
        # 创建情感分析器
        self.analyzer = SentimentAnalyzer()
        
        # 测试文本
        self.positive_text = "这部电影非常精彩，演员表演出色，剧情引人入胜。"
        self.negative_text = "这部电影非常糟糕，演员表演很差，剧情枯燥乏味。"
        self.neutral_text = "这部电影讲述了一个关于科技发展的故事。"
    
    def test_analyze_sentiment(self):
        """测试情感分析功能"""
        # 分析积极文本
        pos_score, neg_score, sentiment = self.analyzer.analyze(self.positive_text)
        
        # 验证结果
        self.assertIsInstance(pos_score, float)
        self.assertIsInstance(neg_score, float)
        self.assertIsInstance(sentiment, str)
        self.assertGreater(pos_score, neg_score)
        self.assertEqual(sentiment, 'positive')
        
        # 分析消极文本
        pos_score, neg_score, sentiment = self.analyzer.analyze(self.negative_text)
        
        # 验证结果
        self.assertGreater(neg_score, pos_score)
        self.assertEqual(sentiment, 'negative')
        
        # 分析中性文本
        pos_score, neg_score, sentiment = self.analyzer.analyze(self.neutral_text)
        
        # 验证结果 - 中性文本可能被分类为积极或消极，但分数应该接近
        self.assertLess(abs(pos_score - neg_score), 0.3)
    
    def test_batch_analyze(self):
        """测试批量情感分析"""
        # 准备批量文本
        texts = [self.positive_text, self.negative_text, self.neutral_text]
        
        # 批量分析
        results = self.analyzer.batch_analyze(texts)
        
        # 验证结果
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0][2], 'positive')
        self.assertEqual(results[1][2], 'negative')
    
    def test_get_sentiment_distribution(self):
        """测试获取情感分布"""
        # 准备批量文本
        texts = [self.positive_text, self.negative_text, self.neutral_text, 
                "非常喜欢这个产品", "这个产品质量很差", "这个产品一般般"]
        
        # 获取情感分布
        distribution = self.analyzer.get_sentiment_distribution(texts)
        
        # 验证结果
        self.assertIn('positive', distribution)
        self.assertIn('negative', distribution)
        self.assertIn('neutral', distribution)
        self.assertEqual(sum(distribution.values()), len(texts))


if __name__ == '__main__':
    unittest.main() 