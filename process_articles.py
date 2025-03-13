"""
文章NLP处理脚本

读取已有的CSV文件，提取关键词和实体信息，并保存结果
"""

import os
import json
import time
import logging
import argparse
import pandas as pd
from typing import List, Dict, Any

# 导入自定义模块
from nlp.segmentation import create_segmenter
from nlp.tfidf import TFIDFExtractor
from nlp.entity import create_entity_extractor
from nlp.relation import create_relation_extractor

# 设置日志
logging.basicConfig(
    level=logging.DEBUG,  # 将日志级别设置为DEBUG，以获取更详细的输出
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('process_articles')

def load_config(config_file: str) -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"成功加载配置文件: {config_file}")
        logger.debug(f"配置内容: {config}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}

def load_articles_from_csv(file_path: str, encoding: str = 'utf-8') -> List[Dict[str, Any]]:
    """从CSV文件加载文章数据"""
    try:
        df = pd.read_csv(file_path, encoding=encoding)
        # 确保content列是字符串类型
        if 'content' in df.columns:
            df['content'] = df['content'].astype(str)
        articles = df.to_dict('records')
        logger.info(f"从CSV文件加载了 {len(articles)} 篇文章")
        return articles
    except Exception as e:
        logger.error(f"加载CSV文件失败: {e}")
        return []

def save_articles_to_csv(articles: List[Dict[str, Any]], file_path: str, encoding: str = 'utf-8') -> bool:
    """保存文章数据到CSV文件"""
    try:
        df = pd.DataFrame(articles)
        df.to_csv(file_path, index=False, encoding=encoding)
        logger.info(f"保存了 {len(articles)} 篇文章到 {file_path}")
        # 检查是否包含关键词和实体字段
        has_keywords = 'keywords' in df.columns
        has_entities = 'entities' in df.columns
        has_triples = 'triples' in df.columns
        logger.info(f"保存的数据包含: 关键词={has_keywords}, 实体={has_entities}, 三元组={has_triples}")
        return True
    except Exception as e:
        logger.error(f"保存CSV文件失败: {e}")
        return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='文章NLP处理工具')
    parser.add_argument('--config', '-c', help='配置文件路径', default='nlp_config.json')
    parser.add_argument('--input', '-i', help='输入CSV文件路径')
    parser.add_argument('--output', '-o', help='输出CSV文件路径')
    parser.add_argument('--debug', '-d', action='store_true', help='启用调试模式')
    return parser.parse_args()

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 如果启用了调试模式，设置日志级别为DEBUG
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("调试模式已启用")
    
    # 加载配置
    config = load_config(args.config)
    
    # 命令行参数覆盖配置文件
    input_file = args.input or config['nlp'].get('input_file')
    output_file = args.output or config['nlp'].get('output_file')
    
    if not input_file:
        logger.error("未指定输入文件")
        return
    
    if not output_file:
        output_file = input_file.replace('.csv', '_analyzed.csv')
    
    logger.info(f"输入文件: {input_file}")
    logger.info(f"输出文件: {output_file}")
    
    # 加载文章
    articles = load_articles_from_csv(input_file, config['output'].get('encoding', 'utf-8'))
    
    if not articles:
        logger.error("没有加载到文章数据")
        return
    
    logger.info(f"开始处理 {len(articles)} 篇文章")
    start_time = time.time()
    
    # 提取文章内容，用于构建语料库
    texts = []
    for article in articles:
        content = article.get('content', '')
        if content and isinstance(content, str):
            texts.append(content)
    
    logger.info(f"构建语料库，共 {len(texts)} 篇文章")
    
    # 创建分词器
    segmenter = create_segmenter(config['nlp']['segmenter'])
    logger.info(f"创建分词器: {config['nlp']['segmenter']}")
    
    # 创建TF-IDF提取器
    tfidf_extractor = TFIDFExtractor(segmenter)
    logger.info("创建TF-IDF提取器")
    tfidf_extractor.add_corpus(texts)
    logger.info("TF-IDF语料库构建完成")
    
    # 创建实体提取器
    entity_extractor = None
    if config['nlp']['entity_extractor'].lower() != 'none':
        try:
            logger.info(f"尝试创建实体提取器: {config['nlp']['entity_extractor']}")
            entity_extractor = create_entity_extractor(config['nlp']['entity_extractor'])
            logger.info(f"实体提取器创建成功: {type(entity_extractor).__name__}")
        except Exception as e:
            logger.error(f"创建实体提取器失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            entity_extractor = None
    else:
        logger.info("实体提取已禁用")
    
    # 创建关系提取器
    relation_extractor = None
    if config['nlp']['relation'].lower() != 'none':
        try:
            logger.info(f"尝试创建关系提取器: {config['nlp']['relation']}")
            relation_extractor = create_relation_extractor(config['nlp']['relation'])
            logger.info(f"关系提取器创建成功: {type(relation_extractor).__name__}")
        except Exception as e:
            logger.error(f"创建关系提取器失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            relation_extractor = None
    else:
        logger.info("关系提取已禁用")
    
    # 处理每篇文章
    keywords_count = 0
    entities_count = 0
    triples_count = 0
    
    for i, article in enumerate(articles):
        logger.info(f"处理文章 {i+1}/{len(articles)}: {article.get('title', '未知标题')}")
        
        # 提取文章内容
        content = article.get('content', '')
        if not content or not isinstance(content, str):
            logger.warning(f"文章 {i+1} 没有有效的内容或内容不是字符串类型")
            continue
        
        # 提取关键词
        try:
            keywords = tfidf_extractor.extract_keywords(content, config['nlp']['top_keywords'])
            article['keywords'] = ','.join([keyword for keyword, _ in keywords])
            keywords_count += 1
            logger.debug(f"文章 {i+1} 提取关键词: {article['keywords']}")
        except Exception as e:
            logger.error(f"提取关键词失败: {e}")
        
        # 提取实体
        if entity_extractor:
            try:
                entities = entity_extractor.extract_entities(content)
                article['entities'] = json.dumps(entities, ensure_ascii=False)
                entities_count += 1
                logger.debug(f"文章 {i+1} 提取实体: {article['entities']}")
            except Exception as e:
                logger.error(f"提取实体失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # 提取关系三元组
        if relation_extractor:
            try:
                triples = relation_extractor.extract_triples(content)
                article['triples'] = json.dumps([triple.to_dict() for triple in triples], ensure_ascii=False)
                triples_count += 1
                logger.debug(f"文章 {i+1} 提取三元组: {article['triples']}")
            except Exception as e:
                logger.error(f"提取关系三元组失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
    
    logger.info(f"NLP处理完成，耗时 {time.time() - start_time:.2f} 秒")
    logger.info(f"处理结果: 关键词={keywords_count}, 实体={entities_count}, 三元组={triples_count}")
    
    # 保存结果
    save_articles_to_csv(articles, output_file, config['output'].get('encoding', 'utf-8'))
    
    logger.info("NLP分析处理已完成")
    logger.info(f"要查看可视化结果，请运行: python -m visualization.app --file {output_file}")

if __name__ == "__main__":
    main() 