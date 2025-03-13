#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试分词器功能
"""

import os
import sys
import unittest

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入项目模块
from nlp.segmentation import create_segmenter


class TestSegmenter(unittest.TestCase):
    """测试分词器功能"""
    
    def setUp(self):
        """测试前准备"""
        # 创建jieba分词器
        self.jieba_segmenter = create_segmenter('jieba')
        
        # 测试文本
        self.test_text = "自然语言处理是人工智能的一个重要分支。"
    
    def test_jieba_segmenter(self):
        """测试jieba分词器"""
        # 分词
        tokens = self.jieba_segmenter.segment(self.test_text)
        
        # 验证结果
        self.assertIsInstance(tokens, list)
        self.assertGreater(len(tokens), 0)
        self.assertIn('自然语言处理', tokens)
        self.assertIn('人工智能', tokens)
    
    def test_clean_text(self):
        """测试文本清洗"""
        # 带HTML标签的文本
        html_text = "<p>自然语言处理</p><div>是人工智能的一个重要分支。</div>"
        
        # 清洗文本
        cleaned_text = self.jieba_segmenter.clean_text(html_text)
        
        # 验证结果
        self.assertNotIn('<p>', cleaned_text)
        self.assertNotIn('</p>', cleaned_text)
        self.assertNotIn('<div>', cleaned_text)
        self.assertNotIn('</div>', cleaned_text)
        self.assertIn('自然语言处理', cleaned_text)
        self.assertIn('是人工智能的一个重要分支', cleaned_text)
    
    def test_remove_stopwords(self):
        """测试去除停用词"""
        # 带停用词的文本
        text_with_stopwords = "这是一个测试文本，用于测试去除停用词功能。"
        
        # 分词并去除停用词
        tokens = self.jieba_segmenter.segment(text_with_stopwords)
        
        # 验证结果
        self.assertNotIn('的', tokens)
        self.assertNotIn('是', tokens)
        self.assertIn('测试', tokens)
        self.assertIn('文本', tokens)
        self.assertIn('功能', tokens)


if __name__ == '__main__':
    unittest.main() 