"""
Flask Web应用

用于展示文章分析结果和关系图谱
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Counter
from flask import Flask, render_template, request, jsonify
from pyecharts import options as opts
from pyecharts.charts import Graph, WordCloud, Pie, Bar, Line, Scatter
from pyecharts.globals import ThemeType
from pyecharts.commons.utils import JsCode
from collections import Counter
import jieba
import re
import argparse

app = Flask(__name__)

# 图表配置
chart_config = {
    'width': '100%',
    'height': '800px',
    'theme': ThemeType.INFOGRAPHIC
}

# CSV数据文件路径
DEFAULT_DATA_PATH = '../data/samples/all_articles.csv'  # 修改为用户提供的路径


def load_data(file_path: str = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """
    加载文章数据
    
    Args:
        file_path: CSV文件路径
        
    Returns:
        DataFrame形式的文章数据
    """
    print(f"尝试加载数据文件: {file_path}")
    
    # 检查文件路径是否为相对路径，如果是，则转换为绝对路径
    if not os.path.isabs(file_path):
        abs_path = os.path.abspath(file_path)
        print(f"转换为绝对路径: {abs_path}")
    else:
        abs_path = file_path
    
    # 检查文件是否存在
    if not os.path.exists(abs_path):
        print(f"错误: 文件不存在: {abs_path}")
        
        # 尝试其他可能的路径
        alt_path = os.path.join(os.getcwd(), file_path)
        print(f"尝试替代路径: {alt_path}")
        
        if os.path.exists(alt_path):
            print(f"找到文件在替代路径: {alt_path}")
            abs_path = alt_path
        else:
            print(f"错误: 替代路径也不存在: {alt_path}")
            
            # 尝试直接使用用户提供的路径
            user_path = 'E:/cursor/202503+/爬取接单/data/samples/all_articles.csv'
            print(f"尝试用户提供的路径: {user_path}")
            if os.path.exists(user_path):
                print(f"找到文件在用户提供的路径: {user_path}")
                abs_path = user_path
            else:
                print(f"错误: 用户提供的路径也不存在: {user_path}")
                return pd.DataFrame()
    
    try:
        print(f"正在读取文件: {abs_path}")
        df = pd.read_csv(abs_path)
        print(f"成功加载数据: {len(df)} 行, 列: {list(df.columns)}")
        return df
    except Exception as e:
        print(f"加载数据失败: {e}")
        import traceback
        print(traceback.format_exc())
        return pd.DataFrame()


def parse_triples(triples_str: str) -> List[Dict[str, str]]:
    """
    解析三元组字符串
    
    Args:
        triples_str: 三元组字符串
        
    Returns:
        三元组字典列表
    """
    if not triples_str or pd.isna(triples_str):
        return []
        
    try:
        # 尝试从JSON字符串解析
        return json.loads(triples_str)
    except:
        # 如果不是JSON格式，尝试从自定义格式解析
        triples = []
        for triple_str in triples_str.split(';'):
            triple_str = triple_str.strip()
            if not triple_str:
                continue
                
            if triple_str.startswith('(') and triple_str.endswith(')'):
                triple_str = triple_str[1:-1]
                
            parts = [p.strip() for p in triple_str.split(',')]
            if len(parts) >= 3:
                triples.append({
                    'subject': parts[0],
                    'predicate': parts[1],
                    'object': parts[2]
                })
        
        return triples


def generate_relation_graph(triples: List[Dict[str, str]]) -> Graph:
    """
    生成关系图谱
    
    Args:
        triples: 三元组列表
        
    Returns:
        ECharts图表实例
    """
    nodes = []
    links = []
    
    # 统计节点
    node_map = {}
    node_count = {}
    
    for triple in triples:
        subject = triple['subject']
        predicate = triple['predicate']
        obj = triple['object']
        
        # 统计主体节点
        if subject not in node_map:
            node_count[subject] = node_count.get(subject, 0) + 1
            node_map[subject] = len(node_map)
            nodes.append({
                "name": subject,
                "symbolSize": 30,
                "category": 0
            })
        else:
            node_count[subject] = node_count.get(subject, 0) + 1
        
        # 统计客体节点
        if obj not in node_map:
            node_count[obj] = node_count.get(obj, 0) + 1
            node_map[obj] = len(node_map)
            nodes.append({
                "name": obj,
                "symbolSize": 30,
                "category": 1
            })
        else:
            node_count[obj] = node_count.get(obj, 0) + 1
        
        # 添加关系边
        links.append({
            "source": subject,
            "target": obj,
            "value": predicate
        })
    
    # 根据节点出现次数调整大小
    for node in nodes:
        count = node_count.get(node["name"], 1)
        node["symbolSize"] = min(30 + count * 3, 80)
    
    # 创建图表
    c = (
        Graph(init_opts=opts.InitOpts(
            width=chart_config['width'],
            height=chart_config['height'],
            theme=chart_config['theme']
        ))
        .add(
            "",
            nodes=nodes,
            links=links,
            categories=[
                {"name": "主体"},
                {"name": "客体"}
            ],
            layout="force",
            is_draggable=True,
            repulsion=5000,  # 节点之间的斥力，值越大间距越大
            gravity=0.2,     # 引力，值越大布局越紧凑
            edge_length=100, # 边的长度
            linestyle_opts=opts.LineStyleOpts(
                width=1,
                curve=0.3,
                opacity=0.8
            ),
            label_opts=opts.LabelOpts(
                is_show=True,
                position="right",
                font_size=12
            ),
            edge_label=opts.LabelOpts(
                is_show=True,
                position="middle",
                formatter="{c}"
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="文章关系图谱"
            ),
            tooltip_opts=opts.TooltipOpts(
                is_show=True,
                formatter=JsCode(
                    "function(params){"
                    "    if(params.dataType === 'node'){"
                    "        return '实体: ' + params.name + '<br/>出现次数: ' + params.data.symbolSize;"
                    "    }else{"
                    "        return '关系: ' + params.value;"
                    "    }"
                    "}"
                )
            ),
            legend_opts=opts.LegendOpts(
                is_show=True,
                pos_left="left",
                orient="vertical"
            )
        )
    )
    
    return c


def generate_keyword_cloud(df: pd.DataFrame) -> WordCloud:
    """
    生成关键词词云图
    
    Args:
        df: 文章数据DataFrame
    
    Returns:
        ECharts词云图实例
    """
    keywords = []
    
    # 提取所有关键词
    for _, row in df.iterrows():
        if 'keywords' in row and not pd.isna(row['keywords']):
            kw_list = row['keywords'].split(',')
            keywords.extend([kw.strip() for kw in kw_list if kw.strip()])
    
    # 统计词频
    keyword_count = Counter(keywords)
    keywords_data = [(k, v) for k, v in keyword_count.items() if k]
    
    # 创建词云图
    c = (
        WordCloud(init_opts=opts.InitOpts(
            width="100%",
            height="600px",
            theme=chart_config['theme']
        ))
        .add(
            series_name="关键词",
            data_pair=keywords_data,
            word_size_range=[15, 100],
            shape="circle",
            textstyle_opts=opts.TextStyleOpts(font_family="微软雅黑"),
            tooltip_opts=opts.TooltipOpts(is_show=True)
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="文章关键词分布",
                subtitle="基于所有文章的关键词统计"
            ),
            tooltip_opts=opts.TooltipOpts(
                is_show=True,
                formatter="{b}: {c}"
            )
        )
    )
    
    return c


def generate_entity_bar(df: pd.DataFrame, entity_type: str = 'all') -> Bar:
    """
    生成实体统计柱状图
    
    Args:
        df: 文章数据DataFrame
        entity_type: 实体类型(all, person, place, organization)
    
    Returns:
        ECharts柱状图实例
    """
    entities = []
    
    # 提取所有实体
    for _, row in df.iterrows():
        if 'entities' in row and not pd.isna(row['entities']):
            try:
                entity_dict = json.loads(row['entities'])
                
                if entity_type == 'all' or entity_type == 'person':
                    entities.extend(entity_dict.get('person', []))
                
                if entity_type == 'all' or entity_type == 'place':
                    entities.extend(entity_dict.get('place', []))
                
                if entity_type == 'all' or entity_type == 'organization':
                    entities.extend(entity_dict.get('organization', []))
            except:
                pass
    
    # 统计实体出现次数
    entity_count = Counter(entities)
    
    # 取前20个最多出现的实体
    top_entities = entity_count.most_common(20)
    
    entity_names = [item[0] for item in top_entities]
    entity_counts = [item[1] for item in top_entities]
    
    # 创建柱状图
    c = (
        Bar(init_opts=opts.InitOpts(
            width="100%",
            height="600px",
            theme=chart_config['theme']
        ))
        .add_xaxis(entity_names)
        .add_yaxis("出现次数", entity_counts)
        .reversal_axis()  # 水平显示
        .set_series_opts(
            label_opts=opts.LabelOpts(position="right")
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title=f"实体统计{'(全部)' if entity_type == 'all' else f'({entity_type})'}"
            ),
            yaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(rotate=-15)
            ),
            xaxis_opts=opts.AxisOpts(
                name="出现次数"
            ),
            tooltip_opts=opts.TooltipOpts(
                is_show=True,
                formatter="{b}: {c}"
            )
        )
    )
    
    return c


def generate_sentiment_pie(df: pd.DataFrame) -> Pie:
    """
    生成情感分析饼图
    
    Args:
        df: 文章数据DataFrame
    
    Returns:
        ECharts饼图实例
    """
    sentiment_count = {"正面": 0, "中性": 0, "负面": 0}
    
    # 提取情感分析结果
    for _, row in df.iterrows():
        if 'sentiment' in row and not pd.isna(row['sentiment']):
            try:
                sentiment = float(row['sentiment'])
                if sentiment > 0.6:
                    sentiment_count["正面"] += 1
                elif sentiment < 0.4:
                    sentiment_count["负面"] += 1
                else:
                    sentiment_count["中性"] += 1
            except:
                sentiment_count["中性"] += 1
        else:
            sentiment_count["中性"] += 1
    
    # 转换为饼图数据格式
    data_pair = [(k, v) for k, v in sentiment_count.items()]
    
    # 创建饼图
    c = (
        Pie(init_opts=opts.InitOpts(
            width="100%",
            height="400px",
            theme=chart_config['theme']
        ))
        .add(
            series_name="情感分布",
            data_pair=data_pair,
            radius=["40%", "70%"],  # 环形图
            label_opts=opts.LabelOpts(
                formatter="{b}: {c} ({d}%)"
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="文章情感分析",
                subtitle="基于所有文章的情感分布"
            ),
            legend_opts=opts.LegendOpts(
                orient="vertical",
                pos_left="left"
            )
        )
    )
    
    return c


def generate_topic_distribution(df: pd.DataFrame) -> Pie:
    """
    生成主题分布图
    
    Args:
        df: 文章数据DataFrame
    
    Returns:
        ECharts饼图实例
    """
    # 使用关键词模拟主题分布
    topics = []
    
    for _, row in df.iterrows():
        if 'keywords' in row and not pd.isna(row['keywords']):
            keywords = row['keywords'].split(',')
            if keywords:
                # 取第一个关键词作为主题（简化处理）
                topics.append(keywords[0].strip())
    
    # 统计主题分布
    topic_count = Counter(topics)
    
    # 获取前10个主题
    top_topics = topic_count.most_common(10)
    
    # 如果不足10个，添加"其他"类别
    if len(topics) > len(top_topics):
        other_count = len(topics) - sum(count for _, count in top_topics)
        if other_count > 0:
            top_topics.append(("其他", other_count))
    
    # 创建饼图
    c = (
        Pie(init_opts=opts.InitOpts(
            width="100%",
            height="500px",
            theme=chart_config['theme']
        ))
        .add(
            series_name="主题分布",
            data_pair=top_topics,
            radius=["30%", "75%"],
            label_opts=opts.LabelOpts(
                formatter="{b}: {c} ({d}%)"
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="文章主题分布",
                subtitle="基于关键词的主题聚类"
            ),
            legend_opts=opts.LegendOpts(
                type_="scroll",
                pos_left="right",
                orient="vertical"
            )
        )
    )
    
    return c


def generate_article_length_histogram(df: pd.DataFrame) -> Bar:
    """
    生成文章长度分布直方图
    
    Args:
        df: 文章数据DataFrame
    
    Returns:
        ECharts柱状图实例
    """
    article_lengths = []
    
    for _, row in df.iterrows():
        if 'content' in row and not pd.isna(row['content']):
            article_lengths.append(len(row['content']))
    
    if not article_lengths:
        # 无数据时返回空图表
        c = (
            Bar()
            .set_global_opts(
                title_opts=opts.TitleOpts(title="无文章长度数据")
            )
        )
        return c
    
    # 计算直方图区间
    min_length = min(article_lengths)
    max_length = max(article_lengths)
    
    # 设置10个区间
    bin_width = max(1, (max_length - min_length) // 10)
    bins = list(range(min_length, max_length + bin_width, bin_width))
    
    # 计算每个区间的文章数量
    hist, bin_edges = np.histogram(article_lengths, bins=bins)
    
    # 生成x轴标签
    x_labels = [f"{int(bin_edges[i])}-{int(bin_edges[i+1])}" for i in range(len(bin_edges)-1)]
    
    # 创建柱状图
    c = (
        Bar(init_opts=opts.InitOpts(
            width="100%",
            height="400px",
            theme=chart_config['theme']
        ))
        .add_xaxis(x_labels)
        .add_yaxis("文章数", hist.tolist())
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="文章长度分布",
                subtitle="字符数统计"
            ),
            xaxis_opts=opts.AxisOpts(
                name="文章长度（字符数）",
                axislabel_opts=opts.LabelOpts(rotate=45)
            ),
            yaxis_opts=opts.AxisOpts(
                name="文章数量"
            ),
            tooltip_opts=opts.TooltipOpts(
                is_show=True,
                formatter="{b}: {c}篇"
            )
        )
    )
    
    return c


def generate_time_trend(df: pd.DataFrame) -> Line:
    """
    生成文章发布时间趋势图
    
    Args:
        df: 文章数据DataFrame
    
    Returns:
        ECharts折线图实例
    """
    # 提取发布日期
    dates = []
    for _, row in df.iterrows():
        if 'crawl_time' in row and not pd.isna(row['crawl_time']):
            # 提取日期部分 (YYYY-MM-DD)
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(row['crawl_time']))
            if date_match:
                dates.append(date_match.group(1))
    
    if not dates:
        # 无数据时返回空图表
        c = (
            Line()
            .set_global_opts(
                title_opts=opts.TitleOpts(title="无发布时间数据")
            )
        )
        return c
    
    # 统计每天的文章数量
    date_count = Counter(dates)
    
    # 按日期排序
    sorted_dates = sorted(date_count.keys())
    counts = [date_count[date] for date in sorted_dates]
    
    # 创建折线图
    c = (
        Line(init_opts=opts.InitOpts(
            width="100%",
            height="400px",
            theme=chart_config['theme']
        ))
        .add_xaxis(sorted_dates)
        .add_yaxis(
            "文章数",
            counts,
            markpoint_opts=opts.MarkPointOpts(
                data=[
                    opts.MarkPointItem(type_="max", name="最大值"),
                    opts.MarkPointItem(type_="min", name="最小值"),
                ]
            ),
            markline_opts=opts.MarkLineOpts(
                data=[opts.MarkLineItem(type_="average", name="平均值")]
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="文章发布时间趋势"
            ),
            xaxis_opts=opts.AxisOpts(
                name="日期",
                axislabel_opts=opts.LabelOpts(rotate=45)
            ),
            yaxis_opts=opts.AxisOpts(
                name="文章数量"
            ),
            datazoom_opts=[
                opts.DataZoomOpts(range_start=0, range_end=100)
            ],
            tooltip_opts=opts.TooltipOpts(
                is_show=True,
                formatter="{a} <br/>{b}: {c}篇"
            )
        )
    )
    
    return c


def get_entity_network(df: pd.DataFrame) -> Graph:
    """
    生成实体关系网络图
    
    Args:
        df: 文章数据DataFrame
    
    Returns:
        ECharts图表实例
    """
    # 提取所有实体和共现关系
    all_entities = {}  # 存储实体及其类型
    co_occurrence = {}  # 存储实体共现关系
    
    # 对每篇文章处理
    for _, row in df.iterrows():
        if 'entities' in row and not pd.isna(row['entities']):
            try:
                article_entities = []
                entity_dict = json.loads(row['entities'])
                
                # 处理人物实体
                for entity in entity_dict.get('person', []):
                    all_entities[entity] = 'person'
                    article_entities.append(entity)
                
                # 处理地点实体
                for entity in entity_dict.get('place', []):
                    all_entities[entity] = 'place'
                    article_entities.append(entity)
                
                # 处理组织实体
                for entity in entity_dict.get('organization', []):
                    all_entities[entity] = 'organization'
                    article_entities.append(entity)
                
                # 计算实体共现关系（同一篇文章中出现）
                for i, entity1 in enumerate(article_entities):
                    for entity2 in article_entities[i+1:]:
                        if entity1 != entity2:
                            pair = tuple(sorted([entity1, entity2]))
                            co_occurrence[pair] = co_occurrence.get(pair, 0) + 1
            except:
                pass
    
    # 构建节点和链接
    nodes = []
    links = []
    entity_to_id = {}
    
    # 添加节点
    for entity, entity_type in all_entities.items():
        if entity not in entity_to_id:
            entity_to_id[entity] = len(entity_to_id)
            
            category = 0  # 默认类别
            if entity_type == 'person':
                category = 0
            elif entity_type == 'place':
                category = 1
            elif entity_type == 'organization':
                category = 2
            
            nodes.append({
                "name": entity,
                "symbolSize": 20,
                "category": category,
                "value": entity_type
            })
    
    # 添加链接（仅保留共现次数超过1的关系）
    for (entity1, entity2), count in co_occurrence.items():
        if count > 1:  # 过滤弱关系
            links.append({
                "source": entity1,
                "target": entity2,
                "value": count
            })
    
    # 创建图表
    c = (
        Graph(init_opts=opts.InitOpts(
            width=chart_config['width'],
            height=chart_config['height'],
            theme=chart_config['theme']
        ))
        .add(
            "",
            nodes=nodes,
            links=links,
            categories=[
                {"name": "人物"},
                {"name": "地点"},
                {"name": "组织"}
            ],
            layout="force",
            is_draggable=True,
            repulsion=4000,
            gravity=0.3,
            edge_length=200,
            is_roam=True,
            linestyle_opts=opts.LineStyleOpts(
                width=1,
                curve=0.3,
                opacity=0.8
            ),
            label_opts=opts.LabelOpts(
                is_show=True,
                position="right",
                font_size=12
            ),
            edge_label=opts.LabelOpts(
                is_show=False
            )
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="实体关系网络图",
                subtitle="基于文章中的实体共现关系"
            ),
            legend_opts=opts.LegendOpts(
                is_show=True,
                pos_left="left",
                orient="vertical"
            ),
            tooltip_opts=opts.TooltipOpts(
                is_show=True,
                formatter=JsCode(
                    "function(params){"
                    "    if(params.dataType === 'node'){"
                    "        return '实体: ' + params.name + '<br/>类型: ' + params.data.value;"
                    "    }else{"
                    "        return '共现次数: ' + params.value;"
                    "    }"
                    "}"
                )
            )
        )
    )
    
    return c


@app.route('/')
def index():
    """
    首页
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    print(f"请求的文件路径: {data_file}")
    print(f"默认文件路径: {DEFAULT_DATA_PATH}")
    
    # 如果URL中没有指定文件路径，但命令行参数指定了，则使用命令行参数
    if data_file == '../data/articles.csv' and DEFAULT_DATA_PATH != '../data/articles.csv':
        data_file = DEFAULT_DATA_PATH
        print(f"使用命令行指定的文件路径: {data_file}")
    
    df = load_data(data_file)
    
    stats = {
        'total_articles': len(df),
        'total_entities': 0,
        'total_triples': 0
    }
    
    print(f"统计信息: 文章总数={stats['total_articles']}")
    
    articles = []
    if not df.empty:
        # 检查是否是电影数据
        is_movie_data = 'movie_title' in df.columns or 'directors' in df.columns or 'actors' in df.columns
        
        # 获取文章统计信息
        for _, row in df.iterrows():
            # 处理电影数据
            if is_movie_data:
                article = {
                    'title': row.get('title', row.get('movie_title', '未知标题')),
                    'author': row.get('author', '未知作者'),
                    'url': row.get('url', row.get('movie_url', '#')),
                    'content': row.get('content', '')
                }
                
                # 提取电影特有信息作为实体
                entities = {
                    'person': [],
                    'place': [],
                    'organization': []
                }
                
                # 导演作为人物实体
                if 'directors' in row and not pd.isna(row['directors']):
                    directors = str(row['directors']).split(',')
                    entities['person'].extend([d.strip() for d in directors if d.strip()])
                
                # 演员作为人物实体
                if 'actors' in row and not pd.isna(row['actors']):
                    actors = str(row['actors']).split(',')
                    entities['person'].extend([a.strip() for a in actors if a.strip()])
                
                # 电影类型作为组织实体
                if 'genres' in row and not pd.isna(row['genres']):
                    genres = str(row['genres']).split(',')
                    entities['organization'].extend([g.strip() for g in genres if g.strip()])
                
                article['entities'] = entities
                
                # 创建电影相关的三元组
                triples = []
                
                # 导演关系
                if 'directors' in row and not pd.isna(row['directors']):
                    directors = str(row['directors']).split(',')
                    for director in directors:
                        director = director.strip()
                        if director:
                            triples.append({
                                'subject': director,
                                'predicate': '导演',
                                'object': article['title']
                            })
                
                # 演员关系
                if 'actors' in row and not pd.isna(row['actors']):
                    actors = str(row['actors']).split(',')
                    for actor in actors:
                        actor = actor.strip()
                        if actor:
                            triples.append({
                                'subject': actor,
                                'predicate': '出演',
                                'object': article['title']
                            })
                
                # 类型关系
                if 'genres' in row and not pd.isna(row['genres']):
                    genres = str(row['genres']).split(',')
                    for genre in genres:
                        genre = genre.strip()
                        if genre:
                            triples.append({
                                'subject': article['title'],
                                'predicate': '属于',
                                'object': genre
                            })
                
                article['triples'] = triples
                
                # 计算实体和三元组数量
                entity_count = sum(len(entities[key]) for key in entities)
                stats['total_entities'] += entity_count
                stats['total_triples'] += len(triples)
            else:
                # 处理普通文章数据
                article = {
                    'title': row.get('title', '未知标题'),
                    'author': row.get('author', '未知作者'),
                    'keywords': str(row.get('keywords', '')).split(',') if not pd.isna(row.get('keywords', '')) else [],
                    'url': row.get('url', '#')
                }
                
                # 获取实体信息
                entities = {}
                if 'entities' in row and not pd.isna(row['entities']):
                    try:
                        # 尝试解析JSON格式的实体
                        entities_str = row['entities']
                        print(f"原始实体数据: {entities_str[:100]}...")  # 打印前100个字符用于调试
                        
                        # 尝试多种可能的格式
                        try:
                            entities = json.loads(entities_str)
                        except:
                            # 如果不是标准JSON，尝试其他格式
                            if isinstance(entities_str, str) and ',' in entities_str:
                                # 可能是逗号分隔的实体列表
                                all_entities = [e.strip() for e in entities_str.split(',')]
                                entities = {'person': all_entities, 'place': [], 'organization': []}
                    except Exception as e:
                        print(f"解析实体信息失败: {e}")
                        print(f"实体数据: {entities_str}")
                
                # 检查实体字典中是否有标准字段，如果没有，尝试其他可能的字段名
                per_entities = []
                loc_entities = []
                org_entities = []
                
                # 尝试标准字段名
                if isinstance(entities, dict):
                    per_entities = entities.get('person', entities.get('PER', []))
                    loc_entities = entities.get('place', entities.get('LOC', []))
                    org_entities = entities.get('organization', entities.get('ORG', []))
                
                # 如果是列表，假设全部是人名实体
                elif isinstance(entities, list):
                    per_entities = entities
                
                # 如果是字符串，尝试分割
                elif isinstance(entities, str):
                    per_entities = [e.strip() for e in entities.split(',') if e.strip()]
                
                article['entities'] = {
                    'person': per_entities,
                    'place': loc_entities,
                    'organization': org_entities
                }
                
                # 计算实体总数
                entity_count = len(per_entities) + len(loc_entities) + len(org_entities)
                stats['total_entities'] += entity_count
                
                # 获取三元组信息
                triples_data = row.get('triples', '[]')
                if pd.isna(triples_data):
                    triples_data = '[]'
                    
                # 尝试解析三元组
                try:
                    # 尝试多种可能的格式
                    if isinstance(triples_data, str):
                        if triples_data.startswith('[') and triples_data.endswith(']'):
                            # 标准JSON格式
                            triples = parse_triples(triples_data)
                        elif ';' in triples_data:
                            # 分号分隔的三元组
                            triples = []
                            for triple_str in triples_data.split(';'):
                                parts = [p.strip() for p in triple_str.split(',')]
                                if len(parts) >= 3:
                                    triples.append({
                                        'subject': parts[0],
                                        'predicate': parts[1],
                                        'object': parts[2]
                                    })
                        else:
                            # 可能是逗号分隔的单个三元组
                            parts = [p.strip() for p in triples_data.split(',')]
                            if len(parts) >= 3:
                                triples = [{
                                    'subject': parts[0],
                                    'predicate': parts[1],
                                    'object': parts[2]
                                }]
                            else:
                                triples = []
                    else:
                        triples = []
                except Exception as e:
                    print(f"解析三元组失败: {e}")
                    print(f"三元组数据: {triples_data}")
                    triples = []
                
                article['triples'] = triples
                stats['total_triples'] += len(triples)
            
            articles.append(article)
    
    print(f"统计信息: 实体总数={stats['total_entities']}, 三元组总数={stats['total_triples']}")
    
    return render_template('index.html', articles=articles, stats=stats)


