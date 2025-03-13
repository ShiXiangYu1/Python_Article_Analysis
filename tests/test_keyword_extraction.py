#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试关键词提取功能
"""

import os
import sys
import unittest

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目模块
from nlp.keywords import KeywordExtractor


class TestKeywordExtractor(unittest.TestCase):
    """测试关键词提取功能"""
    
    def setUp(self):
        """测试前准备"""
        # 创建关键词提取器
        self.extractor = KeywordExtractor()
        
        # 测试文本
        self.test_text = """
        自然语言处理是计算机科学领域与人工智能领域中的一个重要方向。
        它研究能实现人与计算机之间用自然语言进行有效通信的各种理论和方法。
        自然语言处理是一门融语言学、计算机科学、数学于一体的科学。
        因此，这一领域的研究将涉及自然语言，即人们日常使用的语言，
        所以它与语言学的研究有着密切的联系，但又有重要的区别。
        自然语言处理并不是一般地研究自然语言，
        而在于研制能有效地实现自然语言通信的计算机系统，
        特别是其中的软件系统。因而它是计算机科学的一部分。
        """
    
    def test_extract_keywords(self):
        """测试提取关键词"""
        # 提取关键词
        keywords = self.extractor.extract(self.test_text)
        
        # 验证结果
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
        self.assertIn('自然语言处理', [kw[0] for kw in keywords])
        self.assertIn('计算机科学', [kw[0] for kw in keywords])
        self.assertIn('人工智能', [kw[0] for kw in keywords])
    
    def test_extract_with_limit(self):
        """测试限制关键词数量"""
        # 提取5个关键词
        keywords = self.extractor.extract(self.test_text, topK=5)
        
        # 验证结果
        self.assertEqual(len(keywords), 5)
    
    def test_extract_with_allowPOS(self):
        """测试按词性过滤关键词"""
        # 只提取名词
        keywords = self.extractor.extract(self.test_text, allowPOS=('n',))
        
        # 验证结果
        self.assertGreater(len(keywords), 0)
        # 检查是否所有关键词都是名词
        for kw in keywords:
            self.assertIn('自然语言处理', [kw[0] for kw in keywords])
            self.assertIn('计算机科学', [kw[0] for kw in keywords])
    
    def test_extract_from_multiple_texts(self):
        """测试从多个文本中提取关键词"""
        # 准备多个文本
        texts = [
            "自然语言处理是计算机科学领域与人工智能领域中的一个重要方向。",
            "机器学习是人工智能的一个分支，它使用各种算法来解决数据分类和预测问题。",
            "深度学习是机器学习的一个子领域，它使用多层神经网络来模拟人脑的学习过程。"
        ]
        
        # 从多个文本中提取关键词
        all_keywords = self.extractor.extract_from_multiple_texts(texts)
        
        # 验证结果
        self.assertIsInstance(all_keywords, list)
        self.assertEqual(len(all_keywords), len(texts))
        self.assertIn('自然语言处理', [kw[0] for kw in all_keywords[0]])
        self.assertIn('机器学习', [kw[0] for kw in all_keywords[1]])
        self.assertIn('深度学习', [kw[0] for kw in all_keywords[2]])


if __name__ == '__main__':
    unittest.main() 