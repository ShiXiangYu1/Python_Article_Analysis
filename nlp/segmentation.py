"""
分词处理模块

提供多种分词方式，支持jieba、HanLP和LTP等
"""

import os
import re
import logging
from typing import List, Tuple, Optional, Set, Dict, Any
from collections import defaultdict

# 第三方库导入
import jieba
# 尝试导入jieba词性标注模块
try:
    import jieba.posseg as pseg
    JIEBA_POSSEG_AVAILABLE = True
except ImportError:
    JIEBA_POSSEG_AVAILABLE = False
    logging.warning("无法导入jieba.posseg模块，词性标注功能将不可用")

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('segmentation')


class Segmenter:
    """
    分词器基类
    
    所有具体的分词器实现都应继承此类
    """
    
    def __init__(self) -> None:
        """
        初始化分词器
        """
        # 默认停用词文件路径
        self.default_stopwords_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            'data', 
            'stopwords.txt'
        )
        # 加载默认停用词
        self.stopwords = self._load_stopwords(self.default_stopwords_file)
    
    def segment(self, text: str) -> List[str]:
        """
        对文本进行分词
        
        Args:
            text: 待分词文本
            
        Returns:
            分词结果列表
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def segment_with_pos(self, text: str) -> List[Tuple[str, str]]:
        """
        对文本进行词性标注分词
        
        Args:
            text: 待分词文本
            
        Returns:
            (词语, 词性)元组列表
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def filter_stopwords(self, tokens: List[str], stopwords_file: Optional[str] = None) -> List[str]:
        """
        过滤停用词
        
        Args:
            tokens: 分词结果列表
            stopwords_file: 停用词文件路径，为None则使用默认停用词表
            
        Returns:
            过滤停用词后的分词结果
        """
        # 如果提供了新的停用词文件，则重新加载
        if stopwords_file and stopwords_file != self.default_stopwords_file:
            stopwords = self._load_stopwords(stopwords_file)
        else:
            stopwords = self.stopwords
        
        # 过滤停用词
        return [token for token in tokens if token not in stopwords]
    
    def _load_stopwords(self, stopwords_file: str) -> Set[str]:
        """
        加载停用词
        
        Args:
            stopwords_file: 停用词文件路径
            
        Returns:
            停用词集合
        """
        stopwords = set()
        
        # 创建目录（如果不存在）
        os.makedirs(os.path.dirname(stopwords_file), exist_ok=True)
        
        # 如果文件不存在，创建一个空的停用词文件
        if not os.path.exists(stopwords_file):
            with open(stopwords_file, 'w', encoding='utf-8') as f:
                f.write('# 停用词列表\n')
            logger.warning(f"停用词文件不存在，已创建空文件: {stopwords_file}")
            return stopwords
        
        # 加载停用词
        try:
            with open(stopwords_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        stopwords.add(line)
            logger.info(f"已加载 {len(stopwords)} 个停用词")
        except Exception as e:
            logger.error(f"加载停用词文件失败: {e}")
        
        return stopwords
    
    def clean_text(self, text: str) -> str:
        """
        清理文本，去除多余空白字符、特殊符号等
        
        Args:
            text: 原始文本
            
        Returns:
            清理后的文本
        """
        if not text:
            return ""
        
        # 去除HTML标签
        text = re.sub(r'<[^>]+>', ' ', text)
        # 替换多个空白字符为单个空格
        text = re.sub(r'\s+', ' ', text)
        # 去除特殊符号，但保留中文标点
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。？！：；""''（）【】《》、]', '', text)
        # 去除首尾空白
        return text.strip()