@app.route('/article/<int:article_id>')
def article_detail(article_id):
    """
    文章详情页
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty or article_id >= len(df):
        return "文章不存在", 404
    
    article = df.iloc[article_id].to_dict()
    
    # 检查是否是电影数据
    is_movie_data = 'movie_title' in df.columns or 'directors' in df.columns or 'actors' in df.columns
    
    if is_movie_data:
        # 处理电影数据
        # 标题处理
        if 'title' not in article or pd.isna(article['title']):
            article['title'] = article.get('movie_title', '未知标题')
        
        # 处理关键词（使用电影类型作为关键词）
        article['keywords'] = []
        if 'genres' in article and not pd.isna(article['genres']):
            article['keywords'] = [g.strip() for g in str(article['genres']).split(',') if g.strip()]
        
        # 处理实体
        entities = {'person': [], 'place': [], 'organization': []}
        
        # 导演作为人物实体
        if 'directors' in article and not pd.isna(article['directors']):
            directors = str(article['directors']).split(',')
            entities['person'].extend([d.strip() for d in directors if d.strip()])
        
        # 演员作为人物实体
        if 'actors' in article and not pd.isna(article['actors']):
            actors = str(article['actors']).split(',')
            entities['person'].extend([a.strip() for a in actors if a.strip()])
        
        # 电影类型作为组织实体
        if 'genres' in article and not pd.isna(article['genres']):
            genres = str(article['genres']).split(',')
            entities['organization'].extend([g.strip() for g in genres if g.strip()])
        
        article['entities'] = entities
        
        # 创建电影相关的三元组
        triples = []
        
        # 导演关系
        if 'directors' in article and not pd.isna(article['directors']):
            directors = str(article['directors']).split(',')
            for director in directors:
                director = director.strip()
                if director:
                    triples.append({
                        'subject': director,
                        'predicate': '导演',
                        'object': article['title']
                    })
        
        # 演员关系
        if 'actors' in article and not pd.isna(article['actors']):
            actors = str(article['actors']).split(',')
            for actor in actors:
                actor = actor.strip()
                if actor:
                    triples.append({
                        'subject': actor,
                        'predicate': '出演',
                        'object': article['title']
                    })
        
        # 类型关系
        if 'genres' in article and not pd.isna(article['genres']):
            genres = str(article['genres']).split(',')
            for genre in genres:
                genre = genre.strip()
                if genre:
                    triples.append({
                        'subject': article['title'],
                        'predicate': '属于',
                        'object': genre
                    })
        
        article['triples'] = triples
    else:
        # 处理普通文章数据
        # 处理关键词
        if 'keywords' in article and not pd.isna(article['keywords']):
            article['keywords'] = article['keywords'].split(',')
        else:
            article['keywords'] = []
        
        # 处理实体
        entities = {'person': [], 'place': [], 'organization': []}
        if 'entities' in article and not pd.isna(article['entities']):
            try:
                # 尝试解析JSON格式的实体
                entities_str = article['entities']
                
                # 尝试多种可能的格式
                try:
                    parsed_entities = json.loads(entities_str)
                    if isinstance(parsed_entities, dict):
                        # 尝试标准字段名
                        entities['person'] = parsed_entities.get('person', parsed_entities.get('PER', []))
                        entities['place'] = parsed_entities.get('place', parsed_entities.get('LOC', []))
                        entities['organization'] = parsed_entities.get('organization', parsed_entities.get('ORG', []))
                    elif isinstance(parsed_entities, list):
                        # 如果是列表，假设全部是人名实体
                        entities['person'] = parsed_entities
                except:
                    # 如果不是标准JSON，尝试其他格式
                    if isinstance(entities_str, str) and ',' in entities_str:
                        # 可能是逗号分隔的实体列表
                        all_entities = [e.strip() for e in entities_str.split(',') if e.strip()]
                        entities['person'] = all_entities
            except Exception as e:
                print(f"解析实体信息失败: {e}")
        
        article['entities'] = entities
        
        # 处理三元组
        try:
            triples_data = article.get('triples', '[]')
            if pd.isna(triples_data):
                triples_data = '[]'
                
            # 尝试多种可能的格式
            if isinstance(triples_data, str):
                if triples_data.startswith('[') and triples_data.endswith(']'):
                    # 标准JSON格式
                    article['triples'] = parse_triples(triples_data)
                elif ';' in triples_data:
                    # 分号分隔的三元组
                    triples = []
                    for triple_str in triples_data.split(';'):
                        parts = [p.strip() for p in triple_str.split(',')]
                        if len(parts) >= 3:
                            triples.append({
                                'subject': parts[0],
                                'predicate': parts[1],
                                'object': parts[2]
                            })
                    article['triples'] = triples
                else:
                    # 可能是逗号分隔的单个三元组
                    parts = [p.strip() for p in triples_data.split(',')]
                    if len(parts) >= 3:
                        article['triples'] = [{
                            'subject': parts[0],
                            'predicate': parts[1],
                            'object': parts[2]
                        }]
                    else:
                        article['triples'] = []
            else:
                article['triples'] = []
        except Exception as e:
            print(f"解析三元组失败: {e}")
            article['triples'] = []
    
    return render_template('article.html', article=article, article_id=article_id)


@app.route('/graph/<int:article_id>')
def article_graph(article_id):
    """
    文章关系图谱
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty or article_id >= len(df):
        return "文章不存在", 404
    
    article = df.iloc[article_id].to_dict()
    
    # 标题处理
    if 'title' not in article or pd.isna(article['title']):
        article['title'] = article.get('movie_title', f'文章 {article_id}')
    
    title = article.get('title', f'文章 {article_id}')
    
    # 检查是否是电影数据
    is_movie_data = 'movie_title' in df.columns or 'directors' in df.columns or 'actors' in df.columns
    
    # 获取三元组
    if is_movie_data:
        # 处理电影数据
        triples = []
        
        # 导演关系
        if 'directors' in article and not pd.isna(article['directors']):
            directors = str(article['directors']).split(',')
            for director in directors:
                director = director.strip()
                if director:
                    triples.append({
                        'subject': director,
                        'predicate': '导演',
                        'object': title
                    })
        
        # 演员关系
        if 'actors' in article and not pd.isna(article['actors']):
            actors = str(article['actors']).split(',')
            for actor in actors:
                actor = actor.strip()
                if actor:
                    triples.append({
                        'subject': actor,
                        'predicate': '出演',
                        'object': title
                    })
        
        # 类型关系
        if 'genres' in article and not pd.isna(article['genres']):
            genres = str(article['genres']).split(',')
            for genre in genres:
                genre = genre.strip()
                if genre:
                    triples.append({
                        'subject': title,
                        'predicate': '属于',
                        'object': genre
                    })
    else:
        # 处理普通文章数据
        try:
            triples_data = article.get('triples', '[]')
            if pd.isna(triples_data):
                triples_data = '[]'
                
            # 尝试多种可能的格式
            if isinstance(triples_data, str):
                if triples_data.startswith('[') and triples_data.endswith(']'):
                    # 标准JSON格式
                    triples = parse_triples(triples_data)
                elif ';' in triples_data:
                    # 分号分隔的三元组
                    triples = []
                    for triple_str in triples_data.split(';'):
                        parts = [p.strip() for p in triple_str.split(',')]
                        if len(parts) >= 3:
                            triples.append({
                                'subject': parts[0],
                                'predicate': parts[1],
                                'object': parts[2]
                            })
                else:
                    # 可能是逗号分隔的单个三元组
                    parts = [p.strip() for p in triples_data.split(',')]
                    if len(parts) >= 3:
                        triples = [{
                            'subject': parts[0],
                            'predicate': parts[1],
                            'object': parts[2]
                        }]
                    else:
                        triples = []
            else:
                triples = []
        except Exception as e:
            print(f"解析三元组失败: {e}")
            triples = []
    
    # 生成图表
    graph = generate_relation_graph(triples)
    
    return render_template(
        'graph.html',
        article_id=article_id,
        title=title,
        graph_html=graph.render_embed()
    )


