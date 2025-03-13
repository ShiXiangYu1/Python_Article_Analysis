"""
三元组关系增强模块

提供优化关系提取结果的功能，包括复杂句式分析、同义词归一化处理、关系三元组过滤与合并等
"""

import re
import logging
from typing import List, Dict, Tuple, Set, Optional, Any
from collections import defaultdict

# 导入关系提取相关类
try:
    from nlp.relation import Triple
except ImportError:
    # 如果无法导入，定义一个简化版的Triple类
    class Triple:
        """
        三元组类，表示(主体, 谓语, 客体)的关系
        """
        def __init__(self, subject: str, predicate: str, object: str, confidence: float = 1.0) -> None:
            self.subject = subject
            self.predicate = predicate
            self.object = object
            self.confidence = confidence
        
        def __str__(self) -> str:
            return f"({self.subject}, {self.predicate}, {self.object})"
        
        def to_dict(self) -> Dict[str, Any]:
            return {
                'subject': self.subject,
                'predicate': self.predicate,
                'object': self.object,
                'confidence': self.confidence
            }

logger = logging.getLogger('relation_enhancer')

class RelationEnhancer:
    """
    关系三元组增强器
    
    优化关系提取结果，提高质量和准确率
    """
    
    def __init__(self, 
                 synonym_dict: Dict[str, str] = None,
                 filter_predicates: List[str] = None,
                 confidence_threshold: float = 0.5) -> None:
        """
        初始化关系增强器
        
        Args:
            synonym_dict: 同义词词典，格式为{词: 标准词}
            filter_predicates: 需要过滤的谓语词列表
            confidence_threshold: 置信度阈值，低于此值的三元组将被过滤
        """
        # 同义词词典
        self.synonym_dict = synonym_dict or {}
        
        # 过滤谓语
        self.filter_predicates = filter_predicates or [
            '是', '有', '为', '被', '把', '将', '用', '对',
            '说', '道', '讲', '称', '表示',
            '认为', '指出', '声明', '强调'
        ]
        
        # 置信度阈值
        self.confidence_threshold = confidence_threshold
        
        # 主谓宾模板模式
        self.spo_patterns = [
            (r'(.+?)(?:认为|表示|指出|声明|强调|说|讲)(?:，|,|：|:)(.+)', '认为', 2, 1),  # "A认为:B" -> (A, 认为, B)
            (r'(.+?)(?:对|把|将)(.+?)(?:进行|给予|予以)(.+)', 3, 2, 1),  # "A对B进行C" -> (A, C, B)
            (r'(.+?)(?:存在|具有|有)(.+?)', 1, '具有', 2),  # "A具有B" -> (A, 具有, B)
            (r'(.+?)(?:的|之)(.+?)(?:是|为)(.+)', 1, 2, 3),  # "A的B是C" -> (A, B, C)
            (r'(?:由于|因为)(.+?)(?:，|,)(?:所以|因此|故)(.+)', 1, '导致', 2)  # "因为A,所以B" -> (A, 导致, B)
        ]
        
        # 编译模式
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """
        编译模式
        """
        self.compiled_patterns = []
        for pattern in self.spo_patterns:
            try:
                regex = re.compile(pattern[0])
                self.compiled_patterns.append((regex, *pattern[1:]))
            except re.error as e:
                logger.error(f"正则表达式编译错误: {pattern[0]}, {e}")
    
    def add_synonym(self, word: str, standard_word: str) -> bool:
        """
        添加同义词映射
        
        Args:
            word: 词语
            standard_word: 标准词
            
        Returns:
            是否添加成功
        """
        if not word or not standard_word:
            return False
        
        self.synonym_dict[word] = standard_word
        logger.info(f"添加同义词映射: {word} -> {standard_word}")
        return True
    
    def add_filter_predicate(self, predicate: str) -> bool:
        """
        添加需要过滤的谓语
        
        Args:
            predicate: 谓语
            
        Returns:
            是否添加成功
        """
        if not predicate:
            return False
        
        if predicate not in self.filter_predicates:
            self.filter_predicates.append(predicate)
            logger.info(f"添加过滤谓语: {predicate}")
            return True
        
        return False
    
    def enhance_triples(self, triples: List[Triple]) -> List[Triple]:
        """
        增强三元组
        
        Args:
            triples: 原始三元组列表
            
        Returns:
            增强后的三元组列表
        """
        if not triples:
            return []
        
        # 过滤无效三元组
        filtered_triples = self._filter_invalid_triples(triples)
        
        # 规范化主谓宾
        normalized_triples = self._normalize_triples(filtered_triples)
        
        # 去重
        deduplicated_triples = self._deduplicate_triples(normalized_triples)
        
        # 按置信度排序
        sorted_triples = self._sort_triples_by_confidence(deduplicated_triples)
        
        return sorted_triples
    
    def extract_triples_from_patterns(self, text: str) -> List[Triple]:
        """
        使用模式直接从文本提取三元组
        
        Args:
            text: 文本
            
        Returns:
            三元组列表
        """
        if not text:
            return []
        
        triples = []
        
        for sentence in self._split_sentences(text):
            # 使用模式提取
            for regex, subject_idx, predicate_idx, object_idx in self.compiled_patterns:
                matches = regex.findall(sentence)
                if matches:
                    for match in matches:
                        if isinstance(match, tuple):
                            # 如果匹配结果是元组，表示有多个捕获组
                            groups = match
                        else:
                            # 如果匹配结果是字符串，表示只有一个捕获组
                            groups = (match,)
                        
                        # 获取主语、谓语、宾语
                        try:
                            # 如果索引是数字，表示从匹配组获取
                            if isinstance(subject_idx, int) and subject_idx <= len(groups):
                                subject = groups[subject_idx - 1].strip()
                            else:
                                # 否则使用固定值
                                subject = str(subject_idx).strip()
                            
                            if isinstance(predicate_idx, int) and predicate_idx <= len(groups):
                                predicate = groups[predicate_idx - 1].strip()
                            else:
                                predicate = str(predicate_idx).strip()
                            
                            if isinstance(object_idx, int) and object_idx <= len(groups):
                                object_ = groups[object_idx - 1].strip()
                            else:
                                object_ = str(object_idx).strip()
                            
                            # 创建三元组
                            if subject and predicate and object_:
                                triple = Triple(subject, predicate, object_, 0.7)  # 模板匹配的置信度设为0.7
                                triples.append(triple)
                        except (IndexError, ValueError) as e:
                            logger.warning(f"处理模式匹配结果错误: {e}")
        
        return triples
    
    def _filter_invalid_triples(self, triples: List[Triple]) -> List[Triple]:
        """
        过滤无效三元组
        
        Args:
            triples: 三元组列表
            
        Returns:
            过滤后的三元组列表
        """
        valid_triples = []
        
        for triple in triples:
            # 过滤低置信度三元组
            if triple.confidence < self.confidence_threshold:
                continue
            
            # 过滤无效谓语
            if triple.predicate in self.filter_predicates:
                continue
            
            # 过滤主语或宾语为空的三元组
            if not triple.subject or not triple.object:
                continue
            
            # 主语与宾语相同的三元组可能无效
            if triple.subject == triple.object:
                continue
            
            valid_triples.append(triple)
        
        return valid_triples
    
    def _normalize_triples(self, triples: List[Triple]) -> List[Triple]:
        """
        规范化三元组
        
        Args:
            triples: 三元组列表
            
        Returns:
            规范化后的三元组列表
        """
        normalized = []
        
        for triple in triples:
            # 规范化主语
            subject = self._normalize_term(triple.subject)
            
            # 规范化谓语
            predicate = self._normalize_term(triple.predicate)
            
            # 规范化宾语
            object_ = self._normalize_term(triple.object)
            
            # 创建新的三元组
            normalized_triple = Triple(subject, predicate, object_, triple.confidence)
            normalized.append(normalized_triple)
        
        return normalized
    
    def _normalize_term(self, term: str) -> str:
        """
        规范化术语
        
        Args:
            term: 术语
            
        Returns:
            规范化后的术语
        """
        # 清理空白字符
        term = re.sub(r'\s+', ' ', term).strip()
        
        # 同义词替换
        if term in self.synonym_dict:
            return self.synonym_dict[term]
        
        return term
    
    def _deduplicate_triples(self, triples: List[Triple]) -> List[Triple]:
        """
        去重三元组
        
        Args:
            triples: 三元组列表
            
        Returns:
            去重后的三元组列表
        """
        # 使用(subject, predicate, object)元组作为键进行去重
        unique_triples = {}
        
        for triple in triples:
            key = (triple.subject, triple.predicate, triple.object)
            
            # 如果已存在，保留置信度更高的
            if key in unique_triples:
                if triple.confidence > unique_triples[key].confidence:
                    unique_triples[key] = triple
            else:
                unique_triples[key] = triple
        
        return list(unique_triples.values())
    
    def _sort_triples_by_confidence(self, triples: List[Triple]) -> List[Triple]:
        """
        按置信度排序三元组
        
        Args:
            triples: 三元组列表
            
        Returns:
            排序后的三元组列表
        """
        return sorted(triples, key=lambda t: t.confidence, reverse=True)
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        将文本分割为句子
        
        Args:
            text: 待分割文本
            
        Returns:
            句子列表
        """
        # 简单的句子分割规则
        delimiters = ['。', '！', '？', '；', '\n']
        sentences = []
        start = 0
        
        for i, char in enumerate(text):
            if char in delimiters:
                sentence = text[start:i+1].strip()
                if sentence:
                    sentences.append(sentence)
                start = i + 1
        
        # 添加最后一个句子
        if start < len(text):
            sentence = text[start:].strip()
            if sentence:
                sentences.append(sentence)
        
        return sentences


class RelationMerger:
    """
    关系合并器
    
    合并多个来源的关系三元组
    """
    
    def __init__(self, threshold: float = 0.5) -> None:
        """
        初始化关系合并器
        
        Args:
            threshold: 相似度阈值，高于此值的三元组将被合并
        """
        self.threshold = threshold
    
    def merge(self, triples_list: List[List[Triple]]) -> List[Triple]:
        """
        合并多个三元组列表
        
        Args:
            triples_list: 三元组列表的列表，每个元素是一个三元组列表
            
        Returns:
            合并后的三元组列表
        """
        if not triples_list:
            return []
        
        # 使用第一个列表作为基准
        merged = list(triples_list[0])
        
        # 合并其他列表
        for triples in triples_list[1:]:
            for triple in triples:
                if not self._is_duplicate(triple, merged):
                    merged.append(triple)
        
        # 去重和合并相似三元组
        return self._merge_similar_triples(merged)
    
    def _is_duplicate(self, triple: Triple, triples: List[Triple]) -> bool:
        """
        检查三元组是否重复
        
        Args:
            triple: 待检查的三元组
            triples: 三元组列表
            
        Returns:
            是否重复
        """
        for t in triples:
            if (t.subject == triple.subject and
                t.predicate == triple.predicate and
                t.object == triple.object):
                return True
        return False
    
    def _merge_similar_triples(self, triples: List[Triple]) -> List[Triple]:
        """
        合并相似三元组
        
        Args:
            triples: 三元组列表
            
        Returns:
            合并后的三元组列表
        """
        if not triples:
            return []
        
        # 按主语分组
        subject_groups = defaultdict(list)
        for triple in triples:
            subject_groups[triple.subject].append(triple)
        
        merged = []
        
        # 处理每个主语组
        for subject, group in subject_groups.items():
            # 按谓语分组
            predicate_groups = defaultdict(list)
            for triple in group:
                predicate_groups[triple.predicate].append(triple)
            
            # 处理每个谓语组
            for predicate, pred_group in predicate_groups.items():
                # 合并相似宾语
                merged_objects = self._merge_similar_objects(pred_group)
                for obj, confidence in merged_objects.items():
                    merged.append(Triple(subject, predicate, obj, confidence))
        
        return merged
    
    def _merge_similar_objects(self, triples: List[Triple]) -> Dict[str, float]:
        """
        合并相似宾语
        
        Args:
            triples: 具有相同主语和谓语的三元组列表
            
        Returns:
            宾语到置信度的映射
        """
        merged_objects = {}
        
        for triple in triples:
            # 检查是否有相似宾语
            similar_found = False
            for obj in list(merged_objects.keys()):
                if self._is_similar(triple.object, obj):
                    # 选择较长的宾语
                    if len(triple.object) > len(obj):
                        # 移除旧的，添加新的
                        confidence = max(merged_objects[obj], triple.confidence)
                        del merged_objects[obj]
                        merged_objects[triple.object] = confidence
                    else:
                        # 更新置信度
                        merged_objects[obj] = max(merged_objects[obj], triple.confidence)
                    similar_found = True
                    break
            
            # 如果没有相似宾语，直接添加
            if not similar_found:
                merged_objects[triple.object] = triple.confidence
        
        return merged_objects
    
    def _is_similar(self, str1: str, str2: str) -> bool:
        """
        判断两个字符串是否相似
        
        Args:
            str1: 第一个字符串
            str2: 第二个字符串
            
        Returns:
            是否相似
        """
        # 如果一个字符串包含另一个，视为相似
        if str1 in str2 or str2 in str1:
            return True
        
        # 计算编辑距离相似度
        distance = self._levenshtein_distance(str1, str2)
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return True
        
        similarity = 1 - distance / max_len
        return similarity >= self.threshold
    
    def _levenshtein_distance(self, str1: str, str2: str) -> int:
        """
        计算两个字符串的编辑距离
        
        Args:
            str1: 第一个字符串
            str2: 第二个字符串
            
        Returns:
            编辑距离
        """
        m, n = len(str1), len(str2)
        
        # 创建距离矩阵
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # 初始化第一行和第一列
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        # 填充矩阵
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i-1] == str2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = min(dp[i-1][j-1] + 1,  # 替换
                                  dp[i][j-1] + 1,     # 插入
                                  dp[i-1][j] + 1)     # 删除
        
        return dp[m][n]


# 测试代码
if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 测试文本
    text = """
    李明是一名计算机科学专业的学生，他就读于北京大学。
    张教授认为，人工智能技术未来将广泛应用于各个领域。
    由于全球气候变暖，因此极端天气现象越来越频繁。
    该公司对所有产品进行了全面升级，并推出了新的营销策略。
    """
    
    # 创建关系增强器
    enhancer = RelationEnhancer()
    
    # 添加同义词
    enhancer.add_synonym("李明", "小明")
    enhancer.add_synonym("北京大学", "北大")
    
    # 使用模式提取三元组
    pattern_triples = enhancer.extract_triples_from_patterns(text)
    print("模式提取的三元组:")
    for triple in pattern_triples:
        print(f"  {triple}")
    
    # 模拟提取的三元组
    triples = [
        Triple("李明", "是", "学生", 0.9),
        Triple("李明", "就读于", "北京大学", 0.8),
        Triple("小明", "学习", "计算机科学", 0.7),
        Triple("张教授", "认为", "人工智能技术将广泛应用", 0.9),
        Triple("全球气候变暖", "导致", "极端天气现象", 0.8),
        Triple("该公司", "进行", "全面升级", 0.6),
        Triple("该公司", "推出", "新的营销策略", 0.7),
        Triple("该", "是", "公司", 0.4)  # 低置信度
    ]
    
    # 增强三元组
    enhanced_triples = enhancer.enhance_triples(triples)
    print("\n增强后的三元组:")
    for triple in enhanced_triples:
        print(f"  {triple} (置信度: {triple.confidence:.1f})")
    
    # 测试关系合并器
    triples1 = [
        Triple("小明", "学习", "计算机科学", 0.7),
        Triple("张教授", "研究", "人工智能", 0.8)
    ]
    
    triples2 = [
        Triple("小明", "学习", "计算机科学专业", 0.9),
        Triple("张教授", "研究", "深度学习", 0.6)
    ]
    
    merger = RelationMerger(threshold=0.6)
    merged_triples = merger.merge([triples1, triples2])
    
    print("\n合并后的三元组:")
    for triple in merged_triples:
        print(f"  {triple} (置信度: {triple.confidence:.1f})") 