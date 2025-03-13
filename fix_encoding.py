import pandas as pd
import sys

def fix_encoding(input_file, output_file):
    try:
        # 尝试不同的编码方式读取文件
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'gb18030']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(input_file, encoding=encoding)
                print(f"成功使用 {encoding} 编码读取文件")
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"使用 {encoding} 读取时发生错误: {str(e)}")
                continue
        
        if df is None:
            print("无法使用任何编码方式读取文件")
            return False
        
        # 保存为UTF-8-SIG格式
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"文件已成功保存为 {output_file}")
        return True
        
    except Exception as e:
        print(f"处理文件时发生错误: {str(e)}")
        return False

if __name__ == "__main__":
    input_file = "data/articles.csv"
    output_file = "data/articles_fixed.csv"
    
    if fix_encoding(input_file, output_file):
        print("编码修复完成！")
    else:
        print("编码修复失败！") 