@app.route('/full_graph')
def full_graph():
    """
    全部文章的关系图谱
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    all_triples = []
    
    if not df.empty:
        # 检查是否是电影数据
        is_movie_data = 'movie_title' in df.columns or 'directors' in df.columns or 'actors' in df.columns
        
        for _, row in df.iterrows():
            if is_movie_data:
                # 处理电影数据
                # 标题处理
                title = row.get('title', row.get('movie_title', '未知标题'))
                if pd.isna(title):
                    title = '未知标题'
                
                # 导演关系
                if 'directors' in row and not pd.isna(row['directors']):
                    directors = str(row['directors']).split(',')
                    for director in directors:
                        director = director.strip()
                        if director:
                            all_triples.append({
                                'subject': director,
                                'predicate': '导演',
                                'object': title
                            })
                
                # 演员关系
                if 'actors' in row and not pd.isna(row['actors']):
                    actors = str(row['actors']).split(',')
                    for actor in actors:
                        actor = actor.strip()
                        if actor:
                            all_triples.append({
                                'subject': actor,
                                'predicate': '出演',
                                'object': title
                            })
                
                # 类型关系
                if 'genres' in row and not pd.isna(row['genres']):
                    genres = str(row['genres']).split(',')
                    for genre in genres:
                        genre = genre.strip()
                        if genre:
                            all_triples.append({
                                'subject': title,
                                'predicate': '属于',
                                'object': genre
                            })
            else:
                # 处理普通文章数据
                try:
                    triples_data = row.get('triples', '[]')
                    if pd.isna(triples_data):
                        continue
                        
                    # 尝试多种可能的格式
                    if isinstance(triples_data, str):
                        if triples_data.startswith('[') and triples_data.endswith(']'):
                            # 标准JSON格式
                            triples = parse_triples(triples_data)
                        elif ';' in triples_data:
                            # 分号分隔的三元组
                            triples = []
                            for triple_str in triples_data.split(';'):
                                parts = [p.strip() for p in triple_str.split(',')]
                                if len(parts) >= 3:
                                    triples.append({
                                        'subject': parts[0],
                                        'predicate': parts[1],
                                        'object': parts[2]
                                    })
                        else:
                            # 可能是逗号分隔的单个三元组
                            parts = [p.strip() for p in triples_data.split(',')]
                            if len(parts) >= 3:
                                triples = [{
                                    'subject': parts[0],
                                    'predicate': parts[1],
                                    'object': parts[2]
                                }]
                            else:
                                triples = []
                    else:
                        triples = []
                        
                    all_triples.extend(triples)
                except Exception as e:
                    print(f"解析三元组失败: {e}")
    
    # 生成图表
    graph = generate_relation_graph(all_triples)
    
    return render_template(
        'graph.html',
        article_id='full',
        title='全部文章关系图谱',
        graph_html=graph.render_embed()
    )


@app.route('/api/articles')
def api_articles():
    """
    文章数据API
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty:
        return jsonify([])
    
    # 简化输出
    result = []
    for _, row in df.iterrows():
        article = {
            'title': row.get('title', '未知标题'),
            'author': row.get('author', '未知作者'),
            'url': row.get('url', '#'),
            'crawl_time': row.get('crawl_time', '')
        }
        
        # 处理关键词
        if 'keywords' in row and not pd.isna(row['keywords']):
            article['keywords'] = row['keywords'].split(',')
        else:
            article['keywords'] = []
        
        result.append(article)
    
    return jsonify(result)


