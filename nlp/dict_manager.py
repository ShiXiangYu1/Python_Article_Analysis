"""
词典管理模块

提供自定义词典的加载、添加、删除和管理功能，支持多种分词工具的词典统一管理
"""

import os
import json
import logging
from typing import Dict, List, Set, Optional, Tuple, Any
import re

# 设置日志
logger = logging.getLogger('dict_manager')

class DictManager:
    """
    词典管理器
    
    提供自定义词典的统一管理，支持多种分词工具
    """
    
    def __init__(self, dict_dir: str = None, user_dict_file: str = None) -> None:
        """
        初始化词典管理器
        
        Args:
            dict_dir: 词典目录，默认为'nlp/data/dict'
            user_dict_file: 用户词典文件，默认为'user_dict.txt'
        """
        # 词典目录
        if dict_dir:
            self.dict_dir = dict_dir
        else:
            # 默认使用模块所在目录下的data/dict目录
            self.dict_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'nlp', 'data', 'dict'
            )
        
        # 确保目录存在
        os.makedirs(self.dict_dir, exist_ok=True)
        
        # 用户词典文件
        self.user_dict_file = user_dict_file or 'user_dict.txt'
        self.user_dict_path = os.path.join(self.dict_dir, self.user_dict_file)
        
        # 词典类别
        self.dict_categories = {
            'custom': set(),   # 自定义词
            'person': set(),   # 人名
            'place': set(),    # 地名
            'organization': set(),  # 组织机构名
            'time': set(),     # 时间词
            'industry': set(), # 行业术语
            'stop': set()      # 停用词
        }
        
        # 词频和词性映射
        self.word_attrs = {}  # {'word': {'freq': 100, 'pos': 'n'}}
        
        # 加载用户词典
        self.load_dict()
    
    def load_dict(self) -> None:
        """
        加载词典
        """
        # 加载用户词典
        if os.path.exists(self.user_dict_path):
            try:
                with open(self.user_dict_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        parts = line.split()
                        word = parts[0]
                        
                        # 解析词性和频率
                        pos = 'n'  # 默认词性为名词
                        freq = 100  # 默认词频
                        category = 'custom'  # 默认分类
                        
                        if len(parts) > 1:
                            # 解析词性
                            for p in parts[1:]:
                                if p.startswith('pos='):
                                    pos = p[4:]
                                elif p.startswith('freq='):
                                    try:
                                        freq = int(p[5:])
                                    except ValueError:
                                        pass
                                elif p.startswith('category='):
                                    category = p[9:]
                        
                        # 添加到词典
                        if category in self.dict_categories:
                            self.dict_categories[category].add(word)
                        else:
                            self.dict_categories['custom'].add(word)
                        
                        # 记录词性和词频
                        self.word_attrs[word] = {'pos': pos, 'freq': freq}
                
                logger.info(f"已加载用户词典: {self.user_dict_path}")
            except Exception as e:
                logger.error(f"加载用户词典失败: {e}")
        else:
            logger.warning(f"用户词典不存在: {self.user_dict_path}，将创建新词典")
            # 创建空的用户词典文件
            with open(self.user_dict_path, 'w', encoding='utf-8') as f:
                f.write("# 自定义词典\n")
                f.write("# 格式: 词语 [pos=词性] [freq=词频] [category=分类]\n")
                f.write("# 示例: 自然语言处理 pos=nl freq=1000 category=industry\n")
    
    def save_dict(self) -> None:
        """
        保存词典
        """
        try:
            with open(self.user_dict_path, 'w', encoding='utf-8') as f:
                f.write("# 自定义词典\n")
                f.write("# 格式: 词语 [pos=词性] [freq=词频] [category=分类]\n")
                f.write("# 示例: 自然语言处理 pos=nl freq=1000 category=industry\n\n")
                
                # 按类别写入词典
                for category, words in self.dict_categories.items():
                    if words:
                        f.write(f"# {category} 类别\n")
                        for word in sorted(words):
                            # 获取词性和词频
                            attrs = self.word_attrs.get(word, {'pos': 'n', 'freq': 100})
                            f.write(f"{word} pos={attrs['pos']} freq={attrs['freq']} category={category}\n")
                        f.write("\n")
                
                logger.info(f"已保存用户词典: {self.user_dict_path}")
        except Exception as e:
            logger.error(f"保存用户词典失败: {e}")
    
    def add_word(self, word: str, pos: str = 'n', freq: int = 100, category: str = 'custom') -> bool:
        """
        添加词语到词典
        
        Args:
            word: 词语
            pos: 词性，默认为'n'(名词)
            freq: 词频，默认为100
            category: 词语类别，默认为'custom'
            
        Returns:
            是否添加成功
        """
        if not word or not word.strip():
            logger.warning("词语不能为空")
            return False
        
        word = word.strip()
        
        # 检查类别是否有效
        if category not in self.dict_categories:
            logger.warning(f"无效的词语类别: {category}，使用默认类别'custom'")
            category = 'custom'
        
        # 删除可能已存在于其他类别的词语
        for cat in self.dict_categories:
            if word in self.dict_categories[cat]:
                self.dict_categories[cat].remove(word)
        
        # 添加到指定类别
        self.dict_categories[category].add(word)
        
        # 记录词性和词频
        self.word_attrs[word] = {'pos': pos, 'freq': freq}
        
        logger.info(f"已添加词语: {word} (pos={pos}, freq={freq}, category={category})")
        return True
    
    def add_words(self, words: List[Dict[str, Any]]) -> int:
        """
        批量添加词语到词典
        
        Args:
            words: 词语列表，每个词语是一个字典，包含'word', 'pos', 'freq', 'category'字段
            
        Returns:
            成功添加的词语数量
        """
        success_count = 0
        for word_dict in words:
            if 'word' in word_dict:
                pos = word_dict.get('pos', 'n')
                freq = word_dict.get('freq', 100)
                category = word_dict.get('category', 'custom')
                
                if self.add_word(word_dict['word'], pos, freq, category):
                    success_count += 1
        
        logger.info(f"批量添加词语: 成功 {success_count}/{len(words)}")
        return success_count
    
    def remove_word(self, word: str) -> bool:
        """
        从词典删除词语
        
        Args:
            word: 词语
            
        Returns:
            是否删除成功
        """
        if not word or not word.strip():
            logger.warning("词语不能为空")
            return False
        
        word = word.strip()
        removed = False
        
        # 从所有类别中删除词语
        for category in self.dict_categories:
            if word in self.dict_categories[category]:
                self.dict_categories[category].remove(word)
                removed = True
        
        # 删除词性和词频记录
        if word in self.word_attrs:
            del self.word_attrs[word]
        
        if removed:
            logger.info(f"已删除词语: {word}")
        else:
            logger.warning(f"词语不存在: {word}")
        
        return removed
    
    def get_words_by_category(self, category: str) -> List[str]:
        """
        获取指定类别的所有词语
        
        Args:
            category: 词语类别
            
        Returns:
            词语列表
        """
        if category not in self.dict_categories:
            logger.warning(f"无效的词语类别: {category}")
            return []
        
        return sorted(list(self.dict_categories[category]))
    
    def get_all_words(self) -> Dict[str, List[str]]:
        """
        获取所有词语
        
        Returns:
            按类别分类的词语字典
        """
        return {category: sorted(list(words)) for category, words in self.dict_categories.items()}
    
    def export_jieba_dict(self, output_file: str = None) -> str:
        """
        导出为jieba词典格式
        
        Args:
            output_file: 输出文件路径，默认为'jieba_dict.txt'
            
        Returns:
            导出的文件路径
        """
        output_file = output_file or os.path.join(self.dict_dir, 'jieba_dict.txt')
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for category, words in self.dict_categories.items():
                    for word in sorted(words):
                        # 跳过停用词
                        if category == 'stop':
                            continue
                        
                        # 获取词性和词频
                        attrs = self.word_attrs.get(word, {'pos': 'n', 'freq': 100})
                        f.write(f"{word} {attrs['freq']} {attrs['pos']}\n")
                
            logger.info(f"已导出jieba词典: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"导出jieba词典失败: {e}")
            return ""
    
    def export_stopwords(self, output_file: str = None) -> str:
        """
        导出停用词
        
        Args:
            output_file: 输出文件路径，默认为'stopwords.txt'
            
        Returns:
            导出的文件路径
        """
        output_file = output_file or os.path.join(self.dict_dir, 'stopwords.txt')
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# 停用词表\n")
                for word in sorted(self.dict_categories['stop']):
                    f.write(f"{word}\n")
                
            logger.info(f"已导出停用词: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"导出停用词失败: {e}")
            return ""
    
    def import_words_from_file(self, file_path: str, category: str = 'custom') -> int:
        """
        从文件导入词语
        
        Args:
            file_path: 文件路径
            category: 导入的词语类别，默认为'custom'
            
        Returns:
            导入的词语数量
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return 0
        
        if category not in self.dict_categories:
            logger.warning(f"无效的词语类别: {category}，使用默认类别'custom'")
            category = 'custom'
        
        count = 0
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split()
                    word = parts[0]
                    
                    # 解析词性和频率
                    pos = 'n'  # 默认词性为名词
                    freq = 100  # 默认词频
                    
                    if len(parts) > 1 and parts[1].isdigit():
                        freq = int(parts[1])
                    
                    if len(parts) > 2:
                        pos = parts[2]
                    
                    # 添加到词典
                    if self.add_word(word, pos, freq, category):
                        count += 1
            
            logger.info(f"从文件 {file_path} 导入了 {count} 个词语")
            return count
        except Exception as e:
            logger.error(f"从文件导入词语失败: {e}")
            return 0
    
    def build_custom_dict_for_segmenter(self, segmenter_type: str) -> str:
        """
        为指定分词器构建自定义词典
        
        Args:
            segmenter_type: 分词器类型，支持'jieba', 'hanlp', 'ltp'
            
        Returns:
            构建的词典文件路径
        """
        segmenter_type = segmenter_type.lower()
        
        if segmenter_type == 'jieba':
            return self.export_jieba_dict()
        elif segmenter_type == 'hanlp':
            # HanLP使用相同格式，但可能需要不同文件名
            return self.export_jieba_dict(os.path.join(self.dict_dir, 'hanlp_dict.txt'))
        elif segmenter_type == 'ltp':
            # LTP可能使用不同格式，此处简化处理
            return self.export_jieba_dict(os.path.join(self.dict_dir, 'ltp_dict.txt'))
        else:
            logger.warning(f"不支持的分词器类型: {segmenter_type}")
            return ""


# 测试代码
if __name__ == "__main__":
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 创建词典管理器
    dict_manager = DictManager()
    
    # 添加一些测试词语
    dict_manager.add_word("自然语言处理", "nl", 1000, "industry")
    dict_manager.add_word("机器学习", "nl", 900, "industry")
    dict_manager.add_word("深度学习", "nl", 800, "industry")
    dict_manager.add_word("人工智能", "n", 1200, "industry")
    
    dict_manager.add_word("北京大学", "ni", 800, "organization")
    dict_manager.add_word("清华大学", "ni", 800, "organization")
    
    dict_manager.add_word("的", "u", 10000, "stop")
    dict_manager.add_word("了", "u", 9000, "stop")
    dict_manager.add_word("是", "v", 8000, "stop")
    
    # 保存词典
    dict_manager.save_dict()
    
    # 导出jieba词典
    dict_manager.export_jieba_dict()
    
    # 导出停用词
    dict_manager.export_stopwords()
    
    # 打印所有词语
    all_words = dict_manager.get_all_words()
    print("所有词语:")
    for category, words in all_words.items():
        if words:
            print(f"  {category}: {', '.join(words)}") 