class JiebaSegmenter(Segmenter):
    """
    基于jieba的分词器
    """
    
    def __init__(self, user_dict: Optional[str] = None) -> None:
        """
        初始化jieba分词器
        
        Args:
            user_dict: 用户自定义词典路径
        """
        super().__init__()
        
        # 加载自定义词典
        if user_dict and os.path.exists(user_dict):
            try:
                jieba.load_userdict(user_dict)
                logger.info(f"已加载自定义词典: {user_dict}")
            except Exception as e:
                logger.error(f"加载自定义词典失败: {e}")
    
    def segment(self, text: str) -> List[str]:
        """
        使用jieba进行分词
        
        Args:
            text: 待分词文本
            
        Returns:
            分词结果列表
        """
        if not text:
            return []
        
        # 清理文本
        text = self.clean_text(text)
        
        # 使用jieba分词
        try:
            words = jieba.lcut(text)
            return words
        except Exception as e:
            logger.error(f"jieba分词失败: {e}")
            return []
    
    def segment_with_pos(self, text: str) -> List[Tuple[str, str]]:
        """
        使用jieba进行词性标注分词
        
        Args:
            text: 待分词文本
            
        Returns:
            (词语, 词性)元组列表
        """
        if not text:
            return []
        
        # 清理文本
        text = self.clean_text(text)
        
        # 如果没有词性标注模块，返回带有默认词性的结果
        if not JIEBA_POSSEG_AVAILABLE:
            logger.warning("jieba词性标注模块不可用，返回带默认词性'n'的结果")
            words = self.segment(text)
            return [(word, 'n') for word in words]
        
        # 使用jieba分词并标注词性
        try:
            words_pos = pseg.lcut(text)
            return [(word, pos) for word, pos in words_pos]
        except Exception as e:
            logger.error(f"jieba词性标注分词失败: {e}")
            return []


class HanLPSegmenter(Segmenter):
    """
    基于HanLP的分词器
    """
    
    def __init__(self) -> None:
        """
        初始化HanLP分词器
        """
        super().__init__()
        
        # 尝试导入pyhanlp
        try:
            from pyhanlp import HanLP
            self.HanLP = HanLP
            logger.info("已成功导入HanLP")
        except ImportError as e:
            logger.error(f"导入HanLP失败: {e}")
            logger.error("请安装pyhanlp: pip install pyhanlp，并确保JDK已安装")
            raise ImportError("无法导入HanLP，请确保安装了pyhanlp和JDK")
    
    def segment(self, text: str) -> List[str]:
        """
        使用HanLP进行分词
        
        Args:
            text: 待分词文本
            
        Returns:
            分词结果列表
        """
        if not text:
            return []
        
        # 清理文本
        text = self.clean_text(text)
        
        # 使用HanLP分词
        try:
            result = self.HanLP.segment(text)
            return [term.word for term in result]
        except Exception as e:
            logger.error(f"HanLP分词失败: {e}")
            return []
    
    def segment_with_pos(self, text: str) -> List[Tuple[str, str]]:
        """
        使用HanLP进行词性标注分词
        
        Args:
            text: 待分词文本
            
        Returns:
            (词语, 词性)元组列表
        """
        if not text:
            return []
        
        # 清理文本
        text = self.clean_text(text)
        
        # 使用HanLP分词并获取词性
        try:
            result = self.HanLP.segment(text)
            return [(term.word, str(term.nature)) for term in result]
        except Exception as e:
            logger.error(f"HanLP词性标注分词失败: {e}")
            return []


