#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查jieba安装情况
"""

import jieba
import pkgutil

print('jieba版本:', jieba.__version__)
print('jieba路径:', jieba.__path__)
print('可用模块:')
for loader, name, is_pkg in pkgutil.iter_modules(jieba.__path__):
    print('  -', name)

try:
    import jieba.posseg
    print('成功导入jieba.posseg')
except ImportError as e:
    print('导入jieba.posseg失败:', e) 