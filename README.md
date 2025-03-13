# 文章爬取与NLP分析系统

一个集成了爬虫、NLP分析和可视化的系统，用于爬取网站文章，提取关键信息，并进行数据分析与展示。

## 功能特点

- **多网站支持**：内置多个网站解析器，包括知乎、CSDN、简书、新浪新闻等
- **多线程爬取**：支持多线程并行爬取，提高爬取效率
- **增量爬取**：支持增量爬取，避免重复爬取已获取的文章
- **代理IP池**：内置代理IP池，自动获取、验证和管理代理IP，提高爬取稳定性
- **NLP分析**：支持分词、关键词提取、实体识别、关系提取等多种NLP功能
- **数据可视化**：提供Web界面展示爬取结果和分析数据

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
│   └── relation.py      # 关系提取
│
├── visualization/       # 可视化模块
│   ├── app.py           # Flask应用
│   └── static/          # 静态资源
│
├── tests/               # 测试模块
│   ├── test_parsers.py  # 解析器测试
│   └── test_proxy_pool.py # 代理池测试
│
├── data/                # 数据目录
├── main.py              # 主程序
├── config.json          # 配置文件
├── requirements.txt     # 依赖项
└── README.md            # 说明文档
```

## 安装与配置

### 环境要求

- Python 3.7+
- 依赖包：requests, BeautifulSoup4, jieba, pandas, Flask, etc.

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

### 测试代理IP池

```bash
# 测试使用代理爬取
python test_proxy_spider.py

# 测试特定网站
python test_proxy_spider.py --website sina --url https://news.sina.com.cn/

# 对比使用代理和不使用代理的效果
python test_proxy_spider.py --compare
```

## 代理IP池功能

代理IP池模块(`spider/proxy_pool.py`)提供了以下功能：

- **自动获取代理**：从多个公共代理源自动获取代理IP
- **代理验证**：自动验证代理的有效性和响应速度
- **可靠性评估**：根据代理的成功率、响应时间和使用次数评估可靠性
- **动态调整**：自动移除失效代理，保留高质量代理
- **并发检查**：使用多线程并发检查代理有效性
- **持久化存储**：将代理信息保存到文件，下次启动时可继续使用

代理池配置可以在`config.json`文件中的`spider.proxy`部分设置：

```json
"proxy": {
    "enabled": true,                  # 是否启用代理
    "proxy_file": "proxies.json",     # 代理保存文件
    "check_interval": 600,            # 代理检查间隔（秒）
    "fetch_interval": 3600,           # 代理获取间隔（秒）
    "max_workers": 10,                # 代理检查最大线程数
    "timeout": 5,                     # 代理超时时间（秒）
    "check_urls": [                   # 用于检查代理的URL列表
        "https://www.baidu.com",
        "https://www.qq.com",
        "https://www.sina.com.cn"
    ],
    "sources": [                      # 代理来源列表
        "github",
        "proxylist",
        "free-proxy-list",
        "cool-proxy"
    ]
}
```

## 网站解析器

系统支持多个网站的解析，包括：

1. **知乎**：爬取知乎专栏文章
2. **CSDN**：爬取CSDN博客文章
3. **简书**：爬取简书文章
4. **新浪新闻**：爬取新浪新闻文章
5. **通用解析器**：适用于大多数含有文章的网站

可以通过`config.json`中的`spider.website`和`spider.base_url`配置要爬取的网站。

## 贡献指南

欢迎贡献代码或提出改进建议！请遵循以下步骤：

1. Fork 仓库
2. 创建新分支：`git checkout -b feature-xyz`
3. 提交更改：`git commit -am 'Add feature xyz'`
4. 推送到分支：`git push origin feature-xyz`
5. 提交Pull Request

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。 