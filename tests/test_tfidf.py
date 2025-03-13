#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TF-IDF和关键词提取模块单元测试
测试文本分析、TF-IDF计算和关键词提取功能
"""

import unittest
import os
import sys
import json
import tempfile
import shutil
import numpy as np
from unittest.mock import patch, MagicMock

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入TF-IDF和关键词提取模块
from nlp.tfidf import TFIDF, KeywordExtractor
from nlp.segmenter import Segmenter


class TestTFIDF(unittest.TestCase):
    """测试TF-IDF计算模块"""
    
    def setUp(self):
        """测试前准备"""
        # 创建TFIDF计算实例
        self.tfidf = TFIDF()
        
        # 测试文档集
        self.documents = [
            "自然语言处理是人工智能的一个重要分支。",
            "机器学习是实现自然语言处理的重要方法。",
            "深度学习是机器学习的一种方法，在自然语言处理领域取得了很大进展。",
            "词嵌入是深度学习在自然语言处理中的重要应用。"
        ]
        
        # 预分词的文档集
        self.tokenized_docs = [
            ["自然语言处理", "是", "人工智能", "的", "一个", "重要", "分支"],
            ["机器学习", "是", "实现", "自然语言处理", "的", "重要", "方法"],
            ["深度学习", "是", "机器学习", "的", "一种", "方法", "在", "自然语言处理", "领域", "取得", "了", "很大", "进展"],
            ["词嵌入", "是", "深度学习", "在", "自然语言处理", "中", "的", "重要", "应用"]
        ]
        
    def test_compute_tf(self):
        """测试计算词频"""
        # 使用简单文档测试
        document = ["自然语言", "自然语言", "处理", "人工智能"]
        tf = self.tfidf._compute_tf(document)
        
        # 验证结果
        expected_tf = {
            "自然语言": 0.5,  # 2/4
            "处理": 0.25,    # 1/4
            "人工智能": 0.25  # 1/4
        }
        
        self.assertEqual(tf, expected_tf)
        
    def test_compute_idf(self):
        """测试计算逆文档频率"""
        # 计算逆文档频率
        idf = self.tfidf._compute_idf(self.tokenized_docs)
        
        # 验证结果 - "自然语言处理"应该在所有文档中出现
        total_docs = len(self.tokenized_docs)
        self.assertAlmostEqual(idf["自然语言处理"], np.log(total_docs / total_docs) + 1)
        
        # "人工智能"应该只在第一个文档中出现
        self.assertAlmostEqual(idf["人工智能"], np.log(total_docs / 1) + 1)
        
    def test_compute_tfidf(self):
        """测试计算TF-IDF值"""
        # 使用测试文档集计算TF-IDF
        tfidf_matrix = self.tfidf.fit_transform(self.documents)
        
        # 验证基本结构
        self.assertEqual(len(tfidf_matrix), len(self.documents))
        
        # 验证所有TF-IDF值都是非负的
        for doc_tfidf in tfidf_matrix:
            for word, score in doc_tfidf.items():
                self.assertGreaterEqual(score, 0)
                
        # 验证"自然语言处理"在所有文档中都有TF-IDF值
        for doc_tfidf in tfidf_matrix:
            self.assertIn("自然语言处理", doc_tfidf)
            
    def test_get_top_features(self):
        """测试获取顶部特征词"""
        # 首先计算TF-IDF
        self.tfidf.fit_transform(self.documents)
        
        # 获取顶部特征词
        top_features = self.tfidf.get_top_features(10)
        
        # 验证基本结构
        self.assertIsInstance(top_features, list)
        self.assertLessEqual(len(top_features), 10)
        
        # 验证所有项都是(词, 分数)格式
        for feature in top_features:
            self.assertIsInstance(feature, tuple)
            self.assertEqual(len(feature), 2)
            self.assertIsInstance(feature[0], str)
            self.assertIsInstance(feature[1], float)
            
        # 验证排序正确 (分数应该降序排列)
        for i in range(len(top_features) - 1):
            self.assertGreaterEqual(top_features[i][1], top_features[i+1][1])
            
    def test_get_document_vector(self):
        """测试获取文档向量"""
        # 首先计算TF-IDF
        tfidf_matrix = self.tfidf.fit_transform(self.documents)
        
        # 获取第一个文档的向量
        doc_vector = self.tfidf.get_document_vector(0)
        
        # 验证向量内容与TF-IDF矩阵一致
        self.assertEqual(doc_vector, tfidf_matrix[0])
        
        # 测试获取不存在的文档
        with self.assertRaises(IndexError):
            self.tfidf.get_document_vector(len(self.documents))
            
    def test_save_load_model(self):
        """测试保存和加载模型"""
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        model_path = os.path.join(temp_dir, 'tfidf_model.json')
        
        try:
            # 首先计算TF-IDF
            original_tfidf_matrix = self.tfidf.fit_transform(self.documents)
            
            # 保存模型
            self.tfidf.save_model(model_path)
            
            # 验证文件已创建
            self.assertTrue(os.path.exists(model_path))
            
            # 创建新的TFIDF实例
            new_tfidf = TFIDF()
            
            # 加载模型
            new_tfidf.load_model(model_path)
            
            # 验证词汇表和IDF值一致
            self.assertEqual(self.tfidf.vocabulary, new_tfidf.vocabulary)
            self.assertEqual(self.tfidf.idf, new_tfidf.idf)
            
            # 使用新模型转换文档
            new_tfidf_matrix = new_tfidf.transform(self.documents)
            
            # 验证结果一致
            self.assertEqual(len(original_tfidf_matrix), len(new_tfidf_matrix))
            for i in range(len(original_tfidf_matrix)):
                for word in original_tfidf_matrix[i]:
                    self.assertAlmostEqual(original_tfidf_matrix[i][word], new_tfidf_matrix[i][word])
                    
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir)
            

class TestKeywordExtractor(unittest.TestCase):
    """测试关键词提取模块"""
    
    def setUp(self):
        """测试前准备"""
        # 创建关键词提取器实例
        self.extractor = KeywordExtractor()
        
        # 测试文档
        self.document = """
        自然语言处理是计算机科学和人工智能的一个重要分支，研究计算机与人类语言之间的交互问题。
        自然语言处理技术可以让计算机理解、解释和生成人类语言，是实现人机交互的关键技术之一。
        机器学习和深度学习方法在自然语言处理领域取得了显著成果，例如机器翻译、文本分类和问答系统等。
        词嵌入技术是表示自然语言的有效方法，它可以将词语映射到高维向量空间，捕捉词语之间的语义关系。
        """
        
        # 测试文档集
        self.documents = [
            "自然语言处理是人工智能的一个重要分支。",
            "机器学习是实现自然语言处理的重要方法。",
            "深度学习是机器学习的一种方法，在自然语言处理领域取得了很大进展。",
            "词嵌入是深度学习在自然语言处理中的重要应用。"
        ]
        
    def test_extract_keywords_from_document(self):
        """测试从单个文档提取关键词"""
        # 提取关键词
        keywords = self.extractor.extract_keywords(self.document, top_k=5)
        
        # 验证结果格式
        self.assertIsInstance(keywords, list)
        self.assertLessEqual(len(keywords), 5)
        
        # 验证每个关键词格式
        for keyword in keywords:
            self.assertIsInstance(keyword, tuple)
            self.assertEqual(len(keyword), 2)
            self.assertIsInstance(keyword[0], str)
            self.assertIsInstance(keyword[1], float)
            
        # 验证排序正确 (分数应该降序排列)
        for i in range(len(keywords) - 1):
            self.assertGreaterEqual(keywords[i][1], keywords[i+1][1])
            
        # 验证关键词内容 (应该包含"自然语言处理")
        self.assertTrue(any(kw[0] == "自然语言处理" for kw in keywords))
        
    def test_extract_keywords_from_documents(self):
        """测试从多个文档提取关键词"""
        # 提取关键词
        keywords_list = self.extractor.extract_keywords_batch(self.documents, top_k=3)
        
        # 验证结果格式
        self.assertIsInstance(keywords_list, list)
        self.assertEqual(len(keywords_list), len(self.documents))
        
        # 验证每个文档的关键词
        for keywords in keywords_list:
            self.assertIsInstance(keywords, list)
            self.assertLessEqual(len(keywords), 3)
            
            # 验证每个关键词格式
            for keyword in keywords:
                self.assertIsInstance(keyword, tuple)
                self.assertEqual(len(keyword), 2)
                self.assertIsInstance(keyword[0], str)
                self.assertIsInstance(keyword[1], float)
                
            # 验证排序正确 (分数应该降序排列)
            for i in range(len(keywords) - 1):
                self.assertGreaterEqual(keywords[i][1], keywords[i+1][1])
                
    def test_extract_top_keywords(self):
        """测试提取全局顶部关键词"""
        # 提取全局关键词
        global_keywords = self.extractor.extract_top_keywords(self.documents, top_k=5)
        
        # 验证结果格式
        self.assertIsInstance(global_keywords, list)
        self.assertLessEqual(len(global_keywords), 5)
        
        # 验证每个关键词格式
        for keyword in global_keywords:
            self.assertIsInstance(keyword, tuple)
            self.assertEqual(len(keyword), 2)
            self.assertIsInstance(keyword[0], str)
            self.assertIsInstance(keyword[1], float)
            
        # 验证排序正确 (分数应该降序排列)
        for i in range(len(global_keywords) - 1):
            self.assertGreaterEqual(global_keywords[i][1], global_keywords[i+1][1])
            
        # 验证关键词内容 (应该包含"自然语言处理")
        self.assertTrue(any(kw[0] == "自然语言处理" for kw in global_keywords))
        
    def test_extract_with_stopwords(self):
        """测试使用停用词的关键词提取"""
        # 使用自定义停用词
        self.extractor.stopwords = ["是", "的", "在", "和", "等"]
        
        # 提取关键词
        keywords = self.extractor.extract_keywords(self.document, top_k=5)
        
        # 验证停用词不在结果中
        for kw in keywords:
            self.assertNotIn(kw[0], self.extractor.stopwords)
            
    def test_extract_with_custom_segmenter(self):
        """测试使用自定义分词器的关键词提取"""
        # 创建模拟分词器
        mock_segmenter = MagicMock(spec=Segmenter)
        mock_segmenter.segment.return_value = ["自然语言处理", "人工智能", "计算机", "科学", "技术", "研究"]
        
        # 使用自定义分词器
        self.extractor.segmenter = mock_segmenter
        
        # 提取关键词
        keywords = self.extractor.extract_keywords(self.document, top_k=3)
        
        # 验证分词器被调用
        mock_segmenter.segment.assert_called_once()
        
        # 验证关键词在模拟分词结果中
        for kw in keywords:
            self.assertIn(kw[0], mock_segmenter.segment.return_value)


if __name__ == '__main__':
    unittest.main() 