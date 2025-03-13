"""
检查HanLP是否可用
"""

try:
    import pyhanlp
    print('HanLP可用')
except ImportError:
    print('HanLP不可用，请安装：pip install pyhanlp') 