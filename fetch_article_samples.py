#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文章样本批量爬取脚本

该脚本用于批量爬取多个网站的文章样本，支持多线程并行爬取，
增量爬取，以及定制化配置。主要用于构建训练和测试数据集。
"""

import os
import sys
import time
import logging
import argparse
import json
import traceback
from typing import Dict, List, Any, Optional, Tuple

# 将项目根目录添加到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('fetch_samples.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('fetch_samples')

# 尝试导入依赖包，处理可能的兼容性问题
try:
    import pandas as pd
except ImportError:
    logger.error("无法导入pandas，请确保已安装该依赖")
    sys.exit(1)

try:
    from spider.spider import ArticleSpider
    from spider.parser import get_parser
except ImportError:
    logger.error("无法导入spider模块，请确保项目路径正确，且已安装所需依赖")
    traceback.print_exc()
    sys.exit(1)


class ArticleFetcher:
    """文章批量爬取器，用于从多个网站批量爬取文章样本"""
    
    def __init__(
        self, 
        config_file: str = 'fetch_config.json',
        output_dir: str = 'data/samples',
        min_articles: int = 100,
        use_proxy: bool = False
    ) -> None:
        """
        初始化文章批量爬取器
        
        Args:
            config_file: 配置文件路径
            output_dir: 输出目录
            min_articles: 最少爬取文章数量
            use_proxy: 是否使用代理IP
        """
        self.config_file = config_file
        self.output_dir = output_dir
        self.min_articles = min_articles
        self.use_proxy = use_proxy
        self.config = self._load_config()
        self.websites = self.config.get('websites', [])
        self.results = {
            'total_articles': 0,
            'websites': {},
            'success_rate': 0,
            'start_time': None,
            'end_time': None,
            'duration': 0
        }
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        logger.info(f"初始化文章爬取器，目标最少文章数: {min_articles}, 是否使用代理: {use_proxy}")
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"从 {self.config_file} 加载配置成功")
                return config
            else:
                logger.warning(f"配置文件 {self.config_file} 不存在，使用默认配置")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}, 使用默认配置")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            Dict[str, Any]: 默认配置字典
        """
        return {
            "websites": [
                {
                    "name": "zhihu",
                    "base_url": "https://www.zhihu.com/column/c_1261435532773801984",
                    "max_articles": 40,
                    "thread_count": 5,
                    "delay": 2.0,
                    "incremental": True
                },
                {
                    "name": "csdn",
                    "base_url": "https://blog.csdn.net/nav/python",
                    "max_articles": 40,
                    "thread_count": 5,
                    "delay": 2.0,
                    "incremental": True
                },
                {
                    "name": "jianshu",
                    "base_url": "https://www.jianshu.com/c/V2CqjW",
                    "max_articles": 40,
                    "thread_count": 5,
                    "delay": 2.0,
                    "incremental": True
                }
            ],
            "global": {
                "timeout": 10,
                "max_retries": 3,
                "delay": 1.0,
                "proxy": {
                    "enabled": False,
                    "proxy_file": "proxies.json",
                    "max_workers": 10,
                    "check_interval": 600,
                    "fetch_interval": 3600,
                    "check_urls": [
                        "https://www.baidu.com",
                        "https://www.qq.com",
                        "https://www.sina.com.cn"
                    ],
                    "sources": [
                        "github",
                        "proxylist",
                        "free-proxy-list",
                        "cool-proxy"
                    ]
                }
            }
        }
    
    def fetch_all(self) -> Dict[str, Any]:
        """
        批量爬取所有配置的网站的文章
        
        Returns:
            Dict[str, Any]: 爬取结果统计
        """
        logger.info(f"开始批量爬取 {len(self.websites)} 个网站的文章...")
        self.results['start_time'] = time.time()
        
        total_articles = 0
        website_results = {}
        
        # 依次爬取每个网站
        for website_config in self.websites:
            website_name = website_config.get('name', 'unknown')
            try:
                # 爬取单个网站的文章
                articles, stats = self._fetch_website(website_config)
                
                # 更新结果统计
                total_articles += len(articles)
                website_results[website_name] = stats
                
                logger.info(f"成功从 {website_name} 爬取 {len(articles)} 篇文章")
                
                # 如果已达到最低文章数要求，可以提前结束
                if total_articles >= self.min_articles:
                    logger.info(f"已达到最低文章数要求 ({self.min_articles})，不再爬取其他网站")
                    break
                    
            except Exception as e:
                logger.error(f"爬取网站 {website_name} 失败: {str(e)}")
                traceback.print_exc()
                website_results[website_name] = {
                    'status': 'failed',
                    'error': str(e),
                    'articles': 0
                }
        
        # 更新结果统计
        self.results['end_time'] = time.time()
        self.results['duration'] = self.results['end_time'] - self.results['start_time']
        self.results['total_articles'] = total_articles
        self.results['websites'] = website_results
        
        # 计算成功率
        succeeded = sum(1 for stats in website_results.values() if stats.get('status') == 'success')
        if self.websites:
            self.results['success_rate'] = succeeded / len(self.websites)
        
        # 保存结果统计
        self._save_results()
        
        logger.info(f"批量爬取完成，共获取 {total_articles} 篇文章，耗时 {self.results['duration']:.2f} 秒")
        
        return self.results
    
    def _fetch_website(self, config: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        爬取单个网站的文章
        
        Args:
            config: 网站爬取配置
            
        Returns:
            Tuple[List[Dict[str, Any]], Dict[str, Any]]: 爬取到的文章列表和统计信息
        """
        website_name = config.get('name', 'unknown')
        base_url = config.get('base_url', '')
        max_articles = config.get('max_articles', 30)
        thread_count = config.get('thread_count', 5)
        delay = config.get('delay', self.config.get('global', {}).get('delay', 1.0))
        incremental = config.get('incremental', True)
        
        if not base_url:
            raise ValueError(f"网站 {website_name} 未指定base_url")
        
        logger.info(f"开始爬取网站 {website_name} (URL: {base_url})")
        
        # 计算网站特定的输出目录
        website_output_dir = os.path.join(self.output_dir, website_name)
        os.makedirs(website_output_dir, exist_ok=True)
        
        # 创建爬虫实例
        start_time = time.time()
        spider = ArticleSpider(
            base_url=base_url,
            parser_name=website_name,  # 使用网站名称作为解析器名称
            delay=delay,
            max_articles=max_articles,
            output_dir=website_output_dir,
            thread_count=thread_count,
            timeout=self.config.get('global', {}).get('timeout', 10),
            max_retries=self.config.get('global', {}).get('max_retries', 3),
            incremental=incremental,
            use_proxy=self.use_proxy
        )
        
        # 添加网站属性，以防在spider中引用
        setattr(spider, 'website', website_name)
        
        # 爬取文章
        try:
            articles = spider.crawl()
            
            # 手动保存结果，防止spider内部保存失败
            try:
                csv_file = os.path.join(website_output_dir, f'{website_name}_articles.csv')
                self._save_to_csv(articles, csv_file)
            except Exception as e:
                logger.error(f"保存爬取结果失败: {str(e)}")
                # 尝试使用Spider自带的方法保存
                try:
                    if hasattr(spider, 'save_to_csv'):
                        spider.save_to_csv()
                except Exception as e2:
                    logger.error(f"Spider保存结果也失败: {str(e2)}")
            
            end_time = time.time()
            stats = {
                'status': 'success',
                'articles': len(articles),
                'duration': end_time - start_time,
                'avg_time_per_article': (end_time - start_time) / max(len(articles), 1),
                'output_file': os.path.join(website_output_dir, f'{website_name}_articles.csv')
            }
            
            return articles, stats
            
        except Exception as e:
            logger.error(f"爬取 {website_name} 失败: {str(e)}")
            raise
    
    def _save_to_csv(self, articles: List[Dict[str, Any]], file_path: str) -> None:
        """
        将文章保存为CSV文件
        
        Args:
            articles: 文章列表
            file_path: 保存路径
        """
        if not articles:
            logger.warning(f"没有文章需要保存到 {file_path}")
            return
        
        try:
            df = pd.DataFrame(articles)
            
            # 处理可能不兼容CSV的字段
            for col in df.columns:
                if df[col].dtype == 'object':
                    # 将列表和字典转换为字符串
                    df[col] = df[col].apply(
                        lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x
                    )
            
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f"成功保存 {len(articles)} 篇文章到 {file_path}")
        except Exception as e:
            logger.error(f"保存文章到CSV失败: {str(e)}")
            traceback.print_exc()
    
    def _save_results(self) -> None:
        """保存爬取结果统计到JSON文件"""
        result_file = os.path.join(self.output_dir, 'fetch_results.json')
        try:
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            logger.info(f"爬取结果统计已保存到 {result_file}")
        except Exception as e:
            logger.error(f"保存爬取结果统计失败: {str(e)}")
    
    def merge_all_samples(self) -> str:
        """
        合并所有网站的样本文章到一个CSV文件
        
        Returns:
            str: 合并后的CSV文件路径
        """
        merged_file = os.path.join(self.output_dir, 'all_articles.csv')
        all_articles = []
        
        # 遍历所有网站的输出目录
        for website in self.websites:
            website_name = website.get('name', 'unknown')
            website_dir = os.path.join(self.output_dir, website_name)
            csv_file = os.path.join(website_dir, f'{website_name}_articles.csv')
            
            if os.path.exists(csv_file):
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8-sig')
                    # 添加来源标记
                    df['source_website'] = website_name
                    all_articles.append(df)
                    logger.info(f"从 {csv_file} 加载了 {len(df)} 篇文章")
                except Exception as e:
                    logger.error(f"读取 {csv_file} 失败: {str(e)}")
            else:
                # 尝试查找常规articles.csv文件
                alt_csv_file = os.path.join(website_dir, 'articles.csv')
                if os.path.exists(alt_csv_file):
                    try:
                        df = pd.read_csv(alt_csv_file, encoding='utf-8-sig')
                        # 添加来源标记
                        df['source_website'] = website_name
                        all_articles.append(df)
                        logger.info(f"从 {alt_csv_file} 加载了 {len(df)} 篇文章")
                    except Exception as e:
                        logger.error(f"读取 {alt_csv_file} 失败: {str(e)}")
        
        if all_articles:
            try:
                # 合并所有数据框
                merged_df = pd.concat(all_articles, ignore_index=True)
                # 保存合并后的CSV
                merged_df.to_csv(merged_file, index=False, encoding='utf-8-sig')
                logger.info(f"成功合并 {len(merged_df)} 篇文章到 {merged_file}")
                return merged_file
            except Exception as e:
                logger.error(f"合并文章样本失败: {str(e)}")
                traceback.print_exc()
        else:
            logger.warning("没有找到任何文章样本可合并")
        
        return ""


def create_default_config() -> None:
    """创建默认配置文件"""
    config_file = 'fetch_config.json'
    
    if os.path.exists(config_file):
        logger.warning(f"配置文件 {config_file} 已存在，跳过创建")
        return
    
    default_config = {
        "websites": [
            {
                "name": "zhihu",
                "base_url": "https://www.zhihu.com/column/c_1261435532773801984",
                "max_articles": 40,
                "thread_count": 5,
                "delay": 2.0,
                "incremental": True
            },
            {
                "name": "csdn",
                "base_url": "https://blog.csdn.net/nav/python",
                "max_articles": 40,
                "thread_count": 5,
                "delay": 2.0,
                "incremental": True
            },
            {
                "name": "jianshu",
                "base_url": "https://www.jianshu.com/c/V2CqjW",
                "max_articles": 40,
                "thread_count": 5,
                "delay": 2.0,
                "incremental": True
            }
        ],
        "global": {
            "timeout": 10,
            "max_retries": 3,
            "delay": 1.0,
            "proxy": {
                "enabled": False,
                "proxy_file": "proxies.json",
                "max_workers": 10,
                "check_interval": 600,
                "fetch_interval": 3600,
                "check_urls": [
                    "https://www.baidu.com",
                    "https://www.qq.com",
                    "https://www.sina.com.cn"
                ],
                "sources": [
                    "github",
                    "proxylist",
                    "free-proxy-list",
                    "cool-proxy"
                ]
            }
        }
    }
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        logger.info(f"成功创建默认配置文件 {config_file}")
    except Exception as e:
        logger.error(f"创建默认配置文件失败: {str(e)}")
        traceback.print_exc()


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description='批量爬取文章样本')
    parser.add_argument('--config', '-c', type=str, default='fetch_config.json', help='配置文件路径')
    parser.add_argument('--output', '-o', type=str, default='data/samples', help='输出目录')
    parser.add_argument('--min', '-m', type=int, default=100, help='最少爬取文章数量')
    parser.add_argument('--proxy', '-p', action='store_true', help='是否使用代理IP')
    parser.add_argument('--create-config', action='store_true', help='创建默认配置文件并退出')
    parser.add_argument('--test-site', '-t', type=str, default=None, help='只测试单个网站，输入网站名称')
    parser.add_argument('--max-per-site', type=int, default=None, help='每个网站最多爬取文章数量，覆盖配置中的设置')
    return parser.parse_args()


def main() -> None:
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_args()
        
        # 如果指定了创建配置文件选项
        if args.create_config:
            create_default_config()
            return
        
        # 创建文章爬取器
        fetcher = ArticleFetcher(
            config_file=args.config,
            output_dir=args.output,
            min_articles=args.min,
            use_proxy=args.proxy
        )
        
        # 如果指定了测试特定网站，修改网站列表
        if args.test_site:
            # 找到指定的网站
            test_site = None
            for site in fetcher.websites:
                if site.get('name') == args.test_site:
                    test_site = site
                    break
            
            if test_site:
                # 只保留指定网站
                fetcher.websites = [test_site]
                logger.info(f"测试模式：只爬取网站 {args.test_site}")
            else:
                logger.error(f"找不到指定的网站: {args.test_site}")
                return
        
        # 如果指定了每个网站的最大爬取数量
        if args.max_per_site:
            # 修改所有网站的max_articles
            for site in fetcher.websites:
                site['max_articles'] = args.max_per_site
            logger.info(f"已设置每个网站最大爬取文章数为 {args.max_per_site}")
        
        # 批量爬取文章
        results = fetcher.fetch_all()
        
        # 合并所有样本
        merged_file = fetcher.merge_all_samples()
        
        # 输出结果统计
        print("\n爬取结果统计:")
        print(f"总文章数: {results['total_articles']} 篇")
        print(f"总耗时: {results['duration']:.2f}秒")
        print(f"网站成功率: {results['success_rate'] * 100:.1f}%")
        
        if merged_file:
            print(f"\n所有文章已合并到: {merged_file}")
        
        # 更新TODO.md，标记任务为完成
        if results['total_articles'] >= args.min:
            try:
                if os.path.exists('TODO.md'):
                    with open('TODO.md', 'r', encoding='utf-8') as f:
                        todo_content = f.read()
                    
                    # 如果已经是进行中状态，则标记为完成
                    if "- [-] 爬取100篇以上文章样本" in todo_content:
                        updated_content = todo_content.replace(
                            "- [-] 爬取100篇以上文章样本", 
                            "- [x] 爬取100篇以上文章样本"
                        )
                    # 如果是未完成状态，则直接标记为完成
                    else:
                        updated_content = todo_content.replace(
                            "- [ ] 爬取100篇以上文章样本", 
                            "- [x] 爬取100篇以上文章样本"
                        )
                    
                    with open('TODO.md', 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    
                    logger.info("已更新TODO.md，标记爬取任务为已完成")
            except Exception as e:
                logger.error(f"更新TODO.md失败: {str(e)}")
    except Exception as e:
        logger.error(f"程序执行过程中发生错误: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main() 