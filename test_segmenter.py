#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试分词器功能
"""

from nlp.segmentation import create_segmenter

def test_segmenter():
    """测试分词器基本功能"""
    
    # 测试文本
    text = "自然语言处理是计算机科学领域与人工智能领域中的一个重要方向。"
    print(f"测试文本: {text}")
    
    # 创建jieba分词器
    print("\n=== 测试jieba分词器 ===")
    jieba_segmenter = create_segmenter('jieba')
    
    # 测试基本分词
    jieba_result = jieba_segmenter.segment(text)
    print("分词结果:")
    print(jieba_result)
    
    # 测试过滤停用词
    jieba_filtered = jieba_segmenter.filter_stopwords(jieba_result)
    print("\n过滤停用词后:")
    print(jieba_filtered)
    
    # 测试词性标注
    jieba_pos_result = jieba_segmenter.segment_with_pos(text)
    print("\n词性标注结果:")
    print(jieba_pos_result)
    
    # 尝试测试HanLP分词器
    try:
        print("\n=== 尝试测试HanLP分词器 ===")
        hanlp_segmenter = create_segmenter('hanlp')
        hanlp_result = hanlp_segmenter.segment(text)
        print("分词结果:")
        print(hanlp_result)
    except Exception as e:
        print(f"HanLP测试失败: {e}")
    
    # 使用无效的分词器类型测试容错
    print("\n=== 测试无效分词器类型 ===")
    fallback_segmenter = create_segmenter('invalid_type')
    fallback_result = fallback_segmenter.segment(text)
    print("fallback到jieba的分词结果:")
    print(fallback_result)

if __name__ == "__main__":
    test_segmenter() 