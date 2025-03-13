#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试多线程爬虫功能
"""

import os
import time
import argparse
import logging
from spider.spider import ArticleSpider

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_spider')

def test_spider(website: str, url: str, threads: int = 1, max_articles: int = 10):
    """
    测试爬虫功能
    
    Args:
        website: 网站名称
        url: 网站URL
        threads: 线程数
        max_articles: 最大爬取文章数
    """
    logger.info(f"开始测试爬虫 - 网站: {website}, URL: {url}, 线程数: {threads}, 最大文章数: {max_articles}")
    
    # 创建输出目录
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建爬虫实例
    spider = ArticleSpider(
        base_url=url,
        website=website,
        output_dir=output_dir,
        delay=1.0,  # 小延迟用于测试
        max_articles=max_articles,
        thread_count=threads,
        timeout=10,
        max_retries=2
    )
    
    # 测试单线程爬取
    if threads == 1:
        logger.info("使用单线程爬取")
        start_time = time.time()
        articles = spider.crawl()
        elapsed = time.time() - start_time
    else:
        # 测试多线程爬取
        logger.info(f"使用多线程爬取 (线程数: {threads})")
        start_time = time.time()
        articles = spider.crawl()
        elapsed = time.time() - start_time
    
    # 输出结果
    logger.info(f"爬取完成，共获取 {len(articles)} 篇文章")
    logger.info(f"耗时: {elapsed:.2f} 秒")
    logger.info(f"平均每篇文章耗时: {elapsed / max(len(articles), 1):.2f} 秒")
    
    # 输出文章标题
    logger.info("爬取的文章:")
    for i, article in enumerate(articles[:5]):  # 只显示前5篇
        logger.info(f"  {i+1}. {article.get('title', '无标题')} - {article.get('url', '无链接')}")
    
    if len(articles) > 5:
        logger.info(f"  ... 以及其他 {len(articles) - 5} 篇文章")
    
    return articles, elapsed

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='测试多线程爬虫功能')
    parser.add_argument('--website', type=str, default='zhihu', help='网站名称 (zhihu/csdn/jianshu)')
    parser.add_argument('--url', type=str, help='网站URL')
    parser.add_argument('--threads', type=int, default=5, help='线程数')
    parser.add_argument('--max', type=int, default=10, help='最大爬取文章数')
    args = parser.parse_args()
    
    # 设置默认URL
    if not args.url:
        if args.website == 'zhihu':
            args.url = 'https://www.zhihu.com/column/c_1261435532773801984'  # 知乎专栏示例
        elif args.website == 'csdn':
            args.url = 'https://blog.csdn.net/nav/python'  # CSDN Python话题
        elif args.website == 'jianshu':
            args.url = 'https://www.jianshu.com/c/V2CqjW'  # 简书专题示例
        else:
            args.url = 'https://www.zhihu.com/column/c_1261435532773801984'  # 默认使用知乎
    
    # 测试爬虫
    test_spider(args.website, args.url, args.threads, args.max)
    
    # 比较单线程和多线程性能（可选）
    if args.threads > 1 and args.max >= 5:
        logger.info("\n性能比较测试:")
        logger.info("使用单线程爬取相同数量的文章进行比较...")
        
        # 单线程测试
        _, single_elapsed = test_spider(args.website, args.url, 1, min(args.max, 5))
        
        # 多线程测试
        _, multi_elapsed = test_spider(args.website, args.url, args.threads, min(args.max, 5))
        
        # 输出比较结果
        logger.info("\n性能比较结果:")
        logger.info(f"单线程耗时: {single_elapsed:.2f} 秒")
        logger.info(f"多线程耗时: {multi_elapsed:.2f} 秒")
        logger.info(f"性能提升: {(single_elapsed / multi_elapsed):.2f}x")

if __name__ == "__main__":
    main() 