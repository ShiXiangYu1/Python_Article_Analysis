"""
TF-IDF关键词提取模块

实现基于TF-IDF算法的关键词提取功能
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
import logging
from collections import Counter
import re

logger = logging.getLogger('tfidf')

class TFIDF:
    """
    TF-IDF关键词提取器
    
    实现词频(TF)、逆文档频率(IDF)计算，提取文章关键词
    """
    
    def __init__(self, doc_list: Optional[List[List[str]]] = None) -> None:
        """
        初始化TF-IDF提取器
        
        Args:
            doc_list: 文档列表，每个文档是分词后的词语列表
        """
        # 文档数量
        self.n_docs = 0
        # 词语在多少文档中出现
        self.doc_freq = Counter()
        # IDF值缓存
        self.idf = {}
        # 已处理的文档
        self.docs = []
        
        # 如果提供了文档列表，则进行预处理
        if doc_list:
            self.add_documents(doc_list)
    
    def add_documents(self, doc_list: List[List[str]]) -> None:
        """
        添加文档用于IDF计算
        
        Args:
            doc_list: 文档列表，每个文档是分词后的词语列表
        """
        for doc in doc_list:
            # 每个文档中出现的唯一词语
            term_set = set(doc)
            # 更新文档频率
            for term in term_set:
                self.doc_freq[term] += 1
            
            # 更新文档数
            self.n_docs += 1
            self.docs.append(doc)
        
        # 重新计算IDF
        self._calculate_idf()
    
    def _calculate_idf(self) -> None:
        """
        计算IDF值
        """
        if self.n_docs == 0:
            logger.warning("没有文档，无法计算IDF")
            return
        
        # 计算每个词的IDF值
        for term, freq in self.doc_freq.items():
            self.idf[term] = math.log(self.n_docs / (1 + freq))
    
    def calculate_tf(self, doc: List[str]) -> Dict[str, float]:
        """
        计算文档的词频(TF)
        
        Args:
            doc: 分词后的文档
            
        Returns:
            词语到TF值的映射
        """
        # 文档为空时，返回空字典
        if not doc:
            return {}
        
        # 计算词频
        counter = Counter(doc)
        # 文档长度
        doc_len = len(doc)
        # 计算TF值
        tf = {term: count / doc_len for term, count in counter.items()}
        
        return tf
    
    def calculate_idf(self, term: str) -> float:
        """
        获取词语的IDF值
        
        Args:
            term: 词语
            
        Returns:
            IDF值，如果词语未在语料库中出现，则返回默认的最大IDF值
        """
        # 如果词语在IDF缓存中，直接返回
        if term in self.idf:
            return self.idf[term]
        
        # 如果词语未在语料库中出现，使用默认值（最大可能的IDF值）
        if self.n_docs > 0:
            return math.log(self.n_docs)
        else:
            return 0.0
    
    def calculate_tfidf(self, doc: List[str]) -> Dict[str, float]:
        """
        计算文档中词语的TF-IDF值
        
        Args:
            doc: 分词后的文档
            
        Returns:
            词语到TF-IDF值的映射
        """
        # 计算TF值
        tf = self.calculate_tf(doc)
        # 计算TF-IDF值
        tfidf = {term: tf_val * self.calculate_idf(term) for term, tf_val in tf.items()}
        
        return tfidf
    
    def extract_keywords(self, doc: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        """
        提取文档的关键词
        
        Args:
            doc: 分词后的文档
            top_k: 返回的关键词数量
            
        Returns:
            (关键词, TF-IDF值)元组的列表，按TF-IDF值降序排列
        """
        # 计算TF-IDF值
        tfidf = self.calculate_tfidf(doc)
        
        # 排序，获取top_k个关键词
        sorted_tfidf = sorted(tfidf.items(), key=lambda x: x[1], reverse=True)
        
        # 返回top_k个关键词
        return sorted_tfidf[:top_k]
    
    def batch_extract_keywords(self, doc_list: List[List[str]], top_k: int = 5) -> List[List[Tuple[str, float]]]:
        """
        批量提取多个文档的关键词
        
        Args:
            doc_list: 文档列表，每个文档是分词后的词语列表
            top_k: 每个文档返回的关键词数量
            
        Returns:
            每个文档的关键词列表
        """
        results = []
        
        for doc in doc_list:
            keywords = self.extract_keywords(doc, top_k)
            results.append(keywords)
        
        return results


class TFIDFExtractor:
    """
    TF-IDF关键词提取器包装类
    
    提供便捷的接口用于从文本中提取关键词
    """
    
    def __init__(self, segmenter) -> None:
        """
        初始化提取器
        
        Args:
            segmenter: 分词器实例
        """
        self.segmenter = segmenter
        self.tfidf = TFIDF()
        self.corpus_built = False
    
    def add_corpus(self, text_list: List[str]) -> None:
        """
        添加语料库用于IDF计算
        
        Args:
            text_list: 文本列表
        """
        # 对每个文本进行分词
        doc_list = []
        for text in text_list:
            # 分词
            words = self.segmenter.segment(text)
            # 过滤停用词
            filtered_words = self.segmenter.filter_stopwords(words)
            doc_list.append(filtered_words)
        
        # 添加到TFIDF计算器
        self.tfidf.add_documents(doc_list)
        self.corpus_built = True
    
    def extract_keywords(self, text: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        从文本中提取关键词
        
        Args:
            text: 待处理文本
            top_k: 返回的关键词数量
            
        Returns:
            (关键词, TF-IDF值)元组的列表
        """
        if not self.corpus_built:
            logger.warning("未添加语料库，IDF计算可能不准确")
        
        # 分词
        words = self.segmenter.segment(text)
        # 过滤停用词
        filtered_words = self.segmenter.filter_stopwords(words)
        
        if not filtered_words:
            logger.warning("文本分词结果为空")
            return []
        
        # 提取关键词
        keywords = self.tfidf.extract_keywords(filtered_words, top_k)
        
        return keywords
    
    def batch_extract_keywords(self, text_list: List[str], top_k: int = 5) -> List[List[Tuple[str, float]]]:
        """
        批量从多个文本中提取关键词
        
        Args:
            text_list: 文本列表
            top_k: 每个文本返回的关键词数量
            
        Returns:
            每个文本的关键词列表
        """
        if not self.corpus_built:
            logger.warning("未添加语料库，IDF计算可能不准确")
        
        # 对每个文本进行分词
        doc_list = []
        for text in text_list:
            # 分词
            words = self.segmenter.segment(text)
            # 过滤停用词
            filtered_words = self.segmenter.filter_stopwords(words)
            doc_list.append(filtered_words)
        
        # 批量提取关键词
        keywords_list = self.tfidf.batch_extract_keywords(doc_list, top_k)
        
        return keywords_list


# 简单测试
if __name__ == "__main__":
    from nlp.segmentation import create_segmenter
    
    # 测试文本
    texts = [
        "自然语言处理是计算机科学领域与人工智能领域中的一个重要方向。它研究能实现人与计算机之间用自然语言进行有效通信的各种理论和方法。",
        "深度学习是机器学习的分支，是一种以人工神经网络为架构，对数据进行表征学习的算法。",
        "机器学习是人工智能的一个分支，是一门多领域交叉学科，涉及概率论、统计学、逼近论、凸分析、计算复杂性理论等多门学科。"
    ]
    
    # 创建分词器
    segmenter = create_segmenter('jieba')
    
    # 创建TF-IDF提取器
    extractor = TFIDFExtractor(segmenter)
    
    # 添加语料库
    extractor.add_corpus(texts)
    
    # 提取关键词
    for i, text in enumerate(texts):
        print(f"\n文本 {i+1}:")
        print(text)
        keywords = extractor.extract_keywords(text, 5)
        print("关键词:")
        for word, score in keywords:
            print(f"  {word}: {score:.4f}") 