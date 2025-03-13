#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试关系增强模块

测试RelationEnhancer和RelationMerger类的所有功能和边界情况
"""

import unittest
from nlp.relation_enhancer import RelationEnhancer, RelationMerger, Triple

class TestRelationEnhancer(unittest.TestCase):
    """测试关系增强器类"""
    
    def setUp(self):
        """测试前准备"""
        self.enhancer = RelationEnhancer()
        
        # 添加一些测试数据
        self.sample_text = """
        李明是一名计算机科学专业的学生，他就读于北京大学。
        张教授认为，人工智能技术未来将广泛应用于各个领域。
        由于全球气候变暖，因此极端天气现象越来越频繁。
        该公司对所有产品进行了全面升级，并推出了新的营销策略。
        """
        
        # 添加同义词
        self.enhancer.add_synonym("李明", "小明")
        self.enhancer.add_synonym("北京大学", "北大")
        
        # 测试三元组数据
        self.test_triples = [
            Triple("李明", "是", "学生", 0.9),
            Triple("李明", "就读于", "北京大学", 0.8),
            Triple("小明", "学习", "计算机科学", 0.7),
            Triple("张教授", "认为", "人工智能技术将广泛应用", 0.9),
            Triple("全球气候变暖", "导致", "极端天气现象", 0.8),
            Triple("该公司", "进行", "全面升级", 0.6),
            Triple("该公司", "推出", "新的营销策略", 0.7),
            Triple("该", "是", "公司", 0.4)  # 低置信度
        ]
    
    def test_init(self):
        """测试初始化"""
        # 检查默认值
        self.assertIsNotNone(self.enhancer.synonym_dict)
        self.assertIsNotNone(self.enhancer.filter_predicates)
        self.assertEqual(self.enhancer.confidence_threshold, 0.5)
        self.assertIsNotNone(self.enhancer.spo_patterns)
        self.assertIsNotNone(self.enhancer.compiled_patterns)
        
        # 测试自定义初始化
        custom_synonym_dict = {"自定义词1": "标准词1", "自定义词2": "标准词2"}
        custom_filter_predicates = ["谓语1", "谓语2"]
        custom_confidence = 0.7
        
        custom_enhancer = RelationEnhancer(
            synonym_dict=custom_synonym_dict,
            filter_predicates=custom_filter_predicates,
            confidence_threshold=custom_confidence
        )
        
        # 检查自定义值是否正确加载
        self.assertEqual(custom_enhancer.synonym_dict, custom_synonym_dict)
        self.assertEqual(custom_enhancer.filter_predicates, custom_filter_predicates)
        self.assertEqual(custom_enhancer.confidence_threshold, custom_confidence)
    
    def test_add_synonym(self):
        """测试添加同义词"""
        # 添加正常同义词
        self.assertTrue(self.enhancer.add_synonym("自定义词", "标准词"))
        self.assertEqual(self.enhancer.synonym_dict["自定义词"], "标准词")
        
        # 添加已存在的同义词（覆盖）
        self.assertTrue(self.enhancer.add_synonym("自定义词", "新标准词"))
        self.assertEqual(self.enhancer.synonym_dict["自定义词"], "新标准词")
        
        # 添加空同义词或空标准词
        self.assertFalse(self.enhancer.add_synonym("", "标准词"))
        self.assertFalse(self.enhancer.add_synonym("自定义词", ""))
        self.assertFalse(self.enhancer.add_synonym("", ""))
        self.assertFalse(self.enhancer.add_synonym(None, "标准词"))
        self.assertFalse(self.enhancer.add_synonym("自定义词", None))
    
    def test_add_filter_predicate(self):
        """测试添加过滤谓语"""
        # 添加正常谓语
        initial_len = len(self.enhancer.filter_predicates)
        self.assertTrue(self.enhancer.add_filter_predicate("新谓语"))
        self.assertIn("新谓语", self.enhancer.filter_predicates)
        self.assertEqual(len(self.enhancer.filter_predicates), initial_len + 1)
        
        # 添加已存在的谓语
        self.assertFalse(self.enhancer.add_filter_predicate("新谓语"))
        self.assertEqual(len(self.enhancer.filter_predicates), initial_len + 1)
        
        # 添加空谓语
        self.assertFalse(self.enhancer.add_filter_predicate(""))
        self.assertFalse(self.enhancer.add_filter_predicate(None))
    
    def test_extract_triples_from_patterns(self):
        """测试使用模式提取三元组"""
        # 测试正常提取
        triples = self.enhancer.extract_triples_from_patterns(self.sample_text)
        self.assertGreater(len(triples), 0)
        
        # 验证提取结果中包含预期的三元组
        found_climate_triple = False
        found_professor_triple = False
        
        for triple in triples:
            if (triple.subject == "全球气候变暖" and
                triple.predicate == "导致" and
                triple.object == "极端天气现象越来越频繁"):
                found_climate_triple = True
            elif (triple.subject == "张教授" and
                  triple.predicate == "认为" and
                  "人工智能技术未来将广泛应用于各个领域" in triple.object):
                found_professor_triple = True
        
        self.assertTrue(found_climate_triple)
        self.assertTrue(found_professor_triple)
        
        # 测试空文本
        empty_triples = self.enhancer.extract_triples_from_patterns("")
        self.assertEqual(len(empty_triples), 0)
        
        # 测试None文本
        none_triples = self.enhancer.extract_triples_from_patterns(None)
        self.assertEqual(len(none_triples), 0)
    
    def test_enhance_triples(self):
        """测试增强三元组"""
        # 测试正常增强
        enhanced = self.enhancer.enhance_triples(self.test_triples)
        
        # 验证低置信度的三元组被过滤掉
        low_confidence_found = False
        for triple in enhanced:
            if (triple.subject == "该" and
                triple.predicate == "是" and
                triple.object == "公司"):
                low_confidence_found = True
                break
        self.assertFalse(low_confidence_found)
        
        # 验证同义词规范化
        # 由于同义词替换，"小明"应该被替换为"李明"，"北大"应该被替换为"北京大学"
        # 但是注意：这里是逆向操作，我们在初始化时设置了"李明"的同义词是"小明"，所以实际上应该检查"李明"是否被替换为"小明"
        for triple in enhanced:
            if triple.subject == "李明" or triple.object == "李明":
                self.fail("李明应该被替换为小明")
            if triple.subject == "北京大学" or triple.object == "北京大学":
                self.fail("北京大学应该被替换为北大")
        
        # 测试空三元组列表
        empty_enhanced = self.enhancer.enhance_triples([])
        self.assertEqual(len(empty_enhanced), 0)
        
        # 测试None三元组列表
        none_enhanced = self.enhancer.enhance_triples(None)
        self.assertEqual(len(none_enhanced), 0)
    
    def test_filter_invalid_triples(self):
        """测试过滤无效三元组"""
        # 创建测试数据
        triples = [
            Triple("主语1", "谓语1", "宾语1", 0.9),
            Triple("主语2", "是", "宾语2", 0.8),  # 应该被过滤，谓语在filter_predicates中
            Triple("主语3", "谓语3", "宾语3", 0.3),  # 应该被过滤，置信度低于阈值
            Triple("主语4", "谓语4", "", 0.7),  # 应该被过滤，宾语为空
            Triple("", "谓语5", "宾语5", 0.7),  # 应该被过滤，主语为空
            Triple("主语6", "谓语6", "主语6", 0.7)  # 应该被过滤，主语等于宾语
        ]
        
        # 过滤三元组
        filtered = self.enhancer._filter_invalid_triples(triples)
        
        # 验证结果
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].subject, "主语1")
        self.assertEqual(filtered[0].predicate, "谓语1")
        self.assertEqual(filtered[0].object, "宾语1")
    
    def test_normalize_triples(self):
        """测试规范化三元组"""
        # 创建测试数据
        triples = [
            Triple("李明", "就读于", "北京大学", 0.8),
            Triple(" 小明 ", " 学习 ", " 计算机科学 ", 0.7)  # 有多余空格
        ]
        
        # 规范化三元组
        normalized = self.enhancer._normalize_triples(triples)
        
        # 验证结果
        self.assertEqual(len(normalized), 2)
        
        # 验证同义词替换和空格清理
        for triple in normalized:
            if triple.subject == "小明":  # "李明"应该被替换为"小明"
                self.assertEqual(triple.object, "北大")  # "北京大学"应该被替换为"北大"
            elif triple.subject == "小明":  # 应该清理空格
                self.assertEqual(triple.predicate, "学习")  # 应该清理空格
                self.assertEqual(triple.object, "计算机科学")  # 应该清理空格
    
    def test_deduplicate_triples(self):
        """测试去重三元组"""
        # 创建测试数据，包含重复三元组
        triples = [
            Triple("主语1", "谓语1", "宾语1", 0.7),
            Triple("主语1", "谓语1", "宾语1", 0.9),  # 重复，但置信度更高
            Triple("主语2", "谓语2", "宾语2", 0.8),
            Triple("主语2", "谓语2", "宾语2", 0.6),  # 重复，但置信度更低
            Triple("主语3", "谓语3", "宾语3", 0.7)
        ]
        
        # 去重三元组
        deduplicated = self.enhancer._deduplicate_triples(triples)
        
        # 验证结果
        self.assertEqual(len(deduplicated), 3)  # 应该只有3个唯一的三元组
        
        # 验证保留了更高置信度的三元组
        for triple in deduplicated:
            if triple.subject == "主语1":
                self.assertEqual(triple.confidence, 0.9)
            elif triple.subject == "主语2":
                self.assertEqual(triple.confidence, 0.8)
    
    def test_sort_triples_by_confidence(self):
        """测试按置信度排序三元组"""
        # 创建测试数据
        triples = [
            Triple("主语1", "谓语1", "宾语1", 0.5),
            Triple("主语2", "谓语2", "宾语2", 0.9),
            Triple("主语3", "谓语3", "宾语3", 0.7),
            Triple("主语4", "谓语4", "宾语4", 0.3)
        ]
        
        # 排序三元组
        sorted_triples = self.enhancer._sort_triples_by_confidence(triples)
        
        # 验证结果
        self.assertEqual(len(sorted_triples), 4)
        self.assertEqual(sorted_triples[0].subject, "主语2")  # 置信度最高的应该在最前面
        self.assertEqual(sorted_triples[1].subject, "主语3")
        self.assertEqual(sorted_triples[2].subject, "主语1")
        self.assertEqual(sorted_triples[3].subject, "主语4")  # 置信度最低的应该在最后面
    
    def test_split_sentences(self):
        """测试分割句子"""
        # 测试正常文本
        text = "这是第一个句子。这是第二个句子！这是第三个句子？这是第四个句子；这是第五个句子。"
        sentences = self.enhancer._split_sentences(text)
        self.assertEqual(len(sentences), 5)
        
        # 测试包含换行符的文本
        text = "这是第一行。\n这是第二行。\n这是第三行。"
        sentences = self.enhancer._split_sentences(text)
        self.assertEqual(len(sentences), 3)
        
        # 测试空文本
        sentences = self.enhancer._split_sentences("")
        self.assertEqual(len(sentences), 0)


class TestRelationMerger(unittest.TestCase):
    """测试关系合并器类"""
    
    def setUp(self):
        """测试前准备"""
        self.merger = RelationMerger(threshold=0.6)
        
        # 测试三元组数据
        self.triples1 = [
            Triple("小明", "学习", "计算机科学", 0.7),
            Triple("张教授", "研究", "人工智能", 0.8)
        ]
        
        self.triples2 = [
            Triple("小明", "学习", "计算机科学专业", 0.9),
            Triple("张教授", "研究", "深度学习", 0.6),
            Triple("王老师", "教授", "数学", 0.5)
        ]
        
        self.triples3 = [
            Triple("李四", "擅长", "编程", 0.7),
            Triple("王老师", "讲解", "高等数学", 0.6)
        ]
    
    def test_init(self):
        """测试初始化"""
        # 检查默认值
        default_merger = RelationMerger()
        self.assertEqual(default_merger.threshold, 0.5)
        
        # 检查自定义值
        self.assertEqual(self.merger.threshold, 0.6)
    
    def test_merge(self):
        """测试合并三元组列表"""
        # 测试正常合并
        merged = self.merger.merge([self.triples1, self.triples2, self.triples3])
        
        # 验证结果
        self.assertGreaterEqual(len(merged), 4)  # 至少应该有4个唯一的三元组
        
        # 检查是否包含所有预期的三元组
        subjects = [t.subject for t in merged]
        self.assertIn("小明", subjects)
        self.assertIn("张教授", subjects)
        self.assertIn("王老师", subjects)
        self.assertIn("李四", subjects)
        
        # 测试空列表
        empty_merged = self.merger.merge([])
        self.assertEqual(len(empty_merged), 0)
        
        # 测试只有一个列表
        single_merged = self.merger.merge([self.triples1])
        self.assertEqual(len(single_merged), len(self.triples1))
    
    def test_is_duplicate(self):
        """测试检查三元组是否重复"""
        # 创建测试数据
        triple = Triple("小明", "学习", "计算机科学", 0.7)
        triples = [
            Triple("小明", "学习", "计算机科学", 0.9),
            Triple("张教授", "研究", "人工智能", 0.8)
        ]
        
        # 测试重复三元组
        self.assertTrue(self.merger._is_duplicate(triple, triples))
        
        # 测试不重复三元组
        triple2 = Triple("小明", "学习", "编程", 0.7)
        self.assertFalse(self.merger._is_duplicate(triple2, triples))
    
    def test_merge_similar_triples(self):
        """测试合并相似三元组"""
        # 创建测试数据，包含相似三元组
        triples = [
            Triple("小明", "学习", "计算机科学", 0.7),
            Triple("小明", "学习", "计算机科学专业", 0.9),  # 相似宾语
            Triple("张教授", "研究", "人工智能", 0.8),
            Triple("张教授", "研究", "人工智能技术", 0.6)  # 相似宾语
        ]
        
        # 合并相似三元组
        merged = self.merger._merge_similar_triples(triples)
        
        # 验证结果
        self.assertEqual(len(merged), 2)  # 应该合并为2个三元组
        
        # 验证选择了较长的宾语和较高的置信度
        for triple in merged:
            if triple.subject == "小明":
                self.assertEqual(triple.object, "计算机科学专业")  # 较长的宾语
                self.assertEqual(triple.confidence, 0.9)  # 较高的置信度
            elif triple.subject == "张教授":
                self.assertEqual(triple.object, "人工智能技术")  # 较长的宾语
                self.assertEqual(triple.confidence, 0.8)  # 较高的置信度
    
    def test_merge_similar_objects(self):
        """测试合并相似宾语"""
        # 创建测试数据
        triples = [
            Triple("主语", "谓语", "宾语1", 0.7),
            Triple("主语", "谓语", "宾语1更长", 0.8),  # 相似且更长
            Triple("主语", "谓语", "完全不同的宾语", 0.6)
        ]
        
        # 合并相似宾语
        merged_objects = self.merger._merge_similar_objects(triples)
        
        # 验证结果
        self.assertEqual(len(merged_objects), 2)  # 应该有2个唯一的宾语
        self.assertIn("宾语1更长", merged_objects)
        self.assertIn("完全不同的宾语", merged_objects)
        self.assertEqual(merged_objects["宾语1更长"], 0.8)
    
    def test_is_similar(self):
        """测试判断两个字符串是否相似"""
        # 测试包含关系
        self.assertTrue(self.merger._is_similar("计算机", "计算机科学"))
        self.assertTrue(self.merger._is_similar("计算机科学", "计算机"))
        
        # 测试编辑距离相似
        self.assertTrue(self.merger._is_similar("计算机科学", "计算机科学专业"))
        
        # 测试不相似
        self.assertFalse(self.merger._is_similar("计算机", "数学"))
        
        # 测试空字符串
        self.assertTrue(self.merger._is_similar("", ""))
        self.assertFalse(self.merger._is_similar("计算机", ""))
    
    def test_levenshtein_distance(self):
        """测试计算编辑距离"""
        # 测试相同字符串
        self.assertEqual(self.merger._levenshtein_distance("计算机", "计算机"), 0)
        
        # 测试单字符差异
        self.assertEqual(self.merger._levenshtein_distance("计算机", "计算器"), 1)
        
        # 测试多字符差异
        self.assertEqual(self.merger._levenshtein_distance("计算机科学", "数学"), 5)
        
        # 测试空字符串
        self.assertEqual(self.merger._levenshtein_distance("", ""), 0)
        self.assertEqual(self.merger._levenshtein_distance("计算机", ""), 3)
        self.assertEqual(self.merger._levenshtein_distance("", "计算机"), 3)


if __name__ == "__main__":
    unittest.main() 