@app.route('/api/article/<int:article_id>')
def api_article_detail(article_id):
    """
    文章详情API
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty or article_id >= len(df):
        return jsonify({'error': '文章不存在'}), 404
    
    article = df.iloc[article_id].to_dict()
    
    # 处理关键词
    if 'keywords' in article and not pd.isna(article['keywords']):
        article['keywords'] = article['keywords'].split(',')
    else:
        article['keywords'] = []
    
    # 处理实体
    if 'entities' in article and not pd.isna(article['entities']):
        try:
            article['entities'] = json.loads(article['entities'])
        except:
            article['entities'] = {'person': [], 'place': [], 'organization': []}
    else:
        article['entities'] = {'person': [], 'place': [], 'organization': []}
    
    # 处理三元组
    article['triples'] = parse_triples(article.get('triples', '[]'))
    
    return jsonify(article)


@app.route('/api/triples/<int:article_id>')
def api_article_triples(article_id):
    """
    文章三元组API
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty or article_id >= len(df):
        return jsonify({'error': '文章不存在'}), 404
    
    article = df.iloc[article_id].to_dict()
    
    # 处理三元组
    triples = parse_triples(article.get('triples', '[]'))
    
    return jsonify(triples)


@app.route('/analyze')
def analyze():
    """
    数据分析页面
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty:
        return "无数据可分析", 404
    
    # 生成关键词词云
    keyword_cloud = generate_keyword_cloud(df)
    
    # 生成实体统计图表
    entity_bar = generate_entity_bar(df)
    
    # 生成情感分析图表
    sentiment_pie = generate_sentiment_pie(df)
    
    # 生成主题分布图
    topic_pie = generate_topic_distribution(df)
    
    # 生成文章长度分布图
    length_histogram = generate_article_length_histogram(df)
    
    # 生成时间趋势图
    time_trend = generate_time_trend(df)
    
    # 返回分析页面
    return render_template(
        'analyze.html',
        stats={
            'total_articles': len(df),
            'keyword_cloud': keyword_cloud.render_embed(),
            'entity_bar': entity_bar.render_embed(),
            'sentiment_pie': sentiment_pie.render_embed(),
            'topic_pie': topic_pie.render_embed(),
            'length_histogram': length_histogram.render_embed(),
            'time_trend': time_trend.render_embed()
        }
    )


@app.route('/entity_network')
def entity_network():
    """
    实体关系网络图
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty:
        return "无数据可分析", 404
    
    # 生成实体关系网络图
    network = get_entity_network(df)
    
    return render_template(
        'network.html',
        title="实体关系网络图",
        graph_html=network.render_embed()
    )


