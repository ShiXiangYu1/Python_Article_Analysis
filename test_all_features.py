#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
全功能测试脚本
用于测试系统的所有功能，包括爬虫、NLP分析和可视化
"""

import os
import sys
import json
import time
import logging
import argparse
import pandas as pd
from typing import Dict, Any, List, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_all_features.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('test_all_features')

# 添加项目根目录到系统路径
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# 导入项目模块
from spider.spider import ArticleSpider
from spider.proxy_pool import ProxyPool
from nlp.segmentation import create_segmenter
from nlp.tfidf import TFIDFExtractor
from nlp.entity import create_entity_extractor
from nlp.relation import create_relation_extractor
import visualization.app as viz_app


def load_config(config_file: str) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置字典
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"已加载配置文件: {config_file}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}


def test_spider(config: Dict[str, Any], max_articles: int = 5) -> List[Dict[str, Any]]:
    """
    测试爬虫功能
    
    Args:
        config: 配置字典
        max_articles: 最大爬取文章数
        
    Returns:
        爬取的文章列表
    """
    logger.info("开始测试爬虫功能")
    
    # 修改配置，限制爬取文章数量
    spider_config = config.get('spider', {})
    spider_config['max_articles'] = max_articles
    
    # 创建输出目录
    output_dir = spider_config.get('output_dir', 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化代理池（如果配置了使用代理）
    proxy_pool = None
    if spider_config.get('use_proxy', False) and spider_config.get('proxy', {}).get('enabled', False):
        logger.info("初始化代理IP池")
        try:
            proxy_config = spider_config.get('proxy', {})
            proxy_file = os.path.join(output_dir, proxy_config.get('proxy_file', 'proxies.json'))
            
            proxy_pool = ProxyPool(
                proxy_file=proxy_file,
                check_interval=proxy_config.get('check_interval', 600)
            )
            
            # 获取初始代理
            proxy_count = proxy_pool.fetch_proxies_from_sources()
            logger.info(f"从代理源获取了 {proxy_count} 个代理")
            
        except Exception as e:
            logger.error(f"初始化代理池失败: {e}")
            # 如果代理池初始化失败，禁用代理
            spider_config['use_proxy'] = False
            logger.warning("已禁用代理功能")
    
    # 创建爬虫
    spider = ArticleSpider(
        base_url=spider_config.get('base_url', 'https://www.zhihu.com'),
        parser_name=spider_config.get('website', 'zhihu'),
        delay=spider_config.get('delay', 2.0),
        max_articles=spider_config.get('max_articles', 5),
        output_dir=output_dir,
        thread_count=spider_config.get('thread_count', 5),
        timeout=spider_config.get('timeout', 10),
        max_retries=spider_config.get('max_retries', 3),
        incremental=spider_config.get('incremental', False),
        use_proxy=spider_config.get('use_proxy', False),
        proxy_file=os.path.join(output_dir, spider_config.get('proxy', {}).get('proxy_file', 'proxies.json')),
        proxy_pool=proxy_pool
    )
    
    # 爬取文章
    try:
        start_time = time.time()
        articles = spider.crawl()
        elapsed_time = time.time() - start_time
        logger.info(f"爬取完成，共获取 {len(articles)} 篇文章，耗时 {elapsed_time:.2f} 秒")
        
        # 保存文章
        output_file = os.path.join(output_dir, config.get('output', {}).get('csv_file', 'articles.csv'))
        encoding = config.get('output', {}).get('encoding', 'utf-8-sig')
        
        if articles:
            df = pd.DataFrame(articles)
            df.to_csv(output_file, index=False, encoding=encoding)
            logger.info(f"已将 {len(articles)} 篇文章保存至: {output_file}")
        
        return articles
    except Exception as e:
        logger.error(f"爬取文章失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def test_nlp(config: Dict[str, Any], articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    测试NLP功能
    
    Args:
        config: 配置字典
        articles: 文章列表
        
    Returns:
        处理后的文章列表
    """
    logger.info("开始测试NLP功能")
    
    if not articles:
        logger.warning("没有文章可处理")
        return []
    
    try:
        start_time = time.time()
        
        # 创建分词器
        nlp_config = config.get('nlp', {})
        segmenter = create_segmenter(nlp_config.get('segmenter', 'jieba'))
        
        # 创建TF-IDF提取器
        tfidf_extractor = TFIDFExtractor(segmenter)
        
        # 添加语料库
        texts = [article['content'] for article in articles if 'content' in article]
        tfidf_extractor.add_corpus(texts)
        
        # 创建实体提取器
        try:
            entity_extractor = create_entity_extractor(nlp_config.get('extractor', 'hanlp'))
        except Exception as e:
            logger.error(f"创建实体提取器失败: {e}")
            entity_extractor = None
        
        # 创建关系提取器
        try:
            relation_extractor = create_relation_extractor(nlp_config.get('relation', 'hanlp'))
        except Exception as e:
            logger.error(f"创建关系提取器失败: {e}")
            relation_extractor = None
        
        # 处理每篇文章
        for i, article in enumerate(articles):
            logger.info(f"处理文章 {i+1}/{len(articles)}: {article.get('title', '未知标题')}")
            
            # 提取文章内容
            content = article.get('content', '')
            if not content:
                continue
            
            # 提取关键词
            keywords = tfidf_extractor.extract_keywords(content, nlp_config.get('top_keywords', 5))
            article['keywords'] = ','.join([keyword for keyword, _ in keywords])
            
            # 提取实体
            if entity_extractor:
                try:
                    entities = entity_extractor.extract_entities(content)
                    article['entities'] = json.dumps(entities, ensure_ascii=False)
                except Exception as e:
                    logger.error(f"提取实体失败: {e}")
            
            # 提取关系三元组
            if relation_extractor:
                try:
                    triples = relation_extractor.extract_triples(content)
                    article['triples'] = json.dumps([triple.to_dict() for triple in triples], ensure_ascii=False)
                except Exception as e:
                    logger.error(f"提取关系三元组失败: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"NLP处理完成，耗时 {elapsed_time:.2f} 秒")
        
        # 保存处理后的文章
        output_dir = config.get('spider', {}).get('output_dir', 'data')
        output_file = os.path.join(output_dir, config.get('output', {}).get('csv_file', 'articles.csv'))
        encoding = config.get('output', {}).get('encoding', 'utf-8-sig')
        
        if articles:
            df = pd.DataFrame(articles)
            df.to_csv(output_file, index=False, encoding=encoding)
            logger.info(f"已将处理后的 {len(articles)} 篇文章保存至: {output_file}")
        
        return articles
    except Exception as e:
        logger.error(f"NLP处理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return articles


def test_visualization(config: Dict[str, Any]) -> bool:
    """
    测试可视化功能
    
    Args:
        config: 配置字典
        
    Returns:
        测试是否成功
    """
    logger.info("开始测试可视化功能")
    
    try:
        # 检查数据文件
        output_dir = config.get('spider', {}).get('output_dir', 'data')
        output_file = os.path.join(output_dir, config.get('output', {}).get('csv_file', 'articles.csv'))
        
        if not os.path.exists(output_file):
            logger.error(f"数据文件不存在: {output_file}")
            return False
        
        # 加载数据
        df = pd.read_csv(output_file)
        if df.empty:
            logger.error(f"数据文件为空: {output_file}")
            return False
        
        logger.info(f"已加载 {len(df)} 篇文章")
        
        # 测试生成图表
        logger.info("测试生成关系图谱")
        for i in range(min(3, len(df))):
            try:
                # 获取三元组
                triples_str = df.iloc[i].get('triples', '[]')
                triples = json.loads(triples_str) if triples_str and triples_str != '[]' else []
                
                if triples:
                    # 生成关系图谱
                    graph = viz_app.generate_relation_graph(triples)
                    logger.info(f"成功为文章 {i+1} 生成关系图谱，包含 {len(triples)} 个三元组")
                else:
                    logger.warning(f"文章 {i+1} 没有关系三元组")
            except Exception as e:
                logger.error(f"为文章 {i+1} 生成关系图谱失败: {e}")
        
        # 测试生成关键词云
        logger.info("测试生成关键词云")
        try:
            wordcloud = viz_app.generate_keyword_cloud(df)
            logger.info("成功生成关键词云")
        except Exception as e:
            logger.error(f"生成关键词云失败: {e}")
        
        # 测试生成实体统计
        logger.info("测试生成实体统计")
        try:
            entity_bar = viz_app.generate_entity_bar(df)
            logger.info("成功生成实体统计")
        except Exception as e:
            logger.error(f"生成实体统计失败: {e}")
        
        logger.info("可视化功能测试完成")
        return True
    except Exception as e:
        logger.error(f"可视化测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='全功能测试脚本')
    parser.add_argument('--config', '-c', default='config.json', help='配置文件路径')
    parser.add_argument('--max', '-m', type=int, default=5, help='最大爬取文章数')
    parser.add_argument('--spider', '-s', action='store_true', help='只测试爬虫功能')
    parser.add_argument('--nlp', '-n', action='store_true', help='只测试NLP功能')
    parser.add_argument('--visualization', '-v', action='store_true', help='只测试可视化功能')
    parser.add_argument('--all', '-a', action='store_true', help='测试所有功能')
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        logger.error("加载配置失败，退出测试")
        return
    
    # 测试爬虫功能
    articles = []
    if args.spider or args.all or (not args.nlp and not args.visualization):
        articles = test_spider(config, args.max)
    
    # 测试NLP功能
    if args.nlp or args.all or (not args.spider and not args.visualization):
        # 如果没有文章，尝试从文件加载
        if not articles:
            output_dir = config.get('spider', {}).get('output_dir', 'data')
            output_file = os.path.join(output_dir, config.get('output', {}).get('csv_file', 'articles.csv'))
            
            if os.path.exists(output_file):
                try:
                    df = pd.read_csv(output_file)
                    articles = df.to_dict('records')
                    logger.info(f"已从 {output_file} 加载 {len(articles)} 篇文章")
                except Exception as e:
                    logger.error(f"加载文章失败: {e}")
        
        if articles:
            articles = test_nlp(config, articles)
    
    # 测试可视化功能
    if args.visualization or args.all or (not args.spider and not args.nlp):
        test_visualization(config)
    
    logger.info("全功能测试完成")


if __name__ == '__main__':
    main() 