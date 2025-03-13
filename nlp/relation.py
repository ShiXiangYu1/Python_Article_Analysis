"""
关系提取模块

提取句子的主谓宾结构，构建三元组关系
"""

import logging
from typing import List, Dict, Tuple, Any, Optional, Set
import json
import jieba

# 尝试导入HanLP
try:
    import pyhanlp
    HanLP = pyhanlp.JClass('com.hankcs.hanlp.HanLP')
    HANLP_AVAILABLE = True
except ImportError:
    HANLP_AVAILABLE = False

# 尝试导入LTP
try:
    import pyltp
    LTP_AVAILABLE = True
except ImportError:
    LTP_AVAILABLE = False

logger = logging.getLogger('relation')

class Triple:
    """
    三元组类，表示(主体, 谓语, 客体)的关系
    """
    
    def __init__(self, subject: str, predicate: str, object: str, confidence: float = 1.0) -> None:
        """
        初始化三元组
        
        Args:
            subject: 主体
            predicate: 谓语
            object: 客体
            confidence: 置信度
        """
        self.subject = subject
        self.predicate = predicate
        self.object = object
        self.confidence = confidence
    
    def __str__(self) -> str:
        """
        字符串表示
        """
        return f"({self.subject}, {self.predicate}, {self.object})"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        return {
            'subject': self.subject,
            'predicate': self.predicate,
            'object': self.object,
            'confidence': self.confidence
        }


