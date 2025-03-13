"""
实体识别优化模块

提供实体识别结果的优化，包括实体过滤、合并、去重和规则匹配等功能
"""

import re
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict

logger = logging.getLogger('entity_optimizer')

class EntityOptimizer:
    """
    实体优化器
    
    优化实体识别结果，提高准确率
    """
    
    def __init__(self, 
                custom_entities: Dict[str, List[str]] = None,
                entity_rules: Dict[str, List[str]] = None,
                alias_dict: Dict[str, str] = None) -> None:
        """
        初始化实体优化器
        
        Args:
            custom_entities: 自定义实体字典，格式为{类别: [实体列表]}
            entity_rules: 实体识别规则，格式为{类别: [正则表达式列表]}
            alias_dict: 实体别名映射，格式为{别名: 标准名}
        """
        # 自定义实体字典
        self.custom_entities = custom_entities or {
            'person': [],
            'place': [],
            'organization': []
        }
        
        # 实体识别规则
        self.entity_rules = entity_rules or {
            'person': [
                r'[A-Z][a-z]+ [A-Z][a-z]+',  # 英文人名
                r'[\u4e00-\u9fa5]{2,4}'      # 中文人名
            ],
            'place': [
                r'[\u4e00-\u9fa5]{2,}[省市县区]',  # 中文地名
                r'[\u4e00-\u9fa5]{2,}(路|街|道)',  # 中文街道
            ],
            'organization': [
                r'[\u4e00-\u9fa5]{2,}(公司|集团|企业|大学|学院|机构|部门|协会|组织)'  # 中文组织机构
            ]
        }
        
        # 实体别名映射
        self.alias_dict = alias_dict or {}
        
        # 编译正则表达式
        self.compiled_rules = self._compile_rules()
        
        # 停用实体列表（需要过滤的实体）
        self.stop_entities = {
            'person': ['某某', '此人', '他', '她', '谁'],
            'place': ['这里', '那里', '此地', '何处'],
            'organization': ['该公司', '本单位', '该单位']
        }
    
    def _compile_rules(self) -> Dict[str, List[re.Pattern]]:
        """
        编译正则表达式规则
        
        Returns:
            编译后的正则表达式字典
        """
        compiled_rules = {}
        for category, rules in self.entity_rules.items():
            compiled_rules[category] = []
            for rule in rules:
                try:
                    compiled_rules[category].append(re.compile(rule))
                except re.error as e:
                    logger.error(f"正则表达式编译错误: {rule}, {e}")
        return compiled_rules
    
    def add_custom_entity(self, entity: str, category: str) -> bool:
        """
        添加自定义实体
        
        Args:
            entity: 实体名称
            category: 实体类别
            
        Returns:
            是否添加成功
        """
        if not entity or not category:
            return False
        
        if category not in self.custom_entities:
            self.custom_entities[category] = []
        
        if entity not in self.custom_entities[category]:
            self.custom_entities[category].append(entity)
            logger.info(f"添加自定义实体: {entity} ({category})")
            return True
        
        return False
    
    def add_entity_rule(self, rule: str, category: str) -> bool:
        """
        添加实体规则
        
        Args:
            rule: 正则表达式规则
            category: 实体类别
            
        Returns:
            是否添加成功
        """
        if not rule or not category:
            return False
        
        if category not in self.entity_rules:
            self.entity_rules[category] = []
        
        if rule not in self.entity_rules[category]:
            try:
                re.compile(rule)  # 测试规则是否有效
                self.entity_rules[category].append(rule)
                # 更新编译后的规则
                if category not in self.compiled_rules:
                    self.compiled_rules[category] = []
                self.compiled_rules[category].append(re.compile(rule))
                logger.info(f"添加实体规则: {rule} ({category})")
                return True
            except re.error as e:
                logger.error(f"添加实体规则失败，正则表达式错误: {rule}, {e}")
                return False
        
        return False
    
    def add_entity_alias(self, alias: str, standard_name: str) -> bool:
        """
        添加实体别名
        
        Args:
            alias: 别名
            standard_name: 标准名称
            
        Returns:
            是否添加成功
        """
        if not alias or not standard_name:
            return False
        
        self.alias_dict[alias] = standard_name
        logger.info(f"添加实体别名: {alias} -> {standard_name}")
        return True
    
    def recognize_entities_by_rules(self, text: str) -> Dict[str, List[str]]:
        """
        使用规则识别文本中的实体
        
        Args:
            text: 待处理文本
            
        Returns:
            按实体类型分类的实体列表字典
        """
        if not text:
            return {category: [] for category in self.entity_rules}
        
        entities = {category: [] for category in self.entity_rules}
        
        # 使用规则匹配实体
        for category, patterns in self.compiled_rules.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[0]  # 取第一个分组
                        if match and match not in entities[category]:
                            entities[category].append(match)
        
        return entities
    
    def optimize_entities(self, entities: Dict[str, List[str]], text: str = None) -> Dict[str, List[str]]:
        """
        优化实体识别结果
        
        Args:
            entities: 实体识别结果，格式为{类别: [实体列表]}
            text: 原文本，用于规则识别
            
        Returns:
            优化后的实体字典
        """
        # 合并自定义实体
        optimized = self._merge_custom_entities(entities)
        
        # 使用规则识别
        if text:
            rule_entities = self.recognize_entities_by_rules(text)
            optimized = self._merge_entities(optimized, rule_entities)
        
        # 过滤停用实体
        optimized = self._filter_stop_entities(optimized)
        
        # 处理实体别名
        optimized = self._process_aliases(optimized)
        
        # 实体去重和排序
        optimized = self._deduplicate_and_sort(optimized)
        
        return optimized
    
    def _merge_custom_entities(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        合并自定义实体
        
        Args:
            entities: 实体识别结果
            
        Returns:
            合并后的实体字典
        """
        merged = {category: list(entities.get(category, [])) for category in self.custom_entities}
        
        # 添加自定义实体
        for category, custom_list in self.custom_entities.items():
            if category not in merged:
                merged[category] = []
            for entity in custom_list:
                if entity not in merged[category]:
                    merged[category].append(entity)
        
        return merged
    
    def _merge_entities(self, entities1: Dict[str, List[str]], entities2: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        合并两个实体字典
        
        Args:
            entities1: 第一个实体字典
            entities2: 第二个实体字典
            
        Returns:
            合并后的实体字典
        """
        merged = {category: list(entities1.get(category, [])) for category in set(entities1) | set(entities2)}
        
        # 合并第二个字典的实体
        for category, entity_list in entities2.items():
            if category not in merged:
                merged[category] = []
            for entity in entity_list:
                if entity not in merged[category]:
                    merged[category].append(entity)
        
        return merged
    
    def _filter_stop_entities(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        过滤停用实体
        
        Args:
            entities: 实体字典
            
        Returns:
            过滤后的实体字典
        """
        filtered = {}
        
        for category, entity_list in entities.items():
            filtered[category] = []
            stop_list = self.stop_entities.get(category, [])
            
            for entity in entity_list:
                if entity not in stop_list:
                    filtered[category].append(entity)
        
        return filtered
    
    def _process_aliases(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        处理实体别名
        
        Args:
            entities: 实体字典
            
        Returns:
            处理后的实体字典
        """
        processed = {}
        
        for category, entity_list in entities.items():
            processed[category] = []
            alias_map = {}  # 用于记录当前处理的别名映射
            
            for entity in entity_list:
                # 检查是否为别名
                if entity in self.alias_dict:
                    standard_name = self.alias_dict[entity]
                    if standard_name not in processed[category]:
                        processed[category].append(standard_name)
                    alias_map[entity] = standard_name
                else:
                    # 检查是否有其他实体是它的别名
                    is_standard = False
                    for alias, std in alias_map.items():
                        if entity == std:
                            is_standard = True
                            break
                    
                    if not is_standard:
                        processed[category].append(entity)
        
        return processed
    
    def _deduplicate_and_sort(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        实体去重和排序
        
        Args:
            entities: 实体字典
            
        Returns:
            去重和排序后的实体字典
        """
        result = {}
        
        for category, entity_list in entities.items():
            # 去重
            unique_entities = list(set(entity_list))
            
            # 按长度和字母顺序排序
            unique_entities.sort(key=lambda x: (-len(x), x))
            
            result[category] = unique_entities
        
        return result
    

class EntityMerger:
    """
    实体合并器
    
    合并多个来源的实体识别结果
    """
    
    def __init__(self, weights: Dict[str, float] = None) -> None:
        """
        初始化实体合并器
        
        Args:
            weights: 各个来源的权重，格式为{来源名称: 权重}
        """
        # 默认权重
        self.weights = weights or {
            'jieba': 1.0,
            'hanlp': 1.2,
            'ltp': 1.1,
            'custom': 1.5,
            'rule': 1.3
        }
    
    def merge(self, entities_list: List[Dict[str, List[str]]], sources: List[str] = None) -> Dict[str, List[str]]:
        """
        合并多个实体识别结果
        
        Args:
            entities_list: 实体识别结果列表，每个元素是一个实体字典
            sources: 实体来源名称列表，与entities_list一一对应
            
        Returns:
            合并后的实体字典
        """
        if not entities_list:
            return {}
        
        # 如果没有提供来源，使用默认来源名称
        if not sources or len(sources) != len(entities_list):
            sources = [f'source_{i}' for i in range(len(entities_list))]
        
        # 所有实体类别
        all_categories = set()
        for entities in entities_list:
            all_categories.update(entities.keys())
        
        # 初始化结果
        merged = {category: [] for category in all_categories}
        
        # 计算每个实体的权重
        entity_weights = defaultdict(float)
        
        for entities, source in zip(entities_list, sources):
            source_weight = self.weights.get(source, 1.0)
            
            for category, entity_list in entities.items():
                for entity in entity_list:
                    key = (category, entity)
                    entity_weights[key] += source_weight
        
        # 根据权重选择实体
        for (category, entity), weight in entity_weights.items():
            if weight >= 1.0:  # 至少有一个来源支持
                if entity not in merged[category]:
                    merged[category].append(entity)
        
        return merged


# 测试代码
if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 测试文本
    text = "李明在北京大学参加了关于人工智能的会议，会后他前往清华大学拜访了王教授。李教授目前在中国科学院工作。"
    
    # 创建实体优化器
    optimizer = EntityOptimizer()
    
    # 添加自定义实体
    optimizer.add_custom_entity("李明", "person")
    optimizer.add_custom_entity("王教授", "person")
    optimizer.add_custom_entity("北京大学", "organization")
    optimizer.add_custom_entity("清华大学", "organization")
    optimizer.add_custom_entity("中国科学院", "organization")
    
    # 添加实体别名
    optimizer.add_entity_alias("王老师", "王教授")
    optimizer.add_entity_alias("李教授", "李明")
    
    # 使用规则识别实体
    rule_entities = optimizer.recognize_entities_by_rules(text)
    print("规则识别结果:")
    for category, entities in rule_entities.items():
        print(f"  {category}: {entities}")
    
    # 模拟实体识别结果
    entities = {
        'person': ['李明', '王教授', '李教授'],
        'place': ['北京'],
        'organization': ['北京大学', '清华大学']
    }
    
    # 优化实体
    optimized = optimizer.optimize_entities(entities, text)
    print("\n优化后的结果:")
    for category, entities in optimized.items():
        print(f"  {category}: {entities}")
    
    # 测试实体合并器
    entities1 = {
        'person': ['李明', '王教授'],
        'organization': ['北京大学']
    }
    
    entities2 = {
        'person': ['李教授'],
        'place': ['北京'],
        'organization': ['清华大学']
    }
    
    merger = EntityMerger()
    merged = merger.merge([entities1, entities2], ['jieba', 'hanlp'])
    
    print("\n合并多个来源的结果:")
    for category, entities in merged.items():
        print(f"  {category}: {entities}") 