@app.route('/api/analysis/keywords')
def api_keywords_analysis():
    """
    关键词分析API
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty:
        return jsonify([])
    
    # 提取所有关键词
    keywords = []
    for _, row in df.iterrows():
        if 'keywords' in row and not pd.isna(row['keywords']):
            kw_list = row['keywords'].split(',')
            keywords.extend([kw.strip() for kw in kw_list if kw.strip()])
    
    # 统计词频
    keyword_count = Counter(keywords)
    
    # 转换为JSON格式
    result = [{"keyword": k, "count": v} for k, v in keyword_count.most_common(50)]
    
    return jsonify(result)


@app.route('/api/analysis/entities')
def api_entities_analysis():
    """
    实体分析API
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    entity_type = request.args.get('type', 'all')  # person, place, organization, all
    df = load_data(data_file)
    
    if df.empty:
        return jsonify([])
    
    # 提取实体
    entities = []
    for _, row in df.iterrows():
        if 'entities' in row and not pd.isna(row['entities']):
            try:
                entity_dict = json.loads(row['entities'])
                
                if entity_type == 'all' or entity_type == 'person':
                    entities.extend([(e, 'person') for e in entity_dict.get('person', [])])
                
                if entity_type == 'all' or entity_type == 'place':
                    entities.extend([(e, 'place') for e in entity_dict.get('place', [])])
                
                if entity_type == 'all' or entity_type == 'organization':
                    entities.extend([(e, 'organization') for e in entity_dict.get('organization', [])])
            except:
                pass
    
    # 统计实体出现次数
    entity_count = Counter([e[0] for e in entities])
    
    # 获取实体类型
    entity_types = {e[0]: e[1] for e in entities}
    
    # 转换为JSON格式
    result = [
        {"entity": k, "count": v, "type": entity_types.get(k, "unknown")} 
        for k, v in entity_count.most_common(50)
    ]
    
    return jsonify(result)


