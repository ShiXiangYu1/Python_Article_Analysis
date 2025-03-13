"""
实体识别模块

使用HanLP或LTP提取文章中的实体要素
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
import jieba

# 尝试导入HanLP
try:
    import pyhanlp
    HanLP = pyhanlp.JClass('com.hankcs.hanlp.HanLP')
    CustomDictionary = pyhanlp.JClass('com.hankcs.hanlp.dictionary.CustomDictionary')
    HANLP_AVAILABLE = True
except ImportError:
    HANLP_AVAILABLE = False

# 尝试导入LTP
try:
    import pyltp
    LTP_AVAILABLE = True
except ImportError:
    LTP_AVAILABLE = False

logger = logging.getLogger('entity')

class EntityExtractor:
    """
    实体提取器基类
    """
    
    def __init__(self) -> None:
        """
        初始化实体提取器
        """
        pass
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        提取文本中的实体
        
        Args:
            text: 待处理文本
            
        Returns:
            按实体类型分类的实体列表字典
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def batch_extract_entities(self, text_list: List[str]) -> List[Dict[str, List[str]]]:
        """
        批量提取多个文本中的实体
        
        Args:
            text_list: 文本列表
            
        Returns:
            每个文本的实体字典列表
        """
        results = []
        for text in text_list:
            entities = self.extract_entities(text)
            results.append(entities)
        return results


class HanLPEntityExtractor(EntityExtractor):
    """
    基于HanLP的实体提取器
    """
    
    def __init__(self, user_dict: Optional[str] = None) -> None:
        """
        初始化HanLP实体提取器
        
        Args:
            user_dict: 用户自定义词典路径
        """
        super().__init__()
        
        if not HANLP_AVAILABLE:
            raise ImportError("HanLP未安装或无法导入，请先安装HanLP")
        
        # 加载用户词典
        if user_dict:
            try:
                with open(user_dict, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip().split()[0]
                        CustomDictionary.add(word)
                logger.info(f"已加载用户词典: {user_dict}")
            except Exception as e:
                logger.warning(f"加载用户词典失败: {e}")
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        使用HanLP提取文本中的实体
        
        Args:
            text: 待处理文本
            
        Returns:
            按实体类型分类的实体列表字典
        """
        if not text:
            return {}
        
        # 初始化结果字典
        entities = {
            'person': [],     # 人名
            'place': [],      # 地名
            'organization': [] # 组织机构名
        }
        
        try:
            # 使用HanLP命名实体识别
            term_list = HanLP.segment(text)
            
            # 提取实体
            for term in term_list:
                nature = str(term.nature)
                word = term.word
                
                # 人名
                if nature == 'nr' or nature == 'nrj' or nature == 'nrf':
                    if word not in entities['person']:
                        entities['person'].append(word)
                # 地名
                elif nature == 'ns' or nature == 'nsf':
                    if word not in entities['place']:
                        entities['place'].append(word)
                # 组织机构名
                elif nature == 'nt' or nature == 'ntc' or nature == 'ntcf' or nature == 'nto' or nature == 'ntu' or nature == 'nts':
                    if word not in entities['organization']:
                        entities['organization'].append(word)
            
            return entities
        except Exception as e:
            logger.error(f"使用HanLP提取实体失败: {e}")
            return entities


class LTPEntityExtractor(EntityExtractor):
    """
    基于LTP的实体提取器
    """
    
    def __init__(self, segmentor_model: str, postagger_model: str, ner_model: str) -> None:
        """
        初始化LTP实体提取器
        
        Args:
            segmentor_model: 分词模型路径
            postagger_model: 词性标注模型路径
            ner_model: 命名实体识别模型路径
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
        
        # 加载命名实体识别模型
        self.recognizer = pyltp.NamedEntityRecognizer()
        try:
            self.recognizer.load(ner_model)
            logger.info(f"已加载LTP命名实体识别模型: {ner_model}")
        except Exception as e:
            self.segmentor.release()
            self.postagger.release()
            raise RuntimeError(f"加载LTP命名实体识别模型失败: {e}")
    
    def __del__(self) -> None:
        """
        释放LTP资源
        """
        if hasattr(self, 'segmentor'):
            self.segmentor.release()
        if hasattr(self, 'postagger'):
            self.postagger.release()
        if hasattr(self, 'recognizer'):
            self.recognizer.release()
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        使用LTP提取文本中的实体
        
        Args:
            text: 待处理文本
            
        Returns:
            按实体类型分类的实体列表字典
        """
        if not text:
            return {}
        
        # 初始化结果字典
        entities = {
            'person': [],     # 人名
            'place': [],      # 地名
            'organization': [] # 组织机构名
        }
        
        try:
            # LTP分词
            words = self.segmentor.segment(text)
            words_list = list(words)
            
            # LTP词性标注
            postags = self.postagger.postag(words_list)
            postags_list = list(postags)
            
            # LTP命名实体识别
            netags = self.recognizer.recognize(words_list, postags_list)
            netags_list = list(netags)
            
            # 提取实体
            i = 0
            while i < len(words_list):
                # 人名 (Nh)
                if netags_list[i] == 'S-Nh':
                    if words_list[i] not in entities['person']:
                        entities['person'].append(words_list[i])
                    i += 1
                elif netags_list[i] == 'B-Nh':
                    j = i + 1
                    person_name = words_list[i]
                    while j < len(words_list) and (netags_list[j] == 'I-Nh' or netags_list[j] == 'E-Nh'):
                        person_name += words_list[j]
                        j += 1
                    if person_name not in entities['person']:
                        entities['person'].append(person_name)
                    i = j
                # 地名 (Ns)
                elif netags_list[i] == 'S-Ns':
                    if words_list[i] not in entities['place']:
                        entities['place'].append(words_list[i])
                    i += 1
                elif netags_list[i] == 'B-Ns':
                    j = i + 1
                    place_name = words_list[i]
                    while j < len(words_list) and (netags_list[j] == 'I-Ns' or netags_list[j] == 'E-Ns'):
                        place_name += words_list[j]
                        j += 1
                    if place_name not in entities['place']:
                        entities['place'].append(place_name)
                    i = j
                # 组织机构名 (Ni)
                elif netags_list[i] == 'S-Ni':
                    if words_list[i] not in entities['organization']:
                        entities['organization'].append(words_list[i])
                    i += 1
                elif netags_list[i] == 'B-Ni':
                    j = i + 1
                    org_name = words_list[i]
                    while j < len(words_list) and (netags_list[j] == 'I-Ni' or netags_list[j] == 'E-Ni'):
                        org_name += words_list[j]
                        j += 1
                    if org_name not in entities['organization']:
                        entities['organization'].append(org_name)
                    i = j
                else:
                    i += 1
            
            return entities
        except Exception as e:
            logger.error(f"使用LTP提取实体失败: {e}")
            return entities