class RelationExtractor:
    """
    关系提取器基类
    """
    
    def __init__(self) -> None:
        """
        初始化关系提取器
        """
        pass
    
    def extract_triples(self, text: str) -> List[Triple]:
        """
        提取文本中的三元组关系
        
        Args:
            text: 待处理文本
            
        Returns:
            三元组列表
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def batch_extract_triples(self, text_list: List[str]) -> List[List[Triple]]:
        """
        批量提取多个文本中的三元组关系
        
        Args:
            text_list: 文本列表
            
        Returns:
            每个文本的三元组列表
        """
        results = []
        for text in text_list:
            triples = self.extract_triples(text)
            results.append(triples)
        return results
    
    @staticmethod
    def split_sentences(text: str) -> List[str]:
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


class HanLPRelationExtractor(RelationExtractor):
    """
    基于HanLP的关系提取器
    """
    
    def __init__(self) -> None:
        """
        初始化HanLP关系提取器
        """
        super().__init__()
        
        if not HANLP_AVAILABLE:
            raise ImportError("HanLP未安装或无法导入，请先安装HanLP")
    
    def extract_triples(self, text: str) -> List[Triple]:
        """
        使用HanLP提取文本中的三元组关系
        
        Args:
            text: 待处理文本
            
        Returns:
            三元组列表
        """
        if not text:
            return []
        
        triples = []
        
        # 分割句子
        sentences = self.split_sentences(text)
        
        for sentence in sentences:
            sentence_triples = self._extract_sentence_triples(sentence)
            triples.extend(sentence_triples)
        
        return triples
    
    def _extract_sentence_triples(self, sentence: str) -> List[Triple]:
        """
        提取单个句子中的三元组关系
        
        Args:
            sentence: 待处理句子
            
        Returns:
            三元组列表
        """
        try:
            # 使用HanLP进行依存句法分析
            dependency_parse = HanLP.parseDependency(sentence)
            
            # 提取主谓宾关系
            return self._extract_spo_from_dependency(dependency_parse)
        except Exception as e:
            logger.error(f"使用HanLP提取三元组失败: {e}")
            return []
    
    def _extract_spo_from_dependency(self, dependency_parse) -> List[Triple]:
        """
        从依存句法分析结果中提取主谓宾三元组
        
        Args:
            dependency_parse: HanLP依存句法分析结果
            
        Returns:
            三元组列表
        """
        triples = []
        
        # 获取词和依存关系
        words = []
        for word in dependency_parse.getWordArray():
            words.append(word)
        
        # 遍历每个词，寻找动词谓语
        for word in words:
            # 谓语通常是动词
            if word.POSTAG.startswith('v'):
                predicate = word.LEMMA
                subject = None
                objects = []
                
                # 查找主语（通常依存关系为"主语"）
                for w in words:
                    if w.DEPREL == '主语' and w.HEAD.ID == word.ID:
                        subject = w.LEMMA
                        break
                
                # 查找宾语（通常依存关系为"宾语"）
                for w in words:
                    if w.DEPREL == '宾语' and w.HEAD.ID == word.ID:
                        objects.append(w.LEMMA)
                
                # 构建三元组
                if subject and objects:
                    for obj in objects:
                        triple = Triple(subject, predicate, obj)
                        triples.append(triple)
        
        return triples


class LTPRelationExtractor(RelationExtractor):
    """
    基于LTP的关系提取器
    """
    
    def __init__(self, segmentor_model: str, postagger_model: str, parser_model: str) -> None:
        """
        初始化LTP关系提取器
        
        Args:
            segmentor_model: 分词模型路径
            postagger_model: 词性标注模型路径
            parser_model: 依存句法分析模型路径
        """
        super().__init__()
        
        if not LTP_AVAILABLE:
            raise ImportError("LTP未安装或无法导入，请先安装LTP")
        
        # 加载分词模型
        self.segmentor = pyltp.Segmentor()
        try:
            self.segmentor.load(segmentor_model)
            logger.info(f"已加载LTP分词模型: {segmentor_model}")
        except Exception as e:
            raise RuntimeError(f"加载LTP分词模型失败: {e}")
        
        # 加载词性标注模型
        self.postagger = pyltp.Postagger()
        try:
            self.postagger.load(postagger_model)
            logger.info(f"已加载LTP词性标注模型: {postagger_model}")
        except Exception as e:
            self.segmentor.release()
            raise RuntimeError(f"加载LTP词性标注模型失败: {e}")
        
        # 加载依存句法分析模型
        self.parser = pyltp.Parser()
        try:
            self.parser.load(parser_model)
            logger.info(f"已加载LTP依存句法分析模型: {parser_model}")
        except Exception as e:
            self.segmentor.release()
            self.postagger.release()
            raise RuntimeError(f"加载LTP依存句法分析模型失败: {e}")
    
    def __del__(self) -> None:
        """
        释放LTP资源
        """
        if hasattr(self, 'segmentor'):
            self.segmentor.release()
        if hasattr(self, 'postagger'):
            self.postagger.release()
        if hasattr(self, 'parser'):
            self.parser.release()
    
    def extract_triples(self, text: str) -> List[Triple]:
        """
        使用LTP提取文本中的三元组关系
        
        Args:
            text: 待处理文本
            
        Returns:
            三元组列表
        """
        if not text:
            return []
        
        triples = []
        
        # 分割句子
        sentences = self.split_sentences(text)
        
        for sentence in sentences:
            sentence_triples = self._extract_sentence_triples(sentence)
            triples.extend(sentence_triples)
        
        return triples
    
    def _extract_sentence_triples(self, sentence: str) -> List[Triple]:
        """
        提取单个句子中的三元组关系
        
        Args:
            sentence: 待处理句子
            
        Returns:
            三元组列表
        """
        try:
            # LTP分词
            words = self.segmentor.segment(sentence)
            words_list = list(words)
            
            # LTP词性标注
            postags = self.postagger.postag(words_list)
            postags_list = list(postags)
            
            # LTP依存句法分析
            arcs = self.parser.parse(words_list, postags_list)
            arcs_list = list(arcs)
            
            # 提取主谓宾关系
            return self._extract_spo_from_arcs(words_list, postags_list, arcs_list)
        except Exception as e:
            logger.error(f"使用LTP提取三元组失败: {e}")
            return []
    
    def _extract_spo_from_arcs(self, words: List[str], postags: List[str], arcs: List[Any]) -> List[Triple]:
        """
        从依存句法分析结果中提取主谓宾三元组
        
        Args:
            words: 分词结果
            postags: 词性标注结果
            arcs: 依存句法分析结果
            
        Returns:
            三元组列表
        """
        triples = []
        
        for i, (word, pos, arc) in enumerate(zip(words, postags, arcs)):
            # 谓语通常是动词
            if pos.startswith('v'):
                predicate = word
                subject = None
                objects = []
                
                # 查找主语（通常依存关系为"SBV"）
                for j, dependency in enumerate(arcs):
                    if dependency.relation == 'SBV' and dependency.head == i + 1:  # 注意：依存弧的索引从1开始
                        subject = words[j]
                        break
                
                # 查找宾语（通常依存关系为"VOB"）
                for j, dependency in enumerate(arcs):
                    if dependency.relation == 'VOB' and dependency.head == i + 1:
                        objects.append(words[j])
                
                # 构建三元组
                if subject and objects:
                    for obj in objects:
                        triple = Triple(subject, predicate, obj)
                        triples.append(triple)
        
        return triples


class SimpleRuleRelationExtractor(RelationExtractor):
    """
    简单的基于规则的关系提取器，不依赖外部模型
    """
    
    def __init__(self):
        """初始化简单规则关系提取器"""
        super().__init__()
        self.segmenter = jieba
        
        # 常见谓语动词
        self.predicates = {
            '访问', '会见', '会晤', '参观', '考察', '视察', '调研', 
            '表示', '强调', '指出', '认为', '说', '表明', '宣布',
            '签署', '签订', '缔结', '达成', '同意', '批准', '通过',
            '任命', '委任', '授予', '颁发', '授权', '批准', '同意',
            '购买', '收购', '出售', '转让', '投资', '融资', '贷款',
            '研发', '生产', '制造', '销售', '推广', '发布', '上市'
        }
    
    def extract_triples(self, text: str) -> List[Triple]:
        """
        从文本中提取三元组关系
        
        Args:
            text: 输入文本
            
        Returns:
            三元组列表
        """
        if not text:
            return []
        
        # 分句
        sentences = self._split_sentences(text)
        
        # 存储提取的三元组
        triples = []
        
        # 处理每个句子
        for sentence in sentences:
            # 分词
            words = list(self.segmenter.cut(sentence))
            
            # 查找主语、谓语和宾语
            subject = None
            predicate = None
            object_ = None
            
            # 简单规则：查找第一个可能的主语、谓语和宾语
            for i, word in enumerate(words):
                # 如果找到谓语
                if word in self.predicates:
                    predicate = word
                    
                    # 尝试找主语（谓语前的词）
                    for j in range(i-1, -1, -1):
                        if len(words[j]) >= 2 and words[j] not in self.predicates:
                            subject = words[j]
                            break
                    
                    # 尝试找宾语（谓语后的词）
                    for j in range(i+1, len(words)):
                        if len(words[j]) >= 2 and words[j] not in self.predicates:
                            object_ = words[j]
                            break
                    
                    # 如果找到了完整的三元组
                    if subject and predicate and object_:
                        triple = Triple(subject, predicate, object_, confidence=0.7)
                        triples.append(triple)
                        
                        # 重置，继续查找下一个三元组
                        subject = None
                        predicate = None
                        object_ = None
        
        return triples
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        将文本分割为句子
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        # 使用常见的句子分隔符分割文本
        delimiters = ['。', '！', '？', '；', '\n']
        sentences = []
        start = 0
        
        for i, char in enumerate(text):
            if char in delimiters:
                sentence = text[start:i+1].strip()
                if sentence:
                    sentences.append(sentence)
                start = i + 1
        
        # 处理最后一个句子
        if start < len(text):
            sentence = text[start:].strip()
            if sentence:
                sentences.append(sentence)
        
        return sentences


# 工厂函数，根据需求创建关系提取器
def create_relation_extractor(extractor_type: str = 'hanlp', **kwargs) -> RelationExtractor:
    """
    创建关系提取器
    
    Args:
        extractor_type: 提取器类型，支持'hanlp'、'ltp'和'simple'
        **kwargs: 提取器特定参数
        
    Returns:
        对应类型的关系提取器实例
    """
    extractor_type = extractor_type.lower()
    
    if extractor_type == 'hanlp':
        if not HANLP_AVAILABLE:
            raise ImportError("HanLP未安装或无法导入，请先安装HanLP")
            
        return HanLPRelationExtractor()
    elif extractor_type == 'ltp':
        if not LTP_AVAILABLE:
            raise ImportError("LTP未安装或无法导入，请先安装LTP")
        
        segmentor_model = kwargs.get('segmentor_model')
        postagger_model = kwargs.get('postagger_model')
        parser_model = kwargs.get('parser_model')
        
        if not segmentor_model or not postagger_model or not parser_model:
            raise ValueError("使用LTP需要提供分词、词性标注和依存句法分析模型路径")
            
        return LTPRelationExtractor(segmentor_model, postagger_model, parser_model)
    elif extractor_type == 'simple':
        return SimpleRuleRelationExtractor()
    else:
        raise ValueError(f"不支持的关系提取器类型: {extractor_type}")


# 简单测试
if __name__ == "__main__":
    if HANLP_AVAILABLE:
        # 测试HanLP关系提取
        extractor = create_relation_extractor('hanlp')
        
        # 测试文本
        text = "李克强总理在北京人民大会堂会见了来访的美国总统特朗普。此次会谈中，双方就中美贸易问题进行了深入讨论。中国国家主席习近平访问了美国。"
        
        # 提取三元组关系
        triples = extractor.extract_triples(text)
        
        print("使用HanLP提取的三元组关系:")
        for triple in triples:
            print(triple)
    else:
        print("HanLP未安装，无法测试关系提取") 