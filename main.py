"""
文章爬取与分析系统主程序

爬取文章、进行NLP分析并生成结果
"""

import os
import json
import time
import logging
import argparse
import pandas as pd
from typing import List, Dict, Any

# 导入自定义模块
from spider.spider import ArticleSpider
from spider.proxy_pool import ProxyPool
from nlp.segmentation import create_segmenter
from nlp.tfidf import TFIDFExtractor
from nlp.entity import create_entity_extractor
from nlp.relation import create_relation_extractor

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('main')

# 默认配置
DEFAULT_CONFIG = {
    'spider': {
        'website': 'zhihu',  # 目标网站
        'base_url': 'https://www.zhihu.com',  # 网站URL
        'delay': 2.0,  # 爬取延迟
        'max_articles': 100,  # 最大爬取文章数
        'output_dir': 'data',  # 输出目录
        'thread_count': 5,  # 爬虫线程数
        'timeout': 10,  # 请求超时时间(秒)
        'max_retries': 3,  # 最大重试次数
        'incremental': False,
        'use_proxy': False,   # 是否使用代理
        'proxy': {
            'enabled': False,
            'proxy_file': 'proxies.json',
            'check_interval': 600,  # 代理检查间隔（秒）
            'fetch_interval': 3600,  # 代理获取间隔（秒）
            'max_workers': 10,  # 代理检查最大线程数
            'timeout': 5  # 代理超时时间（秒）
        }
    },
    'nlp': {
        'segmenter': 'jieba',  # 分词器
        'extractor': 'hanlp',  # 实体提取器
        'relation': 'hanlp',   # 关系提取器
        'use_stopwords': True, # 是否使用停用词
        'top_keywords': 5,      # 每篇文章提取的关键词数量
        'keywords_count': 10,
        'summary_sentences': 3
    },
    'output': {
        'csv_file': 'articles.csv',  # 输出CSV文件名
        'encoding': 'utf-8-sig'      # 文件编码
    }
}


