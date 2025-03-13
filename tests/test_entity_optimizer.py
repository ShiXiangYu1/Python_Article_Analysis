#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试实体优化器模块

测试EntityOptimizer和EntityMerger类的所有方法和边界情况
"""

import unittest
from nlp.entity_optimizer import EntityOptimizer, EntityMerger

class TestEntityOptimizer(unittest.TestCase):
    """测试实体优化器类"""
    
    def setUp(self):
        """测试前准备"""
        self.optimizer = EntityOptimizer()
        
        # 添加一些测试数据
        self.sample_text = "李明在北京大学参加了关于人工智能的会议，会后他前往清华大学拜访了王教授。李教授目前在中国科学院工作。"
        
        # 添加自定义实体
        self.optimizer.add_custom_entity("李明", "person")
        self.optimizer.add_custom_entity("王教授", "person")
        self.optimizer.add_custom_entity("北京大学", "organization")
        
        # 添加实体别名
        self.optimizer.add_entity_alias("王老师", "王教授")
        self.optimizer.add_entity_alias("李教授", "李明")
        
        # 测试实体数据
        self.test_entities = {
            'person': ['李明', '王教授', '李教授', '他'],
            'place': ['北京', '这里'],
            'organization': ['北京大学', '清华大学', '该单位']
        }
    
    def test_init(self):
        """测试初始化"""
        # 检查默认值
        self.assertIn('person', self.optimizer.custom_entities)
        self.assertIn('place', self.optimizer.custom_entities)
        self.assertIn('organization', self.optimizer.custom_entities)
        
        self.assertIn('person', self.optimizer.entity_rules)
        self.assertIn('place', self.optimizer.entity_rules)
        self.assertIn('organization', self.optimizer.entity_rules)
        
        # 测试自定义初始化
        custom_entities = {
            'person': ['张三', '李四'],
            'custom_category': ['自定义实体']
        }
        
        entity_rules = {
            'person': [r'[A-Za-z]+ [A-Za-z]+'],
            'custom_rule': [r'test\d+']
        }
        
        alias_dict = {
            '小张': '张三',
            '小李': '李四'
        }
        
        custom_optimizer = EntityOptimizer(
            custom_entities=custom_entities,
            entity_rules=entity_rules,
            alias_dict=alias_dict
        )
        
        # 检查自定义值是否正确加载
        self.assertIn('张三', custom_optimizer.custom_entities['person'])
        self.assertIn('自定义实体', custom_optimizer.custom_entities['custom_category'])
        self.assertIn(r'[A-Za-z]+ [A-Za-z]+', custom_optimizer.entity_rules['person'])
        self.assertIn(r'test\d+', custom_optimizer.entity_rules['custom_rule'])
        self.assertEqual(custom_optimizer.alias_dict['小张'], '张三')
        self.assertEqual(custom_optimizer.alias_dict['小李'], '李四')
    
    def test_add_custom_entity(self):
        """测试添加自定义实体"""
        # 添加正常实体
        self.assertTrue(self.optimizer.add_custom_entity("张三", "person"))
        self.assertIn("张三", self.optimizer.custom_entities["person"])
        
        # 添加到不存在的类别
        self.assertTrue(self.optimizer.add_custom_entity("测试实体", "custom_category"))
        self.assertIn("测试实体", self.optimizer.custom_entities["custom_category"])
        
        # 添加已存在的实体
        self.assertFalse(self.optimizer.add_custom_entity("李明", "person"))
        
        # 添加空实体或空类别
        self.assertFalse(self.optimizer.add_custom_entity("", "person"))
        self.assertFalse(self.optimizer.add_custom_entity("实体", ""))
        self.assertFalse(self.optimizer.add_custom_entity("", ""))
        self.assertFalse(self.optimizer.add_custom_entity(None, "person"))
        self.assertFalse(self.optimizer.add_custom_entity("实体", None))
    
    def test_add_entity_rule(self):
        """测试添加实体规则"""
        # 添加正常规则
        self.assertTrue(self.optimizer.add_entity_rule(r"test\d+", "person"))
        self.assertIn(r"test\d+", self.optimizer.entity_rules["person"])
        
        # 添加到不存在的类别
        self.assertTrue(self.optimizer.add_entity_rule(r"[a-z]+", "custom_rule"))
        self.assertIn(r"[a-z]+", self.optimizer.entity_rules["custom_rule"])
        
        # 添加已存在的规则
        self.assertFalse(self.optimizer.add_entity_rule(r"test\d+", "person"))
        
        # 添加无效的正则表达式
        self.assertFalse(self.optimizer.add_entity_rule(r"[未闭合的括号", "person"))
        
        # 添加空规则或空类别
        self.assertFalse(self.optimizer.add_entity_rule("", "person"))
        self.assertFalse(self.optimizer.add_entity_rule(r"[a-z]+", ""))
        self.assertFalse(self.optimizer.add_entity_rule("", ""))
        self.assertFalse(self.optimizer.add_entity_rule(None, "person"))
        self.assertFalse(self.optimizer.add_entity_rule(r"[a-z]+", None))
    
    def test_add_entity_alias(self):
        """测试添加实体别名"""
        # 添加正常别名
        self.assertTrue(self.optimizer.add_entity_alias("小李", "李明"))
        self.assertEqual(self.optimizer.alias_dict["小李"], "李明")
        
        # 添加已存在的别名（覆盖）
        self.assertTrue(self.optimizer.add_entity_alias("小李", "新李明"))
        self.assertEqual(self.optimizer.alias_dict["小李"], "新李明")
        
        # 添加空别名或空标准名
        self.assertFalse(self.optimizer.add_entity_alias("", "李明"))
        self.assertFalse(self.optimizer.add_entity_alias("小李", ""))
        self.assertFalse(self.optimizer.add_entity_alias("", ""))
        self.assertFalse(self.optimizer.add_entity_alias(None, "李明"))
        self.assertFalse(self.optimizer.add_entity_alias("小李", None))
    
    def test_recognize_entities_by_rules(self):
        """测试使用规则识别实体"""
        # 测试正常识别
        entities = self.optimizer.recognize_entities_by_rules(self.sample_text)
        self.assertIn("北京大学", entities["organization"])
        self.assertIn("清华大学", entities["organization"])
        
        # 测试空文本
        empty_entities = self.optimizer.recognize_entities_by_rules("")
        for category in empty_entities:
            self.assertEqual(len(empty_entities[category]), 0)
        
        # 测试None文本
        none_entities = self.optimizer.recognize_entities_by_rules(None)
        for category in none_entities:
            self.assertEqual(len(none_entities[category]), 0)
    
    def test_optimize_entities(self):
        """测试优化实体识别结果"""
        # 测试正常优化
        optimized = self.optimizer.optimize_entities(self.test_entities, self.sample_text)
        
        # 检查停用词过滤
        self.assertNotIn("他", optimized["person"])
        self.assertNotIn("这里", optimized["place"])
        self.assertNotIn("该单位", optimized["organization"])
        
        # 检查别名处理
        self.assertIn("李明", optimized["person"])
        self.assertNotIn("李教授", optimized["person"])
        
        # 检查自定义实体合并
        self.assertIn("李明", optimized["person"])
        self.assertIn("王教授", optimized["person"])
        self.assertIn("北京大学", optimized["organization"])
        
        # 测试无文本优化
        no_text_optimized = self.optimizer.optimize_entities(self.test_entities)
        self.assertIn("李明", no_text_optimized["person"])
        self.assertNotIn("他", no_text_optimized["person"])
        
        # 测试空实体字典
        empty_optimized = self.optimizer.optimize_entities({})
        self.assertEqual(len(empty_optimized["person"]), 2)  # 应包含自定义实体
        
        # 测试None实体字典
        none_optimized = self.optimizer.optimize_entities(None)
        self.assertEqual(len(none_optimized["person"]), 2)  # 应包含自定义实体
    
    def test_merge_custom_entities(self):
        """测试合并自定义实体"""
        # 准备测试数据
        entities = {
            'person': ['张三'],
            'organization': ['公司A']
        }
        
        # 执行合并
        merged = self.optimizer._merge_custom_entities(entities)
        
        # 检查结果
        self.assertIn('张三', merged['person'])
        self.assertIn('李明', merged['person'])  # 自定义实体
        self.assertIn('王教授', merged['person'])  # 自定义实体
        self.assertIn('公司A', merged['organization'])
        self.assertIn('北京大学', merged['organization'])  # 自定义实体
    
    def test_merge_entities(self):
        """测试合并两个实体字典"""
        # 准备测试数据
        entities1 = {
            'person': ['张三', '李四'],
            'organization': ['公司A']
        }
        
        entities2 = {
            'person': ['李四', '王五'],
            'place': ['北京', '上海']
        }
        
        # 执行合并
        merged = self.optimizer._merge_entities(entities1, entities2)
        
        # 检查结果
        self.assertEqual(len(merged['person']), 3)  # 张三、李四、王五
        self.assertEqual(len(merged['organization']), 1)  # 公司A
        self.assertEqual(len(merged['place']), 2)  # 北京、上海
        
        # 检查具体实体
        self.assertIn('张三', merged['person'])
        self.assertIn('李四', merged['person'])
        self.assertIn('王五', merged['person'])
        self.assertIn('公司A', merged['organization'])
        self.assertIn('北京', merged['place'])
        self.assertIn('上海', merged['place'])
    
    def test_filter_stop_entities(self):
        """测试过滤停用实体"""
        # 准备测试数据
        entities = {
            'person': ['张三', '李四', '他', '她', '某某'],
            'place': ['北京', '上海', '这里', '那里'],
            'organization': ['公司A', '本单位', '该单位']
        }
        
        # 执行过滤
        filtered = self.optimizer._filter_stop_entities(entities)
        
        # 检查结果
        self.assertEqual(len(filtered['person']), 2)  # 张三、李四
        self.assertEqual(len(filtered['place']), 2)  # 北京、上海
        self.assertEqual(len(filtered['organization']), 1)  # 公司A
        
        # 检查具体实体
        self.assertIn('张三', filtered['person'])
        self.assertIn('李四', filtered['person'])
        self.assertNotIn('他', filtered['person'])
        self.assertNotIn('她', filtered['person'])
        self.assertNotIn('某某', filtered['person'])
    
    def test_process_aliases(self):
        """测试处理实体别名"""
        # 准备测试数据
        entities = {
            'person': ['张三', '小张', '李四', '王老师'],
            'organization': ['北大', '北京大学']
        }
        
        # 添加别名
        self.optimizer.add_entity_alias('小张', '张三')
        self.optimizer.add_entity_alias('北大', '北京大学')
        
        # 执行别名处理
        processed = self.optimizer._process_aliases(entities)
        
        # 检查结果
        self.assertIn('张三', processed['person'])
        self.assertNotIn('小张', processed['person'])
        self.assertIn('李四', processed['person'])
        self.assertIn('王教授', processed['person'])  # 别名映射
        self.assertNotIn('王老师', processed['person'])
        
        self.assertIn('北京大学', processed['organization'])
        self.assertNotIn('北大', processed['organization'])
    
    def test_deduplicate_and_sort(self):
        """测试实体去重和排序"""
        # 准备测试数据
        entities = {
            'person': ['张三', '张三', '李四', '王五', '王五五'],
            'organization': ['北京大学', '清华大学', '清华大学', '中国科学院']
        }
        
        # 执行去重和排序
        result = self.optimizer._deduplicate_and_sort(entities)
        
        # 检查结果
        self.assertEqual(len(result['person']), 4)  # 去重后的数量
        self.assertEqual(len(result['organization']), 3)  # 去重后的数量
        
        # 检查排序（按长度降序，然后按字母升序）
        self.assertEqual(result['person'][0], '王五五')  # 最长的应该在最前面
        
        # 确认清华大学和北京大学的顺序（相同长度，按字母顺序)
        if '北京大学' in result['organization'] and '清华大学' in result['organization']:
            clean_org = [org for org in result['organization'] if org in ['北京大学', '清华大学']]
            self.assertEqual(clean_org, ['北京大学', '清华大学'])


class TestEntityMerger(unittest.TestCase):
    """测试实体合并器类"""
    
    def setUp(self):
        """测试前准备"""
        self.merger = EntityMerger()
        
        # 测试实体数据
        self.entities1 = {
            'person': ['张三', '李四'],
            'organization': ['北京大学']
        }
        
        self.entities2 = {
            'person': ['李四', '王五'],
            'place': ['北京', '上海']
        }
        
        self.entities3 = {
            'person': ['张三', '赵六'],
            'organization': ['清华大学'],
            'place': ['广州']
        }
    
    def test_init(self):
        """测试初始化"""
        # 检查默认权重
        self.assertIn('jieba', self.merger.weights)
        self.assertIn('hanlp', self.merger.weights)
        self.assertIn('ltp', self.merger.weights)
        self.assertIn('custom', self.merger.weights)
        self.assertIn('rule', self.merger.weights)
        
        # 测试自定义权重
        custom_weights = {
            'source1': 1.5,
            'source2': 2.0
        }
        
        custom_merger = EntityMerger(weights=custom_weights)
        self.assertEqual(custom_merger.weights['source1'], 1.5)
        self.assertEqual(custom_merger.weights['source2'], 2.0)
    
    def test_merge(self):
        """测试合并多个实体识别结果"""
        # 测试正常合并
        merged = self.merger.merge(
            [self.entities1, self.entities2, self.entities3],
            ['jieba', 'hanlp', 'ltp']
        )
        
        # 检查结果
        self.assertEqual(len(merged['person']), 4)  # 张三、李四、王五、赵六
        self.assertEqual(len(merged['organization']), 2)  # 北京大学、清华大学
        self.assertEqual(len(merged['place']), 3)  # 北京、上海、广州
        
        # 检查具体实体
        self.assertIn('张三', merged['person'])
        self.assertIn('李四', merged['person'])
        self.assertIn('王五', merged['person'])
        self.assertIn('赵六', merged['person'])
        self.assertIn('北京大学', merged['organization'])
        self.assertIn('清华大学', merged['organization'])
        self.assertIn('北京', merged['place'])
        self.assertIn('上海', merged['place'])
        self.assertIn('广州', merged['place'])
        
        # 测试不提供来源名称
        auto_merged = self.merger.merge([self.entities1, self.entities2])
        self.assertIn('张三', auto_merged['person'])
        self.assertIn('李四', auto_merged['person'])
        self.assertIn('王五', auto_merged['person'])
        
        # 测试来源数量与实体列表不匹配
        mismatch_merged = self.merger.merge(
            [self.entities1, self.entities2, self.entities3],
            ['jieba', 'hanlp']  # 只有两个来源名称
        )
        self.assertIn('张三', mismatch_merged['person'])
        self.assertIn('李四', mismatch_merged['person'])
        self.assertIn('王五', mismatch_merged['person'])
        self.assertIn('赵六', mismatch_merged['person'])
        
        # 测试空列表
        empty_merged = self.merger.merge([])
        self.assertEqual(empty_merged, {})
        
        # 测试自定义权重
        custom_merger = EntityMerger({
            'source1': 0.1,  # 权重较低
            'source2': 2.0   # 权重较高
        })
        
        # entities1中的实体在source1中权重较低，可能不会被选中
        # entities2中的实体在source2中权重较高，应该会被选中
        custom_merged = custom_merger.merge(
            [self.entities1, self.entities2],
            ['source1', 'source2']
        )
        
        # 检查权重较高的实体是否被选中
        self.assertIn('李四', custom_merged['person'])  # 两个来源都有，总权重>1
        self.assertIn('王五', custom_merged['person'])  # 权重高的来源有，应该被选中
        
        # 张三只在权重低的来源出现，可能不被选中（取决于具体权重和阈值）
        if '张三' in custom_merged.get('person', []):
            self.assertLess(custom_merger.weights['source1'], 1.0)


if __name__ == "__main__":
    unittest.main() 