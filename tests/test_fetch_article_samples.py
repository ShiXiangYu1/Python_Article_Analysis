#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试文章样本批量爬取脚本
"""

import os
import sys
import json
import unittest
import tempfile
import shutil
import pandas as pd
from unittest.mock import patch, MagicMock, mock_open

# 将项目根目录添加到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_article_samples import (
    ArticleFetcher,
    create_default_config,
    parse_args,
    main
)


class TestArticleFetcher(unittest.TestCase):
    """测试ArticleFetcher类"""
    
    def setUp(self):
        """测试前的设置"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        
        # 模拟配置文件
        self.config = {
            "websites": [
                {
                    "name": "test_site",
                    "base_url": "https://example.com",
                    "max_articles": 10,
                    "thread_count": 2,
                    "delay": 1.0,
                    "incremental": False
                }
            ],
            "global": {
                "timeout": 5,
                "max_retries": 2,
                "delay": 0.5,
                "proxy": {
                    "enabled": False,
                    "proxy_file": "test_proxies.json",
                    "max_workers": 2
                }
            }
        }
        
        # 创建临时配置文件
        self.config_file = os.path.join(self.temp_dir, 'test_config.json')
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        
        # 创建模拟文章数据
        self.mock_articles = [
            {
                "title": "测试文章1",
                "content": "这是测试文章1的内容",
                "url": "https://example.com/article1",
                "author": "测试作者1",
                "publish_date": "2023-03-10",
                "keywords": ["测试", "文章"],
                "entities": {"person": ["张三"], "organization": ["测试公司"]}
            },
            {
                "title": "测试文章2",
                "content": "这是测试文章2的内容",
                "url": "https://example.com/article2",
                "author": "测试作者2",
                "publish_date": "2023-03-11",
                "keywords": ["样本", "文章"],
                "entities": {"person": ["李四"], "organization": ["样本公司"]}
            }
        ]
    
    def tearDown(self):
        """测试后的清理"""
        # 删除临时目录及其所有内容
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """测试初始化方法"""
        # 测试使用有效的配置文件初始化
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir,
            min_articles=50,
            use_proxy=True
        )
        
        # 验证属性是否正确设置
        self.assertEqual(fetcher.config_file, self.config_file)
        self.assertEqual(fetcher.output_dir, self.temp_dir)
        self.assertEqual(fetcher.min_articles, 50)
        self.assertTrue(fetcher.use_proxy)
        self.assertEqual(fetcher.websites, self.config["websites"])
    
    def test_load_config_valid_file(self):
        """测试从有效配置文件加载配置"""
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 验证配置是否正确加载
        self.assertEqual(fetcher.config, self.config)
    
    def test_load_config_invalid_file(self):
        """测试从无效配置文件加载配置"""
        # 创建一个不存在的配置文件路径
        nonexistent_file = os.path.join(self.temp_dir, 'nonexistent.json')
        
        # 创建爬取器，应该使用默认配置
        fetcher = ArticleFetcher(
            config_file=nonexistent_file,
            output_dir=self.temp_dir
        )
        
        # 验证是否使用了默认配置
        self.assertTrue('websites' in fetcher.config)
        self.assertTrue('global' in fetcher.config)
        
        # 验证默认配置包含预期的网站
        website_names = [website['name'] for website in fetcher.config['websites']]
        self.assertTrue('zhihu' in website_names)
        self.assertTrue('csdn' in website_names)
        self.assertTrue('jianshu' in website_names)
    
    def test_load_config_corrupt_file(self):
        """测试从损坏的配置文件加载配置"""
        # 创建一个包含无效JSON的配置文件
        corrupt_file = os.path.join(self.temp_dir, 'corrupt.json')
        with open(corrupt_file, 'w', encoding='utf-8') as f:
            f.write('{这不是有效的JSON}')
        
        # 创建爬取器，应该使用默认配置
        fetcher = ArticleFetcher(
            config_file=corrupt_file,
            output_dir=self.temp_dir
        )
        
        # 验证是否使用了默认配置
        self.assertTrue('websites' in fetcher.config)
        self.assertTrue('global' in fetcher.config)
    
    @patch('fetch_article_samples.ArticleFetcher._fetch_website')
    def test_fetch_all(self, mock_fetch_website):
        """测试批量爬取所有网站"""
        # 设置模拟返回值
        mock_fetch_website.return_value = (self.mock_articles, {
            'status': 'success',
            'articles': len(self.mock_articles),
            'duration': 1.5,
            'avg_time_per_article': 0.75,
            'output_file': 'test_output.csv'
        })
        
        # 创建爬取器并执行批量爬取
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir,
            min_articles=5  # 设置一个小的目标以便测试提前退出
        )
        
        # 执行批量爬取
        results = fetcher.fetch_all()
        
        # 验证_fetch_website是否被调用
        mock_fetch_website.assert_called_once_with(self.config["websites"][0])
        
        # 验证结果
        self.assertEqual(results['total_articles'], len(self.mock_articles))
        self.assertEqual(results['success_rate'], 1.0)
        self.assertTrue('test_site' in results['websites'])
        self.assertEqual(results['websites']['test_site']['status'], 'success')
    
    @patch('fetch_article_samples.ArticleFetcher._fetch_website')
    def test_fetch_all_multiple_websites(self, mock_fetch_website):
        """测试批量爬取多个网站，直到达到目标数量"""
        # 修改配置，添加多个网站
        self.config["websites"].append({
            "name": "test_site2",
            "base_url": "https://example2.com",
            "max_articles": 10,
            "thread_count": 2
        })
        
        # 重写临时配置文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        
        # 设置模拟返回值，第一个网站返回部分文章，第二个网站返回剩余文章
        mock_fetch_website.side_effect = [
            (self.mock_articles[:1], {
                'status': 'success',
                'articles': 1,
                'duration': 1.0,
                'output_file': 'test_output1.csv'
            }),
            (self.mock_articles[1:], {
                'status': 'success',
                'articles': 1,
                'duration': 1.0,
                'output_file': 'test_output2.csv'
            })
        ]
        
        # 创建爬取器并执行批量爬取
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir,
            min_articles=2  # 设置目标为2篇文章
        )
        
        # 执行批量爬取
        results = fetcher.fetch_all()
        
        # 验证两个网站都被爬取
        self.assertEqual(mock_fetch_website.call_count, 2)
        
        # 验证结果
        self.assertEqual(results['total_articles'], 2)
        self.assertEqual(results['success_rate'], 1.0)
    
    @patch('fetch_article_samples.ArticleFetcher._fetch_website')
    def test_fetch_all_with_errors(self, mock_fetch_website):
        """测试批量爬取时处理错误"""
        # 修改配置，添加多个网站
        self.config["websites"].append({
            "name": "test_site2",
            "base_url": "https://example2.com",
            "max_articles": 10,
            "thread_count": 2
        })
        
        # 重写临时配置文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        
        # 设置模拟返回值，第一个网站抛出异常，第二个网站正常返回
        mock_fetch_website.side_effect = [
            Exception("爬取失败"),
            (self.mock_articles, {
                'status': 'success',
                'articles': len(self.mock_articles),
                'duration': 1.5,
                'output_file': 'test_output2.csv'
            })
        ]
        
        # 创建爬取器并执行批量爬取
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 执行批量爬取
        results = fetcher.fetch_all()
        
        # 验证两个网站都被尝试爬取
        self.assertEqual(mock_fetch_website.call_count, 2)
        
        # 验证结果
        self.assertEqual(results['total_articles'], len(self.mock_articles))
        self.assertEqual(results['success_rate'], 0.5)  # 一个成功，一个失败
        self.assertEqual(results['websites']['test_site']['status'], 'failed')
        self.assertEqual(results['websites']['test_site2']['status'], 'success')
    
    @patch('fetch_article_samples.ArticleSpider')
    def test_fetch_website(self, mock_spider_class):
        """测试爬取单个网站"""
        # 设置模拟Spider
        mock_spider = MagicMock()
        mock_spider.crawl.return_value = self.mock_articles
        mock_spider_class.return_value = mock_spider
        
        # 创建爬取器
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 添加_save_to_csv的模拟以避免实际写入文件
        with patch.object(fetcher, '_save_to_csv') as mock_save:
            # 爬取单个网站
            website_config = self.config["websites"][0]
            articles, stats = fetcher._fetch_website(website_config)
            
            # 验证Spider是否被正确创建和调用
            mock_spider_class.assert_called_once()
            mock_spider.crawl.assert_called_once()
            
            # 验证返回的文章和统计信息
            self.assertEqual(articles, self.mock_articles)
            self.assertEqual(stats['status'], 'success')
            self.assertEqual(stats['articles'], len(self.mock_articles))
            
            # 验证_save_to_csv是否被调用
            mock_save.assert_called_once()
    
    @patch('fetch_article_samples.ArticleSpider')
    def test_fetch_website_missing_url(self, mock_spider_class):
        """测试爬取没有base_url的网站"""
        # 创建一个没有base_url的网站配置
        invalid_config = {
            "name": "invalid_site",
            "max_articles": 10
        }
        
        # 创建爬取器
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 验证是否抛出ValueError
        with self.assertRaises(ValueError):
            fetcher._fetch_website(invalid_config)
    
    @patch('fetch_article_samples.ArticleSpider')
    def test_fetch_website_spider_error(self, mock_spider_class):
        """测试爬取过程中Spider抛出异常"""
        # 设置模拟Spider抛出异常
        mock_spider = MagicMock()
        mock_spider.crawl.side_effect = Exception("爬取失败")
        mock_spider_class.return_value = mock_spider
        
        # 创建爬取器
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 验证是否传递异常
        with self.assertRaises(Exception):
            fetcher._fetch_website(self.config["websites"][0])
    
    def test_save_to_csv_empty_articles(self):
        """测试保存空文章列表到CSV"""
        # 创建爬取器
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 测试文件路径
        test_file = os.path.join(self.temp_dir, 'empty_test.csv')
        
        # 保存空文章列表
        fetcher._save_to_csv([], test_file)
        
        # 验证文件是否未创建
        self.assertFalse(os.path.exists(test_file))
    
    def test_save_to_csv_valid_articles(self):
        """测试保存有效文章列表到CSV"""
        # 创建爬取器
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 测试文件路径
        test_file = os.path.join(self.temp_dir, 'valid_test.csv')
        
        # 保存文章列表
        fetcher._save_to_csv(self.mock_articles, test_file)
        
        # 验证文件是否创建
        self.assertTrue(os.path.exists(test_file))
        
        # 读取CSV验证内容
        df = pd.read_csv(test_file, encoding='utf-8-sig')
        self.assertEqual(len(df), len(self.mock_articles))
        self.assertEqual(df.iloc[0]['title'], self.mock_articles[0]['title'])
    
    def test_save_to_csv_with_complex_objects(self):
        """测试保存含有复杂对象的文章列表到CSV"""
        # 创建爬取器
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 测试文件路径
        test_file = os.path.join(self.temp_dir, 'complex_test.csv')
        
        # 保存文章列表，包含嵌套对象
        fetcher._save_to_csv(self.mock_articles, test_file)
        
        # 验证文件是否创建
        self.assertTrue(os.path.exists(test_file))
        
        # 读取CSV验证内容
        df = pd.read_csv(test_file, encoding='utf-8-sig')
        
        # 验证复杂对象是否被正确序列化为JSON字符串
        for i, article in enumerate(self.mock_articles):
            entity_json = json.loads(df.iloc[i]['entities'])
            self.assertEqual(entity_json, article['entities'])
    
    def test_merge_all_samples_no_files(self):
        """测试当没有样本文件时合并"""
        # 创建爬取器
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 合并样本
        result = fetcher.merge_all_samples()
        
        # 验证结果
        self.assertEqual(result, "")
    
    @patch('fetch_article_samples.pd.read_csv')
    def test_merge_all_samples_with_files(self, mock_read_csv):
        """测试合并样本文件"""
        # 设置模拟返回值
        df1 = pd.DataFrame(self.mock_articles[:1])
        df2 = pd.DataFrame(self.mock_articles[1:])
        mock_read_csv.side_effect = [df1, df2]
        
        # 创建样本目录结构
        os.makedirs(os.path.join(self.temp_dir, 'test_site'), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, 'test_site2'), exist_ok=True)
        
        # 创建样本CSV文件（内容不重要，因为我们模拟了read_csv）
        with open(os.path.join(self.temp_dir, 'test_site', 'test_site_articles.csv'), 'w') as f:
            f.write('dummy')
        with open(os.path.join(self.temp_dir, 'test_site2', 'test_site2_articles.csv'), 'w') as f:
            f.write('dummy')
        
        # 修改配置，添加多个网站
        self.config["websites"].append({
            "name": "test_site2",
            "base_url": "https://example2.com",
            "max_articles": 10,
            "thread_count": 2
        })
        
        # 重写临时配置文件
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        
        # 创建爬取器
        fetcher = ArticleFetcher(
            config_file=self.config_file,
            output_dir=self.temp_dir
        )
        
        # 模拟pd.concat和to_csv以避免实际写入
        with patch('fetch_article_samples.pd.concat') as mock_concat:
            mock_concat.return_value = pd.DataFrame(self.mock_articles)
            with patch.object(mock_concat.return_value, 'to_csv') as mock_to_csv:
                # 合并样本
                result = fetcher.merge_all_samples()
                
                # 验证pd.read_csv被调用
                self.assertEqual(mock_read_csv.call_count, 2)
                
                # 验证pd.concat被调用
                mock_concat.assert_called_once()
                
                # 验证to_csv被调用
                mock_to_csv.assert_called_once()
                
                # 验证返回的文件路径
                expected_path = os.path.join(self.temp_dir, 'all_articles.csv')
                self.assertEqual(result, expected_path)