class LTPSegmenter(Segmenter):
    """
    基于LTP的分词器
    """
    
    def __init__(self, segmentor_model: str, postagger_model: str) -> None:
        """
        初始化LTP分词器
        
        Args:
            segmentor_model: 分词模型路径
            postagger_model: 词性标注模型路径
        """
        super().__init__()
        
        # 尝试导入pyltp
        try:
            import pyltp
            self.pyltp = pyltp
        except ImportError as e:
            logger.error(f"导入pyltp失败: {e}")
            logger.error("请安装pyltp: pip install pyltp")
            raise ImportError("无法导入pyltp，请确保安装了pyltp")
        
        # 初始化分词器
        try:
            self.segmentor = pyltp.Segmentor()
            if os.path.exists(segmentor_model):
                self.segmentor.load(segmentor_model)
                logger.info(f"已加载LTP分词模型: {segmentor_model}")
            else:
                logger.error(f"LTP分词模型不存在: {segmentor_model}")
                raise FileNotFoundError(f"LTP分词模型不存在: {segmentor_model}")
        except Exception as e:
            logger.error(f"初始化LTP分词器失败: {e}")
            raise RuntimeError(f"初始化LTP分词器失败: {e}")
        
        # 初始化词性标注器
        try:
            self.postagger = pyltp.Postagger()
            if os.path.exists(postagger_model):
                self.postagger.load(postagger_model)
                logger.info(f"已加载LTP词性标注模型: {postagger_model}")
            else:
                logger.error(f"LTP词性标注模型不存在: {postagger_model}")
                raise FileNotFoundError(f"LTP词性标注模型不存在: {postagger_model}")
        except Exception as e:
            logger.error(f"初始化LTP词性标注器失败: {e}")
            raise RuntimeError(f"初始化LTP词性标注器失败: {e}")
    
    def __del__(self) -> None:
        """
        释放资源
        """
        try:
            if hasattr(self, 'segmentor'):
                self.segmentor.release()
            if hasattr(self, 'postagger'):
                self.postagger.release()
        except Exception as e:
            logger.error(f"释放LTP资源失败: {e}")
    
    def segment(self, text: str) -> List[str]:
        """
        使用LTP进行分词
        
        Args:
            text: 待分词文本
            
        Returns:
            分词结果列表
        """
        if not text:
            return []
        
        # 清理文本
        text = self.clean_text(text)
        
        # 使用LTP分词
        try:
            words = list(self.segmentor.segment(text))
            return words
        except Exception as e:
            logger.error(f"LTP分词失败: {e}")
            return []
    
    def segment_with_pos(self, text: str) -> List[Tuple[str, str]]:
        """
        使用LTP进行词性标注分词
        
        Args:
            text: 待分词文本
            
        Returns:
            (词语, 词性)元组列表
        """
        if not text:
            return []
        
        # 清理文本
        text = self.clean_text(text)
        
        # 使用LTP分词
        try:
            words = list(self.segmentor.segment(text))
            
            # 词性标注
            postags = list(self.postagger.postag(words))
            
            return list(zip(words, postags))
        except Exception as e:
            logger.error(f"LTP词性标注分词失败: {e}")
            return []


def create_segmenter(segmenter_type: str = 'jieba', **kwargs) -> Segmenter:
    """
    创建分词器
    
    Args:
        segmenter_type: 分词器类型，支持 'jieba', 'hanlp', 'ltp'
        **kwargs: 额外参数
        
    Returns:
        分词器实例
    """
    segmenter_type = segmenter_type.lower()
    
    if segmenter_type == 'jieba':
        user_dict = kwargs.get('user_dict')
        return JiebaSegmenter(user_dict=user_dict)
    
    elif segmenter_type == 'hanlp':
        try:
            return HanLPSegmenter()
        except (ImportError, RuntimeError) as e:
            logger.warning(f"创建HanLP分词器失败: {e}，使用jieba作为替代")
            return JiebaSegmenter()
    
    elif segmenter_type == 'ltp':
        segmentor_model = kwargs.get('segmentor_model')
        postagger_model = kwargs.get('postagger_model')
        
        if not segmentor_model or not postagger_model:
            logger.error("使用LTP分词器需要提供模型路径")
            logger.warning("使用jieba作为替代")
            return JiebaSegmenter()
        
        try:
            return LTPSegmenter(segmentor_model, postagger_model)
        except (ImportError, FileNotFoundError, RuntimeError) as e:
            logger.warning(f"创建LTP分词器失败: {e}，使用jieba作为替代")
            return JiebaSegmenter()
    
    else:
        logger.warning(f"不支持的分词器类型: {segmenter_type}，使用jieba作为替代")
        return JiebaSegmenter()


# 测试代码
if __name__ == "__main__":
    # 测试文本
    text = "自然语言处理是计算机科学领域与人工智能领域中的一个重要方向。"
    
    # 测试jieba分词器
    jieba_segmenter = create_segmenter('jieba')
    jieba_result = jieba_segmenter.segment(text)
    jieba_pos_result = jieba_segmenter.segment_with_pos(text)
    
    print("Jieba分词结果:")
    print(jieba_result)
    print("\nJieba词性标注结果:")
    print(jieba_pos_result)
    
    # 尝试测试HanLP分词器
    try:
        hanlp_segmenter = create_segmenter('hanlp')
        hanlp_result = hanlp_segmenter.segment(text)
        hanlp_pos_result = hanlp_segmenter.segment_with_pos(text)
        
        print("\nHanLP分词结果:")
        print(hanlp_result)
        print("\nHanLP词性标注结果:")
        print(hanlp_pos_result)
    except Exception as e:
        print(f"\nHanLP测试失败: {e}") 