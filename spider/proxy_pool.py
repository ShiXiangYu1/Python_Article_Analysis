#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
代理IP池模块

提供代理IP的获取、验证、管理等功能
"""

import requests
import logging
import json
import os
import time
import random
import threading
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
import concurrent.futures
from urllib.parse import urlparse
import re

# 设置日志
logger = logging.getLogger('proxy_pool')

class Proxy:
    """
    代理IP类
    
    表示单个代理IP及其相关属性
    """
    
    def __init__(self, 
                 url: str, 
                 protocol: str = 'http', 
                 source: str = '', 
                 last_check: Optional[float] = None,
                 success_count: int = 0,
                 fail_count: int = 0,
                 response_time: float = 0.0) -> None:
        """
        初始化代理对象
        
        Args:
            url: 代理地址，格式为 ip:port
            protocol: 代理协议，如 http, https, socks5
            source: 代理来源
            last_check: 最后一次检查时间戳
            success_count: 成功使用次数
            fail_count: 失败次数
            response_time: 平均响应时间（秒）
        """
        self.url = url
        self.protocol = protocol
        self.source = source
        self.last_check = last_check or time.time()
        self.success_count = success_count
        self.fail_count = fail_count
        self.response_time = response_time
        
    @property
    def is_valid(self) -> bool:
        """
        判断代理是否有效
        
        Returns:
            布尔值，代理是否有效
        """
        # 失败次数过多或连续失败次数过多，认为代理失效
        if self.fail_count >= 5 and self.success_count == 0:
            return False
        
        # 成功率低于30%且使用超过10次，认为代理质量差
        if (self.success_count + self.fail_count) >= 10 and \
           self.success_count / (self.success_count + self.fail_count) < 0.3:
            return False
            
        return True
    
    @property
    def reliability(self) -> float:
        """
        计算代理可靠性得分
        
        Returns:
            0-1之间的浮点数，代理可靠性得分
        """
        # 未使用过的代理，给一个初始可靠性
        if self.success_count + self.fail_count == 0:
            return 0.5
            
        # 计算成功率
        success_rate = self.success_count / (self.success_count + self.fail_count)
        
        # 响应时间影响因子，假设响应时间越短越好
        time_factor = 1.0
        if self.response_time > 0:
            # 假设理想响应时间是0.5秒，超过2秒则效果不佳
            time_factor = min(1.0, 2.0 / (self.response_time + 1.0))
            
        # 使用次数影响因子，使用次数越多越可信
        usage_factor = min(1.0, (self.success_count + self.fail_count) / 10.0)
        
        # 综合计算可靠性得分
        reliability = success_rate * 0.6 + time_factor * 0.3 + usage_factor * 0.1
        
        return reliability
    
    def to_dict(self) -> Dict:
        """
        将代理对象转换为字典
        
        Returns:
            表示代理的字典
        """
        return {
            'url': self.url,
            'protocol': self.protocol,
            'source': self.source,
            'last_check': self.last_check,
            'success_count': self.success_count,
            'fail_count': self.fail_count,
            'response_time': self.response_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Proxy':
        """
        从字典创建代理对象
        
        Args:
            data: 表示代理的字典
            
        Returns:
            创建的代理对象
        """
        return cls(
            url=data['url'],
            protocol=data.get('protocol', 'http'),
            source=data.get('source', ''),
            last_check=data.get('last_check'),
            success_count=data.get('success_count', 0),
            fail_count=data.get('fail_count', 0),
            response_time=data.get('response_time', 0.0)
        )
    
    def __str__(self) -> str:
        """字符串表示"""
        validity = "有效" if self.is_valid else "无效"
        return f"代理({validity}): {self.protocol}://{self.url} 成功:{self.success_count} 失败:{self.fail_count} 可靠性:{self.reliability:.2f}"
    
    def __repr__(self) -> str:
        """对象表示"""
        return self.__str__()


class ProxyPool:
    """
    代理IP池
    
    管理多个代理IP，提供代理获取、验证、更新等功能
    """
    
    def __init__(self, 
                 proxy_file: str = 'proxies.json',
                 check_interval: int = 10 * 60,  # 10分钟
                 check_urls: List[str] = None) -> None:
        """
        初始化代理池
        
        Args:
            proxy_file: 代理保存文件路径
            check_interval: 代理检查间隔（秒）
            check_urls: 用于检查代理有效性的URL列表
        """
        self.proxy_file = proxy_file
        self.check_interval = check_interval
        self.check_urls = check_urls or [
            'https://www.baidu.com',
            'https://www.qq.com',
            'https://www.sina.com.cn'
        ]
        
        self.proxies: Dict[str, Proxy] = {}  # 代理字典，键为代理URL，值为Proxy对象
        self.lock = threading.RLock()  # 用于线程安全
        
        # 加载保存的代理
        self.load_proxies()
        
        # 启动定期检查线程
        self.checker_thread = threading.Thread(target=self._check_proxies_periodically, daemon=True)
        self.running = True
        self.checker_thread.start()
        
        logger.info(f"代理池初始化完成，当前代理数量: {len(self.proxies)}")
    
    def load_proxies(self) -> None:
        """
        从文件加载代理
        """
        if not os.path.exists(self.proxy_file):
            logger.info(f"代理文件 {self.proxy_file} 不存在，创建新代理池")
            return
            
        try:
            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            with self.lock:
                self.proxies = {}
                for proxy_data in data:
                    proxy = Proxy.from_dict(proxy_data)
                    self.proxies[proxy.url] = proxy
                    
            logger.info(f"从文件 {self.proxy_file} 加载了 {len(self.proxies)} 个代理")
        except Exception as e:
            logger.error(f"加载代理文件失败: {e}")
    
    def save_proxies(self) -> None:
        """
        保存代理到文件
        """
        try:
            with self.lock:
                proxy_list = [proxy.to_dict() for proxy in self.proxies.values()]
                
            with open(self.proxy_file, 'w', encoding='utf-8') as f:
                json.dump(proxy_list, f, ensure_ascii=False, indent=2)
                
            logger.info(f"已将 {len(self.proxies)} 个代理保存到文件 {self.proxy_file}")
        except Exception as e:
            logger.error(f"保存代理文件失败: {e}")
    
    def add_proxy(self, proxy: Proxy) -> bool:
        """
        添加代理到代理池
        
        Args:
            proxy: 要添加的代理对象
            
        Returns:
            添加是否成功
        """
        with self.lock:
            # 代理已存在，更新属性
            if proxy.url in self.proxies:
                existing_proxy = self.proxies[proxy.url]
                
                # 保留成功和失败计数
                proxy.success_count += existing_proxy.success_count
                proxy.fail_count += existing_proxy.fail_count
                
                # 如果现有代理有响应时间记录，计算平均值
                if existing_proxy.response_time > 0 and proxy.response_time > 0:
                    proxy.response_time = (existing_proxy.response_time + proxy.response_time) / 2
                elif existing_proxy.response_time > 0:
                    proxy.response_time = existing_proxy.response_time
            
            # 添加到代理池中
            self.proxies[proxy.url] = proxy
            logger.debug(f"添加代理: {proxy.url}")
            
            return True
    
    def remove_proxy(self, proxy_url: str) -> bool:
        """
        从代理池中移除代理
        
        Args:
            proxy_url: 要移除的代理URL
            
        Returns:
            移除是否成功
        """
        with self.lock:
            if proxy_url in self.proxies:
                del self.proxies[proxy_url]
                logger.debug(f"移除代理: {proxy_url}")
                return True
                
        return False
    
    def get_proxy(self, check: bool = False) -> Optional[Proxy]:
        """
        获取一个代理
        
        Args:
            check: 是否先检查代理有效性
            
        Returns:
            代理对象，如果没有可用代理则返回None
        """
        # 获取有效代理列表
        valid_proxies = []
        with self.lock:
            for proxy in self.proxies.values():
                if proxy.is_valid:
                    valid_proxies.append(proxy)
        
        if not valid_proxies:
            logger.warning("没有可用的代理")
            return None
            
        # 按可靠性排序
        valid_proxies.sort(key=lambda p: p.reliability, reverse=True)
        
        # 如果需要检查，则检查排名靠前的几个代理
        if check and valid_proxies:
            for i in range(min(3, len(valid_proxies))):
                proxy = valid_proxies[i]
                if self._check_proxy(proxy):
                    return proxy
                    
            # 如果前几个都不可用，随机选择其他代理
            remaining = valid_proxies[3:]
            if remaining:
                random.shuffle(remaining)
                for proxy in remaining[:3]:  # 最多再试3个
                    if self._check_proxy(proxy):
                        return proxy
                        
            logger.warning("检查了多个代理但都不可用")
            return None
        
        # 不需要检查，直接从可靠性前20%的代理中随机选择一个
        top_count = max(1, len(valid_proxies) // 5)
        return random.choice(valid_proxies[:top_count])
    
    def report_proxy_result(self, proxy_url: str, success: bool, response_time: float = 0.0) -> None:
        """
        报告代理使用结果
        
        Args:
            proxy_url: 代理URL
            success: 使用是否成功
            response_time: 响应时间（秒）
        """
        with self.lock:
            if proxy_url in self.proxies:
                proxy = self.proxies[proxy_url]
                
                if success:
                    proxy.success_count += 1
                    logger.debug(f"代理 {proxy_url} 使用成功，总成功次数: {proxy.success_count}")
                    
                    # 更新响应时间
                    if response_time > 0:
                        if proxy.response_time > 0:
                            # 计算移动平均
                            proxy.response_time = proxy.response_time * 0.7 + response_time * 0.3
                        else:
                            proxy.response_time = response_time
                else:
                    proxy.fail_count += 1
                    logger.debug(f"代理 {proxy_url} 使用失败，总失败次数: {proxy.fail_count}")
                    
                    # 失败次数过多，检查代理是否还有效
                    if not proxy.is_valid:
                        logger.info(f"代理 {proxy_url} 失效，从代理池移除")
                        del self.proxies[proxy_url]
    
    def _check_proxy(self, proxy: Proxy, timeout: int = 5) -> bool:
        """
        检查单个代理是否有效
        
        Args:
            proxy: 要检查的代理
            timeout: 请求超时时间（秒）
            
        Returns:
            代理是否有效
        """
        # 随机选择一个URL进行检查
        test_url = random.choice(self.check_urls)
        
        proxies = {
            'http': f"{proxy.protocol}://{proxy.url}",
            'https': f"{proxy.protocol}://{proxy.url}"
        }
        
        try:
            start_time = time.time()
            response = requests.get(
                test_url, 
                proxies=proxies, 
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            response_time = time.time() - start_time
            
            success = response.status_code == 200
            
            # 更新代理状态
            with self.lock:
                proxy.last_check = time.time()
                if success:
                    proxy.success_count += 1
                    
                    # 更新响应时间
                    if proxy.response_time > 0:
                        # 计算移动平均
                        proxy.response_time = proxy.response_time * 0.7 + response_time * 0.3
                    else:
                        proxy.response_time = response_time
                else:
                    proxy.fail_count += 1
            
            logger.debug(f"代理 {proxy.url} 检查 {'成功' if success else '失败'}, "
                        f"响应时间: {response_time:.2f}s, 状态码: {response.status_code}")
            return success
            
        except Exception as e:
            logger.debug(f"代理 {proxy.url} 检查异常: {e}")
            
            # 更新代理状态
            with self.lock:
                proxy.last_check = time.time()
                proxy.fail_count += 1
                
            return False
    
    def check_proxies(self, max_workers: int = 10) -> None:
        """
        检查所有代理的有效性
        
        Args:
            max_workers: 最大并发检查数
        """
        logger.info("开始检查所有代理有效性...")
        
        # 获取所有代理的副本
        with self.lock:
            proxies_to_check = list(self.proxies.values())
            
        if not proxies_to_check:
            logger.info("当前没有代理，跳过检查")
            return
            
        valid_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._check_proxy, proxy): proxy for proxy in proxies_to_check}
            
            for future in concurrent.futures.as_completed(futures):
                proxy = futures[future]
                try:
                    is_valid = future.result()
                    if is_valid:
                        valid_count += 1
                except Exception as e:
                    logger.error(f"检查代理 {proxy.url} 时发生错误: {e}")
        
        # 清理无效代理
        with self.lock:
            for url in list(self.proxies.keys()):
                if not self.proxies[url].is_valid:
                    del self.proxies[url]
        
        logger.info(f"代理检查完成，共检查 {len(proxies_to_check)} 个代理，"
                   f"有效 {valid_count} 个，当前代理池大小: {len(self.proxies)}")
        
        # 保存到文件
        self.save_proxies()
    
    def _check_proxies_periodically(self) -> None:
        """
        定期检查所有代理有效性的线程函数
        """
        while self.running:
            try:
                # 先睡眠，让刚初始化的代理池有时间添加代理
                time.sleep(self.check_interval)
                
                if not self.running:
                    break
                    
                self.check_proxies()
                
            except Exception as e:
                logger.error(f"定期检查代理时出错: {e}")
    
    def fetch_proxies_from_sources(self) -> int:
        """
        从多个来源获取代理
        
        Returns:
            新增代理数量
        """
        logger.info("开始从多个来源获取代理...")
        
        sources = [
            self._fetch_from_github,
            self._fetch_from_proxylist,
            self._fetch_from_free_proxy_list,
            self._fetch_from_cool_proxy
        ]
        
        new_proxies = 0
        for source_func in sources:
            try:
                count = source_func()
                new_proxies += count
                logger.info(f"从 {source_func.__name__} 获取了 {count} 个代理")
            except Exception as e:
                logger.error(f"从 {source_func.__name__} 获取代理时出错: {e}")
        
        if new_proxies > 0:
            # 如果有新代理，保存到文件
            self.save_proxies()
            
        logger.info(f"代理获取完成，共新增 {new_proxies} 个代理，当前代理池大小: {len(self.proxies)}")
        return new_proxies
    
    def _fetch_from_github(self) -> int:
        """
        从GitHub公共代理仓库获取代理
        
        Returns:
            新增代理数量
        """
        new_count = 0
        
        try:
            # 这里以某个著名的代理仓库为例
            url = "https://raw.githubusercontent.com/fate0/proxylist/master/proxy.list"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # 解析JSON行
                lines = response.text.strip().split("\n")
                for line in lines:
                    try:
                        data = json.loads(line)
                        host = data.get("host")
                        port = data.get("port")
                        proxy_type = data.get("type", "http")
                        
                        if host and port:
                            proxy_url = f"{host}:{port}"
                            proxy = Proxy(
                                url=proxy_url,
                                protocol=proxy_type,
                                source="github",
                            )
                            
                            if self.add_proxy(proxy):
                                new_count += 1
                    except:
                        continue
        except Exception as e:
            logger.error(f"从GitHub获取代理出错: {e}")
            
        return new_count
    
    def _fetch_from_proxylist(self) -> int:
        """
        从ProxyList获取代理
        
        Returns:
            新增代理数量
        """
        new_count = 0
        
        try:
            url = "https://www.proxy-list.download/api/v1/get?type=http"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                proxies = response.text.strip().split("\r\n")
                for proxy_url in proxies:
                    if ':' in proxy_url:
                        proxy = Proxy(
                            url=proxy_url,
                            protocol="http",
                            source="proxylist",
                        )
                        
                        if self.add_proxy(proxy):
                            new_count += 1
        except Exception as e:
            logger.error(f"从ProxyList获取代理出错: {e}")
            
        return new_count
    
    def _fetch_from_free_proxy_list(self) -> int:
        """
        从Free Proxy List获取代理
        
        Returns:
            新增代理数量
        """
        new_count = 0
        
        try:
            url = "https://free-proxy-list.net/"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # 使用正则表达式提取IP和端口
                pattern = r"(\d+\.\d+\.\d+\.\d+):(\d+)"
                matches = re.findall(pattern, response.text)
                
                for ip, port in matches:
                    proxy_url = f"{ip}:{port}"
                    proxy = Proxy(
                        url=proxy_url,
                        protocol="http",
                        source="free-proxy-list",
                    )
                    
                    if self.add_proxy(proxy):
                        new_count += 1
        except Exception as e:
            logger.error(f"从Free Proxy List获取代理出错: {e}")
            
        return new_count
    
    def _fetch_from_cool_proxy(self) -> int:
        """
        从Cool Proxy获取代理
        
        Returns:
            新增代理数量
        """
        new_count = 0
        
        try:
            url = "https://www.cool-proxy.net/proxies.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                proxies = response.json()
                for proxy_data in proxies:
                    try:
                        ip = proxy_data.get("ip")
                        port = proxy_data.get("port")
                        
                        if ip and port:
                            proxy_url = f"{ip}:{port}"
                            proxy = Proxy(
                                url=proxy_url,
                                protocol="http",
                                source="cool-proxy",
                            )
                            
                            if self.add_proxy(proxy):
                                new_count += 1
                    except:
                        continue
        except Exception as e:
            logger.error(f"从Cool Proxy获取代理出错: {e}")
            
        return new_count
    
    def shutdown(self) -> None:
        """
        关闭代理池
        """
        logger.info("代理池正在关闭...")
        
        self.running = False
        if self.checker_thread.is_alive():
            self.checker_thread.join(timeout=1.0)
            
        # 保存最终的代理列表
        self.save_proxies()
        
        logger.info("代理池已关闭")
    
    def __del__(self) -> None:
        """析构函数，确保资源被释放"""
        try:
            self.shutdown()
        except:
            pass
    
    def __str__(self) -> str:
        """字符串表示"""
        valid_count = sum(1 for p in self.proxies.values() if p.is_valid)
        return f"代理池: 共 {len(self.proxies)} 个代理，有效 {valid_count} 个"
    
    def __repr__(self) -> str:
        """对象表示"""
        return self.__str__()


# 全局代理池实例
_proxy_pool = None

def get_proxy_pool(data_dir: str = 'data',
                 max_proxies: int = 100,
                 check_interval: int = 30,
                 max_fail_count: int = 3,
                 timeout: int = 10) -> ProxyPool:
    """
    获取代理池实例（单例模式）
    
    Args:
        data_dir: 数据保存目录
        max_proxies: 最大代理数量
        check_interval: 代理检测间隔（分钟）
        max_fail_count: 最大失败次数
        timeout: 请求超时时间（秒）
        
    Returns:
        代理池实例
    """
    global _proxy_pool
    if _proxy_pool is None:
        _proxy_pool = ProxyPool(
            data_dir=data_dir,
            max_proxies=max_proxies,
            check_interval=check_interval,
            max_fail_count=max_fail_count,
            timeout=timeout
        )
    return _proxy_pool


# 单元测试
if __name__ == "__main__":
    import unittest
    
    class TestProxyPool(unittest.TestCase):
        """代理池单元测试"""
        
        def setUp(self):
            """测试前准备"""
            # 创建临时目录
            import tempfile
            self.test_dir = tempfile.mkdtemp()
            
            # 初始化代理池
            self.pool = ProxyPool(
                data_dir=self.test_dir,
                max_proxies=10,
                check_interval=1,
                max_fail_count=2,
                timeout=5
            )
        
        def tearDown(self):
            """测试后清理"""
            import shutil
            shutil.rmtree(self.test_dir)
        
        def test_add_and_get_proxy(self):
            """测试添加和获取代理"""
            # 正常情况下添加代理会返回False，因为我们没有真实的代理服务器，但我们可以模拟这个过程
            
            # 模拟添加代理
            self.pool.proxies.append(Proxy(
                url="http://127.0.0.1:8080",
                protocol="http",
                source="test",
                last_check=time.time(),
                success_count=1,
                fail_count=0,
                response_time=0.5
            ))
            
            # 获取代理
            proxy = self.pool.get_proxy()
            self.assertIsNotNone(proxy)
            self.assertEqual(proxy.url, "http://127.0.0.1:8080")
        
        def test_remove_proxy(self):
            """测试移除代理"""
            # 模拟添加代理
            self.pool.proxies.append(Proxy(
                url="http://127.0.0.1:8080",
                protocol="http",
                source="test",
                last_check=time.time(),
                success_count=1,
                fail_count=0,
                response_time=0.5
            ))
            
            # 移除代理
            result = self.pool.remove_proxy("http://127.0.0.1:8080")
            self.assertTrue(result)
            self.assertEqual(len(self.pool.proxies), 0)
            
            # 尝试移除不存在的代理
            result = self.pool.remove_proxy("http://127.0.0.1:9090")
            self.assertFalse(result)
        
        def test_report_proxy_result(self):
            """测试报告代理结果"""
            # 模拟添加代理
            proxy = Proxy(
                url="http://127.0.0.1:8080",
                protocol="http",
                source="test",
                last_check=time.time(),
                success_count=1,
                fail_count=0,
                response_time=0.5
            )
            self.pool.proxies.append(proxy)
            
            # 报告成功
            self.pool.report_proxy_result(proxy, True)
            self.assertEqual(self.pool.proxies[0].success_count, 2)
            self.assertEqual(self.pool.proxies[0].fail_count, 0)
            
            # 报告失败
            self.pool.report_proxy_result(proxy, False)
            self.assertEqual(self.pool.proxies[0].success_count, 2)
            self.assertEqual(self.pool.proxies[0].fail_count, 1)
            
            # 报告多次失败直到移除
            self.pool.report_proxy_result(proxy, False)
            self.assertEqual(len(self.pool.proxies), 0)  # 失败次数达到2次，代理被移除
        
        def test_save_and_load_proxies(self):
            """测试保存和加载代理"""
            # 模拟添加代理
            self.pool.proxies.append(Proxy(
                url="http://127.0.0.1:8080",
                protocol="http",
                source="test",
                last_check=time.time(),
                success_count=1,
                fail_count=0,
                response_time=0.5
            ))
            
            # 保存代理
            self.pool.save_proxies()
            
            # 清空代理列表
            self.pool.proxies = []
            
            # 加载代理
            self.pool.load_proxies()
            
            # 验证
            self.assertEqual(len(self.pool.proxies), 1)
            self.assertEqual(self.pool.proxies[0].url, "http://127.0.0.1:8080")
    
    # 运行测试
    unittest.main(argv=['first-arg-is-ignored'], exit=False) 