class TestHelperFunctions(unittest.TestCase):
    """测试辅助函数"""
    
    def setUp(self):
        """测试前的设置"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后的清理"""
        shutil.rmtree(self.temp_dir)
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('fetch_article_samples.json.dump')
    @patch('fetch_article_samples.os.path.exists')
    def test_create_default_config_new_file(self, mock_exists, mock_dump, mock_open):
        """测试创建新的默认配置文件"""
        # 模拟文件不存在
        mock_exists.return_value = False
        
        # 调用函数
        create_default_config()
        
        # 验证是否检查了文件存在性
        mock_exists.assert_called_once_with('fetch_config.json')
        
        # 验证是否打开了文件进行写入
        mock_open.assert_called_once_with('fetch_config.json', 'w', encoding='utf-8')
        
        # 验证是否调用了json.dump写入配置
        mock_dump.assert_called_once()
    
    @patch('fetch_article_samples.os.path.exists')
    def test_create_default_config_existing_file(self, mock_exists):
        """测试当配置文件已存在时创建默认配置文件"""
        # 模拟文件已存在
        mock_exists.return_value = True
        
        # 调用函数
        create_default_config()
        
        # 验证是否检查了文件存在性
        mock_exists.assert_called_once_with('fetch_config.json')
        
        # 确保不会尝试创建新文件
        # 这里我们不需要模拟open或json.dump，因为函数应该在检查到文件存在后直接返回
    
    def test_parse_args_defaults(self):
        """测试解析默认命令行参数"""
        # 保存原始参数
        old_argv = sys.argv
        
        try:
            # 设置测试参数
            sys.argv = ['fetch_article_samples.py']
            
            # 解析参数
            args = parse_args()
            
            # 验证默认值
            self.assertEqual(args.config, 'fetch_config.json')
            self.assertEqual(args.output, 'data/samples')
            self.assertEqual(args.min, 100)
            self.assertFalse(args.proxy)
            self.assertFalse(args.create_config)
        finally:
            # 恢复原始参数
            sys.argv = old_argv
    
    def test_parse_args_custom(self):
        """测试解析自定义命令行参数"""
        # 保存原始参数
        old_argv = sys.argv
        
        try:
            # 设置测试参数
            sys.argv = [
                'fetch_article_samples.py',
                '--config', 'custom_config.json',
                '--output', 'custom_output',
                '--min', '50',
                '--proxy',
                '--create-config'
            ]
            
            # 解析参数
            args = parse_args()
            
            # 验证自定义值
            self.assertEqual(args.config, 'custom_config.json')
            self.assertEqual(args.output, 'custom_output')
            self.assertEqual(args.min, 50)
            self.assertTrue(args.proxy)
            self.assertTrue(args.create_config)
        finally:
            # 恢复原始参数
            sys.argv = old_argv
    
    @patch('fetch_article_samples.create_default_config')
    def test_main_create_config(self, mock_create_config):
        """测试main函数的创建配置文件功能"""
        # 保存原始参数
        old_argv = sys.argv
        
        try:
            # 设置测试参数
            sys.argv = ['fetch_article_samples.py', '--create-config']
            
            # 执行main函数
            main()
            
            # 验证create_default_config是否被调用
            mock_create_config.assert_called_once()
        finally:
            # 恢复原始参数
            sys.argv = old_argv
    
    @patch('fetch_article_samples.ArticleFetcher')
    def test_main_fetch_articles(self, mock_fetcher_class):
        """测试main函数的爬取文章功能"""
        # 设置模拟Fetcher
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_all.return_value = {
            'total_articles': 100,
            'duration': 60.0,
            'success_rate': 0.8,
            'websites': {}
        }
        mock_fetcher.merge_all_samples.return_value = 'all_articles.csv'
        mock_fetcher_class.return_value = mock_fetcher
        
        # 保存原始参数
        old_argv = sys.argv
        
        try:
            # 设置测试参数
            sys.argv = ['fetch_article_samples.py']
            
            # 模拟TODO.md文件
            with patch('builtins.open', mock_open(read_data="- [ ] 爬取100篇以上文章样本")):
                # 执行main函数
                with patch('fetch_article_samples.open', mock_open()):
                    main()
                    
                    # 验证ArticleFetcher是否被创建
                    mock_fetcher_class.assert_called_once()
                    
                    # 验证fetch_all是否被调用
                    mock_fetcher.fetch_all.assert_called_once()
                    
                    # 验证merge_all_samples是否被调用
                    mock_fetcher.merge_all_samples.assert_called_once()
        finally:
            # 恢复原始参数
            sys.argv = old_argv


if __name__ == '__main__':
    unittest.main() 