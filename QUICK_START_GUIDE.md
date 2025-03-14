# 文章爬取与NLP分析系统 - 快速上手指南

本指南将帮助您快速上手使用文章爬取与NLP分析系统，实现文章爬取、CSV格式存储以及可视化展示。

## 目录

1. [安装与配置](#1-安装与配置)
2. [最简单的使用方式](#2-最简单的使用方式)
3. [自定义爬取](#3-自定义爬取)
4. [使用配置文件](#4-使用配置文件)
5. [查看CSV结果](#5-查看csv结果)
6. [可视化结果](#6-可视化结果)
7. [一键测试所有功能](#7-一键测试所有功能)
8. [常见问题解决](#8-常见问题解决)
9. [实用技巧](#9-实用技巧)

## 1. 安装与配置

首先，您需要安装必要的依赖：

```bash
# 克隆或下载项目
git clone https://github.com/yourusername/article-crawler-analyzer.git
cd article-crawler-analyzer

# 安装依赖包
pip install -r requirements.txt

# 如果需要高级NLP功能（实体识别和关系提取），安装HanLP
pip install pyhanlp
python -c "import hanlp; hanlp.pretrained.mtl.ALL"
```

## 2. 最简单的使用方式

如果您想快速开始，只需运行主程序：

```bash
python main.py
```

这将使用默认配置爬取文章（默认是知乎），进行NLP分析，并将结果保存为CSV文件。

## 3. 自定义爬取

您可以通过命令行参数自定义爬取过程：

```bash
# 爬取指定网站
python main.py --url https://www.csdn.net

# 限制爬取文章数量
python main.py --max 20

# 使用多线程加速爬取
python main.py --threads 10

# 使用代理IP池提高稳定性
python main.py --proxy

# 增量爬取（跳过已爬取的文章）
python main.py --incremental

# 组合使用多个参数
python main.py --url https://www.jianshu.com --max 30 --threads 8 --proxy
```

## 4. 使用配置文件

对于更复杂的配置，您可以编辑`config.json`文件，然后运行：

```bash
python main.py --config myconfig.json
```

配置文件示例：
```json
{
    "spider": {
        "website": "zhihu",
        "base_url": "https://www.zhihu.com",
        "delay": 1.0,
        "max_articles": 50,
        "output_dir": "data",
        "thread_count": 8,
        "timeout": 10,
        "max_retries": 3,
        "incremental": true,
        "use_proxy": true
    },
    "nlp": {
        "segmenter": "jieba",
        "extractor": "hanlp",
        "relation": "hanlp",
        "use_stopwords": true,
        "top_keywords": 10,
        "keywords_count": 15,
        "summary_sentences": 3
    },
    "output": {
        "csv_file": "my_articles.csv",
        "encoding": "utf-8-sig"
    }
}
```

## 5. 查看CSV结果

爬取完成后，您可以在`data`目录（或您指定的输出目录）下找到CSV文件。默认文件名是`articles.csv`，您可以用Excel或任何文本编辑器打开它。

CSV文件包含以下字段：
- title: 文章标题
- author: 作者
- url: 文章URL
- date: 发布日期
- content: 文章内容
- keywords: 关键词（逗号分隔）
- entities: 实体（JSON格式）
- triples: 关系三元组（JSON格式）

## 6. 可视化结果

要查看可视化结果，运行：

```bash
python -m visualization.app
```

然后在浏览器中访问 http://127.0.0.1:5000 查看结果。

可视化界面提供：
- 文章列表页：展示所有爬取的文章
- 文章详情页：展示文章内容、关键词、实体和关系
- 关系图谱：可视化文章中的实体关系
- 数据分析：提供关键词云、实体统计、情感分析等多种图表

## 7. 一键测试所有功能

如果您想测试系统的所有功能，可以运行：

```bash
python test_all_features.py --all
```

这将执行爬虫、NLP分析和可视化的全面测试，并生成测试报告。

## 8. 常见问题解决

### 8.1 爬取速度慢

- 增加线程数：`--threads 20`
- 使用代理：`--proxy`
- 减小请求延迟：在配置文件中设置较小的`delay`值

### 8.2 无法爬取某些网站

- 检查网站是否有反爬措施
- 使用代理：`--proxy`
- 尝试使用通用解析器：在配置文件中设置`"website": "general"`

### 8.3 NLP分析失败

- 确保已安装所需的NLP库
- 对于HanLP功能，确保已下载数据包
- 尝试使用jieba代替HanLP：在配置文件中设置`"segmenter": "jieba"`

### 8.4 可视化界面无法显示

- 确保Flask正确安装：`pip install flask`
- 确保pyecharts正确安装：`pip install pyecharts`
- 检查是否有足够的文章数据

## 9. 实用技巧

### 9.1 批量爬取多个网站

创建一个批处理脚本，依次爬取多个网站：

```bash
python main.py --url https://www.zhihu.com --max 30 --output data/zhihu
python main.py --url https://blog.csdn.net --max 30 --output data/csdn
python main.py --url https://www.jianshu.com --max 30 --output data/jianshu
```

### 9.2 定期增量爬取

设置定时任务，定期运行增量爬取：

```bash
python main.py --incremental --proxy
```

### 9.3 自定义输出文件名

在配置文件中设置不同的输出文件名，避免覆盖之前的结果：

```json
"output": {
    "csv_file": "articles_20230901.csv"
}
```

### 9.4 只运行NLP分析

如果已经有文章数据，只想运行NLP分析：

```bash
python test_all_features.py --nlp
```

### 9.5 只查看可视化结果

如果已经完成爬取和分析，只想查看可视化结果：

```bash
python -m visualization.app
```

## 总结

通过以上方法，您可以非常方便地使用这个项目工具，实现文章爬取、CSV格式存储以及可视化展示。整个流程简单直观，即使没有编程经验的用户也能轻松上手。

如果您需要更详细的信息，请参考[用户手册](USER_MANUAL.md)和[README](README.md)文档。 