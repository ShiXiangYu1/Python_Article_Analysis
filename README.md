# 文章爬取与NLP分析系统

一个集成了爬虫、NLP分析和可视化的系统，用于爬取网站文章，提取关键信息，并进行数据分析与展示。

## 功能特点

- **多网站支持**：内置多个网站解析器，包括知乎、CSDN、简书、新浪新闻、豆瓣等
- **多线程爬取**：支持多线程并行爬取，提高爬取效率
- **增量爬取**：支持增量爬取，避免重复爬取已获取的文章
- **代理IP池**：内置代理IP池，自动获取、验证和管理代理IP，提高爬取稳定性
- **NLP分析**：支持分词、关键词提取、实体识别、关系提取等多种NLP功能
- **数据可视化**：提供Web界面展示爬取结果和分析数据

## 快速上手

如果您想快速开始使用本系统，请参考[快速上手指南](QUICK_START_GUIDE.md)，该指南提供了简明的步骤帮助您实现文章爬取、CSV格式存储以及可视化展示。

## 项目结构

```
project/
│
├── spider/              # 爬虫模块
│   ├── spider.py        # 爬虫核心实现
│   ├── parser.py        # 网站解析器
│   └── proxy_pool.py    # 代理IP池
│
├── nlp/                 # NLP模块
│   ├── segmentation.py  # 分词模块
│   ├── tfidf.py         # TF-IDF关键词提取
│   ├── entity.py        # 实体识别
│   ├── relation.py      # 关系提取
│   ├── entity_optimizer.py # 实体优化
│   ├── relation_enhancer.py # 关系增强
│   └── dict_manager.py  # 词典管理
│
├── visualization/       # 可视化模块
│   ├── app.py           # Flask应用
│   ├── templates/       # HTML模板
│   └── static/          # 静态资源
│
├── tests/               # 测试模块
│   ├── test_parsers.py  # 解析器测试
│   ├── test_proxy_pool.py # 代理池测试
│   ├── test_integration.py # 集成测试
│   └── test_full_integration.py # 全面集成测试
│
├── data/                # 数据目录
├── main.py              # 主程序
├── run_tests.py         # 测试运行脚本
├── config.json          # 配置文件
├── requirements.txt     # 依赖项
├── README.md            # 说明文档
├── QUICK_START_GUIDE.md # 快速上手指南
└── USER_MANUAL.md       # 用户手册
```

## 安装与配置

### 环境要求

- Python 3.7+
- 依赖包：requests, BeautifulSoup4, jieba, pandas, Flask, pyecharts等

### 安装步骤

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/article-crawler-analyzer.git
cd article-crawler-analyzer
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 配置：
   
编辑`config.json`文件，设置爬取参数、NLP参数和输出参数。

### 安装HanLP（可选）

本项目使用HanLP进行高级NLP分析，如果需要使用实体识别和关系提取功能，需要安装HanLP：

```bash
pip install pyhanlp
```

安装后，需要下载HanLP的数据包：

```bash
python -c "import hanlp; hanlp.pretrained.mtl.ALL"
```

## 使用方法

### 基本使用

```bash
# 使用默认配置爬取文章并分析
python main.py

# 指定配置文件
python main.py --config myconfig.json

# 指定要爬取的网站URL
python main.py --url https://www.zhihu.com

# 指定最大爬取文章数
python main.py --max 50

# 启用多线程爬取
python main.py --threads 10

# 增量爬取（跳过已爬取的文章）
python main.py --incremental

# 使用代理IP池
python main.py --proxy
```

### 运行可视化界面

爬取和分析完成后，可以运行可视化界面查看结果：

```bash
python -m visualization.app
```

然后在浏览器中访问 http://127.0.0.1:5000 查看结果。

### 运行测试

项目包含多种测试，可以使用测试运行脚本运行：

```bash
# 运行所有测试
python run_tests.py

# 只运行单元测试
python run_tests.py --unit

# 只运行集成测试
python run_tests.py --integration

# 运行全面集成测试
python run_tests.py --full

# 运行特定测试
python run_tests.py --test test_spider test_proxy_pool
```

## 配置文件说明

配置文件`config.json`包含以下主要部分：

### 爬虫配置