class SimpleRuleEntityExtractor(EntityExtractor):
    """
    简单的基于规则的实体提取器，不依赖外部模型
    """
    
    def __init__(self):
        """初始化简单规则实体提取器"""
        super().__init__()
        self.segmenter = jieba
        
        # 加载常见地点、人名、组织机构名词典
        self.locations = set()
        self.persons = set()
        self.organizations = set()
        
        # 尝试加载词典
        try:
            with open('data/dictionaries/locations.txt', 'r', encoding='utf-8') as f:
                self.locations = set([line.strip() for line in f if line.strip()])
        except:
            logger.warning("无法加载地点词典，将使用空词典")
            
        try:
            with open('data/dictionaries/persons.txt', 'r', encoding='utf-8') as f:
                self.persons = set([line.strip() for line in f if line.strip()])
        except:
            logger.warning("无法加载人名词典，将使用空词典")
            
        try:
            with open('data/dictionaries/organizations.txt', 'r', encoding='utf-8') as f:
                self.organizations = set([line.strip() for line in f if line.strip()])
        except:
            logger.warning("无法加载组织机构词典，将使用空词典")
        
        # 添加一些常见地点、人名和组织机构
        self.locations.update(['北京', '上海', '广州', '深圳', '杭州', '南京', '武汉', '成都', '重庆', '天津'])
        self.persons.update(['习近平', '李克强', '王岐山', '马云', '马化腾', '李彦宏', '雷军'])
        self.organizations.update(['中国', '美国', '日本', '俄罗斯', '联合国', '世界卫生组织', '阿里巴巴', '腾讯', '百度', '华为'])
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        从文本中提取实体
        
        Args:
            text: 输入文本
            
        Returns:
            实体字典，格式为 {实体类型: [实体列表]}
        """
        if not text:
            return {'LOC': [], 'PER': [], 'ORG': []}
        
        # 分词
        words = self.segmenter.cut(text)
        words_list = list(words)
        
        # 提取实体
        locations = []
        persons = []
        organizations = []
        
        # 基于词典匹配
        for word in words_list:
            if word in self.locations:
                locations.append(word)
            if word in self.persons:
                persons.append(word)
            if word in self.organizations:
                organizations.append(word)
        
        # 去重
        locations = list(set(locations))
        persons = list(set(persons))
        organizations = list(set(organizations))
        
        return {
            'LOC': locations,
            'PER': persons,
            'ORG': organizations
        }


# 工厂函数，根据需求创建实体提取器
def create_entity_extractor(extractor_type: str = 'hanlp', **kwargs) -> EntityExtractor:
    """
    创建实体提取器
    
    Args:
        extractor_type: 提取器类型，支持'hanlp'、'ltp'和'simple'
        **kwargs: 提取器特定参数
        
    Returns:
        对应类型的实体提取器实例
    """
    extractor_type = extractor_type.lower()
    
    if extractor_type == 'hanlp':
        if not HANLP_AVAILABLE:
            raise ImportError("HanLP未安装或无法导入，请先安装HanLP")
        
        user_dict = kwargs.get('user_dict')
        return HanLPEntityExtractor(user_dict)
    elif extractor_type == 'ltp':
        if not LTP_AVAILABLE:
            raise ImportError("LTP未安装或无法导入，请先安装LTP")
        
        segmentor_model = kwargs.get('segmentor_model')
        postagger_model = kwargs.get('postagger_model')
        ner_model = kwargs.get('ner_model')
        
        if not segmentor_model or not postagger_model or not ner_model:
            raise ValueError("使用LTP需要提供分词、词性标注和命名实体识别模型路径")
            
        return LTPEntityExtractor(segmentor_model, postagger_model, ner_model)
    elif extractor_type == 'simple':
        return SimpleRuleEntityExtractor()
    else:
        raise ValueError(f"不支持的实体提取器类型: {extractor_type}")


# 简单测试
if __name__ == "__main__":
    if HANLP_AVAILABLE:
        # 测试HanLP实体提取
        extractor = create_entity_extractor('hanlp')
        
        # 测试文本
        text = "李克强总理在北京人民大会堂会见了来访的美国总统特朗普。此次会谈中，双方就中美贸易问题进行了深入讨论。"
        
        # 提取实体
        entities = extractor.extract_entities(text)
        
        print("使用HanLP提取的实体:")
        for entity_type, entity_list in entities.items():
            print(f"{entity_type}: {', '.join(entity_list)}")
    else:
        print("HanLP未安装，无法测试实体提取")