@app.route('/api/analysis/triples')
def api_triples_analysis():
    """
    三元组统计API
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty:
        return jsonify([])
    
    all_triples = []
    for _, row in df.iterrows():
        triples = parse_triples(row.get('triples', '[]'))
        all_triples.extend(triples)
    
    # 统计谓语出现频率
    predicate_count = Counter([t['predicate'] for t in all_triples])
    
    # 统计主语出现频率
    subject_count = Counter([t['subject'] for t in all_triples])
    
    # 统计宾语出现频率
    object_count = Counter([t['object'] for t in all_triples])
    
    # 构建结果
    result = {
        "predicates": [{"predicate": k, "count": v} for k, v in predicate_count.most_common(20)],
        "subjects": [{"subject": k, "count": v} for k, v in subject_count.most_common(20)],
        "objects": [{"object": k, "count": v} for k, v in object_count.most_common(20)]
    }
    
    return jsonify(result)


@app.route('/debug')
def debug_data():
    """
    调试数据格式
    """
    data_file = request.args.get('file', DEFAULT_DATA_PATH)
    df = load_data(data_file)
    
    if df.empty:
        return "无数据可分析", 404
    
    # 获取前5篇文章的数据
    sample_data = []
    for i in range(min(5, len(df))):
        article = df.iloc[i].to_dict()
        
        # 获取实体和三元组的原始格式
        entities_raw = article.get('entities', '')
        triples_raw = article.get('triples', '')
        
        # 尝试解析实体
        entities_parsed = "解析失败"
        try:
            if isinstance(entities_raw, str) and entities_raw:
                if entities_raw.startswith('{') and entities_raw.endswith('}'):
                    entities_parsed = json.loads(entities_raw)
                else:
                    entities_parsed = entities_raw
        except:
            pass
        
        # 尝试解析三元组
        triples_parsed = "解析失败"
        try:
            if isinstance(triples_raw, str) and triples_raw:
                if triples_raw.startswith('[') and triples_raw.endswith(']'):
                    triples_parsed = json.loads(triples_raw)
                else:
                    triples_parsed = triples_raw
        except:
            pass
        
        sample_data.append({
            'title': article.get('title', f'文章 {i}'),
            'entities_raw': str(entities_raw)[:200] + ('...' if len(str(entities_raw)) > 200 else ''),
            'entities_type': type(entities_raw).__name__,
            'entities_parsed': str(entities_parsed)[:200] + ('...' if len(str(entities_parsed)) > 200 else ''),
            'triples_raw': str(triples_raw)[:200] + ('...' if len(str(triples_raw)) > 200 else ''),
            'triples_type': type(triples_raw).__name__,
            'triples_parsed': str(triples_parsed)[:200] + ('...' if len(str(triples_parsed)) > 200 else '')
        })
    
    # 获取列名
    columns = list(df.columns)
    
    return render_template(
        'debug.html',
        sample_data=sample_data,
        columns=columns,
        file_path=data_file
    )


if __name__ == '__main__':
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='文章分析可视化应用')
    parser.add_argument('--data', type=str, default=DEFAULT_DATA_PATH,
                        help='数据文件路径，默认为 ' + DEFAULT_DATA_PATH)
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='服务器主机，默认为 0.0.0.0')
    parser.add_argument('--port', type=int, default=5000,
                        help='服务器端口，默认为 5000')
    args = parser.parse_args()
    
    # 设置数据文件路径
    data_path = args.data
    print(f"使用数据文件: {data_path}")
    
    # 预加载数据
    df = load_data(data_path)
    
    # 启动应用
    app.run(debug=True, host=args.host, port=args.port) 