#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试增量爬取功能
"""

import os
import time
import logging
import argparse
from spider.spider import ArticleSpider

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_incremental(website, url, threads=5, max_articles=20):
    """
    测试增量爬取功能
    
    Args:
        website: 网站名称
        url: 网站URL
        threads: 线程数
        max_articles: 最大爬取文章数
    """
    output_dir = f"data/{website}_test_incremental"
    
    # 第一次爬取
    logger.info(f"第一次爬取，目标: {max_articles//2} 篇文章")
    spider1 = ArticleSpider(
        base_url=url,
        parser_name=website,
        delay=1.0,
        max_articles=max_articles//2,  # 第一次爬取一半
        output_dir=output_dir,
        thread_count=threads,
        timeout=10,
        max_retries=3,
        incremental=False  # 非增量模式
    )
    
    start_time = time.time()
    articles1 = spider1.crawl()
    elapsed1 = time.time() - start_time
    
    logger.info(f"第一次爬取完成，获取 {len(articles1)} 篇文章，用时 {elapsed1:.2f} 秒")
    
    # 查看爬取结果
    csv_file = os.path.join(output_dir, 'articles.csv')
    visited_file = os.path.join(output_dir, 'visited_urls.json')
    
    if os.path.exists(csv_file):
        logger.info(f"CSV文件已生成: {csv_file}")
    else:
        logger.warning(f"CSV文件未生成: {csv_file}")
    
    if os.path.exists(visited_file):
        logger.warning(f"访问记录文件不应存在: {visited_file}")
    
    # 第二次爬取（增量模式）
    logger.info(f"第二次爬取（增量模式），目标: {max_articles} 篇文章")
    spider2 = ArticleSpider(
        base_url=url,
        parser_name=website,
        delay=1.0,
        max_articles=max_articles,  # 第二次设置为总数
        output_dir=output_dir,
        thread_count=threads,
        timeout=10,
        max_retries=3,
        incremental=True  # 增量模式
    )
    
    start_time = time.time()
    articles2 = spider2.crawl()
    elapsed2 = time.time() - start_time
    
    logger.info(f"第二次爬取完成，共有 {len(articles2)} 篇文章，用时 {elapsed2:.2f} 秒")
    
    # 验证结果
    if len(articles2) >= len(articles1):
        logger.info("增量爬取成功: 第二次包含了第一次的文章并新增了部分文章")
    else:
        logger.warning("增量爬取异常: 第二次爬取的文章数少于第一次")
    
    # 检查访问记录文件
    if os.path.exists(visited_file):
        logger.info(f"访问记录文件已生成: {visited_file}")
    else:
        logger.warning(f"访问记录文件未生成: {visited_file}")
    
    return {
        "first_crawl": {
            "articles": len(articles1),
            "time": elapsed1,
            "avg_time": elapsed1 / len(articles1) if articles1 else 0
        },
        "incremental_crawl": {
            "articles": len(articles2),
            "time": elapsed2,
            "avg_time": elapsed2 / len(articles2) if articles2 else 0
        }
    }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='测试增量爬取功能')
    parser.add_argument('--website', '-w', help='网站类型', default='general')
    parser.add_argument('--url', '-u', help='网站URL', required=True)
    parser.add_argument('--threads', '-t', type=int, help='线程数', default=5)
    parser.add_argument('--max', '-m', type=int, help='最大爬取文章数', default=20)
    args = parser.parse_args()
    
    results = test_incremental(
        args.website, 
        args.url, 
        args.threads, 
        args.max
    )
    
    # 输出结果比较
    logger.info("\n测试结果:")
    logger.info(f"第一次爬取: {results['first_crawl']['articles']} 篇文章，用时 {results['first_crawl']['time']:.2f} 秒")
    logger.info(f"第二次爬取: {results['incremental_crawl']['articles']} 篇文章，用时 {results['incremental_crawl']['time']:.2f} 秒")
    
    increase = results['incremental_crawl']['articles'] - results['first_crawl']['articles']
    if increase > 0:
        logger.info(f"新增 {increase} 篇文章")
    
    # 时间效率比较
    if results['first_crawl']['articles'] > 0 and results['incremental_crawl']['articles'] > 0:
        logger.info(f"第一次爬取平均用时: {results['first_crawl']['avg_time']:.2f} 秒/篇")
        logger.info(f"第二次爬取平均用时: {results['incremental_crawl']['avg_time']:.2f} 秒/篇")

if __name__ == "__main__":
    main() 