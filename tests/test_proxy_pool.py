#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理池模块单元测试
测试代理IP的获取、验证和管理功能
"""

import unittest
import json
import os
import tempfile
import time
import shutil
from unittest.mock import patch, MagicMock, mock_open
import threading
import requests

# 添加项目根目录到系统路径
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入代理池模块
from spider.proxy_pool import Proxy, ProxyPool


class TestProxy(unittest.TestCase):
    """测试代理IP类"""
    
    def test_init(self):
        """测试代理IP初始化"""
        # 创建代理实例
        proxy = Proxy('http://127.0.0.1:8080', protocol='http', source='测试源')
        
        # 验证属性
        self.assertEqual(proxy.url, 'http://127.0.0.1:8080')
        self.assertEqual(proxy.protocol, 'http')
        self.assertEqual(proxy.source, '测试源')
        self.assertEqual(proxy.success_count, 0)
        self.assertEqual(proxy.fail_count, 0)
        self.assertIsNotNone(proxy.last_check)
        self.assertIsNone(proxy.response_time)
        
    def test_is_valid(self):
        """测试代理IP有效性判断"""
        # 创建代理实例
        proxy = Proxy('http://127.0.0.1:8080')
        
        # 初始状态（未经过验证）
        self.assertTrue(proxy.is_valid)
        
        # 成功次数多于失败次数
        proxy.success_count = 5
        proxy.fail_count = 2
        self.assertTrue(proxy.is_valid)
        
        # 失败次数多于成功次数
        proxy.success_count = 2
        proxy.fail_count = 5
        self.assertFalse(proxy.is_valid)
        
        # 失败次数等于最大失败次数阈值
        proxy.fail_count = Proxy.MAX_FAIL_COUNT
        self.assertFalse(proxy.is_valid)
        
    def test_reliability(self):
        """测试代理IP可靠性计算"""
        # 创建代理实例
        proxy = Proxy('http://127.0.0.1:8080')
        
        # 初始状态
        self.assertEqual(proxy.reliability, 0.0)
        
        # 全部成功
        proxy.success_count = 10
        proxy.fail_count = 0
        self.assertEqual(proxy.reliability, 1.0)
        
        # 全部失败
        proxy.success_count = 0
        proxy.fail_count = 10
        self.assertEqual(proxy.reliability, 0.0)
        
        # 部分成功部分失败
        proxy.success_count = 7
        proxy.fail_count = 3
        self.assertEqual(proxy.reliability, 0.7)
        
    def test_to_dict(self):
        """测试转换为字典格式"""
        # 创建代理实例
        proxy = Proxy('http://127.0.0.1:8080', protocol='http', source='测试源')
        proxy.success_count = 5
        proxy.fail_count = 2
        proxy.response_time = 0.5
        
        # 转换为字典
        proxy_dict = proxy.to_dict()
        
        # 验证字典内容
        self.assertEqual(proxy_dict['url'], 'http://127.0.0.1:8080')
        self.assertEqual(proxy_dict['protocol'], 'http')
        self.assertEqual(proxy_dict['source'], '测试源')
        self.assertEqual(proxy_dict['success_count'], 5)
        self.assertEqual(proxy_dict['fail_count'], 2)
        self.assertEqual(proxy_dict['response_time'], 0.5)
        self.assertIn('last_check', proxy_dict)
        
    def test_from_dict(self):
        """测试从字典创建代理实例"""
        # 准备测试数据
        proxy_data = {
            'url': 'http://127.0.0.1:8080',
            'protocol': 'http',
            'source': '测试源',
            'success_count': 5,
            'fail_count': 2,
            'last_check': '2023-09-01 10:00:00',
            'response_time': 0.5
        }
        
        # 从字典创建代理
        proxy = Proxy.from_dict(proxy_data)
        
        # 验证属性
        self.assertEqual(proxy.url, 'http://127.0.0.1:8080')
        self.assertEqual(proxy.protocol, 'http')
        self.assertEqual(proxy.source, '测试源')
        self.assertEqual(proxy.success_count, 5)
        self.assertEqual(proxy.fail_count, 2)
        self.assertEqual(proxy.response_time, 0.5)
        
    def test_str_representation(self):
        """测试字符串表示"""
        # 创建代理实例
        proxy = Proxy('http://127.0.0.1:8080', protocol='http', source='测试源')
        proxy.success_count = 5
        proxy.fail_count = 2
        proxy.response_time = 0.5
        
        # 获取字符串表示
        proxy_str = str(proxy)
        
        # 验证包含关键信息
        self.assertIn('http://127.0.0.1:8080', proxy_str)
        self.assertIn('成功:5', proxy_str)
        self.assertIn('失败:2', proxy_str)
        self.assertIn('0.5秒', proxy_str)


class TestProxyPool(unittest.TestCase):
    """测试代理池类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时目录
        self.test_dir = tempfile.mkdtemp()
        
        # 代理池实例
        self.pool = ProxyPool(
            proxies_file=os.path.join(self.test_dir, 'proxies.json'),
            check_interval=60,
            max_proxies=100
        )
        
        # 测试代理列表
        self.test_proxies = [
            Proxy('http://proxy1.example.com:8080', protocol='http', source='测试源1'),
            Proxy('https://proxy2.example.com:8443', protocol='https', source='测试源2'),
            Proxy('http://proxy3.example.com:80', protocol='http', source='测试源1')
        ]
        
        # 添加测试代理到池中
        for proxy in self.test_proxies:
            self.pool.add_proxy(proxy)
            
    def tearDown(self):
        """测试后清理"""
        # 停止代理检查线程
        if hasattr(self.pool, '_check_thread') and self.pool._check_thread.is_alive():
            self.pool._stop_checking = True
            self.pool._check_thread.join(timeout=1)
            
        # 删除临时目录
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
    def test_add_proxy(self):
        """测试添加代理"""
        # 创建新代理
        new_proxy = Proxy('http://new.example.com:8080')
        
        # 添加到池中
        self.pool.add_proxy(new_proxy)
        
        # 验证是否添加成功
        self.assertIn(new_proxy.url, self.pool._proxies)
        self.assertEqual(self.pool._proxies[new_proxy.url], new_proxy)
        
        # 测试添加重复代理
        self.pool.add_proxy(new_proxy)
        proxy_count = len(self.pool._proxies)
        duplicate_proxy = Proxy('http://new.example.com:8080')
        self.pool.add_proxy(duplicate_proxy)
        self.assertEqual(len(self.pool._proxies), proxy_count)  # 数量不应该增加
        
    def test_remove_proxy(self):
        """测试移除代理"""
        # 确保代理池中有代理
        self.assertGreater(len(self.pool._proxies), 0)
        
        # 获取第一个代理的URL
        proxy_url = list(self.pool._proxies.keys())[0]
        
        # 移除该代理
        self.pool.remove_proxy(proxy_url)
        
        # 验证是否成功移除
        self.assertNotIn(proxy_url, self.pool._proxies)
        
    def test_get_proxy(self):
        """测试获取代理"""
        # 获取随机代理
        proxy = self.pool.get_proxy()
        
        # 验证返回了有效代理
        self.assertIsNotNone(proxy)
        self.assertIsInstance(proxy, Proxy)
        self.assertIn(proxy.url, self.pool._proxies)
        
        # 当代理池为空时
        self.pool._proxies.clear()
        empty_proxy = self.pool.get_proxy()
        self.assertIsNone(empty_proxy)
        
        # 测试按协议获取代理
        self.pool._proxies = {p.url: p for p in self.test_proxies}
        http_proxy = self.pool.get_proxy(protocol='http')
        self.assertEqual(http_proxy.protocol, 'http')
        
        https_proxy = self.pool.get_proxy(protocol='https')
        self.assertEqual(https_proxy.protocol, 'https')
        
        # 测试获取最可靠的代理
        for proxy in self.test_proxies:
            if proxy.url == 'http://proxy1.example.com:8080':
                proxy.success_count = 10
                proxy.fail_count = 0
            else:
                proxy.success_count = 5
                proxy.fail_count = 5
                
        most_reliable = self.pool.get_proxy(get_most_reliable=True)
        self.assertEqual(most_reliable.url, 'http://proxy1.example.com:8080')
        
    def test_report_proxy_result(self):
        """测试报告代理使用结果"""
        # 获取测试代理
        test_url = self.test_proxies[0].url
        test_proxy = self.pool._proxies[test_url]
        original_success = test_proxy.success_count
        original_fail = test_proxy.fail_count
        
        # 报告成功结果
        self.pool.report_proxy_result(test_url, success=True, response_time=0.3)
        
        # 验证成功次数增加
        self.assertEqual(test_proxy.success_count, original_success + 1)
        self.assertEqual(test_proxy.response_time, 0.3)
        
        # 报告失败结果
        self.pool.report_proxy_result(test_url, success=False)
        
        # 验证失败次数增加
        self.assertEqual(test_proxy.fail_count, original_fail + 1)
        
        # 测试报告不存在的代理
        with self.assertLogs(level='WARNING'):
            self.pool.report_proxy_result('http://nonexistent.example.com', success=True)
            
    def test_save_load_proxies(self):
        """测试保存和加载代理列表"""
        # 确保有测试代理
        self.assertGreater(len(self.pool._proxies), 0)
        
        # 计算初始代理数量
        original_count = len(self.pool._proxies)
        
        # 保存代理
        proxies_file = os.path.join(self.test_dir, 'test_proxies.json')
        self.pool.save_proxies(proxies_file)
        
        # 验证文件已创建
        self.assertTrue(os.path.exists(proxies_file))
        
        # 清空代理池
        self.pool._proxies.clear()
        self.assertEqual(len(self.pool._proxies), 0)
        
        # 加载代理
        self.pool.load_proxies(proxies_file)
        
        # 验证代理数量恢复
        self.assertEqual(len(self.pool._proxies), original_count)
        
    @patch('requests.get')
    def test_check_proxy(self, mock_get):
        """测试检查代理有效性"""
        # 创建测试代理
        test_proxy = Proxy('http://127.0.0.1:8080')
        self.pool.add_proxy(test_proxy)
        
        # 模拟成功响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_get.return_value = mock_response
        
        # 执行检查
        self.pool._check_proxy(test_proxy.url)
        
        # 验证代理状态更新
        self.assertEqual(test_proxy.success_count, 1)
        self.assertEqual(test_proxy.fail_count, 0)
        self.assertEqual(test_proxy.response_time, 0.5)
        
        # 模拟失败响应
        mock_get.side_effect = Exception("Connection error")
        
        # 执行检查
        self.pool._check_proxy(test_proxy.url)
        
        # 验证代理状态更新
        self.assertEqual(test_proxy.success_count, 1)
        self.assertEqual(test_proxy.fail_count, 1)
        
    @patch.object(ProxyPool, '_fetch_proxies_from_source')
    def test_fetch_proxies(self, mock_fetch):
        """测试获取代理列表"""
        # 模拟从源获取代理
        mock_fetch.return_value = [
            Proxy('http://new1.example.com:8080'),
            Proxy('http://new2.example.com:8080')
        ]
        
        # 记录初始代理数量
        original_count = len(self.pool._proxies)
        
        # 执行获取
        self.pool.fetch_proxies()
        
        # 验证代理数量增加
        self.assertGreater(len(self.pool._proxies), original_count)
        
        # 验证新代理被添加
        self.assertIn('http://new1.example.com:8080', self.pool._proxies)
        
    @patch('threading.Thread')
    def test_start_check_proxies_thread(self, mock_thread):
        """测试启动代理检查线程"""
        # 模拟线程
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        # 启动检查线程
        self.pool.start_check_proxies_thread()
        
        # 验证线程已创建并启动
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()


if __name__ == '__main__':
    unittest.main() 