def load_config(config_file: str) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置字典
    """
    config = DEFAULT_CONFIG.copy()
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                
            # 合并用户配置
            for section, section_config in user_config.items():
                if section in config:
                    config[section].update(section_config)
                else:
                    config[section] = section_config
                    
            logger.info(f"已加载配置文件: {config_file}")
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")
    else:
        logger.warning(f"配置文件不存在: {config_file}，使用默认配置")
    
    return config


def save_articles_to_csv(articles: List[Dict[str, Any]], output_file: str, encoding: str = 'utf-8-sig') -> None:
    """
    将文章保存为CSV文件
    
    Args:
        articles: 文章列表
        output_file: 输出文件路径
        encoding: 文件编码
    """
    if not articles:
        logger.warning("没有文章可保存")
        return
    
    try:
        df = pd.DataFrame(articles)
        df.to_csv(output_file, index=False, encoding=encoding)
        logger.info(f"已将 {len(articles)} 篇文章保存至: {output_file}")
    except Exception as e:
        logger.error(f"保存CSV文件失败: {e}")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='文章爬取与分析工具')
    parser.add_argument('--config', '-c', help='配置文件路径', default='config.json')
    parser.add_argument('--url', '-u', help='要爬取的网站URL')
    parser.add_argument('--output', '-o', help='输出目录')
    parser.add_argument('--delay', '-d', type=float, help='请求间隔(秒)')
    parser.add_argument('--max', '-m', type=int, help='最大爬取文章数')
    parser.add_argument('--threads', '-t', type=int, help='爬取线程数')
    parser.add_argument('--incremental', '-i', action='store_true', help='增量爬取，跳过已爬取的文章')
    parser.add_argument('--proxy', '-p', action='store_true', help='使用代理IP池')
    parser.add_argument('--analyzer', '-a', choices=['keywords', 'summary', 'entities', 'sentiment', 'all'], 
                        help='分析器类型', default='all')
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 命令行参数覆盖配置文件
    if args.url:
        config['spider']['base_url'] = args.url
    if args.output:
        config['spider']['output_dir'] = args.output
    if args.delay:
        config['spider']['delay'] = args.delay
    if args.max:
        config['spider']['max_articles'] = args.max
    if args.threads:
        config['spider']['thread_count'] = args.threads
    if args.incremental:
        config['spider']['incremental'] = True
    if args.proxy:
        config['spider']['use_proxy'] = True
        config['spider']['proxy']['enabled'] = True
    
    # 输出目录
    output_dir = config['spider']['output_dir']
    os.makedirs(output_dir, exist_ok=True)
    
    # 输出文件路径
    output_file = os.path.join(output_dir, config['output']['csv_file'])
    
    # 爬取文章
    articles = []
    
    if not args.incremental:
        logger.info("开始爬取文章")
        start_time = time.time()
        
        # 初始化代理池（如果配置了使用代理）
        proxy_pool = None
        if config['spider']['use_proxy'] and config['spider']['proxy']['enabled']:
            logger.info("初始化代理IP池")
            try:
                proxy_config = config['spider']['proxy']
                proxy_file = os.path.join(output_dir, proxy_config['proxy_file'])
                
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
                config['spider']['use_proxy'] = False
                logger.warning("已禁用代理功能")
        
        # 创建爬虫
        spider = ArticleSpider(
            base_url=config['spider']['base_url'],
            parser_name=config['spider']['website'],
            delay=config['spider']['delay'],
            max_articles=config['spider']['max_articles'],
            output_dir=output_dir,
            thread_count=config['spider']['thread_count'],
            timeout=config['spider']['timeout'],
            max_retries=config['spider']['max_retries'],
            incremental=config['spider']['incremental'],
            use_proxy=config['spider']['use_proxy'],
            proxy_file=os.path.join(output_dir, config['spider']['proxy'].get('proxy_file', 'proxies.json')),
            proxy_pool=proxy_pool
        )
        
        # 爬取文章
        try:
            articles = spider.crawl()
            logger.info(f"爬取完成，共获取 {len(articles)} 篇文章，耗时 {time.time() - start_time:.2f} 秒")
        except Exception as e:
            logger.error(f"爬取文章失败: {e}")
            return
    else:
        # 从CSV加载已有数据
        if os.path.exists(output_file):
            try:
                df = pd.read_csv(output_file)
                articles = df.to_dict('records')
                logger.info(f"已从 {output_file} 加载 {len(articles)} 篇文章")
            except Exception as e:
                logger.error(f"加载CSV文件失败: {e}")
                return
        else:
            logger.error(f"文件不存在: {output_file}")
            return
    
    # NLP处理
    if articles:
        logger.info("开始NLP处理")
        start_time = time.time()
        
        # 创建分词器
        segmenter = create_segmenter(config['nlp']['segmenter'])
        
        # 创建TF-IDF提取器
        tfidf_extractor = TFIDFExtractor(segmenter)
        
        # 添加语料库
        texts = [article['content'] for article in articles if 'content' in article]
        tfidf_extractor.add_corpus(texts)
        
        # 创建实体提取器
        try:
            entity_extractor = create_entity_extractor(config['nlp']['extractor'])
        except Exception as e:
            logger.error(f"创建实体提取器失败: {e}")
            entity_extractor = None
        
        # 创建关系提取器
        try:
            relation_extractor = create_relation_extractor(config['nlp']['relation'])
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
            keywords = tfidf_extractor.extract_keywords(content, config['nlp']['top_keywords'])
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
        
        logger.info(f"NLP处理完成，耗时 {time.time() - start_time:.2f} 秒")
    
    # 保存结果
    save_articles_to_csv(articles, output_file, config['output']['encoding'])
    
    # 启动可视化Web应用
    logger.info("NLP分析处理已完成")
    logger.info(f"要查看可视化结果，请运行: python -m visualization.app")


if __name__ == "__main__":
    main()