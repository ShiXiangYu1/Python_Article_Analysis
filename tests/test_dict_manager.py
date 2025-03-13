#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试词典管理模块

测试词典管理器的所有功能和边界条件
"""

import unittest
import os
import shutil
import tempfile
from nlp.dict_manager import DictManager

class TestDictManager(unittest.TestCase):
    """测试词典管理器类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        self.dict_manager = DictManager(dict_dir=self.test_dir)
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时目录
        shutil.rmtree(self.test_dir)
    
    def test_init(self):
        """测试初始化"""
        # 检查默认值
        self.assertEqual(self.dict_manager.dict_dir, self.test_dir)
        self.assertEqual(self.dict_manager.user_dict_file, 'user_dict.txt')
        self.assertEqual(self.dict_manager.user_dict_path, os.path.join(self.test_dir, 'user_dict.txt'))
        
        # 检查目录是否已创建
        self.assertTrue(os.path.exists(self.test_dir))
        
        # 检查用户词典文件是否已创建
        self.assertTrue(os.path.exists(self.dict_manager.user_dict_path))
        
        # 检查默认类别
        self.assertIn('custom', self.dict_manager.dict_categories)
        self.assertIn('person', self.dict_manager.dict_categories)
        self.assertIn('place', self.dict_manager.dict_categories)
        self.assertIn('organization', self.dict_manager.dict_categories)
        self.assertIn('time', self.dict_manager.dict_categories)
        self.assertIn('industry', self.dict_manager.dict_categories)
        self.assertIn('stop', self.dict_manager.dict_categories)
    
    def test_add_word(self):
        """测试添加词语"""
        # 添加正常词语
        self.assertTrue(self.dict_manager.add_word("测试词语", "n", 100, "custom"))
        self.assertIn("测试词语", self.dict_manager.dict_categories['custom'])
        self.assertEqual(self.dict_manager.word_attrs["测试词语"], {'pos': 'n', 'freq': 100})
        
        # 添加到不同类别
        self.assertTrue(self.dict_manager.add_word("北京", "ns", 200, "place"))
        self.assertIn("北京", self.dict_manager.dict_categories['place'])
        self.assertEqual(self.dict_manager.word_attrs["北京"], {'pos': 'ns', 'freq': 200})
        
        # 添加到无效类别（应该添加到默认类别'custom'）
        self.assertTrue(self.dict_manager.add_word("无效类别", "n", 100, "invalid"))
        self.assertIn("无效类别", self.dict_manager.dict_categories['custom'])
        
        # 添加空词语（应该失败）
        self.assertFalse(self.dict_manager.add_word("", "n", 100, "custom"))
        self.assertFalse(self.dict_manager.add_word(None, "n", 100, "custom"))
        
        # 添加已存在但类别不同的词语（应该更新类别）
        self.assertTrue(self.dict_manager.add_word("北京", "ns", 300, "custom"))
        self.assertNotIn("北京", self.dict_manager.dict_categories['place'])
        self.assertIn("北京", self.dict_manager.dict_categories['custom'])
        self.assertEqual(self.dict_manager.word_attrs["北京"], {'pos': 'ns', 'freq': 300})
    
    def test_add_words(self):
        """测试批量添加词语"""
        # 批量添加正常词语
        words = [
            {'word': '词语1', 'pos': 'n', 'freq': 100, 'category': 'custom'},
            {'word': '词语2', 'pos': 'v', 'freq': 200, 'category': 'custom'},
            {'word': '词语3', 'pos': 'adj', 'freq': 300, 'category': 'custom'}
        ]
        self.assertEqual(self.dict_manager.add_words(words), 3)
        self.assertIn('词语1', self.dict_manager.dict_categories['custom'])
        self.assertIn('词语2', self.dict_manager.dict_categories['custom'])
        self.assertIn('词语3', self.dict_manager.dict_categories['custom'])
        
        # 批量添加含有空词语
        words = [
            {'word': '词语4', 'pos': 'n', 'freq': 100, 'category': 'custom'},
            {'word': '', 'pos': 'v', 'freq': 200, 'category': 'custom'},
            {'word': '词语5', 'pos': 'adj', 'freq': 300, 'category': 'custom'}
        ]
        self.assertEqual(self.dict_manager.add_words(words), 2)
        self.assertIn('词语4', self.dict_manager.dict_categories['custom'])
        self.assertIn('词语5', self.dict_manager.dict_categories['custom'])
        
        # 批量添加含有缺失字段的词语
        words = [
            {'word': '词语6'},
            {'pos': 'v', 'freq': 200, 'category': 'custom'},  # 缺少word字段
            {'word': '词语7', 'category': 'place'}  # 缺少pos和freq字段
        ]
        self.assertEqual(self.dict_manager.add_words(words), 2)
        self.assertIn('词语6', self.dict_manager.dict_categories['custom'])
        self.assertIn('词语7', self.dict_manager.dict_categories['place'])
    
    def test_remove_word(self):
        """测试删除词语"""
        # 添加测试词语
        self.dict_manager.add_word("待删除词语", "n", 100, "custom")
        
        # 删除存在的词语
        self.assertTrue(self.dict_manager.remove_word("待删除词语"))
        self.assertNotIn("待删除词语", self.dict_manager.dict_categories['custom'])
        self.assertNotIn("待删除词语", self.dict_manager.word_attrs)
        
        # 删除不存在的词语
        self.assertFalse(self.dict_manager.remove_word("不存在词语"))
        
        # 删除空词语
        self.assertFalse(self.dict_manager.remove_word(""))
        self.assertFalse(self.dict_manager.remove_word(None))
    
    def test_get_words_by_category(self):
        """测试获取指定类别的词语"""
        # 添加测试词语
        self.dict_manager.add_word("测试词语1", "n", 100, "custom")
        self.dict_manager.add_word("测试词语2", "n", 100, "custom")
        self.dict_manager.add_word("北京", "ns", 200, "place")
        self.dict_manager.add_word("上海", "ns", 200, "place")
        
        # 获取有效类别的词语
        custom_words = self.dict_manager.get_words_by_category("custom")
        self.assertEqual(len(custom_words), 2)
        self.assertIn("测试词语1", custom_words)
        self.assertIn("测试词语2", custom_words)
        
        place_words = self.dict_manager.get_words_by_category("place")
        self.assertEqual(len(place_words), 2)
        self.assertIn("北京", place_words)
        self.assertIn("上海", place_words)
        
        # 获取无效类别的词语
        invalid_words = self.dict_manager.get_words_by_category("invalid")
        self.assertEqual(len(invalid_words), 0)
    
    def test_get_all_words(self):
        """测试获取所有词语"""
        # 添加测试词语
        self.dict_manager.add_word("测试词语1", "n", 100, "custom")
        self.dict_manager.add_word("北京", "ns", 200, "place")
        self.dict_manager.add_word("清华大学", "ni", 300, "organization")
        
        # 获取所有词语
        all_words = self.dict_manager.get_all_words()
        
        # 检查是否包含所有类别
        self.assertEqual(len(all_words), 7)  # 7个预定义类别
        
        # 检查词语是否正确分类
        self.assertIn("测试词语1", all_words['custom'])
        self.assertIn("北京", all_words['place'])
        self.assertIn("清华大学", all_words['organization'])
    
    def test_save_and_load_dict(self):
        """测试保存和加载词典"""
        # 添加测试词语
        self.dict_manager.add_word("测试词语1", "n", 100, "custom")
        self.dict_manager.add_word("北京", "ns", 200, "place")
        self.dict_manager.add_word("清华大学", "ni", 300, "organization")
        
        # 保存词典
        self.dict_manager.save_dict()
        
        # 创建新的词典管理器，加载已保存的词典
        new_dict_manager = DictManager(dict_dir=self.test_dir)
        
        # 检查是否成功加载
        all_words = new_dict_manager.get_all_words()
        self.assertIn("测试词语1", all_words['custom'])
        self.assertIn("北京", all_words['place'])
        self.assertIn("清华大学", all_words['organization'])
        
        # 检查词性和词频是否正确加载
        self.assertEqual(new_dict_manager.word_attrs["测试词语1"], {'pos': 'n', 'freq': 100})
        self.assertEqual(new_dict_manager.word_attrs["北京"], {'pos': 'ns', 'freq': 200})
        self.assertEqual(new_dict_manager.word_attrs["清华大学"], {'pos': 'ni', 'freq': 300})
    
    def test_export_jieba_dict(self):
        """测试导出jieba词典"""
        # 添加测试词语
        self.dict_manager.add_word("测试词语1", "n", 100, "custom")
        self.dict_manager.add_word("北京", "ns", 200, "place")
        self.dict_manager.add_word("的", "u", 10000, "stop")
        
        # 导出jieba词典
        jieba_dict_path = self.dict_manager.export_jieba_dict()
        
        # 检查文件是否存在
        self.assertTrue(os.path.exists(jieba_dict_path))
        
        # 检查文件内容
        with open(jieba_dict_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 应该包含非停用词
            self.assertIn("测试词语1 100 n", content)
            self.assertIn("北京 200 ns", content)
            # 不应该包含停用词
            self.assertNotIn("的", content)
    
    def test_export_stopwords(self):
        """测试导出停用词"""
        # 添加测试停用词
        self.dict_manager.add_word("的", "u", 10000, "stop")
        self.dict_manager.add_word("了", "u", 9000, "stop")
        
        # 导出停用词
        stopwords_path = self.dict_manager.export_stopwords()
        
        # 检查文件是否存在
        self.assertTrue(os.path.exists(stopwords_path))
        
        # 检查文件内容
        with open(stopwords_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("的", content)
            self.assertIn("了", content)
    
    def test_import_words_from_file(self):
        """测试从文件导入词语"""
        # 创建测试词典文件
        test_dict_path = os.path.join(self.test_dir, 'test_dict.txt')
        with open(test_dict_path, 'w', encoding='utf-8') as f:
            f.write("# 测试词典\n")
            f.write("测试词语1 100 n\n")
            f.write("测试词语2 200 v\n")
            f.write("测试词语3 300 adj\n")
        
        # 导入词语
        count = self.dict_manager.import_words_from_file(test_dict_path, 'custom')
        
        # 检查导入结果
        self.assertEqual(count, 3)
        self.assertIn("测试词语1", self.dict_manager.dict_categories['custom'])
        self.assertIn("测试词语2", self.dict_manager.dict_categories['custom'])
        self.assertIn("测试词语3", self.dict_manager.dict_categories['custom'])
        
        # 导入不存在的文件
        count = self.dict_manager.import_words_from_file('not_exist.txt')
        self.assertEqual(count, 0)
    
    def test_build_custom_dict_for_segmenter(self):
        """测试为分词器构建自定义词典"""
        # 添加测试词语
        self.dict_manager.add_word("测试词语1", "n", 100, "custom")
        self.dict_manager.add_word("测试词语2", "v", 200, "custom")
        
        # 为jieba构建词典
        jieba_dict_path = self.dict_manager.build_custom_dict_for_segmenter('jieba')
        self.assertTrue(os.path.exists(jieba_dict_path))
        self.assertEqual(jieba_dict_path, os.path.join(self.test_dir, 'jieba_dict.txt'))
        
        # 为hanlp构建词典
        hanlp_dict_path = self.dict_manager.build_custom_dict_for_segmenter('hanlp')
        self.assertTrue(os.path.exists(hanlp_dict_path))
        self.assertEqual(hanlp_dict_path, os.path.join(self.test_dir, 'hanlp_dict.txt'))
        
        # 为ltp构建词典
        ltp_dict_path = self.dict_manager.build_custom_dict_for_segmenter('ltp')
        self.assertTrue(os.path.exists(ltp_dict_path))
        self.assertEqual(ltp_dict_path, os.path.join(self.test_dir, 'ltp_dict.txt'))
        
        # 为不支持的分词器构建词典
        invalid_dict_path = self.dict_manager.build_custom_dict_for_segmenter('invalid')
        self.assertEqual(invalid_dict_path, "")


if __name__ == "__main__":
    unittest.main() 