```json
"spider": {
    "website": "zhihu",          # 目标网站
    "base_url": "https://www.zhihu.com",  # 网站URL
    "delay": 2.0,                # 爬取延迟
    "max_articles": 100,         # 最大爬取文章数
    "output_dir": "data",        # 输出目录
    "thread_count": 5,           # 爬虫线程数
    "timeout": 10,               # 请求超时时间(秒)
    "max_retries": 3,            # 最大重试次数
    "incremental": false,        # 是否增量爬取
    "use_proxy": false,          # 是否使用代理
    "proxy": {
        "enabled": false,
        "proxy_file": "proxies.json",
        "check_interval": 600,   # 代理检查间隔（秒）
        "fetch_interval": 3600,  # 代理获取间隔（秒）
        "max_workers": 10,       # 代理检查最大线程数
        "timeout": 5             # 代理超时时间（秒）
    }
}
```

### NLP配置

```json
"nlp": {
    "segmenter": "jieba",        # 分词器
    "extractor": "hanlp",        # 实体提取器
    "relation": "hanlp",         # 关系提取器
    "use_stopwords": true,       # 是否使用停用词
    "top_keywords": 5,           # 每篇文章提取的关键词数量
    "keywords_count": 10,        # 关键词数量
    "summary_sentences": 3       # 摘要句子数量
}
```

### 输出配置

```json
"output": {
    "csv_file": "articles.csv",  # 输出CSV文件名
    "encoding": "utf-8-sig"      # 文件编码
}
```

## 网站解析器

系统支持多个网站的解析，包括：

1. **知乎**：爬取知乎专栏文章
2. **CSDN**：爬取CSDN博客文章
3. **简书**：爬取简书文章
4. **新浪新闻**：爬取新浪新闻文章
5. **豆瓣**：爬取豆瓣电影、书籍评论
6. **通用解析器**：适用于大多数含有文章的网站

可以通过`config.json`中的`spider.website`和`spider.base_url`配置要爬取的网站。

## 代理IP池功能

代理IP池模块(`spider/proxy_pool.py`)提供了以下功能：

- **自动获取代理**：从多个公共代理源自动获取代理IP
- **代理验证**：自动验证代理的有效性和响应速度
- **可靠性评估**：根据代理的成功率、响应时间和使用次数评估可靠性
- **动态调整**：自动移除失效代理，保留高质量代理
- **并发检查**：使用多线程并发检查代理有效性
- **持久化存储**：将代理信息保存到文件，下次启动时可继续使用

## NLP分析功能

NLP模块提供以下功能：

1. **分词**：使用jieba或HanLP进行中文分词
2. **关键词提取**：使用TF-IDF算法提取文章关键词
3. **实体识别**：识别文章中的人名、地名、组织机构等实体
4. **关系提取**：提取文章中的主谓宾关系三元组
5. **实体优化**：优化实体识别结果，提高准确率
6. **关系增强**：增强关系提取结果，添加更多语义信息

## 可视化功能

可视化模块提供以下功能：

1. **文章列表**：展示所有爬取的文章
2. **文章详情**：展示文章内容、关键词、实体和关系
3. **关系图谱**：可视化文章中的实体关系
4. **关键词云**：展示文章关键词
5. **实体统计**：统计不同类型的实体数量
6. **情感分析**：分析文章情感倾向
7. **主题分布**：展示文章主题分布
8. **文章长度分布**：统计文章长度分布
9. **时间趋势**：展示文章发布时间趋势

## 常见问题

### 1. 爬取速度慢

- 尝试增加线程数：`python main.py --threads 20`
- 使用代理IP池：`python main.py --proxy`
- 减小请求延迟：编辑`config.json`，将`spider.delay`设置为较小的值

### 2. 无法爬取某些网站

- 检查网站是否有反爬措施
- 尝试使用代理IP池
- 检查网站解析器是否适用于目标网站
- 可能需要自定义网站解析器

### 3. NLP分析失败

- 检查是否安装了所需的NLP库
- 对于HanLP相关功能，确保已安装pyhanlp并下载了数据包
- 检查文章内容是否为空或格式不正确

### 4. 可视化界面无法显示

- 确保Flask正确安装
- 检查数据文件路径是否正确
- 检查是否有足够的文章数据

## 贡献指南

欢迎贡献代码或提出改进建议！请遵循以下步骤：

1. Fork 仓库
2. 创建新分支：`git checkout -b feature-xyz`
3. 提交更改：`git commit -am 'Add feature xyz'`
4. 推送到分支：`git push origin feature-xyz`
5. 提交Pull Request

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。 