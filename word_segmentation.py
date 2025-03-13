import pandas as pd
import jieba
import os

# 确保输出目录存在
output_dir = 'data/processed'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# 读取CSV文件
print("正在读取文章数据...")
df = pd.read_csv('data/samples/all_articles.csv')

# 检查数据结构
print(f"数据集包含 {len(df)} 行和以下列: {df.columns.tolist()}")

# 假设文章内容在'content'列中，如果不是，请修改列名
content_column = 'content'  # 根据实际情况修改
if content_column not in df.columns:
    # 尝试找到可能包含文章内容的列
    possible_content_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in ['content', 'text', 'article', '内容', '正文'])]
    if possible_content_columns:
        content_column = possible_content_columns[0]
        print(f"使用 '{content_column}' 列作为文章内容")
    else:
        # 如果找不到，使用第一个非数值类型的列
        for col in df.columns:
            if df[col].dtype == 'object':
                content_column = col
                print(f"使用 '{content_column}' 列作为文章内容")
                break

# 分词处理函数
def segment_text(text):
    if pd.isna(text):
        return ""
    # 使用jieba进行分词
    words = jieba.cut(str(text))
    # 将分词结果用空格连接
    return ' '.join(words)

# 应用分词处理
print("正在进行分词处理...")
df['segmented_content'] = df[content_column].apply(segment_text)

# 保存处理后的数据
output_file = os.path.join(output_dir, 'all_articles_segmented.csv')
df.to_csv(output_file, index=False)
print(f"分词处理完成，结果已保存至 {output_file}")

# 输出一些统计信息
total_articles = len(df)
avg_words_per_article = df['segmented_content'].str.split().str.len().mean()
print(f"总共处理了 {total_articles} 篇文章")
print(f"平均每篇文章分词数量: {avg_words_per_article:.2f}")

# 展示前5篇文章的分词结果示例
print("\n前5篇文章的分词结果示例:")
for i, (original, segmented) in enumerate(zip(df[content_column].head(), df['segmented_content'].head())):
    print(f"\n文章 {i+1}:")
    print(f"原文(前100字符): {str(original)[:100]}...")
    print(f"分词结果(前100字符): {segmented[:100]}...") 